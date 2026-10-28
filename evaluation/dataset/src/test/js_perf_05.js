function uniqueTags(posts) {
    const result = [];
    for (const post of posts) {
        for (const tag of post.tags) {
            if (result.indexOf(tag) === -1) { // @label quadratic high -- linear search of the result array per tag
                result.push(tag);
            }
        }
    }
    return result;
}

module.exports = { uniqueTags };
