const puppeteer = require("puppeteer"), path = require("path");
(async () => {
  const b = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
  const p = await b.newPage();
  for (const n of [1, 2]) {
    await p.setViewport({ width: 1000, height: 400, deviceScaleFactor: 1 });
    await p.goto("file://" + path.resolve(__dirname, `report_${n}.html`), { waitUntil: "networkidle0" });
    const h = await p.evaluate(() => document.body.scrollHeight);
    const dpr = Math.min(2, 2990 / h); await p.setViewport({ width: 1000, height: h, deviceScaleFactor: dpr });
    const out = process.argv[2] + `/validation_report_${n}.png`;
    await p.screenshot({ path: out, fullPage: true });
    console.log(n, "CSS 높이", h, "배율", dpr.toFixed(2), "→", Math.round(1000*dpr) + "x" + Math.round(h*dpr));
  }
  await b.close();
})();
