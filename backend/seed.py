from __future__ import annotations

from .constants import Result
from .db import get_connection
from .seed_data import INITIAL_PAIRINGS, PLAYER_SEED_DATA


def seed_database() -> None:
    with get_connection() as connection:
        connection.executescript("DELETE FROM matches; DELETE FROM rounds; DELETE FROM players;")

        connection.executemany(
            """
            INSERT INTO players (id, name, full_name, contact, department, register_number, seed, add_score)
            VALUES (:id, :name, :fullName, :contact, :department, :registerNumber, :seed, 0)
            """,
            PLAYER_SEED_DATA,
        )

        round_id = connection.execute(
            "INSERT INTO rounds (round_number) VALUES (?)",
            (1,),
        ).lastrowid

        match_rows = []
        for pairing in INITIAL_PAIRINGS:
            player2 = pairing.get("player2")
            result = Result.UNPLAYED.value if player2 is not None else Result.BYE.value
            match_rows.append(
                (
                    round_id,
                    pairing["table"],
                    pairing["player1"],
                    player2,
                    result,
                )
            )

        connection.executemany(
            """
            INSERT INTO matches (round_id, table_number, player1_id, player2_id, result)
            VALUES (?, ?, ?, ?, ?)
            """,
            match_rows,
        )


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully.")
