function findMatches(lines, term) {
    const matches = [];
    for (const line of lines) {
        const pattern = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"); // @label repeated_work medium -- identical regex rebuilt on every iteration
        if (pattern.test(line)) {
            matches.push(line);
        }
    }
    return matches;
}

module.exports = { findMatches };
