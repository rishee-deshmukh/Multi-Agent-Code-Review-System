function usersWithOrders(users, orders) {
    return users.filter((u) => orders.some((o) => o.userId === u.id));
}

function totalRevenue(orders) {
    return orders.reduce((sum, o) => sum + o.total, 0);
}

module.exports = { usersWithOrders, totalRevenue };
