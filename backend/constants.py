from enum import Enum


class Result(str, Enum):
    """Possible match results."""

    UNPLAYED = "UNPLAYED"
    PLAYER1 = "PLAYER1"
    PLAYER2 = "PLAYER2"
    DRAW = "DRAW"
    BYE = "BYE"


RESULT_VALUES = {result.value for result in Result}
