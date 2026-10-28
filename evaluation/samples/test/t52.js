const express = require("express");

const app = express();

app.get("/evaluate", (req, res) => {
    const expr = String(req.query.expr || "0");
    if (expr.length > 100) {
        return res.status(400).json({ error: "too long" });
    }
    const fn = new Function("x", "return " + expr);
    res.json({ result: fn(Number(req.query.x || 0)) });
});

app.listen(3000);
