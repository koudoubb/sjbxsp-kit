// 模板：由 scripts/render.py safe 填充执行。不要直接跑。
// 列出指定页各元素在 3:4 裁切区内的四边留白，任何一项 < MARGIN 即不达标（退出码 2）。
const task = await taskSpace("sjbxsp safe area");
const page = task.page("p1");

const BASE = "__BASE__";
const HTML = "__HTML__";
const PG = __PAGE__;
const TOP = __TOP__;
const HEIGHT = __HEIGHT__;
const MARGIN = __MARGIN__;

await page.cdp("Emulation.setDeviceMetricsOverride", {
  width: 1080, height: 1920, deviceScaleFactor: 1, mobile: false,
});
await page.goto("file://" + BASE + "/" + HTML);
await page.waitForLoadState("load");
await page.waitForTimeout(1200);
await page.evaluate((i) => window.setPage(i), PG);
await page.waitForTimeout(200);
await page.evaluate(() => window.setT(4)); // 让所有动效落位，否则量到的是初始位移
await page.waitForTimeout(300);

const res = await page.evaluate(([top, height]) => {
  const sel = ".top,.pill,.pg,.kick,h1,h2,.num,.num .big,.num .unit,.num .rule,.lead,.art,.tag,.cardw,.ch,.bars,.tbl,.shot,.shotcap,.kpis,.bignums,[data-safe]";
  const out = [];
  for (const el of [...document.querySelectorAll(sel)]) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    out.push({
      cls: typeof el.className === "string" ? el.className.split(" ")[0] : el.tagName,
      txt: (el.textContent || "").replace(/\s+/g, "").slice(0, 16),
      mt: Math.round(r.top - top),
      mb: Math.round(top + height - (r.top + r.height)),
      ml: Math.round(r.left),
      mr: Math.round(1080 - r.left - r.width),
    });
  }
  return out;
}, [TOP, HEIGHT]);

console.log(`=== 第 ${PG} 页在 3:4 裁切区（y ${TOP}–${TOP + HEIGHT}）内的边距，要求 ≥ ${MARGIN}px ===`);
let bad = [];
for (const e of res) {
  const min = Math.min(e.mt, e.mb, e.ml, e.mr);
  const flag = min < MARGIN ? "  <<< 过近" : "";
  if (flag) bad.push([e, min]);
  console.log(`${(e.txt || e.cls).padEnd(18)} 上${String(e.mt).padStart(5)} 下${String(e.mb).padStart(5)} 左${String(e.ml).padStart(4)} 右${String(e.mr).padStart(4)}${flag}`);
}
console.log(`===== 不达标：${bad.length} 个 =====`);
for (const [e, m] of bad) console.log(`  ! ${e.txt || e.cls}  最小边距 ${m}px`);
if (bad.length) process.exitCode = 2;
