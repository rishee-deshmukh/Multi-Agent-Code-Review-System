const crypto = require("crypto");

function hashPassword(password) {
    return crypto.createHash("md5").update(password).digest("hex");
}

function checkPassword(password, storedHash) {
    return crypto.timingSafeEqual(Buffer.from(hashPassword(password)), Buffer.from(storedHash));
}

module.exports = { hashPassword, checkPassword };
