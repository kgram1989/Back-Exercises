# Handoff: add a spoken voice to the Back Exercises workout video

Everything needed is on the GitHub branch **`video-voice-handoff`** of `kgram1989/Back-Exercises`, in the
folder `video-handoff/`. That branch is separate from `main`; the live site only serves `main`.

## Prompt to paste into the new session

> I'm continuing a task from another session. Repo: kgram1989/Back-Exercises. Please read
> `video-handoff/HANDOFF.md` on the branch `video-voice-handoff` (fetch that branch) and follow it: add a spoken
> voice to the Beginner workout video in that folder, then send me the MP4 so I can save it to my phone.
> Afterwards, offer to make the app itself play the same recorded voice clips (so the voice also reaches the TV
> when I screen-mirror my phone to my Roku).

The new session's cloud environment must allow **huggingface.co** (Network access → Allowed domains), with
package managers left allowed.

## What's in `video-handoff/`

| File | What it is |
|---|---|
| `Back-Exercises-Beginner-Workout.mp4` | The finished video **without voice**: 1920×1080, 24 fps, 11 min 13 s, with beeps. |
| `meta/seg0.json` … `seg6.json` | One per exercise, recorded during rendering: `frames`, `fps`, `beeps` (`t`, `f`) and `spoken` (`t`, `text`). `t` is the second within that exercise's segment at which the app spoke or beeped. |
| `add_voice.py` | Adds the voice to the existing video using `meta/`. Tested end to end with `--test-tones`. |
| `render.js` | Re-renders the video from the app (only needed for the full route below). |
| `assemble.py` | Joins re-rendered frames into a video with beeps (full route only). |

## Background

- The app is `index.html` (no build step), live at https://kgram1989.github.io/Back-Exercises/. The guided
  workout reads instructions aloud with the browser's built-in speech and plays beeps with Web Audio.
- The user screen-mirrors a phone to a Roku TV. Beeps reach the TV, but the phone keeps its built-in speech on
  its own speaker. That's why the voice must be **pre-recorded audio** (in the video, and later in the app).
- The previous session couldn't make a voice because huggingface.co was blocked. `pip install piper-tts` works
  (PyPI is allowed).

## Quick route (recommended): add the voice to the existing video

1. Get the files: `git fetch origin video-voice-handoff` and then `git checkout origin/video-voice-handoff -- video-handoff`.
   Work on copies in the scratchpad, and don't commit them to `main`.
2. Check `curl -sI https://huggingface.co` succeeds.
3. Create a virtual environment **in the scratchpad**, not in the repo:
   - `python3 -m venv <scratchpad>/tts/venv`
   - then `<scratchpad>/tts/venv/bin/pip install piper-tts`
4. Download the voice **en_US-ljspeech-high** from
   https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/high/
   - files: `en_US-ljspeech-high.onnx`, `en_US-ljspeech-high.onnx.json` and `MODEL_CARD`
   - LJSpeech is a public-domain recording set; confirm the licence in `MODEL_CARD`.
5. Preview the 192 spoken lines and their times (no model needed):
   `python3 add_voice.py --video x --meta meta --out x --list`
   - Expected, for example: `1:56.58 Rest for 10 seconds. Next: Pelvic tilt.` then `2:06.62 Get ready: Pelvic tilt. 5 times.`
   - The script already rewrites the old recording's wording to the app's current wording (rest, get-ready and
     closing lines; the 1 s round pause stays silent).
6. Make the video:
   ```
   <scratchpad>/tts/venv/bin/python add_voice.py --video Back-Exercises-Beginner-Workout.mp4 --meta meta \
       --model <path>/en_US-ljspeech-high.onnx --out Back-Exercises-Beginner-Workout-voice.mp4
   ```
   - The script uses `PiperVoice.load(model)` and `voice.synthesize_wav(text, wave_file)`, the piper-tts API
     checked against the installed version.
   - It places each line at its moment. If a line would run into the next one, it fades out over 80 ms there, as
     the app cuts speech short.
   - It mixes the voice with the existing beeps (beeps at 0.7) and copies the picture unchanged.
7. Check the result:
   - `ffprobe` duration ≈ 673 s, with h264 + aac streams.
   - Listen-check numerically: the audio should have energy right after 0:00, 1:56.6 and 2:06.6.
   - Pull out a couple of frames with ffmpeg and look at them.
8. Send the MP4 to the user with SendUserFile (display: attach). Tell them to save it from the Claude app,
   because the cloud machine is temporary.

## Full route (only if the video itself must change)

Re-render from the current app with `node render.js <outDir>`. It takes about 20 min with 4 workers; run it in the
background.
- **Setup:** Playwright and Chromium are preinstalled. The script expects the repo at `/home/user/Back-Exercises`;
  change the `URL` constant otherwise.
- **Pacing:** the app itself now has the 10 s rest between exercises and 1 s pause between rounds (PR #8), so
  `render.js` doesn't add them.
- **Output:** frames and `meta.json` per segment. Then `python3 assemble.py <outDir> out.mp4` for the video with
  beeps, then `add_voice.py` with `--meta` pointing at a folder of the new `segN.json` files.
- The ~2.3 GB of frames from the first render weren't pushed (too large for Git).

## What the video looks like (keep it)

- **Layout:** TV-mode layout with buttons, hints and progress bar hidden. The picture is on the left, with a
  form-check line and coloured muscle label underneath. One large instruction with a countdown ring, round number
  and "Up next" is on the right, with the steps underneath and the current one highlighted.
- **Get ready / rest cards:**
  - The get-ready card says "Get ready / Starting soon".
  - The rest card says "Rest / Take a short break / Up next: (exercise)".
- **Closing screen:** "Workout complete — All 7 exercises finished. Great work! If your back hurts more than usual
  over the next 2 hours, contact your provider."

## Optional follow-up for the app (offer, don't do without asking)

- Generate clips for every phrase the app can say, from `speechFor()` in `index.html`:
  - fixed instruction labels
  - "Hold for N seconds"
  - "Rest for 10 seconds. Next: (exercise)"
  - "Round N"
  - "Get ready: (exercise). N times"
- Numbers vary with "Your plan" (reps 1–30, holds 1–60 s), so record number words and join them.
- Add the clips to the repo (e.g. `audio/`) and play them with Web Audio, like the beeps, so they follow the
  phone's media output to the TV. Fall back to speechSynthesis if they fail to load.
- Work on a branch, open a PR, and merge only when the user says so.
