const sessions = new Map();

function createSession(userId) {
    const sessionId = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
    sessions.set(sessionId, { userId, createdAt: Date.now() });
    return sessionId;
}

function getSession(sessionId) {
    return sessions.get(sessionId) || null;
}

module.exports = { createSession, getSession };
