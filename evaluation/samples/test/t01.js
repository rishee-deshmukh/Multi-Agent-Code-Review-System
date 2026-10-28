const express = require("express");
const mysql = require("mysql2/promise");

const app = express();
const pool = mysql.createPool({ host: process.env.DB_HOST, user: process.env.DB_USER, password: process.env.DB_PASS, database: "shop" });

function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

app.get("/products", async (req, res) => {
    const term = req.query.q || "";
    const [rows] = await pool.query("SELECT id, name, price FROM products WHERE name LIKE ? LIMIT 50", [`%${term}%`]);
    res.json(rows);
});

app.get("/hello", (req, res) => {
    res.type("html").send(`<main><h1>Hello, ${escapeHtml(req.query.name || "friend")}!</h1></main>`);
});

app.listen(3000);
