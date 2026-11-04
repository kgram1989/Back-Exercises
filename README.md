# Back Exercises

An animated guide to seven back exercises from a patient handout: single knee to chest, pelvic tilt, cat–cow, press-ups, bridges, belly crunches and back lifts. Everything is in `index.html` with no dependencies.

Live site: https://kgram1989.github.io/Back-Exercises/

## Features

- **Detailed animations.** An illustrated person in a small room: shaded body and clothes, hands, face and shoes. The spine bends at several points, and the head and arms follow through naturally. Working muscles are highlighted (red) or stretched (blue) during each hold.
- **Exercise cards** show each exercise's main position. Press play to watch the full animation, with spoken instructions and beeps like the guided workout, the matching step highlighted, a hold timer, arrows for the direction of movement, a form check for each position, and close-ups for small movements.
- **Guided workout** takes you through all seven exercises one at a time. It has spoken instructions (recorded clips, so the voice follows your phone's sound to a TV when screen-mirroring), countdown beeps, Back / Pause / Skip and an "Up next" line, and it keeps the screen awake.
- **TV mode** gives a big-screen layout you can read from the sofa.
  - It switches on automatically in smart-TV browsers (Samsung, LG, Fire TV, Android TV), or with the **TV mode** button, or by adding `?tv=1` to the address.
  - Remote control: ◀ / ▶ go back or skip, OK or Play/Pause pauses and resumes, and Back exits. The arrow keys move between buttons.
  - **Watch on TV** explains how to cast or mirror from a computer or phone.
- **Your plan** sets repeats and hold times (Beginner / Standard / Max, or your own numbers).
- **Today** tracks sessions per day against a daily goal, with the last 7 days.
- Light/dark theme, printable layout, phone-friendly in portrait and landscape, and respects "reduce motion".

Plan, progress and preferences are stored only in the browser on each device.

## Gym workout

The **Gym workout** link at the top (`?w=gym`) opens a second page with a full-body gym plan in the same style: animated cards, a guided workout with rest timers between sets, TV mode and the recorded voice.

- **Workout A:** planks, plank pyramids, glute bridges, goblet squats, hammer curl + press, lat pulldown machine, seated hamstring curls, V-ups.
- **Workout B:** side planks, glute bridges, air squats, dumbbell deadlifts, mid-row machine, assisted push-ups, lateral raises, flutter kicks.
- **Custom:** tick any of these exercises and put them in your own order.
- **Reps:** *Card* (the trainer's numbers), 8, 10 or 12 reps per set, or *Custom* reps or seconds for each set (0 skips a set), with a weight note per exercise and a choice of rest between sets.

Exercises live in one library. Each one carries its own plan type, scene and voice pack, and a workout is a list of exercise ids, so back and gym exercises can be mixed in one workout later.

## Workout video

[`video/Back-Exercises-Beginner-Workout.mp4`](video/Back-Exercises-Beginner-Workout.mp4) is the full Beginner guided workout as a video (1080p, 11 min 13 s, with voice and beeps), for playing on a TV without the app.

## Recorded voice

The voice is in `voice/clips.*` for the back exercises and `voice/gym.*` for the gym page (about 2–2.5 MB each, loaded when a workout or exercise starts). It was made with [Piper](https://github.com/rhasspy/piper) and the public-domain LJSpeech voice (`en_US-ljspeech-high`). Each line plays as a whole clip when it was recorded. Otherwise, as with custom plan numbers, it's joined from pieces and number clips (1–60 for back, 1–90 for gym). If the clips can't load, the browser's built-in speech is used instead.

After changing any spoken wording, re-record the clips:

```
pip install piper-tts                                # plus en_US-ljspeech-high.onnx(.json) from huggingface.co/rhasspy/piper-voices
node tools/voice-lines.js back > back-lines.json     # needs Playwright + Chromium
python tools/make-voice.py back-lines.json en_US-ljspeech-high.onnx voice/clips 60
node tools/voice-lines.js gym > gym-lines.json
python tools/make-voice.py gym-lines.json en_US-ljspeech-high.onnx voice/gym 90
```

## Deploy with GitHub Pages

1. In the repository, open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to *Deploy from a branch*, pick `main` and `/ (root)`, then **Save**.
3. After a minute the site is live at `https://kgram1989.github.io/Back-Exercises/`.

This page is a visual aid only and does not replace advice from your health care provider.
