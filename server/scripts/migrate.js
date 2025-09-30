import db from '../db.js';
import { RESULT } from '../../shared/constants.js';

const allowedResults = Object.values(RESULT)
  .map((value) => `'${value}'`)
  .join(', ');

db.exec(`
  CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    full_name TEXT,
    contact TEXT,
    department TEXT,
    register_number TEXT,
    seed INTEGER NOT NULL,
    add_score REAL NOT NULL DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_number INTEGER NOT NULL UNIQUE
  );

  CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    table_number INTEGER NOT NULL,
    player1_id INTEGER NOT NULL REFERENCES players(id),
    player2_id INTEGER REFERENCES players(id),
    result TEXT NOT NULL DEFAULT '${RESULT.UNPLAYED}',
    UNIQUE(round_id, table_number),
    CHECK (result IN (${allowedResults}))
  );
`);

console.log('Database migrations completed.');
