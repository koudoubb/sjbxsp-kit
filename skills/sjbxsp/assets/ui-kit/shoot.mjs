// UI 界面重绘截图：按卡片槽位尺寸设计，2 倍输出
// 用法：改 BASE 与 SHOTS → cd <project>/anim/ui && ego-browser nodejs < shoot.mjs
// 注意：task.page() 只能用已存在的 label（通常是 p1）；必须用 stdin 重定向执行，
//       `ego-browser nodejs shoot.mjs` 会把路径当代码执行，报 ReferenceError
const task = await taskSpace("sjbxsp ui mock");
const page = task.page("p1");

// 改成项目里 anim/ui 的绝对路径（ego 的 node 环境 cwd=/，拿不到相对路径与环境变量）
const BASE = "/绝对路径/<project>/anim/ui";

// w/h = 卡片里图片槽位的宽高（先量槽位再设计）；输出到 BASE/out/，实际像素是 2 倍
// 不是每支片都要三张：按分镜只做需要的那几张，原片 UI 截图留 0–1 张
const SHOTS = [
  { file: "phone-form.html",    w: 400, h: 535, out: "m-form.png" },
  { file: "desktop-table.html", w: 928, h: 427, out: "dash.png" },
  { file: "phone-chat.html",    w: 330, h: 594, out: "m-chat.png" },
];

for (const s of SHOTS) {
  // ego 的 screenshot 只接受 scale:"css"，所以用「viewport 2 倍 + 页面 zoom 2」拿 2x 像素
  await page.cdp("Emulation.setDeviceMetricsOverride", {
    width: s.w * 2, height: s.h * 2, deviceScaleFactor: 1, mobile: false,
  });
  await page.goto("file://" + BASE + "/" + s.file);
  await page.waitForLoadState("load");
  await page.evaluate(() => { document.body.style.zoom = "2"; });
  await page.waitForTimeout(350);
  await page.screenshot({ path: BASE + "/out/" + s.out, scale: "css" });
  console.log("shot", s.out, s.w * 2 + "x" + s.h * 2);
}
console.log("UI DONE");
