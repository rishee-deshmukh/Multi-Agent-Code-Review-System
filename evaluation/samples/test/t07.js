function findMatches(lines, term) {
    const matches = [];
    for (const line of lines) {
        const pattern = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
        if (pattern.test(line)) {
            matches.push(line);
        }
    }
    return matches;
}

module.exports = { findMatches };
