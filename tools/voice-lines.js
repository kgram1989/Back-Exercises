// Lists every line the guided workout speaks, for each "Your plan" preset, by fast-forwarding the real app
// in headless Chromium. Output (JSON on stdout): { lines: [...whole lines], fragments: [...] }.
// Fragments are the pieces between numbers ("Rest for", "seconds. Next: Pelvic tilt."), so any plan's line
// can be joined from fragments plus number clips. Usage: node tools/voice-lines.js > voice-lines.json
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const url = 'file://' + path.resolve(__dirname, '..', 'index.html') + '?debug';
  const lines = new Set();
  for (const level of ['beginner', 'standard', 'max']) {
    const page = await browser.newPage();
    await page.addInitScript((lvl) => {
      localStorage.setItem('backex.settings', JSON.stringify({ level: lvl, voice: true, sound: false }));
      window.speechSynthesis && (window.speechSynthesis.speak = () => {});
    }, level);
    await page.goto(url);
    const said = await page.evaluate(() => {
      const out = [];
      const live = document.getElementById('wkLive');
      document.getElementById('startWorkout').click();
      const B = window.__backExercises, done = document.getElementById('wkDone');
      let lastText = null;
      for (let i = 0; i < 200000 && done.hidden; i++) {
        B.tick(50);
        // say() replaces the text node, so a repeated line still counts as new.
        const node = live.firstChild;
        if (node && node !== lastText) { lastText = node; out.push(node.textContent); }
      }
      return out;
    });
    said.forEach((t) => t && lines.add(t));
    await page.close();
  }
  await browser.close();
  // Lines the app can say that the run above may not reach.
  lines.add('Workout complete. Well done.');
  lines.add('Workout ended.');
  const fragments = new Set();
  for (const l of lines) l.split(/\d+/).map((s) => s.trim()).filter(Boolean).forEach((f) => fragments.add(f));
  process.stdout.write(JSON.stringify({ lines: [...lines].sort(), fragments: [...fragments].sort() }, null, 1));
})();
