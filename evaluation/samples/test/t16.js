const jwt = require("jsonwebtoken");

const JWT_SECRET = "s3cr3t-signing-key-prod-2024";

function issueToken(user) {
    return jwt.sign({ sub: user.id, role: user.role }, JWT_SECRET, { expiresIn: "1h" });
}

function verifyToken(token) {
    return jwt.verify(token, JWT_SECRET);
}

module.exports = { issueToken, verifyToken };
