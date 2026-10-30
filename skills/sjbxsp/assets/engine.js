/* 统一动画引擎：所有元素用 data-a 声明动画类型，data-d 声明延迟（秒） */
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const easeOut = t => 1 - Math.pow(1 - clamp(t), 3);
const easeInOut = t => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeBack = t => { t = clamp(t); const c = 1.9; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const lerp = (a, b, t) => a + (b - a) * t;

window.setT = function (t) {
  // 背景
  const grid = document.getElementById('grid');
  if (grid) grid.style.transform = `translate(${(t * 8) % 72 - 36}px, ${(t * 5) % 72 - 36}px)`;
  const glows = document.querySelectorAll('.glow');
  glows.forEach((g, i) => {
    const a = .4 + i * .5;
    g.style.transform = `translate(${Math.sin(t * .5 + a) * 44}px, ${Math.cos(t * .4 + a) * 32}px) scale(${1 + .035 * Math.sin(t * .6 + a)})`;
  });

  document.querySelectorAll('[data-a]').forEach(el => {
    const d = parseFloat(el.dataset.d || 0);
    const dur = parseFloat(el.dataset.dur || 0.6);
    const p = clamp((t - d) / dur);
    const type = el.dataset.a;

    if (type === 'in') {
      const dy = parseFloat(el.dataset.y || 40);
      const e = easeOut(p);
      el.style.opacity = e;
      el.style.transform = `translateY(${dy * (1 - e)}px)`;
    } else if (type === 'pop') {
      const e = easeBack(p);
      el.style.opacity = clamp(p * 3);
      el.style.transform = `translateY(${28 * (1 - e)}px) scale(${lerp(.9, 1, e)})`;
    } else if (type === 'num') {
      const to = parseFloat(el.dataset.to);
      const dec = parseInt(el.dataset.dec || 0);
      const e = easeOut(p);
      el.textContent = (to * e).toFixed(dec);
    } else if (type === 'bar') {
      const e = easeInOut(p);
      el.style.transform = `scaleX(${e})`;
    } else if (type === 'grow') {
      const e = easeInOut(p);
      el.style.transform = `scaleY(${e})`;
    } else if (type === 'wipe') {
      el.style.transform = `scaleX(${easeInOut(p)})`;
    } else if (type === 'pulse') {
      el.style.opacity = clamp(p * 2) * (0.75 + 0.25 * Math.sin(t * 4));
    }
  });
};

// 页面级：给 body 加 data-page 便于样式区分
window.setPage = function (n) { document.body.dataset.page = n; };
window.setT(0);
