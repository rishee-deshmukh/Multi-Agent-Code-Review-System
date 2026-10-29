function collectIds(users) {
    return users.reduce((acc, u) => [...acc, u.id], []);
}

function activeCount(users) {
    return users.filter((u) => u.active).length;
}

module.exports = { collectIds, activeCount };
