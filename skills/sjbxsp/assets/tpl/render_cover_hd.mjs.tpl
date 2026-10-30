// 模板：由 scripts/render.py cover-hd 填充执行。不要直接跑。
// 2 倍超采样渲封面母版：视口放大到 2160x3840，再给 body 加 zoom，
// 浏览器按放大后的精度重新栅格化文字与矢量图形。
// （screenshot 的 scale:"device" 在当前 ego-browser 会报参数校验失败，deviceScaleFactor 也拿不到 2x 像素）
const task = await taskSpace("sjbxsp cover hd");
const page = task.page("p1");

const BASE = "__BASE__";
const HTML = "__HTML__";
const PG = __PAGE__;
const SCALE = __SCALE__;
const OUT = "__OUT__";

await page.cdp("Emulation.setDeviceMetricsOverride", {
  width: 1080 * SCALE, height: 1920 * SCALE, deviceScaleFactor: 1, mobile: false,
});
await page.goto("file://" + BASE + "/" + HTML);
await page.waitForLoadState("load");
await page.waitForTimeout(1500);

await page.evaluate((s) => {
  document.documentElement.style.overflow = "hidden";
  document.body.style.zoom = String(s);
}, SCALE);
await page.waitForTimeout(500);

await page.evaluate((i) => window.setPage(i), PG);
await page.waitForTimeout(200);
await page.evaluate(() => window.setT(4));
await page.waitForTimeout(400);

await page.screenshot({ path: BASE + "/" + OUT, scale: "css" });
console.log(`HD DONE ${1080 * SCALE}x${1920 * SCALE} -> ${OUT}`);
