const express = require("express");
const mysql = require("mysql2/promise");

const app = express();
const pool = mysql.createPool({ host: process.env.DB_HOST, user: process.env.DB_USER, password: process.env.DB_PASS, database: "shop" });

app.get("/products", async (req, res) => {
    const term = req.query.q || "";
    const [rows] = await pool.query(`SELECT id, name, price FROM products WHERE name LIKE '%${term}%' LIMIT 50`);
    res.json(rows);
});

app.listen(3000);
