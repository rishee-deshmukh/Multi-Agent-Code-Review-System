import random

TIPS = [
    "Press ? to see all keyboard shortcuts.",
    "You can drag cards between columns.",
    "Use filters to narrow the board.",
]


def tip_of_the_day():
    return random.choice(TIPS)


def shuffled_avatars(avatars):
    order = list(avatars)
    random.shuffle(order)
    return order
