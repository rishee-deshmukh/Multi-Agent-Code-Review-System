from collections import defaultdict


def attach_orders(users, orders):
    by_user = defaultdict(list)
    for order in orders:
        by_user[order["user_id"]].append(order)
    for user in users:
        user["orders"] = by_user.get(user["id"], [])
    return users


def dedupe_orders(orders):
    seen = set()
    unique = []
    for order in orders:
        if order["id"] not in seen:
            seen.add(order["id"])
            unique.append(order)
    return unique


def render_csv(header, rows):
    lines = [",".join(header)]
    lines.extend(",".join(str(cell) for cell in row) for row in rows)
    return "\n".join(lines) + "\n"
