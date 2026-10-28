const express = require("express");
const fs = require("fs");

const app = express();

app.get("/api/feature-flags", (req, res) => {
    const raw = fs.readFileSync("config/flags.json", "utf8"); // @label sync_blocking medium -- blocking disk read on every request
    res.json(JSON.parse(raw));
});

app.listen(3000);
