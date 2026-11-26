"""Render posts/<post>/slides.html to posts/<post>/01.png, 02.png ... (1080x1350).
Slides inside slides.html are separated by a line containing <!--SLIDE-->."""
import asyncio, pathlib
from playwright.async_api import async_playwright

async def main():
    root = pathlib.Path(__file__).parent
    jobs = []
    for src in sorted(root.glob('posts/*/slides.html')):
        parts = [p.strip() for p in src.read_text(encoding='utf-8').split('<!--SLIDE-->') if p.strip()]
        for i, html in enumerate(parts, 1):
            jobs.append((html, src.parent / f'{i:02d}.png'))
    if not jobs:
        print('nothing to render')
        return
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=1)
        for html, png in jobs:
            await pg.set_content(html, wait_until='load')
            await pg.evaluate('document.fonts.ready')
            await pg.screenshot(path=str(png), clip={'x': 0, 'y': 0, 'width': 1080, 'height': 1350})
            print('rendered', png)
        await b.close()

asyncio.run(main())
