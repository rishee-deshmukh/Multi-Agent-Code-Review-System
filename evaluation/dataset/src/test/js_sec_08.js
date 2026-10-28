const express = require("express");

const app = express();

app.get("/login/complete", (req, res) => {
    const target = req.query.returnTo || "/dashboard";
    res.cookie("seen_welcome", "1", { httpOnly: true });
    res.redirect(target); // @label open_redirect medium
});

app.listen(3000);
