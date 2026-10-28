const express = require("express");
const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const path = require("path");
const { execFile } = require("child_process");

const app = express();
app.use(express.json());
const UPLOADS = path.join(__dirname, "uploads");
const agent = new https.Agent({ keepAlive: true });

app.post("/imports", (req, res) => {
    const repo = String(req.body.repo || "");
    if (!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+(\.git)?$/.test(repo)) {
        return res.status(400).json({ error: "unsupported repository url" });
    }
    execFile("git", ["clone", "--depth", "1", "--", repo, "/tmp/imports/job"], { timeout: 60000 }, (err) => {
        res.status(err ? 500 : 202).json({ status: err ? "failed" : "queued" });
    });
});

app.put("/upload", (req, res) => {
    const dest = path.join(UPLOADS, `${crypto.randomUUID()}.bin`);
    req.pipe(fs.createWriteStream(dest))
        .on("finish", () => res.sendStatus(201))
        .on("error", () => res.sendStatus(500));
});

function collectIds(users) {
    const ids = [];
    for (const u of users) {
        ids.push(u.id);
    }
    return ids;
}

app.listen(3000);
module.exports = { collectIds, agent };
