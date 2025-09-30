from __future__ import annotations

from typing import Any, Dict, List

from flask import Flask, jsonify, request, g
from flask_cors import CORS

from .constants import RESULT_VALUES, Result
from .db import get_connection
from .rules import RULES_TEXT
from .seed import seed_database
from .tournament import (
    can_generate_next_round,
    create_swiss_pairings,
    gather_opponent_history,
    recalculate_standings,
)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    def get_db():
        if "db" not in g:
            g.db = get_connection()
        return g.db

    @app.teardown_appcontext
    def close_db(exception: Exception | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def fetch_players() -> List[Dict[str, Any]]:
        connection = get_db()
        cursor = connection.execute(
            """
            SELECT id, name, full_name AS fullName, contact, department, register_number AS registerNumber, seed, add_score AS addScore
            FROM players
            ORDER BY id
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_rounds(players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        connection = get_db()
        players_by_id = {player["id"]: player for player in players}
        cursor = connection.execute(
            """
            SELECT r.id as roundId, r.round_number as roundNumber, m.id as matchId, m.table_number as tableNumber,
                   m.player1_id as player1, m.player2_id as player2, m.result as result
            FROM rounds r
            LEFT JOIN matches m ON m.round_id = r.id
            ORDER BY r.round_number ASC, m.table_number ASC
            """
        )
        rounds: Dict[int, Dict[str, Any]] = {}
        for row in cursor.fetchall():
            round_id = row["roundId"]
            round_info = rounds.setdefault(
                round_id,
                {
                    "id": round_id,
                    "roundNumber": row["roundNumber"],
                    "pairings": [],
                },
            )
            if row["matchId"] is None:
                continue
            player1 = row["player1"]
            player2 = row["player2"]
            round_info["pairings"].append(
                {
                    "id": row["matchId"],
                    "table": row["tableNumber"],
                    "player1": player1,
                    "player2": player2,
                    "result": row["result"],
                    "player1Name": players_by_id.get(player1, {}).get("name"),
                    "player2Name": (
                        players_by_id.get(player2, {}).get("name") if player2 is not None else "Bye"
                    ),
                }
            )
        return list(rounds.values())

    def get_state() -> Dict[str, Any]:
        players = fetch_players()
        rounds = fetch_rounds(players)
        standings = recalculate_standings(players, rounds)
        next_round_available = can_generate_next_round(rounds)
        return {
            "rules": RULES_TEXT,
            "players": players,
            "rounds": rounds,
            "standings": standings,
            "canGenerateNextRound": next_round_available,
        }

    @app.get("/api/state")
    def api_state() -> Any:
        return jsonify(get_state())

    @app.get("/api/rules")
    def api_rules() -> Any:
        return jsonify({"rules": RULES_TEXT})

    @app.get("/api/players")
    def api_players() -> Any:
        return jsonify({"players": fetch_players()})

    @app.get("/api/players/<int:player_id>")
    def api_player(player_id: int) -> Any:
        connection = get_db()
        cursor = connection.execute(
            """
            SELECT id, name, full_name AS fullName, contact, department, register_number AS registerNumber, seed, add_score AS addScore
            FROM players
            WHERE id = ?
            """,
            (player_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"message": "Player not found"}), 404
        return jsonify(dict(row))

    @app.put("/api/players/<int:player_id>/adjustment")
    def api_adjust_player(player_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        try:
            add_score = float(payload.get("addScore", 0))
        except (TypeError, ValueError):
            add_score = 0

        connection = get_db()
        cursor = connection.execute(
            "UPDATE players SET add_score = ? WHERE id = ?",
            (add_score, player_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"message": "Player not found"}), 404
        connection.commit()
        return ("", 204)

    @app.get("/api/rounds")
    def api_rounds() -> Any:
        players = fetch_players()
        return jsonify({"rounds": fetch_rounds(players)})

    @app.get("/api/matches")
    def api_matches() -> Any:
        players = fetch_players()
        rounds = fetch_rounds(players)
        matches: List[Dict[str, Any]] = []
        for round_info in rounds:
            for pairing in round_info.get("pairings", []):
                matches.append({**pairing, "roundId": round_info["id"], "roundNumber": round_info["roundNumber"]})
        return jsonify({"matches": matches})

    @app.put("/api/matches/<int:match_id>")
    def api_update_match(match_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        result = payload.get("result")
        if result not in RESULT_VALUES:
            return jsonify({"message": "Invalid result value"}), 400

        connection = get_db()
        cursor = connection.execute("SELECT player2_id FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        if row is None:
            return jsonify({"message": "Match not found"}), 404

        if row["player2_id"] is None and result != Result.BYE.value:
            return jsonify({"message": "Bye matches must remain BYE"}), 400

        connection.execute("UPDATE matches SET result = ? WHERE id = ?", (result, match_id))
        connection.commit()
        return ("", 204)

    @app.get("/api/standings")
    def api_standings() -> Any:
        players = fetch_players()
        rounds = fetch_rounds(players)
        standings = recalculate_standings(players, rounds)
        return jsonify({"standings": standings})

    @app.post("/api/rounds")
    def api_create_round():
        players = fetch_players()
        rounds = fetch_rounds(players)
        if not can_generate_next_round(rounds):
            return (
                jsonify({"message": "All matches must be completed before generating the next round."}),
                400,
            )

        standings = recalculate_standings(players, rounds)
        opponent_history = gather_opponent_history(players, rounds)
        players_to_pair = [entry["id"] for entry in standings]
        try:
            pairings = create_swiss_pairings(players_to_pair, opponent_history)
        except ValueError as error:
            return jsonify({"message": str(error)}), 500

        connection = get_db()
        cursor = connection.execute("SELECT COUNT(*) FROM rounds")
        next_round_number = cursor.fetchone()[0] + 1
        round_id = connection.execute(
            "INSERT INTO rounds (round_number) VALUES (?)",
            (next_round_number,),
        ).lastrowid

        new_pairings: List[Dict[str, Any]] = []
        for index, pair in enumerate(pairings, start=1):
            if len(pair) == 1:
                player_id = pair[0]
                cursor = connection.execute(
                    "INSERT INTO matches (round_id, table_number, player1_id, player2_id, result) VALUES (?, ?, ?, NULL, ?)",
                    (round_id, index, player_id, Result.BYE.value),
                )
                player = next((player for player in players if player["id"] == player_id), None)
                new_pairings.append(
                    {
                        "id": cursor.lastrowid,
                        "table": index,
                        "player1": player_id,
                        "player2": None,
                        "result": Result.BYE.value,
                        "player1Name": player.get("name") if player else None,
                        "player2Name": "Bye",
                    }
                )
                continue

            player1, player2 = pair
            cursor = connection.execute(
                "INSERT INTO matches (round_id, table_number, player1_id, player2_id, result) VALUES (?, ?, ?, ?, ?)",
                (round_id, index, player1, player2, Result.UNPLAYED.value),
            )
            row_id = cursor.lastrowid
            player1_info = next((player for player in players if player["id"] == player1), None)
            player2_info = next((player for player in players if player["id"] == player2), None)
            new_pairings.append(
                {
                    "id": row_id,
                    "table": index,
                    "player1": player1,
                    "player2": player2,
                    "result": Result.UNPLAYED.value,
                    "player1Name": player1_info.get("name") if player1_info else None,
                    "player2Name": player2_info.get("name") if player2_info else None,
                }
            )

        connection.commit()
        return (
            jsonify(
                {
                    "round": {
                        "id": round_id,
                        "roundNumber": next_round_number,
                        "pairings": new_pairings,
                    }
                }
            ),
            201,
        )

    @app.post("/api/reset")
    def api_reset():
        seed_database()
        return jsonify({"message": "Tournament reset to the initial state."})

    return app
