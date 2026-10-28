const express = require("express");
const app = express();

app.get("/search", (req, res) => {
    const q = req.query.q || "";
    res.send("<h1>Results for: " + q + "</h1>");  // @label xss high
});

app.listen(3000);