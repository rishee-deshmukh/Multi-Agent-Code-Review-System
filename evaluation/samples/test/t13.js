const express = require("express");

const app = express();

app.get("/hello", (req, res) => {
    const name = req.query.name || "friend";
    res.type("html").send(`<main><h1>Hello, ${name}!</h1></main>`);
});

app.get("/status", (req, res) => {
    res.json({ ok: true });
});

app.listen(3000);
