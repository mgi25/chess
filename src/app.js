import { rulesText, players as playerSeedData, initialPairings } from './data.js';

const RESULT = {
  UNPLAYED: 'UNPLAYED',
  PLAYER1: 'PLAYER1',
  PLAYER2: 'PLAYER2',
  DRAW: 'DRAW',
  BYE: 'BYE'
};

const state = createInitialState();

function createInitialState() {
  const players = playerSeedData.map((player) => ({
    ...player,
    addScore: 0,
    history: []
  }));

  const rounds = [
    {
      roundNumber: 1,
      pairings: initialPairings.map((pairing) => ({
        ...pairing,
        result: RESULT.UNPLAYED
      }))
    }
  ];

  return { players, rounds };
}

function resetTournament() {
  const fresh = createInitialState();
  state.players = fresh.players;
  state.rounds = fresh.rounds;
  renderApp();
}

function createElement(tag, options = {}, ...children) {
  const el = document.createElement(tag);
  if (options.className) {
    el.className = options.className;
  }
  if (options.dataset) {
    Object.entries(options.dataset).forEach(([key, value]) => {
      el.dataset[key] = value;
    });
  }
  if (options.attrs) {
    Object.entries(options.attrs).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      el.setAttribute(key, value);
    });
  }
  if (options.textContent !== undefined) {
    el.textContent = options.textContent;
  }
  children.flat().forEach((child) => {
    if (child === null || child === undefined) return;
    el.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  });
  return el;
}

function getPlayerById(id) {
  return state.players.find((player) => player.id === id);
}

function gatherOpponentHistory() {
  const history = new Map();
  state.players.forEach((player) => {
    history.set(player.id, new Set());
  });

  state.rounds.forEach((round) => {
    round.pairings.forEach((pairing) => {
      if (!pairing.player1 || !pairing.player2) return;
      history.get(pairing.player1).add(pairing.player2);
      history.get(pairing.player2).add(pairing.player1);
    });
  });

  return history;
}

function recalculateStandings() {
  const statsMap = new Map();

  state.players.forEach((player) => {
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

  state.rounds.forEach((round) => {
    round.pairings.forEach((pairing) => {
      const { player1, player2, result } = pairing;
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
      const opponentData = getPlayerById(opponent);
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

function handleAddScoreChange(playerId, value) {
  const player = getPlayerById(playerId);
  if (!player) return;
  const numericValue = Number.parseFloat(value);
  player.addScore = Number.isFinite(numericValue) ? numericValue : 0;
  renderApp();
}

function setMatchResult(roundIndex, table, result) {
  const round = state.rounds[roundIndex];
  if (!round) return;
  const pairing = round.pairings.find((match) => match.table === table);
  if (!pairing) return;

  pairing.result = result;
  renderApp();
}

function canGenerateNextRound() {
  return state.rounds.every((round) => round.pairings.every((pairing) => pairing.result !== RESULT.UNPLAYED));
}

function generateNextRound() {
  if (!canGenerateNextRound()) {
    alert('Please enter results for every match before pairing the next round.');
    return;
  }

  const standings = recalculateStandings();
  const opponentHistory = gatherOpponentHistory();
  const playersToPair = standings.map((entry) => entry.id);
  const pairings = createSwissPairings(playersToPair, opponentHistory);
  const nextRoundNumber = state.rounds.length + 1;

  state.rounds.push({
    roundNumber: nextRoundNumber,
    pairings: pairings.map((pair, index) => {
      if (pair.length === 1) {
        return {
          table: index + 1,
          player1: pair[0],
          player2: null,
          player1Name: getPlayerById(pair[0]).name,
          player2Name: 'Bye',
          result: RESULT.BYE
        };
      }

      const [player1Id, player2Id] = pair;
      return {
        table: index + 1,
        player1: player1Id,
        player2: player2Id,
        player1Name: getPlayerById(player1Id).name,
        player2Name: getPlayerById(player2Id).name,
        result: RESULT.UNPLAYED
      };
    })
  });

  renderApp();
}

function createSwissPairings(playerIds, opponentHistory) {
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
      if (opponentHistory.get(player).has(opponent)) {
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

function renderRulesPanel() {
  const panel = createElement('section', { className: 'panel' });
  const title = createElement('h2', {}, createElement('span', { className: 'emoji' }, '📘'), 'Rules overview');
  const description = createElement('div', { className: 'rules-list' });

  description.append(
    ...rulesText.map((paragraph) => {
      if (paragraph === 'Swiss-style tournaments were developed to counteract this problem. Swiss-style tournaments generally have two rules:') {
        const intro = createElement('p', { textContent: paragraph });
        const list = createElement('ul');
        list.append(
          createElement('li', { textContent: 'Participants are paired with opponents who have similar scores.' }),
          createElement('li', { textContent: 'Participants cannot play the same opponent twice.' })
        );
        return createElement('div', {}, intro, list);
      }
      return createElement('p', { textContent: paragraph });
    })
  );

  panel.append(title, description);
  return panel;
}

function renderStandingsPanel() {
  const panel = createElement('section', { className: 'panel' });
  const header = createElement('div', { className: 'controls' });
  const title = createElement('h2', {}, createElement('span', { className: 'emoji' }, '🏆'), 'Tournament control centre');
  header.append(title);

  const controls = createElement('div', { className: 'controls' });
  const nextRoundButton = createElement('button', {
    className: 'primary',
    textContent: 'Generate next round',
    attrs: { type: 'button' }
  });
  nextRoundButton.disabled = !canGenerateNextRound();
  nextRoundButton.addEventListener('click', generateNextRound);

  const resetButton = createElement('button', {
    className: 'secondary',
    textContent: 'Reset tournament',
    attrs: { type: 'button' }
  });
  resetButton.addEventListener('click', resetTournament);

  controls.append(nextRoundButton, resetButton);

  const standings = recalculateStandings();

  const table = createElement('table');
  const thead = createElement('thead');
  const headerRow = createElement('tr');
  ['Rank', 'Player', 'Score', 'Adjust', 'Total', 'Win %', 'Opponents'].forEach((label) => {
    headerRow.append(createElement('th', { textContent: label }));
  });
  thead.append(headerRow);

  const tbody = createElement('tbody');
  standings.forEach((entry, index) => {
    const row = createElement('tr');
    row.append(createElement('td', { textContent: `#${index + 1}` }));
    row.append(
      createElement('td', {},
        createElement('div', { className: 'meta-grid' },
          createElement('strong', { textContent: `${entry.displayName} (ID ${entry.id})` }),
          createElement('span', { textContent: `Seed: ${entry.seed}` })
        )
      )
    );
    row.append(createElement('td', { textContent: entry.basePoints.toFixed(1) }));

    const input = createElement('input', {
      attrs: { type: 'number', step: '0.5', value: entry.addScore }
    });
    input.addEventListener('change', (event) => {
      handleAddScoreChange(entry.id, event.target.value);
    });
    row.append(createElement('td', {}, input));

    row.append(createElement('td', { textContent: entry.totalPoints.toFixed(1) }));
    row.append(createElement('td', { textContent: `${entry.winPercent.toFixed(1)}%` }));

    if (!entry.opponentSummaries.length) {
      row.append(createElement('td', { textContent: '—' }));
    } else {
      row.append(createElement('td', { textContent: entry.opponentSummaries.join(', ') }));
    }

    tbody.append(row);
  });

  table.append(thead, tbody);

  panel.append(header, controls, createElement('div', { className: 'table-wrapper' }, table), renderRoundsSection());
  return panel;
}

function renderRoundsSection() {
  const container = createElement('div', {});

  state.rounds.forEach((round, roundIndex) => {
    const completed = round.pairings.every((pairing) => pairing.result !== RESULT.UNPLAYED);
    const roundCard = createElement('div', { className: 'round-card' });
    const roundHeader = createElement('div', { className: 'round-header' });
    const title = createElement('h3', { textContent: `Round ${round.roundNumber}` });
    const status = createElement('span', {
      className: 'badge ' + (completed ? 'win' : ''),
      textContent: completed ? 'Completed' : 'Awaiting results'
    });

    roundHeader.append(title, status);
    roundCard.append(roundHeader);

    if (round.pairings.length === 0) {
      roundCard.append(createElement('div', { className: 'empty-state', textContent: 'No matches scheduled yet.' }));
    } else {
      round.pairings.forEach((pairing) => {
        roundCard.append(renderMatchRow(roundIndex, pairing));
      });
    }

    container.append(roundCard);
  });

  return container;
}

function renderMatchRow(roundIndex, pairing) {
  const { table, player1, player2, player1Name, player2Name, result } = pairing;
  const row = createElement('div', { className: 'match-row' });

  row.append(createElement('div', { className: 'table-id badge', textContent: `Table ${table}` }));

  const player1Info = getPlayerById(player1);
  const player2Info = player2 ? getPlayerById(player2) : null;

  const player1Block = createElement('div', { className: 'player' },
    createElement('span', { textContent: `${player1Name || (player1Info?.name ?? 'Player')} (#${player1})` }),
    createElement('span', { textContent: player1Info ? player1Info.department || '—' : '—' })
  );

  const player2Block = createElement('div', { className: 'player' },
    createElement('span', { textContent: player2 ? `${player2Name || (player2Info?.name ?? 'Player')} (#${player2})` : 'Bye' }),
    createElement('span', { textContent: player2Info ? player2Info.department || '—' : '—' })
  );

  const versus = createElement('div', { className: 'versus', textContent: 'vs' });

  const select = createElement('select', {
    className: 'match-result',
    attrs: { 'aria-label': `Result for table ${table}` }
  });
  [
    { value: RESULT.UNPLAYED, label: 'Not played' },
    { value: RESULT.PLAYER1, label: `${player1Name || 'Player 1'} wins` },
    { value: RESULT.DRAW, label: 'Draw' },
    { value: RESULT.PLAYER2, label: `${player2Name || 'Player 2'} wins` }
  ].forEach((option) => {
    if (!player2 && option.value === RESULT.PLAYER2) return;
    const optionEl = createElement('option', {
      attrs: { value: option.value },
      textContent: option.label
    });
    if (option.value === result) {
      optionEl.selected = true;
    }
    select.append(optionEl);
  });

  if (!player2) {
    select.disabled = true;
  }

  select.addEventListener('change', (event) => {
    setMatchResult(roundIndex, table, event.target.value);
  });

  row.append(player1Block, versus, player2Block, select);
  return row;
}

function renderDirectoryPanel() {
  const panel = createElement('section', { className: 'panel' });
  const title = createElement('h2', {}, createElement('span', { className: 'emoji' }, '📇'), 'Player directory');
  const wrapper = createElement('div', { className: 'table-wrapper' });
  const table = createElement('table');
  const headRow = createElement('tr');
  ['ID', 'Name', 'Contact', 'Department', 'Register no.'].forEach((label) => {
    headRow.append(createElement('th', { textContent: label }));
  });
  const thead = createElement('thead', {}, headRow);
  const tbody = createElement('tbody');

  [...state.players]
    .sort((a, b) => a.id - b.id)
    .forEach((player) => {
      const row = createElement('tr');
      row.append(
        createElement('td', { textContent: `#${player.id}` }),
        createElement('td', { textContent: player.name }),
        createElement('td', { textContent: player.contact || '—' }),
        createElement('td', { textContent: player.department || '—' }),
        createElement('td', { textContent: player.registerNumber || '—' })
      );
      tbody.append(row);
    });

  table.append(thead, tbody);
  wrapper.append(table);
  panel.append(title, wrapper);
  return panel;
}

function renderApp() {
  const root = document.getElementById('app');
  root.innerHTML = '';
  root.append(renderRulesPanel(), renderStandingsPanel(), renderDirectoryPanel());
}

renderApp();
