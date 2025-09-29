# Swiss League Web App — Single‑file Flask app
# -----------------------------------------------------------
# Purpose: Replicates an Excel‑style Swiss chess league workflow
# (Players → Rounds/Pairings → Live Results → Standings → Export)
#
# Features
# - Manage players (add/edit/delete/import CSV)
# - Generate Swiss pairings for the next round (group by score, avoid rematches, color balance, bye handling)
# - Live match tracking: start / enter result / finish
# - Auto standings with tiebreaks (Buchholz, Sonneborn‑Berger, wins)
# - Export snapshot to XLSX with multiple sheets (Players, Rounds, Standings)
# - Looks/behaves like a clean, grid‑first “Excel sheet” but in the browser
#
# Quick start
# 1) pip install -r requirements.txt
#    (Flask, SQLAlchemy, pandas, xlsxwriter)
# 2) python app.py
# 3) Open http://127.0.0.1:5000
#
# NOTE: This is a pragmatic Swiss pairing engine that satisfies common
# tournament needs. For FIDE‑strict edge cases you may need deeper constraints
# (forbidden pair lists, floaters across multiple rounds, fine‑grained color
# history rules, accelerated pairings, etc.). Those can be added in the
# `make_swiss_pairings()` function.
# -----------------------------------------------------------

from __future__ import annotations
import csv
import io
import math
import os
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash
from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey,
                        create_engine, UniqueConstraint, func)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session
import pandas as pd
import xlsxwriter

# ---------------------------------
# Flask / DB setup
# ---------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///swiss.db")
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


# ---------------------------------
# Models
# ---------------------------------
class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    rating = Column(Integer, default=1200)
    club = Column(String, default="")
    bye_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Player {self.id} {self.name} ({self.rating})>"


class Round(Base):
    __tablename__ = "rounds"
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False, unique=True)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    pairings = relationship("Pairing", back_populates="round", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Round {self.number} locked={self.is_locked}>"


class Pairing(Base):
    __tablename__ = "pairings"
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    board_no = Column(Integer, nullable=False)
    white_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    black_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    # result values: "1-0", "0-1", "0.5-0.5", "BYE", "*" (ongoing/not set)
    result = Column(String, default="*")
    started = Column(Boolean, default=False)
    finished = Column(Boolean, default=False)

    round = relationship("Round", back_populates="pairings")
    white = relationship("Player", foreign_keys=[white_id])
    black = relationship("Player", foreign_keys=[black_id])

    __table_args__ = (
        UniqueConstraint("round_id", "board_no", name="uq_round_board"),
    )

    def __repr__(self):
        return f"<Pairing R{self.round_id} B{self.board_no} {self.white_id} vs {self.black_id} {self.result}>"


Base.metadata.create_all(engine)


# ---------------------------------
# Helpers: scoring, color history, opponents, tiebreaks
# ---------------------------------
Result = str  # alias

SCORE_MAP = {
    "1-0": (1.0, 0.0),
    "0-1": (0.0, 1.0),
    "0.5-0.5": (0.5, 0.5),
    "BYE": (1.0, 0.0),  # white gets a bye point
}


def get_all_rounds(sess) -> List[Round]:
    return sess.query(Round).order_by(Round.number.asc()).all()


def get_current_round_number(sess) -> int:
    r = sess.query(func.max(Round.number)).scalar()
    return int(r or 0)


def get_scores(sess) -> Dict[int, float]:
    """Compute total points per player from all finished results."""
    scores: Dict[int, float] = {p.id: 0.0 for p in sess.query(Player).all()}
    pairings: List[Pairing] = sess.query(Pairing).all()
    for pr in pairings:
        if pr.result in SCORE_MAP and pr.finished:
            w, b = pr.white_id, pr.black_id
            ws, bs = SCORE_MAP[pr.result]
            if pr.result == "BYE":
                # BYE is recorded as white_id gets 1 point, black_id is None
                scores[w] = scores.get(w, 0.0) + ws
            else:
                scores[w] = scores.get(w, 0.0) + ws
                scores[b] = scores.get(b, 0.0) + bs
    return scores


def get_color_history(sess) -> Dict[int, Tuple[int, int]]:
    """Return {player_id: (white_count, black_count)}"""
    hist = {p.id: (0, 0) for p in sess.query(Player).all()}
    for pr in sess.query(Pairing).all():
        if pr.white_id:
            w = hist[pr.white_id]
            hist[pr.white_id] = (w[0] + 1, w[1])
        if pr.black_id:
            b = hist[pr.black_id]
            hist[pr.black_id] = (b[0], b[1] + 1)
    return hist


def opponents_map(sess) -> Dict[int, set]:
    om: Dict[int, set] = {p.id: set() for p in sess.query(Player).all()}
    for pr in sess.query(Pairing).all():
        if pr.white_id and pr.black_id:
            om[pr.white_id].add(pr.black_id)
            om[pr.black_id].add(pr.white_id)
    return om


def tiebreaks(sess) -> Dict[int, Dict[str, float]]:
    """Calculate Buchholz and Sonneborn‑Berger for each player."""
    scores = get_scores(sess)
    om = opponents_map(sess)

    # Buchholz: sum of opponents' scores
    buchholz: Dict[int, float] = {pid: 0.0 for pid in scores}
    sb: Dict[int, float] = {pid: 0.0 for pid in scores}

    # Build quick lookup of results by (round, white, black)
    by_players = []
    for pr in sess.query(Pairing).filter(Pairing.finished == True).all():
        by_players.append(pr)

    for pid in scores:
        # Buchholz
        buchholz[pid] = sum(scores.get(opp, 0.0) for opp in om.get(pid, ()))

        # SB: add opponent score for wins + half for draws
        sb_total = 0.0
        for pr in by_players:
            if pr.white_id == pid and pr.result in SCORE_MAP:
                ws, bs = SCORE_MAP[pr.result]
                opp = pr.black_id
                if ws == 1.0:
                    sb_total += scores.get(opp, 0.0)
                elif ws == 0.5:
                    sb_total += 0.5 * scores.get(opp, 0.0)
            elif pr.black_id == pid and pr.result in SCORE_MAP:
                ws, bs = SCORE_MAP[pr.result]
                opp = pr.white_id
                if bs == 1.0:
                    sb_total += scores.get(opp, 0.0)
                elif bs == 0.5:
                    sb_total += 0.5 * scores.get(opp, 0.0)
        sb[pid] = sb_total

    return {pid: {"buchholz": buchholz[pid], "sb": sb[pid]} for pid in scores}


# ---------------------------------
# Swiss pairing engine (pragmatic)
# ---------------------------------
@dataclass
class Seed:
    pid: int
    name: str
    rating: int
    score: float
    white_ct: int
    black_ct: int

    @property
    def color_balance(self) -> int:
        return self.white_ct - self.black_ct  # prefer closer to 0


def make_swiss_pairings(sess, round_number: int) -> List[Tuple[Optional[int], Optional[int]]]:
    """Return list of (white_id, black_id) for the next round, including BYE as (pid, None).
    - Groups players by current score, breaks ties by rating, then id.
    - Avoids rematches where possible.
    - Tries to balance colors: player with lower white_count is more likely to get white.
    - Assigns one BYE if needed to the lowest‑score player who has not had a bye.
    """
    players = sess.query(Player).all()
    if not players:
        return []

    scores = get_scores(sess)
    colors = get_color_history(sess)
    opps = opponents_map(sess)

    # Seed list
    seeds: List[Seed] = []
    for p in players:
        s = Seed(
            pid=p.id,
            name=p.name,
            rating=p.rating or 1200,
            score=round(float(scores.get(p.id, 0.0)), 2),
            white_ct=colors.get(p.id, (0, 0))[0],
            black_ct=colors.get(p.id, (0, 0))[1],
        )
        seeds.append(s)

    # Sort by (score desc, rating desc, id asc)
    seeds.sort(key=lambda x: (-x.score, -x.rating, x.pid))

    # Handle bye if odd
    bye_pid: Optional[int] = None
    if len(seeds) % 2 == 1:
        # choose lowest score, fewest byes, then lowest rating
        # (we search from the end of the sorted list)
        candidates = list(reversed(seeds))
        # filter players with no prior bye if possible
        with_byecount = {p.id: p.bye_count for p in sess.query(Player).all()}
        no_bye = [s for s in candidates if with_byecount.get(s.pid, 0) == 0]
        pool = no_bye if no_bye else candidates
        pool.sort(key=lambda s: (s.score, s.rating))
        bye_pid = pool[0].pid
        # Remove the bye player from pairing pool
        seeds = [s for s in seeds if s.pid != bye_pid]

    # Group by score buckets
    buckets: Dict[float, List[Seed]] = {}
    for s in seeds:
        buckets.setdefault(s.score, []).append(s)
    for sc in buckets:
        buckets[sc].sort(key=lambda x: (-x.rating, x.pid))

    pairings: List[Tuple[Optional[int], Optional[int]]] = []
    used: set = set()

    # Helper to pick partner inside same bucket with constraints
    def pick_partner(i_seed: Seed, group: List[Seed]) -> Optional[Seed]:
        for cand in group:
            if cand.pid in used or cand.pid == i_seed.pid:
                continue
            if cand.pid in opps.get(i_seed.pid, set()):
                continue  # avoid rematch
            return cand
        # fallback: allow rematch if unavoidable
        for cand in group:
            if cand.pid in used or cand.pid == i_seed.pid:
                continue
            return cand
        return None

    # Try to pair within buckets first, then borrow from adjacent buckets if odd
    remaining: List[Seed] = []
    sorted_scores = sorted(buckets.keys(), reverse=True)

    for sc in sorted_scores:
        group = buckets[sc]
        i = 0
        while i < len(group):
            if group[i].pid in used:
                i += 1
                continue
            a = group[i]
            partner = pick_partner(a, group)
            if not partner:
                remaining.append(a)
                used.add(a.pid)
                i += 1
                continue
            # mark both used
            used.add(a.pid)
            used.add(partner.pid)

            # color choice: give white to who played fewer whites; tie → higher rating gets black last time
            a_balance = a.color_balance
            b_balance = partner.color_balance
            white_id, black_id = (a.pid, partner.pid)
            if a_balance > b_balance:
                # a has had more whites; give white to partner
                white_id, black_id = (partner.pid, a.pid)
            pairings.append((white_id, black_id))
            i += 1

    # Cross‑bucket pairing for any leftover
    leftovers = [s for s in seeds if s.pid not in used]
    leftovers.extend(remaining)
    leftovers = [s for s in leftovers if s.pid not in used]

    # Simple greedy across leftovers
    leftovers.sort(key=lambda x: (-x.score, -x.rating, x.pid))
    while leftovers:
        a = leftovers.pop(0)
        # pick the first available candidate
        cand_idx = None
        for j, b in enumerate(leftovers):
            if b.pid not in opps.get(a.pid, set()):
                cand_idx = j
                break
        if cand_idx is None:
            cand_idx = 0  # unavoidable rematch
        b = leftovers.pop(cand_idx)
        # color preference as above
        white_id, black_id = (a.pid, b.pid)
        if a.color_balance > b.color_balance:
            white_id, black_id = (b.pid, a.pid)
        pairings.append((white_id, black_id))

    # Insert bye as (pid, None)
    if bye_pid is not None:
        pairings.append((bye_pid, None))

    # Persist Round & Pairings
    nxt = get_current_round_number(sess) + 1
    rnd = Round(number=nxt)
    sess.add(rnd)
    sess.flush()

    # board numbers: 1..N, keep bye at last board
    for i, (w, b) in enumerate(pairings, 1):
        pr = Pairing(round_id=rnd.id, board_no=i, white_id=w, black_id=b)
        if b is None:
            pr.result = "BYE"
            pr.started = True
            pr.finished = True
            # increment player's bye_count
            pl = sess.get(Player, w)
            pl.bye_count += 1
        sess.add(pr)

    sess.commit()
    return pairings


# ---------------------------------
# UI templates (inline Jinja)
# ---------------------------------
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Swiss League</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: Inter, ui-sans-serif, system-ui; }
    .card { @apply bg-white/90 dark:bg-slate-900/70 backdrop-blur rounded-2xl shadow p-6; }
    .gridhead { @apply text-xs uppercase tracking-wider text-slate-500; }
    .btn { @apply inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold bg-slate-900 text-white hover:bg-slate-700; }
    .btn-sec { @apply inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold bg-slate-200 hover:bg-slate-300 text-slate-800; }
    .tag { @apply text-xs px-2 py-0.5 rounded-full; }
  </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-200/80 dark:from-slate-950 dark:to-slate-900 text-slate-900 dark:text-slate-100">
  <div class="max-w-7xl mx-auto p-6 space-y-6">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl md:text-3xl font-bold">Swiss League</h1>
      <nav class="flex gap-2">
        <a class="btn-sec" href="{{ url_for('index') }}">Standings</a>
        <a class="btn-sec" href="{{ url_for('players') }}">Players</a>
        <a class="btn-sec" href="{{ url_for('rounds') }}">Rounds</a>
        <a class="btn" href="{{ url_for('export_xlsx') }}">Export XLSX</a>
      </nav>
    </header>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
      <div class="space-y-2">
        {% for m in messages %}
          <div class="card border border-amber-300/60 bg-amber-50 text-amber-900">{{ m }}</div>
        {% endfor %}
      </div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
    <footer class="text-xs text-slate-500 py-6">Built for Excel‑style Swiss tournaments.</footer>
  </div>
</body>
</html>
"""

INDEX_HTML = """
{% extends 'base.html' %}
{% block content %}
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <section class="lg:col-span-2 card">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold">Standings</h2>
      <form method="post" action="{{ url_for('generate_round') }}">
        <button class="btn" {% if not can_generate %}disabled class="opacity-50"{% endif %}>Generate Round {{ next_round }}</button>
      </form>
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="gridhead">
          <tr class="text-left">
            <th class="p-2">#</th>
            <th class="p-2">Player</th>
            <th class="p-2">Rating</th>
            <th class="p-2">Pts</th>
            <th class="p-2">Buchholz</th>
            <th class="p-2">Sonneborn‑Berger</th>
            <th class="p-2">Wins</th>
          </tr>
        </thead>
        <tbody>
          {% for row in table %}
          <tr class="border-t border-slate-200/60">
            <td class="p-2">{{ loop.index }}</td>
            <td class="p-2 font-medium">{{ row.name }}</td>
            <td class="p-2">{{ row.rating }}</td>
            <td class="p-2 font-semibold">{{ '%.1f'|format(row.score) }}</td>
            <td class="p-2">{{ '%.1f'|format(row.buchholz) }}</td>
            <td class="p-2">{{ '%.1f'|format(row.sb) }}</td>
            <td class="p-2">{{ row.wins }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
    <ul class="space-y-2">
      <li><a class="btn-sec" href="{{ url_for('players') }}">Add/Import Players</a></li>
      <li><a class="btn-sec" href="{{ url_for('rounds') }}">Enter Results</a></li>
      <li><a class="btn-sec" href="{{ url_for('export_xlsx') }}">Export XLSX Snapshot</a></li>
    </ul>
    <div class="mt-6 text-sm text-slate-600 dark:text-slate-400">
      <p>This mirrors your Excel flow: maintain Players → generate Round pairings → enter results → view real‑time Standings → export.</p>
    </div>
  </section>
</div>
{% endblock %}
"""

PLAYERS_HTML = """
{% extends 'base.html' %}
{% block content %}
<section class="card">
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-xl font-semibold">Players</h2>
    <form method="post" class="flex gap-2">
      <input type="text" name="name" placeholder="Name" class="px-3 py-2 rounded-xl border" required>
      <input type="number" name="rating" placeholder="Rating" class="px-3 py-2 rounded-xl border" value="1200">
      <input type="text" name="club" placeholder="Club (optional)" class="px-3 py-2 rounded-xl border">
      <button class="btn" type="submit">Add</button>
    </form>
  </div>

  <div class="mb-6">
    <form method="post" action="{{ url_for('import_csv') }}" enctype="multipart/form-data" class="flex items-center gap-3">
      <label class="font-semibold">Import CSV</label>
      <input type="file" name="file" accept=".csv" class="px-3 py-2 rounded-xl border" required>
      <button class="btn" type="submit">Upload</button>
      <span class="text-xs text-slate-500">Headers: name,rating,club</span>
    </form>
  </div>

  <div class="overflow-x-auto">
    <table class="min-w-full text-sm">
      <thead class="gridhead">
        <tr class="text-left">
          <th class="p-2">ID</th><th class="p-2">Name</th><th class="p-2">Rating</th><th class="p-2">Club</th><th class="p-2">Byes</th><th class="p-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for p in players %}
        <tr class="border-t border-slate-200/60">
          <td class="p-2">{{ p.id }}</td>
          <td class="p-2 font-medium">{{ p.name }}</td>
          <td class="p-2">{{ p.rating }}</td>
          <td class="p-2">{{ p.club }}</td>
          <td class="p-2">{{ p.bye_count }}</td>
          <td class="p-2">
            <a class="btn-sec" href="{{ url_for('delete_player', pid=p.id) }}" onclick="return confirm('Delete player?')">Delete</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
"""

ROUNDS_HTML = """
{% extends 'base.html' %}
{% block content %}
<section class="card space-y-6">
  <div class="flex items-center justify-between">
    <h2 class="text-xl font-semibold">Rounds & Pairings</h2>
    <form method="post" action="{{ url_for('generate_round') }}">
      <button class="btn">Generate Round {{ next_round }}</button>
    </form>
  </div>

  {% for r in rounds %}
  <div class="border rounded-2xl p-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="font-semibold">Round {{ r.number }}</h3>
      <span class="tag bg-slate-200 text-slate-800">{{ r.pairings|length }} boards</span>
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="gridhead">
          <tr class="text-left">
            <th class="p-2">Board</th>
            <th class="p-2">White</th>
            <th class="p-2">Black</th>
            <th class="p-2">Result</th>
            <th class="p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for pr in r.pairings|sort(attribute='board_no') %}
          <tr class="border-t border-slate-200/60">
            <td class="p-2">{{ pr.board_no }}</td>
            <td class="p-2">{{ pr.white.name if pr.white else '-' }}</td>
            <td class="p-2">{{ pr.black.name if pr.black else '-' }}</td>
            <td class="p-2 font-medium">{{ pr.result }}</td>
            <td class="p-2">
              {% if pr.black is none %}
                <span class="tag bg-emerald-100 text-emerald-700">BYE</span>
              {% else %}
              <form method="post" action="{{ url_for('update_result', pairing_id=pr.id) }}" class="flex flex-wrap items-center gap-2">
                <select name="result" class="px-2 py-1 rounded border">
                  <option value="*" {% if pr.result=='*' %}selected{% endif %}>*</option>
                  <option value="1-0" {% if pr.result=='1-0' %}selected{% endif %}>1‑0</option>
                  <option value="0-1" {% if pr.result=='0-1' %}selected{% endif %}>0‑1</option>
                  <option value="0.5-0.5" {% if pr.result=='0.5-0.5' %}selected{% endif %}>½‑½</option>
                </select>
                <label class="inline-flex items-center gap-1 text-xs"><input type="checkbox" name="started" value="1" {% if pr.started %}checked{% endif %}> started</label>
                <label class="inline-flex items-center gap-1 text-xs"><input type="checkbox" name="finished" value="1" {% if pr.finished %}checked{% endif %}> finished</label>
                <button class="btn-sec" type="submit">Save</button>
              </form>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endfor %}
</section>
{% endblock %}
"""

# Register templates
app.jinja_loader.mapping = {
    'base.html': BASE_HTML,
    'index.html': INDEX_HTML,
    'players.html': PLAYERS_HTML,
    'rounds.html': ROUNDS_HTML,
}


# ---------------------------------
# Routes
# ---------------------------------
@app.route("/")
def index():
    sess = SessionLocal()
    try:
        # standings
        scores = get_scores(sess)
        tb = tiebreaks(sess)

        # wins count
        win_count: Dict[int, int] = {pid: 0 for pid in scores}
        for pr in sess.query(Pairing).filter(Pairing.finished == True).all():
            if pr.result == "1-0":
                win_count[pr.white_id] = win_count.get(pr.white_id, 0) + 1
            elif pr.result == "0-1":
                win_count[pr.black_id] = win_count.get(pr.black_id, 0) + 1

        rows = []
        for p in sess.query(Player).all():
            rows.append({
                "pid": p.id,
                "name": p.name,
                "rating": p.rating,
                "score": scores.get(p.id, 0.0),
                "buchholz": tb.get(p.id, {}).get("buchholz", 0.0),
                "sb": tb.get(p.id, {}).get("sb", 0.0),
                "wins": win_count.get(p.id, 0)
            })

        rows.sort(key=lambda r: (-r["score"], -r["buchholz"], -r["sb"], -r["wins"], -r["rating"], r["pid"]))

        cur = get_current_round_number(sess)
        can_gen = sess.query(Player).count() >= 2
        return render_template_string(
            INDEX_HTML,
            table=rows,
            can_generate=can_gen,
            next_round=cur + 1
        )
    finally:
        sess.close()


@app.route("/players", methods=["GET", "POST"])
def players():
    sess = SessionLocal()
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            rating = int(request.form.get("rating", 1200))
            club = request.form.get("club", "").strip()
            if name:
                sess.add(Player(name=name, rating=rating, club=club))
                sess.commit()
                flash("Player added.")
            return redirect(url_for("players"))

        return render_template_string(PLAYERS_HTML, players=sess.query(Player).order_by(Player.id.asc()).all())
    finally:
        sess.close()


@app.route("/players/delete/<int:pid>")
def delete_player(pid: int):
    sess = SessionLocal()
    try:
        p = sess.get(Player, pid)
        if p:
            # Prevent deletion if already paired
            used = sess.query(Pairing).filter((Pairing.white_id == pid) | (Pairing.black_id == pid)).first()
            if used:
                flash("Cannot delete: player already has pairings.")
            else:
                sess.delete(p)
                sess.commit()
                flash("Player deleted.")
        return redirect(url_for("players"))
    finally:
        sess.close()


@app.route("/import_csv", methods=["POST"])
def import_csv():
    file = request.files.get("file")
    if not file:
        flash("No file uploaded.")
        return redirect(url_for("players"))
    sess = SessionLocal()
    try:
        content = file.stream.read().decode("utf-8")
        rdr = csv.DictReader(io.StringIO(content))
        count = 0
        for row in rdr:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            rating = int(row.get("rating") or 1200)
            club = (row.get("club") or "").strip()
            sess.add(Player(name=name, rating=rating, club=club))
            count += 1
        sess.commit()
        flash(f"Imported {count} players.")
    finally:
        sess.close()
    return redirect(url_for("players"))


@app.route("/rounds")
def rounds():
    sess = SessionLocal()
    try:
        return render_template_string(
            ROUNDS_HTML,
            rounds=get_all_rounds(sess),
            next_round=get_current_round_number(sess) + 1,
        )
    finally:
        sess.close()


@app.route("/generate_round", methods=["POST"]) 
def generate_round():
    sess = SessionLocal()
    try:
        pairings = make_swiss_pairings(sess, get_current_round_number(sess) + 1)
        flash(f"Generated {len(pairings)} pairings.")
    finally:
        sess.close()
    return redirect(url_for("rounds"))


@app.route("/update_result/<int:pairing_id>", methods=["POST"]) 
def update_result(pairing_id: int):
    sess = SessionLocal()
    try:
        pr = sess.get(Pairing, pairing_id)
        if not pr:
            flash("Pairing not found.")
            return redirect(url_for("rounds"))
        res = request.form.get("result", "*")
        started = request.form.get("started") == "1"
        finished = request.form.get("finished") == "1"
        if res not in {"*", "1-0", "0-1", "0.5-0.5"}:
            res = "*"
        pr.result = res if pr.black_id is not None else "BYE"
        pr.started = started or pr.result in {"1-0", "0-1", "0.5-0.5", "BYE"}
        pr.finished = finished or pr.result in {"1-0", "0-1", "0.5-0.5", "BYE"}
        sess.commit()
        flash("Result updated.")
    finally:
        sess.close()
    return redirect(url_for("rounds"))


@app.route("/export.xlsx")
def export_xlsx():
    sess = SessionLocal()
    try:
        # Build DataFrames
        players = sess.query(Player).order_by(Player.id.asc()).all()
        scores = get_scores(sess)
        tbs = tiebreaks(sess)

        standings_rows = []
        for p in players:
            standings_rows.append({
                "Player ID": p.id,
                "Name": p.name,
                "Rating": p.rating,
                "Score": scores.get(p.id, 0.0),
                "Buchholz": tbs.get(p.id, {}).get("buchholz", 0.0),
                "Sonneborn-Berger": tbs.get(p.id, {}).get("sb", 0.0),
            })
        standings_df = pd.DataFrame(standings_rows).sort_values(
            by=["Score", "Buchholz", "Sonneborn-Berger", "Rating", "Player ID"], ascending=[False, False, False, False, True]
        )

        rounds = sess.query(Round).order_by(Round.number.asc()).all()

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Players sheet
            pd.DataFrame([
                {"ID": p.id, "Name": p.name, "Rating": p.rating, "Club": p.club, "Byes": p.bye_count}
                for p in players
            ]).to_excel(writer, index=False, sheet_name="Players")

            # Round sheets
            for r in rounds:
                rows = []
                for pr in sorted(r.pairings, key=lambda x: x.board_no):
                    rows.append({
                        "Board": pr.board_no,
                        "White": pr.white.name if pr.white else "-",
                        "Black": pr.black.name if pr.black else "-",
                        "Result": pr.result,
                        "Started": pr.started,
                        "Finished": pr.finished,
                    })
                pd.DataFrame(rows).to_excel(writer, index=False, sheet_name=f"Round {r.number}")

            # Standings
            standings_df.to_excel(writer, index=False, sheet_name="Standings")

        output.seek(0)
        return send_file(output, as_attachment=True, download_name="SwissLeagueSnapshot.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    finally:
        sess.close()


# ---------------------------------
# Dev seed: add sample players if DB empty
# ---------------------------------
def maybe_seed():
    sess = SessionLocal()
    try:
        if sess.query(Player).count() == 0:
            for i, (n, r) in enumerate([
                ("Alpha", 1800), ("Bravo", 1700), ("Charlie", 1650), ("Delta", 1600),
                ("Echo", 1550), ("Foxtrot", 1500), ("Golf", 1450), ("Hotel", 1400),
            ], start=1):
                sess.add(Player(name=n, rating=r, club=""))
            sess.commit()
    finally:
        sess.close()


if __name__ == "__main__":
    maybe_seed()
    app.run(debug=True)
