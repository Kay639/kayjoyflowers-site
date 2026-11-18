"""Make blog hero images (WebP, 4:3) and share images (JPEG, 1200x630) from Kay's six originals."""
import json, sys
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1])
U = sys.argv[2] if len(sys.argv) > 2 else "content/blog/hero-originals/"  # folder holding the six original images
# slug: (source, filename, focal y 0-1 for crops, alt text)
HEROES = {
 "why-body-still-braces": (U + "f0c08b18-image.png", "woman-sage-sweater-window-reflection", 0.36,
   "A woman in a sage-green sweater sits by a window, chin resting on her hand, looking out thoughtfully."),
 "why-receiving-feels-dangerous": (U + "67df5fa6-image.png", "woman-open-hands-golden-sunlight", 0.42,
   "A woman in an ivory embroidered blouse stands in golden sunlight with her eyes closed and her hands open."),
 "overwhelmed-cant-think-clearly": (U + "c6050c56-image.png", "woman-desk-unfinished-work", 0.40,
   "A woman in a slate-blue cardigan sits at a desk covered in papers and books, resting her chin on her hand."),
 "who-are-you-beyond-your-roles": (U + "d2f0cf9f-image.png", "woman-teal-coat-ocean-cliff", 0.30,
   "A woman in a deep teal coat stands on a windswept ocean cliff, eyes closed and face turned to the sky."),
 "frequency-and-healing": (U + "079c151c-image.png", "golden-ripples-indigo-water", 0.42,
   "Golden ripples spreading in rings across deep indigo water."),
 "teacher-exhaustion-survival-mode": (U + "fd09bb99-image.png", "empty-classroom-afternoon-light", 0.55,
   "An empty classroom in afternoon sunlight, with books, a mug and a mustard-coloured bag on the teacher's desk."),
}

def crop(im, ratio, fy):
    w, h = im.size
    ch = round(w / ratio)
    if ch > h:
        cw = round(h * ratio); x = (w - cw) // 2
        return im.crop((x, 0, x + cw, h))
    top = min(max(round(fy * h - ch / 2), 0), h - ch)
    return im.crop((0, top, w, top + ch))

out = root / "images" / "blog"; out.mkdir(parents=True, exist_ok=True)
manifest = {}
for slug, (src, name, fy, alt) in HEROES.items():
    im = Image.open(src).convert("RGB")
    hero = crop(im, 4 / 3, fy)                      # 1122 x 842
    sizes = {}
    for w in (640, hero.width):
        r = hero if w == hero.width else hero.resize((w, round(w * hero.height / hero.width)), Image.LANCZOS)
        p = out / f"{name}-{w}.webp"
        r.save(p, "WEBP", quality=80, method=6)
        sizes[w] = (p.name, r.height, p.stat().st_size)
    og = crop(im, 1200 / 630, fy).resize((1200, 630), Image.LANCZOS)
    og.save(root / "images" / "og" / f"blog-{slug}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
    manifest[slug] = {"name": name, "alt": alt, "widths": sorted(sizes), "full": [hero.width, hero.height]}
    print(slug, {w: f"{s[0]} {s[2]//1024}KB" for w, s in sizes.items()})
(root / "content" / "blog" / "heroes.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
