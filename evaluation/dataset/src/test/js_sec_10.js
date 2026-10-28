const crypto = require("crypto");

function hashPassword(password) {
    return crypto.createHash("md5").update(password).digest("hex"); // @label weak_crypto medium -- fast unsalted hash used for passwords
}

function checkPassword(password, storedHash) {
    return crypto.timingSafeEqual(Buffer.from(hashPassword(password)), Buffer.from(storedHash));
}

module.exports = { hashPassword, checkPassword };
