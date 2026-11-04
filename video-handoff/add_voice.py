"""Adds a spoken voice to the Beginner workout video, using the timing recorded when it was rendered.

Usage:
  python add_voice.py --video Back-Exercises-Beginner-Workout.mp4 --meta meta \
      --model en_US-ljspeech-high.onnx --out Back-Exercises-Beginner-Workout-voice.mp4
  (add --test-tones to check the timing with short tones instead of a voice; no voice model needed)

meta/seg0.json … seg6.json hold, per exercise segment: frames, fps and `spoken` = [{t, text}], where t is the
second within that segment at which the app spoke the line. Needs: piper-tts (pip), ffmpeg.
"""
import argparse, json, math, os, re, struct, subprocess, tempfile, wave

ap = argparse.ArgumentParser()
ap.add_argument('--video', required=True)
ap.add_argument('--meta', required=True)
ap.add_argument('--model')
ap.add_argument('--out', required=True)
ap.add_argument('--test-tones', action='store_true')
ap.add_argument('--list', action='store_true', help='print the spoken lines with their times and stop')
ap.add_argument('--beep-level', type=float, default=0.7)
args = ap.parse_args()

# 1. Timeline of spoken lines across the whole video.
segs = sorted((f for f in os.listdir(args.meta) if re.fullmatch(r'seg\d+\.json', f)), key=lambda f: int(f[3:-5]))
lines, offset = [], 0.0
for i, f in enumerate(segs):
    m = json.load(open(os.path.join(args.meta, f)))
    length = m['frames'] / m['fps']
    spoken = [s for s in m['spoken'] if s['t'] < length]  # lines at the very end belong to the next segment
    # The video was rendered before the app's own rest/round-pause wording existed; use the app's current wording:
    #   rest (start of every exercise after the first) -> "Rest for 10 seconds. Next: <exercise>."
    #   get-ready card                                  -> "Get ready: <exercise>. <n> <unit>."
    #   1 s round pause                                  -> silent (the next round announces itself)
    intro = [k for k, s in enumerate(spoken) if s['text'].startswith('Next: ')]
    for k, s in enumerate(spoken):
        text = s['text']
        if text.startswith('Next round'):
            continue
        if text.startswith('Next: '):
            name = text[6:].split('.')[0]
            if i > 0 and k == intro[0] and len(intro) > 1:
                text = f'Rest for 10 seconds. Next: {name}.'
            else:
                text = 'Get ready: ' + text[6:]
        if text.startswith('Workout ended'):
            text = 'Workout complete. Well done.'  # the closing screen shows the completed message
        lines.append((offset + s['t'], text))
    offset += length
total = offset
print(f'{len(lines)} spoken lines over {total / 60:.1f} min')
if args.list:
    for t, text in lines:
        print(f'{int(t // 60):2d}:{t % 60:05.2f}  {text}')
    raise SystemExit

# 2. Synthesise each distinct line once.
tmp = tempfile.mkdtemp(prefix='voice-')
clips = {}
if args.test_tones:
    rate = 22050
    for _, text in lines:
        if text not in clips:
            n = int(rate * min(2.5, 0.25 + 0.06 * len(text)))
            clips[text] = [0.3 * math.sin(2 * math.pi * 440 * k / rate) for k in range(n)]
else:
    from piper import PiperVoice
    voice = PiperVoice.load(args.model)
    rate = None
    for _, text in lines:
        if text in clips:
            continue
        path = os.path.join(tmp, f'{len(clips)}.wav')
        with wave.open(path, 'wb') as w:
            voice.synthesize_wav(text.replace('—', ','), w)
        with wave.open(path, 'rb') as r:
            rate = r.getframerate()
            raw = r.readframes(r.getnframes())
        clips[text] = [v / 32768 for v in struct.unpack(f'<{len(raw) // 2}h', raw)]

# 3. Voice track: each line at its moment; if it would run into the next line, fade it out there
#    (the app also cuts a line short when the next one starts).
track = [0.0] * (int(total * rate) + rate)
for idx, (t, text) in enumerate(lines):
    clip = clips[text]
    start = int(t * rate)
    end = int(lines[idx + 1][0] * rate) if idx + 1 < len(lines) else len(track)
    n = min(len(clip), end - start)
    fade = int(0.08 * rate)
    for k in range(max(0, n)):
        g = 1.0
        if len(clip) > end - start and k > n - fade:
            g = max(0.0, (n - k) / fade)
        if start + k < len(track):
            track[start + k] += clip[k] * g
voice_wav = os.path.join(tmp, 'voice.wav')
with wave.open(voice_wav, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b''.join(struct.pack('<h', max(-32767, min(32767, int(v * 32767)))) for v in track))

# 4. Mix with the video's existing beeps and write the new video (picture copied as is).
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', args.video, '-i', voice_wav, '-filter_complex',
                f'[0:a]volume={args.beep_level}[b];[1:a]aresample=44100,volume=1.0[v];[b][v]amix=inputs=2:duration=first:normalize=0[a]',
                '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', args.out], check=True)
print(f'wrote {args.out}')
