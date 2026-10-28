def attach_orders(users, orders):
    for user in users:
        user["orders"] = []
        for order in orders:  # @label quadratic high -- every user scans every order; index orders by user_id once
            if order["user_id"] == user["id"]:
                user["orders"].append(order)
    return users
