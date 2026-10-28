const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const NOTES_DIR = path.join(__dirname, "notes");

app.get("/notes/:name", (req, res) => {
    const file = path.join(NOTES_DIR, req.params.name);
    fs.readFile(file, "utf8", (err, text) => { // @label path_traversal high
        if (err) {
            return res.status(404).json({ error: "not found" });
        }
        res.json({ name: req.params.name, text });
    });
});

app.listen(3000);
