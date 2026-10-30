// 模板：由 scripts/render.py 填占位符后执行。不要直接跑本文件。
// ego-browser 的 node 环境拿不到环境变量（cwd=/，env 仅 14 个键），
// 所有参数都必须在生成时写死在脚本正文里。
const task = await taskSpace("sjbxsp frames");
const page = task.page("p1");

const BASE = "__BASE__";
const HTML = "__HTML__";
const PAGES = __PAGES__;
const FROM = __FROM__;
const FPS = __FPS__;
const FRAMES = __FRAMES__;

await page.cdp("Emulation.setDeviceMetricsOverride", {
  width: 1080, height: 1920, deviceScaleFactor: 1, mobile: false,
});
await page.goto("file://" + BASE + "/" + HTML);
await page.waitForLoadState("load");
await page.waitForTimeout(1500);

const dir = BASE + "/anim/frames";
const t0 = Date.now();
for (let n = FROM; n <= PAGES; n++) {
  await page.evaluate((i) => window.setPage(i), n);
  await page.waitForTimeout(120);
  for (let i = 0; i < FRAMES; i++) {
    await page.evaluate((tt) => window.setT(tt), i / FPS);
    await page.screenshot({
      path: `${dir}/p${String(n).padStart(2, "0")}/f${String(i).padStart(4, "0")}.png`,
      scale: "css",
    });
  }
  console.log("page", n, "done", ((Date.now() - t0) / 1000).toFixed(0), "s");
}
console.log("ALL DONE", ((Date.now() - t0) / 1000).toFixed(1), "s");
