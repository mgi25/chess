from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker, selectinload


# ---------------------------------------------------------------------------
# Flask / SQLAlchemy setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///swiss.db")
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False))
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    rating = Column(Integer, default=1200)
    club = Column(String, default="")
    bye_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    white_pairings = relationship(
        "Pairing",
        primaryjoin="Player.id==Pairing.white_id",
        back_populates="white",
        cascade="all,delete",
    )
    black_pairings = relationship(
        "Pairing",
        primaryjoin="Player.id==Pairing.black_id",
        back_populates="black",
        cascade="all,delete",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Player {self.id} {self.name} ({self.rating})>"


class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pairings = relationship("Pairing", back_populates="round", cascade="all,delete")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Round {self.number}>"

class Pairing(Base):
    __tablename__ = "pairings"
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    board_no = Column(Integer, nullable=False)
    white_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"))
    black_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"))
    result = Column(String, default="*")
    started = Column(Boolean, default=False)
    finished = Column(Boolean, default=False)

    round = relationship("Round", back_populates="pairings")
    white = relationship("Player", foreign_keys=[white_id], back_populates="white_pairings")
    black = relationship("Player", foreign_keys=[black_id], back_populates="black_pairings")

    __table_args__ = (UniqueConstraint("round_id", "board_no", name="uq_round_board"),)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Pairing R{self.round_id} B{self.board_no} {self.white_id} vs "
            f"{self.black_id} {self.result}>"
        )


Base.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
Result = str

SCORE_MAP: Dict[str, Tuple[float, float]] = {
    "1-0": (1.0, 0.0),
    "0-1": (0.0, 1.0),
    "0.5-0.5": (0.5, 0.5),
    "BYE": (1.0, 0.0),
}

ALLOWED_RESULTS = {"*", "1-0", "0-1", "0.5-0.5"}


def safe_rating(value: Optional[str], default: int = 1200) -> int:
def parse_bool_cell(value: object) -> bool:
    return text in {"1", "true", "yes", "y", "done", "finished", "x", "✓"}
def normalize_result(value: object) -> str:
def get_all_rounds(sess) -> List[Round]:
    return (
        sess.query(Round)
        .options(
            selectinload(Round.pairings).selectinload(Pairing.white),
            selectinload(Round.pairings).selectinload(Pairing.black),
        )
        .order_by(Round.number.asc())
        .all()
    )


def get_current_round_number(sess) -> int:
    value = sess.query(func.max(Round.number)).scalar()
    return int(value or 0)


def get_scores(sess) -> Dict[int, float]:
    scores: Dict[int, float] = {p.id: 0.0 for p in sess.query(Player).all()}
    for pr in sess.query(Pairing).all():
        if pr.result not in SCORE_MAP:
            continue
        white_score, black_score = SCORE_MAP[pr.result]
        if pr.white_id is not None:
            scores[pr.white_id] = scores.get(pr.white_id, 0.0) + white_score
        if pr.black_id is not None and pr.result != "BYE":
            scores[pr.black_id] = scores.get(pr.black_id, 0.0) + black_score
    return scores


def get_color_history(sess) -> Dict[int, Tuple[int, int]]:
    history: Dict[int, Tuple[int, int]] = {p.id: (0, 0) for p in sess.query(Player).all()}
    for pr in sess.query(Pairing).all():
        if pr.white_id:
            w_white, w_black = history.get(pr.white_id, (0, 0))
            history[pr.white_id] = (w_white + 1, w_black)
        if pr.black_id:
            b_white, b_black = history.get(pr.black_id, (0, 0))
            history[pr.black_id] = (b_white, b_black + 1)
    return history


def opponents_map(sess) -> Dict[int, set]:
    mapping: Dict[int, set] = {p.id: set() for p in sess.query(Player).all()}
    for pr in sess.query(Pairing).all():
        if pr.white_id and pr.black_id:
            mapping[pr.white_id].add(pr.black_id)
            mapping[pr.black_id].add(pr.white_id)
    return mapping


def tiebreaks(sess) -> Dict[int, Dict[str, float]]:
    scores = get_scores(sess)
    opponents = opponents_map(sess)

    buchholz: Dict[int, float] = {pid: 0.0 for pid in scores}
    sb: Dict[int, float] = {pid: 0.0 for pid in scores}

    for pid, opps in opponents.items():
        buchholz[pid] = sum(scores.get(opp, 0.0) for opp in opps)

    for pr in sess.query(Pairing).filter(Pairing.finished == True).all():  # noqa: E712
        if pr.white_id is None:
            continue
        if pr.result == "1-0" and pr.black_id is not None:
            sb[pr.white_id] += scores.get(pr.black_id, 0.0)
        elif pr.result == "0-1" and pr.black_id is not None:
            sb[pr.black_id] += scores.get(pr.white_id, 0.0)
        elif pr.result == "0.5-0.5" and pr.black_id is not None:
            sb[pr.white_id] += scores.get(pr.black_id, 0.0) / 2
            sb[pr.black_id] += scores.get(pr.white_id, 0.0) / 2

    return {pid: {"buchholz": buchholz.get(pid, 0.0), "sb": sb.get(pid, 0.0)} for pid in scores}



    for pr in sess.query(Pairing).filter(Pairing.finished == True).all():  # noqa: E712
        if pr.result == "1-0" and pr.white_id:
        elif pr.result == "0-1" and pr.black_id:

    rows: List[Dict[str, float]] = []
        rows.append(
            {
                "pid": p.id,
                "name": p.name,
                "rating": p.rating,
                "club": p.club,
                "score": round(float(scores.get(p.id, 0.0)), 2),
                "buchholz": round(float(tb.get(p.id, {}).get("buchholz", 0.0)), 2),
                "sb": round(float(tb.get(p.id, {}).get("sb", 0.0)), 2),
                "wins": wins.get(p.id, 0),
                "byes": p.bye_count,
            }
        )

    rows.sort(
        key=lambda r: (
            -r["score"],
            -r["buchholz"],
            -r["sb"],
            -r["wins"],
            -r["rating"],
            r["pid"],
        )
    )


        return self.white_ct - self.black_ct


def choose_bye(seeds: List[Seed]) -> Optional[int]:
    if len(seeds) % 2 == 0:
        return None
    candidates = sorted(seeds, key=lambda s: (s.bye_count, s.score, s.rating, s.pid))
    return candidates[0].pid if candidates else None


def make_swiss_pairings(sess, round_number: int) -> List[Tuple[int, Optional[int]]]:
    players = sess.query(Player).order_by(Player.id.asc()).all()
    existing_round = sess.query(Round).filter(Round.number == round_number).first()
    if existing_round:
        return []

    opponents = opponents_map(sess)

    seeds: List[Seed] = []
    for p in players:
        seeds.append(
            Seed(
                pid=p.id,
                name=p.name,
                rating=p.rating or 1200,
                score=round(float(scores.get(p.id, 0.0)), 2),
                white_ct=colors.get(p.id, (0, 0))[0],
                black_ct=colors.get(p.id, (0, 0))[1],
                bye_count=p.bye_count,
            )

    seeds.sort(key=lambda s: (-s.score, -s.rating, s.pid))

    bye_pid = choose_bye(seeds)
    pool = [s for s in seeds if s.pid != bye_pid]

    pairings: List[Tuple[int, Optional[int]]] = []
    used = set()

    def candidate_score(a: Seed, b: Seed) -> Tuple[float, int, int, int]:
        score_gap = abs(a.score - b.score)
        color_diff = abs((a.color_balance) - (-b.color_balance))
        rating_gap = abs(a.rating - b.rating)
        return (score_gap, color_diff, rating_gap, b.pid)

    while pool:
        a = pool.pop(0)
        if a.pid in used:
            continue
        best_idx = None
        best_metric = None
        for idx, b in enumerate(pool):
            if b.pid in used:
                continue
            if b.pid in opponents.get(a.pid, set()):
                continue
            metric = candidate_score(a, b)
            if best_metric is None or metric < best_metric:
                best_metric = metric
                best_idx = idx
        if best_idx is None:
            # no opponent avoiding rematch found; pick first available
            for idx, b in enumerate(pool):
                if b.pid not in used:
                    best_idx = idx
                    break
        if best_idx is None:
            break
        opponent = pool.pop(best_idx)
        used.add(a.pid)
        used.add(opponent.pid)
        pairings.append((a.pid, opponent.pid))

    if bye_pid is not None:
        pairings.append((bye_pid, None))

    if not pairings:
        return []

    sess.add(rnd)
    sess.flush()

    for board_no, (white_id, black_id) in enumerate(pairings, start=1):
        pr = Pairing(round_id=rnd.id, board_no=board_no, white_id=white_id, black_id=black_id)
        if black_id is None:
            pr.result = "BYE"
            pr.started = True
            pr.finished = True
            player = sess.get(Player, white_id)
            if player:
                player.bye_count += 1
        sess.add(pr)
    sess.commit()
    return pairings


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
<html lang=\"en\">
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    :root { color-scheme: light; }
      .layout { grid-template-columns: 1fr; }
    .btn:disabled {
    input[type=\"text\"], input[type=\"number\"], input[type=\"file\"], select {
  <div class=\"page\">
      <h1 style=\"margin:0;font-size:28px;font-weight:700;\">Swiss League</h1>
        <a class=\"btn btn-secondary\" href=\"{{ url_for('index') }}\">Standings</a>
        <a class=\"btn btn-secondary\" href=\"{{ url_for('players') }}\">Players</a>
        <a class=\"btn btn-secondary\" href=\"{{ url_for('rounds') }}\">Rounds</a>
        <a class=\"btn btn-secondary\" href=\"{{ url_for('import_xlsm') }}\">Import XLSM</a>
        <a class=\"btn\" href=\"{{ url_for('export_xlsx') }}\">Export XLSX</a>
          <div class=\"flash\">{{ m }}</div>
<div class=\"layout\">
  <section class=\"card\">
    <div style=\"display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:20px;\">
      <h2 style=\"margin:0;font-size:20px;\">Standings</h2>
      <form method=\"post\" action=\"{{ url_for('generate_round') }}\">
        <button class=\"btn\" {% if not can_generate %}disabled{% endif %}>Generate Round {{ next_round }}</button>
    <div style=\"overflow-x:auto;\">
      <table class=\"table\">
            <th>Rank</th>
            <th>Name</th>
            <th>Club</th>
            <th>Score</th>
            <th>SB</th>
            <th>Byes</th>
            <td style=\"font-weight:600;\">{{ row.name }}</td>
            <td>{{ row.club }}</td>
            <td>{{ '%.1f'|format(row.score) }}</td>
            <td>{{ row.byes }}</td>
  <section class=\"card\" style=\"height:fit-content;\">
    <h2 style=\"margin-top:0;font-size:18px;\">Quick Add Player</h2>
    <form method=\"post\" action=\"{{ url_for('players') }}\" style=\"display:grid;gap:12px;\">
      <label> Name <input type=\"text\" name=\"name\" required></label>
      <label> Rating <input type=\"number\" name=\"rating\" value=\"1200\"></label>
      <label> Club <input type=\"text\" name=\"club\"></label>
      <button class=\"btn\" type=\"submit\">Add player</button>
    </form>
<section class=\"card\">
  <div style=\"display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:20px;\">
    <h2 style=\"margin:0;font-size:20px;\">Players</h2>
    <form method=\"post\" style=\"display:flex;gap:8px;flex-wrap:wrap;align-items:center;\">
      <input type=\"text\" name=\"name\" placeholder=\"Name\" required>
      <input type=\"number\" name=\"rating\" placeholder=\"Rating\" value=\"1200\">
      <input type=\"text\" name=\"club\" placeholder=\"Club\">
      <button class=\"btn\" type=\"submit\">Add</button>
  <div style=\"overflow-x:auto;\">
    <table class=\"table\">
          <td style=\"font-weight:600;\">{{ p.name }}</td>
            <a class=\"btn btn-secondary\" href=\"{{ url_for('delete_player', pid=p.id) }}\" onclick=\"return confirm('Delete player?')\">Delete</a>
<section class=\"card\">
  <div style=\"display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:20px;\">
    <h2 style=\"margin:0;font-size:20px;\">Rounds &amp; Pairings</h2>
    <form method=\"post\" action=\"{{ url_for('generate_round') }}\">
      <button class=\"btn\">Generate Round {{ next_round }}</button>
  <div style=\"border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px;background:#fafbff;\">
    <div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:10px;\">
      <h3 style=\"margin:0;font-size:18px;\">Round {{ r.number }}</h3>
      <span class=\"tag\">{{ r.pairings|length }} boards</span>
    <div style=\"overflow-x:auto;\">
      <table class=\"table\">
            <td style=\"font-weight:600;\">{{ pr.result }}</td>
                <span class=\"tag\">BYE</span>
              <form method=\"post\" action=\"{{ url_for('update_result', pairing_id=pr.id) }}\" class=\"inline\">
                <select name=\"result\">
                  <option value=\"*\" {% if pr.result=='*' %}selected{% endif %}>*</option>
                  <option value=\"1-0\" {% if pr.result=='1-0' %}selected{% endif %}>1-0</option>
                  <option value=\"0-1\" {% if pr.result=='0-1' %}selected{% endif %}>0-1</option>
                  <option value=\"0.5-0.5\" {% if pr.result=='0.5-0.5' %}selected{% endif %}>½-½</option>
                <label class=\"checkbox\"><input type=\"checkbox\" name=\"started\" value=\"1\" {% if pr.started %}checked{% endif %}> started</label>
                <label class=\"checkbox\"><input type=\"checkbox\" name=\"finished\" value=\"1\" {% if pr.finished %}checked{% endif %}> finished</label>
                <button class=\"btn btn-secondary\" type=\"submit\">Save</button>
<section class=\"card\" style=\"max-width:720px;margin:0 auto;\">
  <h2 style=\"margin-top:0;font-size:20px;\">Import SwissChessLeaguev4.xlsm</h2>
  <p style=\"font-size:14px;color:#475569;line-height:1.5;\">Provide a file path or upload the workbook so players, past rounds, and standings mirror Excel.</p>
  <form method=\"post\" enctype=\"multipart/form-data\" style=\"display:grid;gap:16px;margin-top:24px;\">
    <label style=\"display:grid;gap:8px;font-size:14px;\">
      <span style=\"font-weight:600;\">Workbook path (optional)</span>
      <input type=\"text\" name=\"path\" placeholder=\"SwissChessLeaguev4.xlsm\" value=\"{{ default_path }}\">
    <label style=\"display:grid;gap:8px;font-size:14px;\">
      <span style=\"font-weight:600;\">Or upload .xlsm</span>
      <input type=\"file\" name=\"file\" accept=\".xlsm,.xlsx\">
    <div style=\"display:flex;justify-content:flex-end;gap:12px;flex-wrap:wrap;\">
      <a class=\"btn btn-secondary\" href=\"{{ url_for('index') }}\">Cancel</a>
      <button class=\"btn\" type=\"submit\">Import Workbook</button>
app.jinja_loader = DictLoader(
    {
        "base.html": BASE_HTML,
        "index.html": INDEX_HTML,
        "players.html": PLAYERS_HTML,
        "rounds.html": ROUNDS_HTML,
        "import_xlsm.html": IMPORT_XLSM_HTML,
    }
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
        standings = compute_standings(sess)
        next_round = get_current_round_number(sess) + 1
        can_generate = sess.query(Player).count() >= 2
            table=standings,
            can_generate=can_generate,
            next_round=next_round,


        players_list = sess.query(Player).order_by(Player.id.asc()).all()
        return render_template("players.html", players=players_list)


@app.route("/players/<int:pid>/delete")
def delete_player(pid: int):
    sess = SessionLocal()
    try:
        player = sess.get(Player, pid)
        if player:
            sess.delete(player)
            sess.commit()
            flash("Player deleted.")
        else:
            flash("Player not found.")
    finally:
        sess.close()
    return redirect(url_for("players"))


            rounds=sess.query(Round).order_by(Round.number.asc()).all(),




        if pr is None:
            flash("Pairing not found.")
            return redirect(url_for("rounds"))

        result = request.form.get("result", "*").strip()
        if result not in ALLOWED_RESULTS:
            result = "*"
        started = request.form.get("started") == "1"
        finished = request.form.get("finished") == "1"

        pr.result = result
        pr.started = started or result in SCORE_MAP
        pr.finished = finished or result in SCORE_MAP and result != "*"

        if pr.result != "BYE" and pr.black_id is None and result in SCORE_MAP and result != "*":
            # ensure both players exist for scored games
            flash("Cannot record a result without two players.")
        else:
            sess.commit()
            flash("Result updated.")
            workbook = load_workbook(io.BytesIO(data), data_only=True, keep_vba=True)
    except Exception as exc:  # pragma: no cover - defensive
    def first_header(sheet) -> Tuple[Optional[int], Dict[str, int]]:
        mapping: Dict[str, int] = {}
        header_idx: Optional[int] = None
            labels = [str(cell).strip().lower() if cell is not None else "" for cell in row]
            if any(labels):
                mapping = {label: i for i, label in enumerate(labels) if label}
                header_idx = idx
                break
        return header_idx, mapping

    def find_col(mapping: Dict[str, int], name: str) -> Optional[int]:
        name = name.lower()
        for key, idx in mapping.items():
            if name == key or name in key:
                return idx
        existing_players: Dict[str, Player] = {p.name.casefold(): p for p in sess.query(Player).all()}
        added_players = updated_players = 0
        players_sheet = workbook["Players"] if "Players" in workbook.sheetnames else None
                name = (row[mapping.get("name", -1)] or "").strip() if mapping.get("name") is not None else ""
                rating_val = row[mapping.get("rating", -1)] if mapping.get("rating") is not None else None
                club = (row[mapping.get("club", -1)] or "").strip() if mapping.get("club") is not None else ""
                rating = safe_rating(rating_val)
                if key in existing_players:
                    player = existing_players[key]
                    player.rating = rating
                    player.club = club
                round_no = int(match.group(1))
                round_sheets.append((round_no, workbook[name]))
        rounds_imported = pairings_imported = 0
            if not mapping:
                continue
            for values in sheet.iter_rows(min_row=start_row, values_only=True):
                values = list(values)

                white_name = str(take(white_idx)).strip() if take(white_idx) else ""
                black_name = str(take(black_idx)).strip() if take(black_idx) else ""
                is_bye = normalized_result == "BYE" or (black_player is None and not black_name)
@app.route("/export_xlsx")
        rounds = sess.query(Round).order_by(Round.number.asc()).all()
        standings = compute_standings(sess)

        players_rows = [
            {
                "Player ID": p.id,
                "Name": p.name,
                "Rating": p.rating,
                "Club": p.club,
                "Byes": p.bye_count,
            }
            for p in players
        ]

        standings_rows = [
            {
                "Rank": idx + 1,
                "Wins": row["wins"],
                "Byes": row["byes"],
            }
            for idx, row in enumerate(standings)
        ]
        rounds_rows: List[Dict[str, object]] = []
        for rnd in rounds:
            for pr in sorted(rnd.pairings, key=lambda p: p.board_no):
                rounds_rows.append(
                    {
                        "Round": rnd.number,
                        "Board": pr.board_no,
                        "White": pr.white.name if pr.white else "",
                        "Black": pr.black.name if pr.black else "",
                        "Result": pr.result,
                        "Started": pr.started,
                        "Finished": pr.finished,
                    }
                )
            pd.DataFrame(players_rows).to_excel(writer, sheet_name="Players", index=False)
            pd.DataFrame(rounds_rows).to_excel(writer, sheet_name="Rounds", index=False)
            pd.DataFrame(standings_rows).to_excel(writer, sheet_name="Standings", index=False)

        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"swiss_export_{get_current_round_number(sess)}.xlsx",
        )
    finally:
        sess.close()


# ---------------------------------------------------------------------------
# Development helpers
# ---------------------------------------------------------------------------
def seed_if_empty() -> None:
            for name, rating in [
                ("Alpha", 1800),
                ("Bravo", 1700),
                ("Charlie", 1650),
                ("Delta", 1600),
            ]:
                sess.add(Player(name=name, rating=rating))
            sess.commit()
    finally:
        return redirect(url_for("import_xlsm"))

    def first_header(sheet):
        for idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            values = []
            for cell in row:
                if cell is None:
                    values.append("")
                else:
                    values.append(str(cell).strip())
            if not any(values):
                continue
            lowered = [v.lower() for v in values]
            mapping = {lowered[i]: i for i in range(len(lowered)) if lowered[i]}
            return idx, mapping
        return None, {}

    def find_col(mapping: Dict[str, int], *keys: str) -> Optional[int]:
        normalised = {k.replace(" ", ""): v for k, v in mapping.items()}
        for key in keys:
            key_norm = key.replace(" ", "").lower()
            for header, idx in normalised.items():
                if header == key_norm or header.endswith(key_norm):
                    return idx
                if key_norm in header:
                    return idx
        return None

    sess = SessionLocal()
    try:
        added_players = 0
        updated_players = 0
        rounds_imported = 0
        pairings_imported = 0

        existing_players = {p.name.strip().casefold(): p for p in sess.query(Player).all()}

        # Identify player sheet
        players_sheet = None
        for name in workbook.sheetnames:
            if name.strip().lower() == "players":
                players_sheet = workbook[name]
                break
        if players_sheet is None:
            for name in workbook.sheetnames:
                sheet = workbook[name]
                header_idx, mapping = first_header(sheet)
                if not mapping:
                    continue
                if "name" in mapping and ("rating" in mapping or "elo" in mapping):
                    players_sheet = sheet
                    break

        if players_sheet is not None:
            header_idx, mapping = first_header(players_sheet)
            name_idx = find_col(mapping, "name")
            rating_idx = find_col(mapping, "rating", "elo")
            club_idx = find_col(mapping, "club", "team")
            start_row = (header_idx or 0) + 1
            if name_idx is None:
                name_idx = 0
            for row in players_sheet.iter_rows(min_row=start_row, values_only=True):
                values = list(row)
                if not any(str(v).strip() if v is not None else "" for v in values):
                    continue
                name_val = values[name_idx] if name_idx is not None and name_idx < len(values) else None
                name = str(name_val).strip() if name_val is not None else ""
                if not name:
                    continue
                rating_val = values[rating_idx] if rating_idx is not None and rating_idx < len(values) else None
                club_val = values[club_idx] if club_idx is not None and club_idx < len(values) else ""
                rating = safe_rating(rating_val, 1200)
                club = str(club_val).strip() if club_val is not None else ""
                key = name.casefold()
                player = existing_players.get(key)
                if player:
                    if rating_val not in (None, ""):
                        player.rating = rating
                    if club:
                        player.club = club
                    updated_players += 1
                else:
                    player = Player(name=name, rating=rating, club=club)
                    sess.add(player)
                    sess.flush()
                    existing_players[key] = player
                    added_players += 1

        # Reset rounds and bye counters
        sess.query(Pairing).delete()
        sess.query(Round).delete()
        for player in sess.query(Player).all():
            player.bye_count = 0
        sess.flush()

        # Build round sheets
        round_sheets: List[Tuple[int, object]] = []
        for name in workbook.sheetnames:
            match = re.search(r"round\s*(\d+)", name, re.IGNORECASE)
            if match:
                round_number = int(match.group(1))
                round_sheets.append((round_number, workbook[name]))
        round_sheets.sort(key=lambda x: x[0])

        for round_no, sheet in round_sheets:
            header_idx, mapping = first_header(sheet)
            board_idx = find_col(mapping, "board")
            white_idx = find_col(mapping, "white")
            black_idx = find_col(mapping, "black")
            result_idx = find_col(mapping, "result")
            started_idx = find_col(mapping, "started")
            finished_idx = find_col(mapping, "finished")
            start_row = (header_idx or 0) + 1

            rnd = Round(number=round_no)
            sess.add(rnd)
            sess.flush()
            rounds_imported += 1

            board_counter = 1
            round_pairs = 0
            for row in sheet.iter_rows(min_row=start_row, values_only=True):
                values = list(row)
                if not any(str(v).strip() if v is not None else "" for v in values):
                    continue

                def take(idx: Optional[int]):
                    if idx is None or idx >= len(values):
                        return None
                    return values[idx]

                board_val = take(board_idx)
                try:
                    board_no = int(str(board_val).strip()) if board_val not in (None, "") else board_counter
                except (ValueError, TypeError):
                    board_no = board_counter
                white_name = str(take(white_idx)).strip() if take(white_idx) is not None else ""
                black_raw = take(black_idx)
                black_name = str(black_raw).strip() if black_raw is not None else ""
                result_raw = take(result_idx)
                normalized_result = normalize_result(result_raw)
                started = parse_bool_cell(take(started_idx))
                finished = parse_bool_cell(take(finished_idx))

                if not white_name and not black_name:
                    continue

                def ensure_player(name: str) -> Player:
                    key = name.casefold()
                    player = existing_players.get(key)
                    if player is None:
                        player = Player(name=name, rating=1200, club="")
                        sess.add(player)
                        sess.flush()
                        existing_players[key] = player
                    return player

                white_player = ensure_player(white_name) if white_name else None
                black_player = ensure_player(black_name) if black_name else None

                is_bye = normalized_result == "BYE" or (black_player is None and black_name == "")
                if is_bye and white_player is None:
                    continue
                if not is_bye and (white_player is None or black_player is None):
                    continue

                pairing = Pairing(round_id=rnd.id, board_no=board_no)
                pairing.white_id = white_player.id if white_player else None
                pairing.black_id = None if is_bye else (black_player.id if black_player else None)

                if is_bye:
                    pairing.result = "BYE"
                    pairing.started = True
                    pairing.finished = True
                    if white_player:
                        white_player.bye_count += 1
                else:
                    pairing.result = normalized_result
                    pairing.started = started or normalized_result in {"1-0", "0-1", "0.5-0.5"}
                    pairing.finished = finished or pairing.result in {"1-0", "0-1", "0.5-0.5"}

                sess.add(pairing)
                pairings_imported += 1
                round_pairs += 1
                board_counter = max(board_counter + 1, board_no + 1)

            if round_pairs == 0:
                sess.delete(rnd)
                rounds_imported -= 1

        sess.commit()
        flash(
            f"Imported {added_players} new players, updated {updated_players} players, "
            f"{rounds_imported} rounds, and {pairings_imported} pairings from {source_desc}."
        )
    finally:
        sess.close()

    return redirect(url_for("index"))


@app.route("/export.xlsx")
def export_xlsx():
    sess = SessionLocal()
    try:
        # Build DataFrames
        players = sess.query(Player).order_by(Player.id.asc()).all()
        standings_rows = []
        for row in compute_standings(sess):
            standings_rows.append({
                "Player ID": row["pid"],
                "Name": row["name"],
                "Rating": row["rating"],
                "Score": row["score"],
                "Buchholz": row["buchholz"],
                "Sonneborn-Berger": row["sb"],
            })
        standings_df = pd.DataFrame(standings_rows)

        rounds = sess.query(Round).order_by(Round.number.asc()).all()

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
# Dev seed: add sample players if DB empty
# ---------------------------------
def seed_if_empty():
    sess = SessionLocal()
    try:
        if sess.query(Player).count() == 0:
            for i, (n, r) in enumerate([
                ("Alpha", 1800), ("Bravo", 1700), ("Charlie", 1650), ("Delta", 1600),
        sess.close()


if __name__ == "__main__":
    seed_if_empty()
    app.run(debug=True)
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
