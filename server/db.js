import Database from 'better-sqlite3';
import { mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbDirectory = join(__dirname, 'data');
mkdirSync(dbDirectory, { recursive: true });
const dbPath = join(dbDirectory, 'tournament.sqlite');

const db = new Database(dbPath);
db.pragma('foreign_keys = ON');

export default db;
