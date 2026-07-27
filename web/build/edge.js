const { chromium } = require("playwright"); const fs = require("fs");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const ctx = await b.newContext({ viewport:{width:390,height:844} });
  const errs = [];
  async function fresh() {
    const p = await ctx.newPage();
    p.on("pageerror", e => errs.push(e.message));
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8"></head><body>`+fs.readFileSync("saju.html","utf8")+`</body></html>`);
    return p;
  }
  async function attempt(p, {cal, y, mo, d, t, leap, noTime, gender}) {
    if (cal === "lunar") await p.click('#calSeg button[data-cal="lunar"]');
    if (gender) await p.click(`#genderSeg button[data-g="${gender}"]`);
    await p.fill("#y", String(y)); await p.fill("#mo", String(mo)); await p.fill("#d", String(d));
    if (leap) await p.check("#leap");
    if (noTime) await p.check("#noTime"); else if (t) await p.fill("#t", t);
    await p.click("#calcBtn");
    await p.waitForTimeout(120);
    const err = await p.$eval("#err", e => e.classList.contains("hidden") ? null : e.textContent);
    const ok = await p.$eval("#result", e => !e.classList.contains("hidden"));
    const sum = ok ? await p.$eval(".summary", e => e.innerText.replace(/\s+/g," ")) : null;
    const note = ok ? await p.$eval("#result", e => e.querySelector(".note")?.textContent ?? null) : null;
    return { err, sum, note };
  }

  // 1) 음력 입력 (CLI 예시: 음력 1977-03-24 → 양력)
  let p = await fresh();
  console.log("음력 1977-03-24:", JSON.stringify(await attempt(p, {cal:"lunar", y:1977, mo:3, d:24, t:"04:14"})));

  // 2) 윤달
  p = await fresh();
  console.log("음력 2020-04-15 윤달:", JSON.stringify(await attempt(p, {cal:"lunar", y:2020, mo:4, d:15, leap:true, t:"09:00"})));

  // 3) 존재하지 않는 양력 날짜
  p = await fresh();
  console.log("양력 2023-02-30:", JSON.stringify(await attempt(p, {y:2023, mo:2, d:30, t:"10:00"})));

  // 4) 범위 밖 연도
  p = await fresh();
  console.log("양력 1850년:", JSON.stringify(await attempt(p, {y:1850, mo:5, d:5, t:"10:00"})));

  // 5) 시간 모름
  p = await fresh();
  console.log("시간 모름:", JSON.stringify(await attempt(p, {y:2001, mo:9, d:11, noTime:true, gender:"여"})));

  // 6) 없는 윤달 요청
  p = await fresh();
  console.log("음력 2021-04 윤달(없음):", JSON.stringify(await attempt(p, {cal:"lunar", y:2021, mo:4, d:5, leap:true, t:"10:00"})));

  // 7) 2051년 이후(음력 정보 없음)
  p = await fresh();
  console.log("양력 2060년:", JSON.stringify(await attempt(p, {y:2060, mo:6, d:6, t:"10:00"})));

  console.log("페이지 에러:", errs.length ? errs : "없음");
  await b.close();
})();
