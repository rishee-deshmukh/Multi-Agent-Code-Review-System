const express = require("express");

const app = express();
app.use(express.json());

app.post("/api/formula", (req, res) => {
    const { formula } = req.body;
    if (typeof formula !== "string" || formula.length > 120) {
        return res.status(400).json({ error: "bad formula" });
    }
    const value = eval(formula); // @label code_injection critical
    res.json({ value });
});

app.listen(3000);
