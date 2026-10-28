const crypto = require("crypto");

function newSessionId() {
    return crypto.randomBytes(32).toString("hex");
}

function fileDigest(buffer) {
    return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function loadAccounts(pool, ids) {
    const rows = await Promise.all(
        ids.map((id) => pool.query("SELECT id, name, balance FROM accounts WHERE id = ?", [id]))
    );
    return rows.map(([result]) => result[0]);
}

function usersWithOrders(users, orders) {
    const withOrders = new Set(orders.map((o) => o.userId));
    return users.filter((u) => withOrders.has(u.id));
}

module.exports = { newSessionId, fileDigest, loadAccounts, usersWithOrders };
