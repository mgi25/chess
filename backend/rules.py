RULES_TEXT = [
    "What is a Swiss-style Tournament?",
    "Right, so what are we trying to do anyway? We’re trying to code a Tournament Manager, which is useful for things like e-sports, trading card games, and anything else that’s vaguely competitive. In general, tournaments aim to determine the best player/team (I’ll just use player from now on) in a competition; obviously, the best way to go about this is to make each participant play each other, and the player with the highest score at the end of it all wins — this is known as a “Round-Robin” style tournament.",
    "The problem with a Round-Robin tournament is that it doesn’t scale very well to large numbers of participants. For example, 4-player round-robin tournament requires 3 rounds to be played. But the same tournament style for 32 players would require 31 rounds — a logistical nightmare at beast.",
    "Swiss-style tournaments were developed to counteract this problem. Swiss-style tournaments generally have two rules:",
    "Participants are paired with opponents who have similar scores.",
    "Participants cannot play the same opponent twice.",
    "In this way, the tournament aims to pair similarly ranked players until a winner is determined, and this process generally takes much fewer rounds than a round-robin tournament to resolve. For example, a 32-player Swiss tournament would only need 5 rounds to conclude rather than a 31-Round-Robin tournament — much better!",
    "Thus, to create our Tournament Manager app, we’re first going to need to come with an algorithm that does the above."
]
