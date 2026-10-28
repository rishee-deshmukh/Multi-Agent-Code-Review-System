function buildMessage(items) {
    let message = "";

    for (let i = 0; i < items.length; i++) {
        message = message + items[i] + ",";  // @label string_concat_loop low
    }

    return message;
}

module.exports = { buildMessage };