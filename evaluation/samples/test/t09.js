function uniqueTags(posts) {
    const result = [];
    for (const post of posts) {
        for (const tag of post.tags) {
            if (result.indexOf(tag) === -1) {
                result.push(tag);
            }
        }
    }
    return result;
}

module.exports = { uniqueTags };
