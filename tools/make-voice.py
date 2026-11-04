"""Records the guided workout's voice clips with Piper and packs them for the app.

  node tools/voice-lines.js back > back-lines.json
  python tools/make-voice.py back-lines.json en_US-ljspeech-high.onnx voice/clips 60
  node tools/voice-lines.js gym > gym-lines.json
  python tools/make-voice.py gym-lines.json en_US-ljspeech-high.onnx voice/gym 90

Writes <prefix>.bin (separate MP3 files, back to back) and <prefix>.json ({text: [offset, length]}).
Clips: every whole line from the presets, every fragment between numbers, and the numbers 1..N, so the
app can join any line for a custom plan. Needs piper-tts (pip) and ffmpeg. Voice: en_US-ljspeech-high
(LJSpeech, public domain) from https://huggingface.co/rhasspy/piper-voices.
"""
import json, os, re, struct, subprocess, sys, tempfile, wave
from piper import PiperVoice

lines_json, model, prefix = sys.argv[1:4]
max_n = int(sys.argv[4]) if len(sys.argv) > 4 else 60
d = json.load(open(lines_json))
norm = lambda s: re.sub(r'^[.\s]+', '', s).strip()
texts = list(dict.fromkeys(d['lines'] + [norm(f) for f in d['fragments'] if norm(f)] + [str(n) for n in range(1, max_n + 1)]))

voice = PiperVoice.load(model)
tmp = tempfile.mkdtemp(prefix='clips-')
os.makedirs(os.path.dirname(prefix) or '.', exist_ok=True)
index, blob = {}, bytearray()
for i, text in enumerate(texts):
    raw_wav = os.path.join(tmp, 'raw.wav')
    with wave.open(raw_wav, 'wb') as w:
        voice.synthesize_wav(text.replace('—', ',').replace('–', ' ').replace(' + ', ' and '), w)
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
    index[text] = [len(blob), len(chunk)]
    blob += chunk
open(prefix + '.bin', 'wb').write(blob)
json.dump(index, open(prefix + '.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'{len(index)} clips, {len(blob) / 1e6:.2f} MB')
