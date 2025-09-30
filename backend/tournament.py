from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Set

from .constants import Result


PlayerDict = Mapping[str, object]


def _player_id(player: PlayerDict) -> int:
    return int(player["id"])  # type: ignore[index]


def gather_opponent_history(players: Sequence[PlayerDict], rounds: Sequence[Dict]) -> Dict[int, Set[int]]:
    history: Dict[int, Set[int]] = {_player_id(player): set() for player in players}
    for round_data in rounds:
        for pairing in round_data.get("pairings", []):
            player1 = pairing.get("player1")
            player2 = pairing.get("player2")
            if not player1 or not player2:
                continue
            history.setdefault(player1, set()).add(player2)
            history.setdefault(player2, set()).add(player1)
    return history


def recalculate_standings(players: Sequence[PlayerDict], rounds: Sequence[Dict]) -> List[Dict]:
    stats_map: Dict[int, Dict] = {}
    players_by_id = {_player_id(player): player for player in players}

    for player in players:
        player_id = _player_id(player)
        name = str(player.get("name", ""))
        full_name = player.get("fullName") or name
        add_score = float(player.get("addScore") or 0)
        stats_map[player_id] = {
            "id": player_id,
            "seed": int(player.get("seed", 0)),
            "name": full_name,
            "displayName": name,
            "addScore": add_score,
            "opponents": set(),
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "byes": 0,
            "basePoints": 0.0,
        }

    for round_data in rounds:
        for pairing in round_data.get("pairings", []):
            player1 = pairing.get("player1")
            player2 = pairing.get("player2")
            result = pairing.get("result")

            if player1 not in stats_map:
                continue

            p1_stats = stats_map[player1]
            p2_stats = stats_map.get(player2) if player2 is not None else None

            if player2 is not None:
                p1_stats["opponents"].add(player2)
                if p2_stats is not None:
                    p2_stats["opponents"].add(player1)

            if result == Result.PLAYER1.value:
                p1_stats["wins"] += 1
                p1_stats["basePoints"] += 1
                if p2_stats is not None:
                    p2_stats["losses"] += 1
            elif result == Result.PLAYER2.value:
                if p2_stats is not None:
                    p2_stats["wins"] += 1
                    p2_stats["basePoints"] += 1
                p1_stats["losses"] += 1
            elif result == Result.DRAW.value:
                p1_stats["draws"] += 1
                p1_stats["basePoints"] += 0.5
                if p2_stats is not None:
                    p2_stats["draws"] += 1
                    p2_stats["basePoints"] += 0.5
            elif result == Result.BYE.value:
                p1_stats["byes"] += 1
                p1_stats["basePoints"] += 1
                p1_stats["opponents"].add("Bye")

    standings: List[Dict] = []
    for stats in stats_map.values():
        games_played = stats["wins"] + stats["losses"] + stats["draws"] + stats["byes"]
        total_points = stats["basePoints"] + stats["addScore"]
        win_percent = 0 if games_played == 0 else (stats["basePoints"] / games_played) * 100

        opponent_summaries: List[str] = []
        for opponent in stats["opponents"]:
            if opponent == "Bye":
                opponent_summaries.append("Bye")
                continue
            opponent_data = players_by_id.get(opponent)
            if opponent_data is not None:
                opponent_name = opponent_data.get("name") or opponent_data.get("fullName") or "Unknown"
                opponent_summaries.append(f"{opponent_name} (#{opponent})")
            else:
                opponent_summaries.append(f"#{opponent}")

        standings.append(
            {
                **stats,
                "gamesPlayed": games_played,
                "totalPoints": total_points,
                "winPercent": win_percent,
                "opponentSummaries": opponent_summaries,
            }
        )

    standings.sort(
        key=lambda entry: (
            -entry["totalPoints"],
            -entry["basePoints"],
            -entry["winPercent"],
            entry["seed"],
        )
    )
    return standings


def can_generate_next_round(rounds: Sequence[Dict]) -> bool:
    if not rounds:
        return False
    return all(
        pairing.get("result") != Result.UNPLAYED.value
        for round_data in rounds
        for pairing in round_data.get("pairings", [])
    )


def create_swiss_pairings(player_ids: Sequence[int], opponent_history: Dict[int, Set[int]]) -> List[List[int]]:
    pool = list(player_ids)
    bye_player: Optional[int] = None

    if len(pool) % 2 == 1:
        bye_player = pool.pop()

    solution: Optional[List[List[int]]] = None

    def backtrack(available: List[int], current_pairs: List[List[int]]) -> bool:
        nonlocal solution
        if not available:
            solution = list(current_pairs)
            return True

        player = available[0]
        rest = available[1:]

        for index, opponent in enumerate(rest):
            if opponent in opponent_history.get(player, set()):
                continue
            remaining = rest[:index] + rest[index + 1 :]
            if backtrack(remaining, current_pairs + [[player, opponent]]):
                return True

        for index, opponent in enumerate(rest):
            remaining = rest[:index] + rest[index + 1 :]
            if backtrack(remaining, current_pairs + [[player, opponent]]):
                return True

        return False

    if not backtrack(pool, []):
        raise ValueError("Unable to create Swiss pairings without conflicts.")

    final_pairs = list(solution or [])
    if bye_player is not None:
        final_pairs.append([bye_player])
    return final_pairs
