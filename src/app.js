import { RESULT } from '../shared/constants.js';

const API_BASE = (window.APP_API_BASE || `${window.location.origin.replace(/\/$/, '')}/api`).replace(/\/$/, '');

const state = {
  rules: [],
  players: [],
  rounds: [],
  standings: [],
  canGenerateNextRound: false
};

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Request failed');
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function refreshState() {
  const data = await fetchJSON(`${API_BASE}/state`);
  Object.assign(state, data);
  renderApp();
}

async function resetTournament() {
  await fetchJSON(`${API_BASE}/reset`, { method: 'POST' });
  await refreshState();
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

async function handleAddScoreChange(playerId, value) {
  const numericValue = Number.parseFloat(value);
  const payload = Number.isFinite(numericValue) ? numericValue : 0;
  await fetchJSON(`${API_BASE}/players/${playerId}/adjustment`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ addScore: payload })
  });
  await refreshState();
}

async function setMatchResult(matchId, result) {
  await fetchJSON(`${API_BASE}/matches/${matchId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result })
  });
  await refreshState();
}

async function generateNextRound() {
  try {
    await fetchJSON(`${API_BASE}/rounds`, { method: 'POST' });
    await refreshState();
  } catch (error) {
    alert(error.message || 'Unable to generate the next round.');
  }
}

function renderRulesPanel() {
  const panel = createElement('section', { className: 'panel' });
  const title = createElement('h2', {}, createElement('span', { className: 'emoji' }, '📘'), 'Rules overview');
  const description = createElement('div', { className: 'rules-list' });

  description.append(
    ...state.rules.map((paragraph) => {
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
  nextRoundButton.disabled = !state.canGenerateNextRound;
  nextRoundButton.addEventListener('click', generateNextRound);

  const resetButton = createElement('button', {
    className: 'secondary',
    textContent: 'Reset tournament',
    attrs: { type: 'button' }
  });
  resetButton.addEventListener('click', () => {
    if (confirm('Reset the tournament to the initial seeded state?')) {
      resetTournament().catch((error) => alert(error.message));
    }
  });

  controls.append(nextRoundButton, resetButton);

  const table = createElement('table');
  const thead = createElement('thead');
  const headerRow = createElement('tr');
  ['Rank', 'Player', 'Score', 'Adjust', 'Total', 'Win %', 'Opponents'].forEach((label) => {
    headerRow.append(createElement('th', { textContent: label }));
  });
  thead.append(headerRow);

  const tbody = createElement('tbody');
  state.standings.forEach((entry, index) => {
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
      handleAddScoreChange(entry.id, event.target.value).catch((error) => alert(error.message));
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

  state.rounds.forEach((round) => {
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
        roundCard.append(renderMatchRow(pairing));
      });
    }

    container.append(roundCard);
  });

  return container;
}

function renderMatchRow(pairing) {
  const { id, table, player1, player2, player1Name, player2Name, result } = pairing;
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
    setMatchResult(id, event.target.value).catch((error) => {
      alert(error.message);
      refreshState();
    });
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

function renderLoading() {
  const root = document.getElementById('app');
  root.innerHTML = '';
  root.append(createElement('div', { className: 'panel', textContent: 'Loading tournament data…' }));
}

renderLoading();
refreshState().catch((error) => {
  const root = document.getElementById('app');
  root.innerHTML = '';
  root.append(createElement('div', { className: 'panel', textContent: `Failed to load tournament data: ${error.message}` }));
});
