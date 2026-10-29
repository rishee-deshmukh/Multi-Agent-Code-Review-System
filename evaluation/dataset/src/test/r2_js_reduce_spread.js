function collectIds(users) {
    return users.reduce((acc, u) => [...acc, u.id], []); // @label quadratic high -- the accumulator is copied on every step
}

function activeCount(users) {
    return users.filter((u) => u.active).length;
}

module.exports = { collectIds, activeCount };
