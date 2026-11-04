// Renders the Beginner guided workout to JPEG frames, one folder per exercise, plus a beep log.
// Usage: node render.js <outDir> [preview]
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2];
const PREVIEW = process.argv[3] === 'preview';
const FPS = 24;
const URL = 'file:///home/user/Back-Exercises/index.html?tv=1&debug';
const N_EX = 7, WORKERS = 4;

// Video-only styling: hide controls that can't be pressed in a video and give the text room to breathe.
const VIDEO_CSS = `
  .wk-controls, .wk-toggles, #wkHint, .wk-progress { display: none !important; }
  html.tv .wk { padding: 2.2rem 2.6rem 2rem; gap: 1.3rem; }
  html.tv .wk-top .titles { display: flex; align-items: baseline; gap: 1.2rem; }
  html.tv .wk-count { font-size: 1.05rem; letter-spacing: 0.04em; text-transform: uppercase; }
  html.tv .wk-top h2 { font-size: 2.1rem; }
  html.tv .wk-body { gap: 1.4rem; grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr); }
  html.tv #wkStage svg.scene { max-height: calc(100vh - 12rem); }
  html.tv #wkStage .form-note { font-size: 1rem; min-height: 4.4rem; padding: 0.8rem 1.4rem; gap: 0.45rem; flex-direction: column; align-items: flex-start; justify-content: center; }
  html.tv #wkStage .form-note::before { display: none; }
  html.tv #wkStage .form-note:not(.show) .txt { visibility: hidden; }
  html.tv #wkStage .form-note .txt { flex: none; line-height: 1.35; }
  html.tv .wk-hud { padding: 1.5rem 1.6rem; gap: 1.5rem; align-items: center; }
  html.tv .wk-hud .timer { width: 7.5rem; height: 7.5rem; }
  html.tv .wk-hud .phase strong { font-size: 1.7rem; line-height: 1.3; margin-bottom: 0.6rem; }
  html.tv .wk-hud .phase span { display: block; font-size: 1.05rem; line-height: 1.4; }
  html.tv .upnext { margin-top: 0.7rem !important; padding-top: 0.7rem; border-top: 1px solid var(--border); }
  html.tv .wk-side { padding: 1.3rem 1.5rem; font-size: 1rem; }
  html.tv .wk-side h3 { display: block; margin-bottom: 0.8rem; }
  html.tv .wk-side li { margin: 0 0 0.75rem; line-height: 1.45; padding-left: 0.2rem; }
  html.tv .wk-side .tip { margin-top: 1rem; line-height: 1.45; }
  html.tv .wk-done h2 { font-size: 2.6rem; }
  html.tv .wk-done p { font-size: 1.15rem; line-height: 1.5; }
  html.tv .wk-done .row { display: none; }
`;

async function renderExercise(browser, i) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  await page.addInitScript(() => {
    window.requestAnimationFrame = () => 0; // the script drives time itself, frame by frame
    window.__vt = 0; window.__beeps = []; window.__spoken = [];
    Object.defineProperty(window, 'speechSynthesis', { value: { cancel() {}, speak(u) { window.__spoken.push({ t: window.__vt, text: u.text }); } }, configurable: true });
    window.SpeechSynthesisUtterance = function (t) { this.text = t; };
    const AC = window.AudioContext || window.webkitAudioContext;
    const orig = AC.prototype.createOscillator;
    AC.prototype.createOscillator = function () {
      const o = orig.call(this); const start = o.start.bind(o);
      o.start = (when) => { window.__beeps.push({ t: window.__vt, f: o.frequency.value }); return start(when); };
      return o;
    };
    Element.prototype.requestFullscreen = function () { return Promise.resolve(); };
  });
  await page.goto(URL);
  await page.addStyleTag({ content: VIDEO_CSS });
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('startWorkout').click());
  await page.evaluate((i) => {
    const D = window.__backExercises, W = D.W;
    for (let k = 0; k < i; k++) document.getElementById('wkNext').click();
    // The app already adds the 10 s rest before each exercise and the 1 s pause between rounds.
    // For the video: the title names the exercise, so the get-ready card just says "Get ready".
    for (const p of W.pl.phases) if (p.intro) p.holdLabel = 'Get ready';
    W.played = 1e12; // counts as a completed workout, so the closing screen says "finished"
    W.lastKey = ''; W.beepKey = '';
    window.__beeps = []; window.__spoken = []; window.__vt = 0;
    D.tick(0);
  }, i);
  const dir = `${OUT}/seg${i}`;
  fs.mkdirSync(dir, { recursive: true });
  let f = 0, doneFrames = 0;
  const maxFrames = PREVIEW ? 0 : 1e6;
  for (; f < maxFrames; f++) {
    const state = await page.evaluate(([f, fps, i]) => {
      const D = window.__backExercises, W = D.W;
      window.__vt = f / fps;
      if (f > 0) D.tick(1000 / fps);
      // One clear line under the instruction: no repeats of "Get ready".
      const pl = W.pl, ph = pl.phases.find((p) => Math.min(pl.time, pl.total - 1) < p.t1);
      if (ph && (ph.rest || ph.intro)) document.getElementById('wkSub').textContent = ph.rest ? 'Take a short break' : 'Starting soon';
      if (ph && ph.rest) document.getElementById('wkUpNext').textContent = `Up next: ${D.EXERCISES[i].name}`;
      const doneText = document.getElementById('wkDoneText');
      if (!document.getElementById('wkDone').hidden) doneText.textContent = 'All 7 exercises finished. Great work! If your back hurts more than usual over the next 2 hours, contact your provider.';
      return { idx: W.idx, done: !document.getElementById('wkDone').hidden };
    }, [f, FPS, i]);
    if (state.idx !== i && !state.done) break;      // this exercise has finished
    if (state.done) { if (i !== N_EX - 1 || ++doneFrames > FPS * 5) break; }
    await page.screenshot({ path: `${dir}/f${String(f).padStart(6, '0')}.jpg`, type: 'jpeg', quality: 88 });
  }
  if (PREVIEW) {
    // A few sample frames at chosen times.
    const times = await page.evaluate(() => { const pl = window.__backExercises.W.pl; return pl.phases.slice(0, 8).map((p) => p.t0 + p.move + 400); });
    for (const [k, t] of times.entries()) {
      await page.evaluate((t) => { const D = window.__backExercises, W = D.W; W.pl.time = t; W.lastKey = ''; D.tick(0);
        const pl = W.pl, ph = pl.phases.find((p) => pl.time < p.t1);
        if (ph && (ph.rest || ph.intro)) document.getElementById('wkSub').textContent = ph.rest ? 'Take a short break' : 'Starting soon';
        if (ph && ph.rest) document.getElementById('wkUpNext').textContent = 'Up next: ' + D.EXERCISES[W.idx].name; }, t);
      await page.screenshot({ path: `${dir}/preview-${k}.jpg`, type: 'jpeg', quality: 88 });
    }
  }
  const meta = await page.evaluate(() => ({ beeps: window.__beeps, spoken: window.__spoken }));
  fs.writeFileSync(`${dir}/meta.json`, JSON.stringify({ frames: f, fps: FPS, ...meta, errors: errs }));
  await ctx.close();
  return { i, frames: f, errors: errs.length };
}

(async () => {
  const browser = await chromium.launch();
  const queue = PREVIEW ? [0, 1, 6] : [...Array(N_EX).keys()];
  const results = [];
  await Promise.all(Array.from({ length: Math.min(WORKERS, queue.length) }, async () => {
    while (queue.length) { const i = queue.shift(); const r = await renderExercise(browser, i); results.push(r); console.log('done', JSON.stringify(r)); }
  }));
  await browser.close();
})();
