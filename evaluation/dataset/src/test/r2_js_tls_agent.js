const https = require("https");

const agent = new https.Agent({ rejectUnauthorized: false }); // @label tls_verification high

function getJson(url) {
    return new Promise((resolve, reject) => {
        https.get(url, { agent }, (res) => {
            let body = "";
            res.on("data", (chunk) => { body += chunk; });
            res.on("end", () => resolve(JSON.parse(body)));
        }).on("error", reject);
    });
}

module.exports = { getJson };
