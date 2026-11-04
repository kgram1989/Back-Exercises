"""Records the guided workout's voice clips with Piper and packs them for the app.

  node tools/voice-lines.js > voice-lines.json
  python tools/make-voice.py voice-lines.json en_US-ljspeech-high.onnx voice/

Writes voice/clips.bin (separate MP3 files, back to back) and voice/clips.json ({text: [offset, length, seconds]}).
The app uses the seconds to give every step enough time for its spoken line.
Clips: every whole line from the three presets, every fragment between numbers, and the numbers 1-60, so the
app can join any line for a custom plan. Needs piper-tts (pip) and ffmpeg. Voice: en_US-ljspeech-high
(LJSpeech, public domain) from https://huggingface.co/rhasspy/piper-voices.
"""
import json, os, re, struct, subprocess, sys, tempfile, wave
from piper import PiperVoice

lines_json, model, out_dir = sys.argv[1:4]
d = json.load(open(lines_json))
norm = lambda s: re.sub(r'^[.\s]+', '', s).strip()
texts = list(dict.fromkeys(d['lines'] + [norm(f) for f in d['fragments'] if norm(f)] + [str(n) for n in range(1, 61)]))

voice = PiperVoice.load(model)
tmp = tempfile.mkdtemp(prefix='clips-')
os.makedirs(out_dir, exist_ok=True)
index, blob = {}, bytearray()
for i, text in enumerate(texts):
    raw_wav = os.path.join(tmp, 'raw.wav')
    with wave.open(raw_wav, 'wb') as w:
        voice.synthesize_wav(text.replace('—', ',').replace('–', ' '), w)
    with wave.open(raw_wav, 'rb') as r:
        rate, data = r.getframerate(), r.readframes(r.getnframes())
    s = struct.unpack(f'<{len(data) // 2}h', data)
    # Trim silence at both ends, keeping 30 ms, so joined clips run on naturally.
    loud = [k for k, v in enumerate(s) if abs(v) > 300]
    pad = int(0.03 * rate)
    a, b = (max(0, loud[0] - pad), min(len(s), loud[-1] + pad)) if loud else (0, len(s))
    trimmed = os.path.join(tmp, 'trim.wav')
    with wave.open(trimmed, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack(f'<{b - a}h', *s[a:b]))
    mp3 = os.path.join(tmp, 'clip.mp3')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', trimmed, '-c:a', 'libmp3lame', '-b:a', '40k',
                    '-map_metadata', '-1', '-id3v2_version', '0', mp3], check=True)
    chunk = open(mp3, 'rb').read()
    secs = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3],
                                capture_output=True, text=True, check=True).stdout.strip())
    index[text] = [len(blob), len(chunk), round(secs, 3)]
    blob += chunk
open(os.path.join(out_dir, 'clips.bin'), 'wb').write(blob)
json.dump(index, open(os.path.join(out_dir, 'clips.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'{len(index)} clips, {len(blob) / 1e6:.2f} MB')
