import re, json, subprocess, os, sys, glob, tempfile
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='ep001yt-')
F = os.path.join(OUT, 'fonts') + '/'
os.makedirs(F, exist_ok=True)
for wf in glob.glob(f'{SITE}/fonts/*.woff2'):
    t = TTFont(wf); t.flavor = None; t.save(F + os.path.basename(wf).replace('.woff2', '.ttf'))
W, H = 1920, 1080
DUR = 642.298776

def font(name, size): return ImageFont.truetype(F + name, size)
disp = lambda s: font('cormorant-garamond-latin-600-normal.ttf', s)
dispi = lambda s: font('cormorant-garamond-latin-500-italic.ttf', s)
body = lambda s: font('source-serif-4-latin-400-normal.ttf', s)
ui = lambda s: font('inter-latin-500-normal.ttf', s)

GOLD = (232, 196, 120); CREAM = (245, 238, 228); MUTED = (190, 178, 196)
COL = {'Iris': (229, 138, 168), 'Jonah': (158, 194, 169)}

segs = []
for ln in open(f'{SITE}/content/podcast/s01e001_transcript.txt', encoding='utf-8'):
    m = re.match(r'\[(\d+):(\d+\.\d)\] (\w+): (.*)', ln.strip())
    if m: segs.append((int(m[1]) * 60 + float(m[2]), m[3], m[4]))
chapters = json.load(open(f'{SITE}/podcast/s01e001/chapters.json'))['chapters']
def chapter_at(t):
    c = chapters[0]['title']
    for ch in chapters:
        if ch['startTime'] <= t + 0.05: c = ch['title']
    return c

cover = Image.open(f'{SITE}/podcast/podcast-cover.jpg').convert('RGB')
bg = cover.resize((W, W)).crop((0, (W - H) // 2, W, (W - H) // 2 + H)).filter(ImageFilter.GaussianBlur(40))
bg = ImageEnhance.Brightness(bg).enhance(0.32)
bgd = ImageDraw.Draw(bg)
CS = 860
bg.paste(cover.resize((CS, CS), Image.LANCZOS), (110, 110))
PX, PW = 1060, 760

def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def base():
    im = bg.copy(); d = ImageDraw.Draw(im)
    d.text((PX, 118), 'SERIES ONE  ·  WHO ARE YOU?  ·  EPISODE 001', font=ui(22), fill=GOLD)
    y = 160
    for l in wrap(d, 'Who Are You Beneath the Roles You’ve Been Playing?', disp(52), PW):
        d.text((PX, y), l, font=disp(52), fill=CREAM); y += 60
    d.line((PX, y + 18, PX + 120, y + 18), fill=GOLD, width=2)
    d.text((PX, 930), 'Created by Kay Joy Flowers  ·  Hosts Iris and Jonah are AI voices', font=ui(19), fill=MUTED)
    d.text((PX, 958), 'kayjoyflowers.online/podcast', font=ui(19), fill=GOLD)
    return im, y + 50

def frame(chap, spk, text):
    im, y = base(); d = ImageDraw.Draw(im)
    d.text((PX, y), chap, font=dispi(34), fill=GOLD); y += 70
    if spk:
        d.text((PX, y), spk.upper(), font=ui(24), fill=COL[spk]); y += 44
        for sz in (40, 36, 32, 29):
            lines = wrap(d, text, body(sz), PW)
            if y + len(lines) * sz * 1.4 < 900: break
        for l in lines:
            d.text((PX, y), l, font=body(sz), fill=CREAM); y += int(sz * 1.4)
    return im

os.makedirs(f'{OUT}/frames', exist_ok=True)
items = []
for i, (t, spk, text) in enumerate(segs):
    end = segs[i + 1][0] if i + 1 < len(segs) else DUR
    if i == 0 and t > 0.05: items.append((0, t, None, ''))
    items.append((t, end, spk, text))
concat = []
for i, (t, end, spk, text) in enumerate(items):
    p = f'{OUT}/frames/{i:03d}.png'
    frame(chapter_at(t), spk, text).save(p)
    concat.append(f"file '{p}'\nduration {end - t:.3f}")
concat.append(f"file '{OUT}/frames/{len(items)-1:03d}.png'")
open(f'{OUT}/list.txt', 'w').write('\n'.join(concat) + '\n')

# SRT for YouTube captions
def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60)
    return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}'
with open(f'{OUT}/s01e001.srt', 'w', encoding='utf-8') as f:
    n = 0
    for t, end, spk, text in items:
        if not spk: continue
        n += 1; f.write(f'{n}\n{ts(t)} --> {ts(end)}\n{spk}: {text}\n\n')
print(len(items), 'frames')

# Keep the last caption on screen through the audio tail with no extra frame.
last_frame_pts = round(items[-1][0] * 25) / 25
last_frame_duration = 642.262 - last_frame_pts
duration_filter = (
    f"setts=duration=if(eq(N\\,{len(items) - 1})"
    f"\\,round({last_frame_duration:.6f}/TB)\\,DURATION)"
)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', f'{OUT}/list.txt',
    '-i', f'{SITE}/podcast/audio/s01e001.mp3', '-map', '0:v', '-map', '1:a', '-fps_mode', 'vfr',
    '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', '20',
    '-bf', '0', '-bsf:v', duration_filter,
    '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', f'{OUT}/S01E001_youtube.mp4'], check=True)
print('wrote', f'{OUT}/S01E001_youtube.mp4')
