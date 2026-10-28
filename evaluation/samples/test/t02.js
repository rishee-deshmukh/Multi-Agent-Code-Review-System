const express = require("express");
const { execFile } = require("child_process");
const path = require("path");

const app = express();
const UPLOADS = path.resolve(__dirname, "uploads");

app.get("/log", (req, res) => {
    const count = Number.parseInt(req.query.n, 10);
    if (!Number.isInteger(count) || count < 1 || count > 100) {
        return res.status(400).json({ error: "n must be 1-100" });
    }
    execFile("git", ["log", "--oneline", "-n", String(count)], { timeout: 5000 }, (err, stdout) => {
        if (err) {
            return res.status(500).json({ error: "git failed" });
        }
        res.json({ commits: stdout.split("\n").filter(Boolean) });
    });
});

app.get("/files/:name", (req, res) => {
    const full = path.resolve(UPLOADS, req.params.name);
    if (!full.startsWith(UPLOADS + path.sep)) {
        return res.sendStatus(400);
    }
    res.sendFile(full);
});

app.listen(3000);
