const express = require("express");
const { execSync } = require("child_process");

const app = express();

app.get("/thumbnail", (req, res) => {
    const file = req.query.file;
    if (!file) {
        return res.status(400).json({ error: "file required" });
    }
    execSync(`convert uploads/${file} -resize 200x200 thumbs/${file}.png`); // @label command_injection critical
    res.json({ thumbnail: `/thumbs/${file}.png` });
});

app.listen(3000);
