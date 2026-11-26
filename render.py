"""Render each posts/<post>/slides.html into Instagram-ready files:
  01.png, 02.png ...  carousel slides, 1080x1350
  reel.mp4            9:16 Reel of the slides (1080x1920, ~2.5 s per slide)
  story.png           9:16 Story announcing the post (1080x1920)
Slides in slides.html are separated by a line containing <!--SLIDE-->.
A post is skipped when .rendered holds the hash of its slides.html and this script."""
import asyncio, base64, hashlib, pathlib, subprocess, tempfile
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).parent
VERSION = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:12]
W, H, VH = 1080, 1350, 1920
XF = 0.35  # cross-fade seconds


def bg_hex(png):
    from PIL import Image
    r, g, b = Image.open(png).convert('RGB').getpixel((6, 6))
    return f'{r:02X}{g:02X}{b:02X}'


def make_reel(post, pngs):
    durs = [3.0] + [2.6] * (len(pngs) - 2) + [3.2] if len(pngs) > 1 else [4.0]
    total = sum(durs) - XF * (len(pngs) - 1)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error']
    for p, d in zip(pngs, durs):
        cmd += ['-loop', '1', '-t', f'{d}', '-i', str(p)]
    cmd += ['-f', 'lavfi', '-t', f'{total}', '-i', 'anullsrc=r=44100:cl=stereo']
    f = []
    for i, p in enumerate(pngs):
        f.append(f'[{i}:v]scale={W}:{H},pad={W}:{VH}:0:{(VH - H) // 2}:color=0x{bg_hex(p)},'
                 f'setsar=1,fps=30,format=yuv420p[v{i}]')
    last, off = 'v0', 0.0
    for i in range(1, len(pngs)):
        off += durs[i - 1] - XF
        f.append(f'[{last}][v{i}]xfade=transition=slideleft:duration={XF}:offset={off:.2f}[x{i}]')
        last = f'x{i}'
    cmd += ['-filter_complex', ';'.join(f), '-map', f'[{last}]', '-map', f'{len(pngs)}:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', str(post / 'reel.mp4')]
    subprocess.run(cmd, check=True)


STORY = """<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0}}</style></head><body>
<div style="width:1080px;height:1920px;background:#{bg};font-family:Poppins,sans-serif;display:flex;flex-direction:column;
align-items:center;justify-content:center;gap:48px">
<span style="background:#B8322B;color:#fff;font-weight:800;font-size:44px;letter-spacing:3px;padding:16px 44px;border-radius:999px">NEW POST</span>
<img src="data:image/png;base64,{img}" style="width:920px;height:1150px;border-radius:36px;box-shadow:0 24px 60px rgba(30,35,64,.25)">
<span style="color:#1E2340;font-weight:700;font-size:46px">Tap my profile to see the full list</span>
</div></body></html>"""


async def main():
    posts = []
    for src in sorted(ROOT.glob('posts/*/slides.html')):
        stamp = hashlib.sha256(src.read_bytes()).hexdigest()[:12] + VERSION
        marker = src.parent / '.rendered'
        if marker.exists() and marker.read_text().strip() == stamp:
            continue
        parts = [p.strip() for p in src.read_text(encoding='utf-8').split('<!--SLIDE-->') if p.strip()]
        posts.append((src.parent, parts, marker, stamp))
    if not posts:
        print('nothing to render')
        return
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        sp = await b.new_page(viewport={'width': W, 'height': VH}, device_scale_factor=1)
        for post, parts, marker, stamp in posts:
            pngs = []
            for i, html in enumerate(parts, 1):
                png = post / f'{i:02d}.png'
                await pg.set_content(html, wait_until='load')
                await pg.evaluate('document.fonts.ready')
                await pg.screenshot(path=str(png), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
                pngs.append(png)
            img = base64.b64encode(pngs[0].read_bytes()).decode()
            await sp.set_content(STORY.format(bg=bg_hex(pngs[0]), img=img), wait_until='load')
            await sp.evaluate('document.fonts.ready')
            await sp.screenshot(path=str(post / 'story.png'), clip={'x': 0, 'y': 0, 'width': W, 'height': VH})
            make_reel(post, pngs)
            marker.write_text(stamp + '\n')
            print('rendered', post.name, len(pngs), 'slides + reel + story')
        await b.close()

asyncio.run(main())
