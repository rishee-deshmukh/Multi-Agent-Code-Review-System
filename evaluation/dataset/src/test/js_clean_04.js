const express = require("express");
const fs = require("fs");

const app = express();
const flags = JSON.parse(fs.readFileSync("config/flags.json", "utf8"));

app.get("/api/feature-flags", (req, res) => {
    res.json(flags);
});

app.get("/login/complete", (req, res) => {
    const target = typeof req.query.returnTo === "string" && req.query.returnTo.startsWith("/") && !req.query.returnTo.startsWith("//")
        ? req.query.returnTo
        : "/dashboard";
    res.redirect(target);
});

app.listen(3000);
