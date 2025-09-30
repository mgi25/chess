import { RESULT } from './constants.js';

export function gatherOpponentHistory(players, rounds) {
  const history = new Map(players.map((player) => [player.id, new Set()]));

  rounds.forEach((round) => {
    round.pairings.forEach((pairing) => {
      if (!pairing.player1 || !pairing.player2) return;
      history.get(pairing.player1)?.add(pairing.player2);
      history.get(pairing.player2)?.add(pairing.player1);
    });
  });

  return history;
}

export function recalculateStandings(players, rounds) {
  const statsMap = new Map();
  const playersById = new Map(players.map((player) => [player.id, player]));

  players.forEach((player) => {
    statsMap.set(player.id, {
      id: player.id,
      seed: player.seed,
      name: player.fullName || player.name,
      displayName: player.name,
      addScore: player.addScore ?? 0,
      opponents: new Set(),
      wins: 0,
      losses: 0,
      draws: 0,
      byes: 0,
      basePoints: 0
    });
  });

  rounds.forEach((round) => {
    round.pairings.forEach((pairing) => {
      const { player1, player2, result } = pairing;
      if (!statsMap.has(player1)) return;
      const p1Stats = statsMap.get(player1);
      const p2Stats = player2 ? statsMap.get(player2) : null;

      if (player2) {
        p1Stats.opponents.add(player2);
        if (p2Stats) {
          p2Stats.opponents.add(player1);
        }
      }

      switch (result) {
        case RESULT.PLAYER1:
          p1Stats.wins += 1;
          p1Stats.basePoints += 1;
          if (p2Stats) {
            p2Stats.losses += 1;
          }
          break;
        case RESULT.PLAYER2:
          if (p2Stats) {
            p2Stats.wins += 1;
            p2Stats.basePoints += 1;
          }
          p1Stats.losses += 1;
          break;
        case RESULT.DRAW:
          p1Stats.draws += 1;
          p1Stats.basePoints += 0.5;
          if (p2Stats) {
            p2Stats.draws += 1;
            p2Stats.basePoints += 0.5;
          }
          break;
        case RESULT.BYE:
          p1Stats.byes += 1;
          p1Stats.basePoints += 1;
          p1Stats.opponents.add('Bye');
          break;
        default:
          break;
      }
    });
  });

  const standings = Array.from(statsMap.values()).map((stats) => {
    const gamesPlayed = stats.wins + stats.losses + stats.draws + stats.byes;
    const totalPoints = stats.basePoints + stats.addScore;
    const winPercent = gamesPlayed === 0 ? 0 : (stats.basePoints / gamesPlayed) * 100;
    const opponentSummaries = Array.from(stats.opponents).map((opponent) => {
      if (opponent === 'Bye') {
        return 'Bye';
      }
      const opponentData = playersById.get(opponent);
      return opponentData ? `${opponentData.name} (#${opponentData.id})` : `#${opponent}`;
    });

    return {
      ...stats,
      gamesPlayed,
      totalPoints,
      winPercent,
      opponentSummaries
    };
  });

  standings.sort((a, b) => {
    if (b.totalPoints !== a.totalPoints) {
      return b.totalPoints - a.totalPoints;
    }
    if (b.basePoints !== a.basePoints) {
      return b.basePoints - a.basePoints;
    }
    if (b.winPercent !== a.winPercent) {
      return b.winPercent - a.winPercent;
    }
    return a.seed - b.seed;
  });

  return standings;
}

export function canGenerateNextRound(rounds) {
  if (!rounds.length) return false;
  return rounds.every((round) =>
    round.pairings.every((pairing) => pairing.result !== RESULT.UNPLAYED)
  );
}

export function createSwissPairings(playerIds, opponentHistory) {
  const pool = [...playerIds];
  let byePlayer = null;

  if (pool.length % 2 === 1) {
    byePlayer = pool.pop();
  }

  let solution = null;

  function backtrack(available, currentPairs) {
    if (available.length === 0) {
      solution = currentPairs;
      return true;
    }

    const [player, ...rest] = available;

    for (let i = 0; i < rest.length; i += 1) {
      const opponent = rest[i];
      if (opponentHistory.get(player)?.has(opponent)) {
        continue;
      }
      const remaining = rest.slice(0, i).concat(rest.slice(i + 1));
      if (backtrack(remaining, [...currentPairs, [player, opponent]])) {
        return true;
      }
    }

    for (let i = 0; i < rest.length; i += 1) {
      const opponent = rest[i];
      const remaining = rest.slice(0, i).concat(rest.slice(i + 1));
      if (backtrack(remaining, [...currentPairs, [player, opponent]])) {
        return true;
      }
    }

    return false;
  }

  if (!backtrack(pool, [])) {
    throw new Error('Unable to create Swiss pairings without conflicts.');
  }

  const finalPairs = solution ? [...solution] : [];
  if (byePlayer !== null) {
    finalPairs.push([byePlayer]);
  }
  return finalPairs;
}
