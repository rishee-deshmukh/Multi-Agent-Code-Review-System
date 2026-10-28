def dedupe_orders(orders):
    seen_ids = []
    unique = []
    for order in orders:
        if order["id"] not in seen_ids:
            seen_ids.append(order["id"])
            unique.append(order)
    return unique


def total_value(orders):
    return sum(o["qty"] * o["unit_price"] for o in orders)
