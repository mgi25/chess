# Swiss Chess League Manager

This repository now ships a browser-based recreation of the original `SwissChessLeaguev4.xlsm` workbook. It keeps the same player roster, Round 1 pairings, and tournament rules while adding a modern interface for entering results and generating additional Swiss rounds.

## Getting started

1. Start a local static file server from the repository root. For example, with Python installed you can run:
   ```bash
   python -m http.server 8000
   ```
2. Open your browser at [http://localhost:8000](http://localhost:8000) and load `index.html`.

No build tooling or external dependencies are required – everything runs directly in the browser.

## Features

- ✅ Rules panel reproducing the explanatory text from the `Rules` worksheet.
- ✅ Player directory containing the full contact list from the `Matches` worksheet.
- ✅ Standings table with live win/draw/loss tallies, manual score adjustments, and opponent history.
- ✅ Interactive match cards for every recorded round (Round 1 pre-loaded from the workbook).
- ✅ One-click generation of future rounds using a Swiss pairing algorithm that respects the “no rematches” constraint and uses the workbook’s random seeds as tie-breakers.

## Notes

- Results are stored in-memory. Refreshing the page resets the state to match the Excel workbook.
- When generating additional rounds, ensure all matches in the current schedule have recorded results.
- If an odd number of players ever needs to be paired, the UI will automatically assign a bye worth 1 point.

Enjoy running your Swiss tournaments on the web! 🏆
