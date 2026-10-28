def attach_orders(users, orders):
    for user in users:
        user["orders"] = []
        for order in orders:
            if order["user_id"] == user["id"]:
                user["orders"].append(order)
    return users
