"""Assemble the 일상 주역 artifact page into a standalone PWA folder."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

SRC = sys.argv[1]
OUT = sys.argv[2]
VERSION = sys.argv[3] if len(sys.argv) > 3 else "v1"
os.makedirs(os.path.join(OUT, "icons"), exist_ok=True)

page = open(SRC, encoding="utf-8").read()
# drop artifact-only head bits; the real <head> below replaces them
page = page.replace("<title>일상 주역</title>\n", "").replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")

head = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>일상 주역</title>
<meta name="description" content="엽전 세 닢으로 주역 괘를 얻고 일상의 말로 풀이합니다.">
<meta name="theme-color" content="#EBEFE8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131816" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="일상 주역">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<style>
:root { color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }
html, body { margin: 0; }
img { max-width: 100%; }
[hidden] { display: none !important; }
body { -webkit-text-size-adjust: 100%; -webkit-tap-highlight-color: transparent; }
</style>
"""

sw_reg = """
<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
</script>
"""

# split the artifact body: everything up to the first <div class="wrap"> is head material (links + style)
i = page.index('<div class="wrap">')
html = head + page[:i] + "</head>\n<body>\n" + page[i:] + sw_reg + "</body>\n</html>\n"
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n").write(html)

manifest = {
    "name": "일상 주역",
    "short_name": "일상 주역",
    "description": "엽전 세 닢으로 주역 괘를 얻고 일상의 말로 풀이합니다.",
    "lang": "ko",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#EBEFE8",
    "theme_color": "#EBEFE8",
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
open(os.path.join(OUT, "manifest.webmanifest"), "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, ensure_ascii=False, indent=2))

sw = """// 일상 주역 offline cache. Bump VERSION whenever index.html changes.
const VERSION = "v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open("shell-" + VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("shell-") && k !== "shell-" + VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // Google Fonts: cache after first load so the app keeps its fonts offline
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(caches.open("fonts").then((c) => c.match(e.request).then((hit) => hit || fetch(e.request).then((res) => { c.put(e.request, res.clone()); return res; }))));
    return;
  }
  if (url.origin !== location.origin) return;
  // app shell: network first so updates show up, cache when offline
  e.respondWith(fetch(e.request).then((res) => {
    const copy = res.clone();
    caches.open("shell-" + VERSION).then((c) => c.put(e.request, copy));
    return res;
  }).catch(() => caches.match(e.request).then((hit) => hit || caches.match("index.html"))));
});
"""
open(os.path.join(OUT, "sw.js"), "w", encoding="utf-8", newline="\n").write(sw.replace('const VERSION = "v1";', 'const VERSION = "%s";' % VERSION))
open(os.path.join(OUT, ".nojekyll"), "w").close()

# icon: 인주 seal with 易 on celadon hanji
PAPER, SEAL = (235, 239, 232), (166, 52, 42)
FONT = r"C:\Windows\Fonts\NotoSerifKR-VF.ttf"

def icon(size, pad_ratio):
    S = size * 4
    img = Image.new("RGB", (S, S), PAPER)
    seal = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(seal)
    box = S * (1 - 2 * pad_ratio)
    x0 = (S - box) / 2
    w = int(box * 0.06)
    d.rounded_rectangle([x0, x0, x0 + box, x0 + box], radius=box * 0.08, outline=SEAL, width=w)
    f = ImageFont.truetype(FONT, int(box * 0.66))
    try:
        f.set_variation_by_axes([800])
    except Exception:
        pass
    d.text((S / 2, S / 2 + box * 0.02), "易", font=f, fill=SEAL, anchor="mm")
    seal = seal.rotate(4, resample=Image.BICUBIC, center=(S / 2, S / 2))
    img.paste(seal, (0, 0), seal)
    return img.resize((size, size), Image.LANCZOS)

icon(180, 0.16).save(os.path.join(OUT, "icons", "apple-touch-icon.png"))
icon(192, 0.16).save(os.path.join(OUT, "icons", "icon-192.png"))
icon(512, 0.16).save(os.path.join(OUT, "icons", "icon-512.png"))
icon(512, 0.24).save(os.path.join(OUT, "icons", "icon-maskable-512.png"))
print("built", OUT)
