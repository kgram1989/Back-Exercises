// Lists every line a page's guided workout speaks, by fast-forwarding the real app in headless Chromium.
//   node tools/voice-lines.js back > back-lines.json   (Back exercises: Beginner, Standard and Max plans)
//   node tools/voice-lines.js gym > gym-lines.json     (Gym workouts A and B: Card, 8, 10 and 12 reps)
// Output: { lines: [...whole lines], fragments: [...] }. Fragments are the pieces between numbers
// ("Rest for", "seconds. Next: Pelvic tilt."), so any plan's line can be joined from fragments and number clips.
const path = require('path');
const { chromium } = require('playwright');

const prog = process.argv[2] === 'gym' ? 'gym' : 'back';
const RUNS = prog === 'gym'
  ? ['a', 'b'].flatMap((workout) => ['card', '8', '10', '12'].map((level) => ({ key: 'backex.gym', value: { workout, level } })))
  : ['beginner', 'standard', 'max'].map((level) => ({ key: 'backex.settings', value: { level, voice: true, sound: false } }));

(async () => {
  const browser = await chromium.launch();
  const url = 'file://' + path.resolve(__dirname, '..', 'index.html') + (prog === 'gym' ? '?w=gym&debug' : '?debug');
  const lines = new Set();
  for (const run of RUNS) {
    const page = await browser.newPage();
    await page.addInitScript((run) => {
      localStorage.setItem(run.key, JSON.stringify(run.value));
      localStorage.setItem('backex.settings', JSON.stringify({ ...(run.key === 'backex.settings' ? run.value : {}), voice: true, sound: false }));
      window.speechSynthesis && (window.speechSynthesis.speak = () => {});
    }, run);
    await page.goto(url);
    const said = await page.evaluate(() => {
      const out = [];
      const live = document.getElementById('wkLive');
      document.getElementById('startWorkout').click();
      const B = window.__backExercises, done = document.getElementById('wkDone');
      let lastText = null;
      for (let i = 0; i < 400000 && done.hidden; i++) {
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
  // Lines the app can say that the runs above may not reach.
  lines.add('Workout complete. Well done.');
  lines.add('Workout ended.');
  lines.add('Set complete. Starting again.'); // end of each loop on an exercise card
  if (prog === 'gym') { lines.add('Get ready: Planks. 2 sets.'); lines.add('Get ready: Planks. 1 set of 8.'); } // custom plans: uneven or single sets
  const fragments = new Set();
  for (const l of lines) l.split(/\d+/).map((s) => s.trim()).filter(Boolean).forEach((f) => fragments.add(f));
  process.stdout.write(JSON.stringify({ lines: [...lines].sort(), fragments: [...fragments].sort() }, null, 1));
})();
