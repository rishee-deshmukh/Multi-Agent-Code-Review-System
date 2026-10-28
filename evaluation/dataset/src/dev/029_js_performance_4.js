function getSortedNames(users) {
    return users
        .map(user => user.name)
        .sort()
        .map(name => name.toUpperCase())
        .sort()  // @label repeated_work medium -- three sorts in one chain; one issue
        .filter(name => name.length > 0)
        .sort();
}

module.exports = { getSortedNames };