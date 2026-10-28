const express = require("express");
const { exec } = require("child_process");

const app = express();
app.use(express.json());

app.post("/imports", (req, res) => {
    const { repo } = req.body;
    if (typeof repo !== "string" || !repo.startsWith("https://")) {
        return res.status(400).json({ error: "https repository url required" });
    }
    exec(`git clone --depth 1 ${repo} /tmp/imports/job`, (err) => { // @label command_injection critical -- startsWith("https://") does not stop shell metacharacters
        if (err) {
            return res.status(500).json({ error: "clone failed" });
        }
        res.status(202).json({ status: "queued" });
    });
});

app.listen(3000);
