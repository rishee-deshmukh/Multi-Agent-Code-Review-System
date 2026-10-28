async function loadAccounts(pool, ids) {
    const accounts = [];
    for (let i = 0; i < ids.length; i++) {
        const [rows] = await pool.query("SELECT id, name, balance FROM accounts WHERE id = ?", [ids[i]]); // @label io_in_loop high
        accounts.push(rows[0]);
    }
    return accounts;
}

module.exports = { loadAccounts };
