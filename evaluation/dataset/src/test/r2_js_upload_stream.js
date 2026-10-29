const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const UPLOADS = path.join(__dirname, "uploads");

app.put("/upload/:name", (req, res) => {
    if (Number(req.headers["content-length"]) > 10 * 1024 * 1024) {
        return res.sendStatus(413);
    }
    const dest = path.join(UPLOADS, req.params.name);
    req.pipe(fs.createWriteStream(dest)) // @label path_traversal high -- :name can contain encoded ../ segments
        .on("finish", () => res.sendStatus(201))
        .on("error", () => res.sendStatus(500));
});

app.listen(3000);
