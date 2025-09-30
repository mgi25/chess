# Swiss Chess League Manager

This repository contains a browser-based recreation of the original `SwissChessLeaguev4.xlsm` workbook along with a complementary Express/SQLite backend. The service keeps the same player roster, Round 1 pairings, and tournament rules while providing REST APIs, data persistence, and a modern interface for driving the tournament.

## Requirements

- [Node.js](https://nodejs.org/) 18 or later
- npm (ships with Node.js)

## Installation & database setup

From the repository root run:

```bash
npm install
npm run migrate
npm run seed
```

The first command installs the backend and tooling dependencies. `npm run migrate` creates the SQLite schema in `server/data/tournament.sqlite`, and `npm run seed` loads the historical player roster plus the Round 1 pairings from the workbook.

## Running the application locally

Start the backend API (defaults to port 4000):

```bash
npm run start:server
```

In a second terminal start the static front-end server (defaults to port 4173):

```bash
npm run start:client
```

Open [http://localhost:4173](http://localhost:4173) in your browser. The page is preconfigured to call the backend at `http://localhost:4000/api`, but you can override the base URL by setting `window.APP_API_BASE` before loading `src/app.js`.

## Verifying persistence

1. With both servers running, open the app and record a few match results or add manual score adjustments.
2. Refresh the page or close and reopen the browser tab.
3. The previously entered results and adjustments will reload from the SQLite database via the backend API, confirming that tournament state now survives page refreshes.

## Available features

- ✅ REST backend exposing players, rounds, matches, standings, and adjustment endpoints with Swiss pairing enforcement.
- ✅ Rules panel reproducing the explanatory text from the `Rules` worksheet.
- ✅ Player directory containing the full contact list from the `Matches` worksheet.
- ✅ Standings table with live win/draw/loss tallies, manual score adjustments, opponent history, and persisted totals.
- ✅ Interactive match cards for every recorded round with automatic bye handling.
- ✅ One-click generation of future rounds using a Swiss pairing algorithm that reuses the workbook logic while preventing rematches.

## Operational tips

- Run `npm run reset` to drop all rounds/results and reseed the database back to the workbook starting state.
- Always ensure every match in the current round has a recorded result before asking the backend to generate the next round.
- If an odd number of players needs pairing, the backend automatically awards a bye worth 1 point and prevents players from receiving multiple byes.

Enjoy running your Swiss tournaments on the web! 🏆
