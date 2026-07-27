const fs = require("fs");
eval(fs.readFileSync("saju_data.js","utf8") + "\n" + fs.readFileSync("saju_engine.js","utf8"));

const expected = JSON.parse(fs.readFileSync("expected.json", "utf8"));
let ok = 0, bad = [];
for (const c of expected) {
  if (c.err) continue;
  const [y, m, d, h, mi, g] = c.in;
  let got;
  try { got = toDict(getSaju(y, m, d, h, mi, g)); }
  catch (e) { bad.push({ in: c.in, why: "throw: " + e.message }); continue; }
  const a = JSON.stringify(got), b = JSON.stringify(c.out);
  if (a === b) ok++;
  else {
    // 어느 키가 다른지 찾기
    let diff = "";
    for (const k of Object.keys(c.out)) {
      if (JSON.stringify(got[k]) !== JSON.stringify(c.out[k])) { diff = k; break; }
    }
    bad.push({ in: c.in, why: "diff:" + diff, exp: JSON.stringify(c.out[diff]).slice(0,200), got: JSON.stringify(got[diff]).slice(0,200) });
  }
}
console.log(`일치 ${ok} / 검증대상 ${expected.filter(c=>!c.err).length}, 불일치 ${bad.length}`);
bad.slice(0, 5).forEach(b => console.log(JSON.stringify(b, null, 1)));
