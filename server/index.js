import express from 'express';
import cors from 'cors';

import db from './db.js';
import { seedDatabase } from './scripts/seed.js';
import { RESULT } from '../shared/constants.js';
import { rulesText } from '../shared/rules.js';
import {
  gatherOpponentHistory,
  recalculateStandings,
  createSwissPairings,
  canGenerateNextRound
} from '../shared/tournament.js';

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

function getPlayers() {
  return db
    .prepare(
      `SELECT id, name, full_name AS fullName, contact, department, register_number AS registerNumber, seed, add_score AS addScore
       FROM players
       ORDER BY id`
    )
    .all();
}

function getRounds(players) {
  const playersById = new Map(players.map((player) => [player.id, player]));
  const rows = db
    .prepare(
      `SELECT r.id as roundId, r.round_number as roundNumber, m.id as matchId, m.table_number as tableNumber,
              m.player1_id as player1, m.player2_id as player2, m.result as result
       FROM rounds r
       LEFT JOIN matches m ON m.round_id = r.id
       ORDER BY r.round_number ASC, m.table_number ASC`
    )
    .all();

  const rounds = new Map();
  rows.forEach((row) => {
    if (!rounds.has(row.roundId)) {
      rounds.set(row.roundId, {
        id: row.roundId,
        roundNumber: row.roundNumber,
        pairings: []
      });
    }
    if (!row.matchId) {
      return;
    }
    const round = rounds.get(row.roundId);
    round.pairings.push({
      id: row.matchId,
      table: row.tableNumber,
      player1: row.player1,
      player2: row.player2,
      result: row.result,
      player1Name: playersById.get(row.player1)?.name ?? null,
      player2Name: row.player2 ? playersById.get(row.player2)?.name ?? null : 'Bye'
    });
  });

  return Array.from(rounds.values());
}

function getTournamentState() {
  const players = getPlayers();
  const rounds = getRounds(players);
  const standings = recalculateStandings(players, rounds);
  const nextRoundAvailable = canGenerateNextRound(rounds);

  return {
    rules: rulesText,
    players,
    rounds,
    standings,
    canGenerateNextRound: nextRoundAvailable
  };
}

app.get('/api/state', (req, res) => {
  res.json(getTournamentState());
});

app.get('/api/rules', (req, res) => {
  res.json({ rules: rulesText });
});

app.get('/api/players', (req, res) => {
  res.json({ players: getPlayers() });
});

app.get('/api/players/:id', (req, res) => {
  const player = db
    .prepare(
      `SELECT id, name, full_name AS fullName, contact, department, register_number AS registerNumber, seed, add_score AS addScore
       FROM players WHERE id = ?`
    )
    .get(Number(req.params.id));
  if (!player) {
    res.status(404).json({ message: 'Player not found' });
    return;
  }
  res.json(player);
});

app.put('/api/players/:id/adjustment', (req, res) => {
  const playerId = Number(req.params.id);
  const { addScore } = req.body;
  const numericValue = Number.parseFloat(addScore);
  const value = Number.isFinite(numericValue) ? numericValue : 0;
  const result = db.prepare('UPDATE players SET add_score = ? WHERE id = ?').run(value, playerId);
  if (result.changes === 0) {
    res.status(404).json({ message: 'Player not found' });
    return;
  }
  res.status(204).end();
});

app.get('/api/rounds', (req, res) => {
  const players = getPlayers();
  res.json({ rounds: getRounds(players) });
});

app.get('/api/matches', (req, res) => {
  const players = getPlayers();
  const rounds = getRounds(players);
  const matches = rounds.flatMap((round) =>
    round.pairings.map((pairing) => ({
      ...pairing,
      roundId: round.id,
      roundNumber: round.roundNumber
    }))
  );
  res.json({ matches });
});

app.put('/api/matches/:id', (req, res) => {
  const matchId = Number(req.params.id);
  const { result } = req.body;
  if (!Object.values(RESULT).includes(result)) {
    res.status(400).json({ message: 'Invalid result value' });
    return;
  }
  const match = db.prepare('SELECT player2_id FROM matches WHERE id = ?').get(matchId);
  if (!match) {
    res.status(404).json({ message: 'Match not found' });
    return;
  }
  if (match.player2_id === null && result !== RESULT.BYE) {
    res.status(400).json({ message: 'Bye matches must remain BYE' });
    return;
  }
  db.prepare('UPDATE matches SET result = ? WHERE id = ?').run(result, matchId);
  res.status(204).end();
});

app.get('/api/standings', (req, res) => {
  const players = getPlayers();
  const rounds = getRounds(players);
  res.json({ standings: recalculateStandings(players, rounds) });
});

app.post('/api/rounds', (req, res) => {
  const players = getPlayers();
  const rounds = getRounds(players);
  if (!canGenerateNextRound(rounds)) {
    res.status(400).json({ message: 'All matches must be completed before generating the next round.' });
    return;
  }

  const standings = recalculateStandings(players, rounds);
  const opponentHistory = gatherOpponentHistory(players, rounds);
  const playersToPair = standings.map((entry) => entry.id);
  let pairings;
  try {
    pairings = createSwissPairings(playersToPair, opponentHistory);
  } catch (error) {
    res.status(500).json({ message: error.message });
    return;
  }

  const nextRoundNumber = rounds.length + 1;
  const roundResult = db.prepare('INSERT INTO rounds (round_number) VALUES (?)').run(nextRoundNumber);
  const roundId = roundResult.lastInsertRowid;
  const insertMatch = db.prepare(
    'INSERT INTO matches (round_id, table_number, player1_id, player2_id, result) VALUES (?, ?, ?, ?, ?)'
  );
  const lastInsertStatement = db.prepare('SELECT last_insert_rowid() as id');

  const newPairings = pairings.map((pair, index) => {
    if (pair.length === 1) {
      insertMatch.run(roundId, index + 1, pair[0], null, RESULT.BYE);
      const player = players.find((p) => p.id === pair[0]);
      return {
        id: lastInsertStatement.get().id,
        table: index + 1,
        player1: pair[0],
        player2: null,
        result: RESULT.BYE,
        player1Name: player?.name ?? null,
        player2Name: 'Bye'
      };
    }

    const [player1, player2] = pair;
    insertMatch.run(roundId, index + 1, player1, player2, RESULT.UNPLAYED);
    const [player1Info, player2Info] = [player1, player2].map((id) => players.find((player) => player.id === id));
    return {
      id: lastInsertStatement.get().id,
      table: index + 1,
      player1,
      player2,
      result: RESULT.UNPLAYED,
      player1Name: player1Info?.name ?? null,
      player2Name: player2Info?.name ?? null
    };
  });

  res.status(201).json({
    round: {
      id: roundId,
      roundNumber: nextRoundNumber,
      pairings: newPairings
    }
  });
});

app.post('/api/reset', (req, res) => {
  seedDatabase();
  res.status(200).json({ message: 'Tournament reset to the initial state.' });
});

app.listen(PORT, () => {
  console.log(`Swiss Chess backend listening on port ${PORT}`);
});
