"""Joins the rendered exercise segments into one MP4 with a beep sound track.
Usage: python3 assemble.py <renderDir> <out.mp4>
"""
import json, math, os, struct, subprocess, sys, wave

src, out = sys.argv[1], sys.argv[2]
segs = sorted((d for d in os.listdir(src) if d.startswith('seg') and os.path.isdir(os.path.join(src, d))), key=lambda d: int(d[3:]))
RATE = 44100
DUR = {990: 0.12, 660: 0.10, 880: 0.15, 1175: 0.25}  # beep lengths used by the app

# 1. Encode each segment.
parts, beeps, offset = [], [], 0.0
for d in segs:
    meta = json.load(open(os.path.join(src, d, 'meta.json')))
    fps, frames = meta['fps'], meta['frames']
    length = frames / fps
    for b in meta['beeps']:
        if b['t'] < length:  # beeps at the very end belong to the next segment's start
            beeps.append((offset + b['t'], round(b['f'])))
    mp4 = os.path.join(src, f'{d}.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', os.path.join(src, d, 'f%06d.jpg'),
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-tune', 'animation', '-pix_fmt', 'yuv420p', mp4], check=True)
    parts.append(mp4)
    offset += length
    print(f'{d}: {frames} frames, {length:.1f}s')

# 2. Beep sound track (the app's tone: quick rise, then fade).
n = int(math.ceil(offset * RATE)) + RATE
pcm = [0.0] * n
for t, f in beeps:
    dur = DUR.get(f, 0.12)
    start = int(t * RATE)
    for i in range(int(dur * RATE)):
        x = i / RATE
        env = 0.25 * (x / 0.02) if x < 0.02 else 0.25 * math.exp(math.log(0.0004) * (x - 0.02) / max(0.01, dur - 0.02))
        if start + i < n:
            pcm[start + i] += env * math.sin(2 * math.pi * f * x)
wav = os.path.join(src, 'beeps.wav')
with wave.open(wav, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
    w.writeframes(b''.join(struct.pack('<h', max(-32767, min(32767, int(v * 32767)))) for v in pcm))
print(f'{len(beeps)} beeps')

# 3. Join and add the sound.
lst = os.path.join(src, 'list.txt')
with open(lst, 'w') as fh:
    fh.writelines(f"file '{p}'\n" for p in parts)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart',
                '-metadata', 'title=Back Exercises — Beginner workout', out], check=True)
print(f'wrote {out}: {offset/60:.1f} min')
