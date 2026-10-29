// A small Express server with deliberate problems, for trying out the code reviewer.
// Paste this file into the app (or POST it to /review). Nothing here is meant to be run.
var express = require("express");
var fs = require("fs");
var app = express();

var ADMIN_TOKEN = "letmein-admin";

app.get("/calc", function (req, res) {
    // evaluates user input as code
    var result = eval(req.query.expr);
    res.send("Result: " + result);
});

app.get("/greet", function (req, res) {
    // reflected cross-site scripting: user input is written into HTML unescaped
    res.send("<h1>Hello, " + req.query.name + "</h1>");
});

app.get("/download", function (req, res) {
    // path traversal: the file name is user-controlled and can climb out of ./uploads
    fs.readFile("./uploads/" + req.query.file, function (err, data) {
        res.send(data);
    });
});

app.post("/admin", function (req, res) {
    if (req.headers["x-token"] == ADMIN_TOKEN) {
        res.send("welcome");
    } else {
        res.status(403).send("no");
    }
});

async function loadAll(ids, db) {
    // awaits one request at a time instead of running them together
    var out = [];
    for (var i = 0; i < ids.length; i++) {
        var row = await db.query("SELECT * FROM items WHERE id = ?", [ids[i]]);
        out.push(row);
    }
    return out;
}

function total(items) {
    var sum = 0;
    for (var i = 0; i < items.length; i++) {
        if (items[i].price != null) {
            sum = sum + items[i].price * items[i].qty;
        }
    }
    console.log("total is " + sum);
    return sum;
}

app.listen(3000);
