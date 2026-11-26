# windo-shoppin-media

Post media for [@windo_shoppin](https://www.instagram.com/windo_shoppin/) on Instagram.

Each post lives in `posts/YYYY-MM-DD-slug/slides.html`. On every push, the **Render slides**
workflow runs `render.py`, which turns it into carousel slides (`01.png`, `02.png` ...),
a Reel (`reel.mp4`) and a Story (`story.png`). Metricool publishes from these files.
