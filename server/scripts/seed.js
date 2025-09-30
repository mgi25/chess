import db from '../db.js';
import { playerSeedData, initialPairings } from '../seed-data.js';
import { RESULT } from '../../shared/constants.js';

const seedTransaction = db.transaction(() => {
  db.exec('DELETE FROM matches; DELETE FROM rounds; DELETE FROM players;');

  const insertPlayer = db.prepare(`
    INSERT INTO players (id, name, full_name, contact, department, register_number, seed, add_score)
    VALUES (@id, @name, @fullName, @contact, @department, @registerNumber, @seed, 0)
  `);
  playerSeedData.forEach((player) => {
    insertPlayer.run(player);
  });

  const roundResult = db.prepare('INSERT INTO rounds (round_number) VALUES (?)').run(1);
  const roundId = roundResult.lastInsertRowid;

  const insertMatch = db.prepare(`
    INSERT INTO matches (round_id, table_number, player1_id, player2_id, result)
    VALUES (?, ?, ?, ?, ?)
  `);

  initialPairings.forEach((pairing) => {
    const result = pairing.player2 ? RESULT.UNPLAYED : RESULT.BYE;
    insertMatch.run(roundId, pairing.table, pairing.player1, pairing.player2 ?? null, result);
  });
});

export function seedDatabase() {
  seedTransaction();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedDatabase();
  console.log('Database seeded successfully.');
}
