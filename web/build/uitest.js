const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const errors = [];

  async function run(theme, colorScheme) {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, colorScheme,
    });
    const page = await ctx.newPage();
    page.on("console", m => { if (m.type() === "error") errors.push(`[console] ${m.text()}`); });
    page.on("pageerror", e => errors.push(`[pageerror] ${e.message}`));

    await page.setContent(
      `<!doctype html><html${theme ? ` data-theme="${theme}"` : ""}><head><meta charset="utf-8">
       <meta name="viewport" content="width=device-width,initial-scale=1"></head><body>` +
      fs.readFileSync("saju.html", "utf8") + `</body></html>`);

    await page.fill("#y", "1990"); await page.fill("#mo", "5"); await page.fill("#d", "15");
    await page.fill("#t", "14:30");
    await page.click("#calcBtn");
    await page.waitForSelector("#result:not(.hidden)");

    const data = await page.evaluate(() => ({
      pillars: [...document.querySelectorAll(".pillar")].map(p => p.querySelector(".kr").textContent),
      ilgan: document.querySelector(".summary b:last-of-type") ? null : null,
      summary: document.querySelector(".summary").innerText.replace(/\s+/g, " "),
      strength: document.querySelector(".verdict .v").textContent,
      now: document.querySelector(".dw.now")?.innerText.replace(/\n/g, " "),
      sewoon: document.querySelector(".sewoon").innerText.replace(/\n/g, " "),
      ohaeng: [...document.querySelectorAll(".oh-row")].map(r => r.innerText.replace(/\n/g, " ")),
      prompt: (() => { try { return buildPrompt().length; } catch (e) { return "ERR " + e.message; } })(),
      // 가로 스크롤 발생 여부
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    }));

    const label = theme || `auto-${colorScheme}`;
    await page.screenshot({ path: `shot-${label}.png`, fullPage: true });
    await ctx.close();
    return { label, data };
  }

  const light = await run(null, "light");
  const dark  = await run("dark", "light");   // 토글이 미디어쿼리를 이기는지 확인
  console.log("─── 라이트 ───");
  console.log(JSON.stringify(light.data, null, 1));
  console.log("─── 다크(토글 강제) 결과 동일 여부:", JSON.stringify(light.data) === JSON.stringify(dark.data));

  // 배경색이 실제로 테마별로 다른지
  const ctx = await browser.newContext({ colorScheme: "dark" });
  const p2 = await ctx.newPage();
  await p2.setContent(`<!doctype html><html data-theme="light"><head><meta charset="utf-8"></head><body>` + fs.readFileSync("saju.html","utf8") + `</body></html>`);
  const bgLightForced = await p2.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await p2.evaluate(() => document.documentElement.setAttribute("data-theme","dark"));
  const bgDarkForced = await p2.evaluate(() => getComputedStyle(document.body).backgroundColor);
  console.log("data-theme=light 배경:", bgLightForced, "| data-theme=dark 배경:", bgDarkForced);
  await ctx.close();

  console.log("에러:", errors.length ? errors : "없음");
  await browser.close();
})();
