"""Photograph two saved /state responses with the incident-era Arcana duel UI."""
import argparse
import gzip
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


def read_frame(directory, filename):
    path = directory / filename
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def render(browser, frame, body, args, art):
    turn = frame["turn"]
    page = browser.new_page(viewport={"width": 1420, "height": 810},
                            device_scale_factor=2, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def serve(route):
        url = urlsplit(route.request.url)
        path = url.path
        if url.hostname != "arcana.test" or route.request.method != "GET":
            return route.abort()
        if path == "/state":
            return route.fulfill(body=body, content_type="application/json")
        if path == "/glossary":
            return route.fulfill(json={})
        if path == "/art":
            query = parse_qs(url.query)
            name = query["name"][0].lower()
            if name in art:
                image_url = art[name][int(query.get("crop") == ["art"])]
                if urlsplit(image_url).hostname == "cards.scryfall.io":
                    dest = args.cache / urlsplit(image_url).path.lstrip("/")
                    if not dest.exists():
                        request = Request(image_url, headers={"User-Agent": "ArcanaEssayCapture/1.0"})
                        with urlopen(request, timeout=25) as response:
                            data = response.read()
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(data)
                    return route.fulfill(path=dest, content_type="image/jpeg")
            return route.fulfill(status=404, body="No mapped card art")
        local = args.ui / ("index.html" if path == "/duel" else path.lstrip("/"))
        if local.resolve().is_relative_to(args.ui.resolve()) and local.is_file():
            return route.fulfill(path=local)
        return route.fulfill(status=404, body="No such resource")

    page.route("**/*", serve)
    page.goto("http://arcana.test/duel")
    board = page.locator("#opponent")
    board.locator(".ac-count").first.wait_for()
    board.locator('img[alt="Zombie"]').first.scroll_into_view_if_needed()
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    if errors:
        raise RuntimeError(errors)
    zombie_tiles = board.locator('.ac-card:has(img[alt="Zombie"])')
    counts = zombie_tiles.evaluate_all("""cards => cards.map(c => {
      const img = c.querySelector('img');
      if (!img.complete || !img.naturalWidth) throw Error('Missing Zombie art');
      return Number((c.querySelector('.ac-count')?.textContent || '1').replace('×',''));
    })""")
    if sum(counts) != frame["zombies"]:
        raise ValueError(f"Turn {turn} rendered {counts}, expected {frame['zombies']} Zombies")
    start = page.locator("#panel-board").bounding_box()
    end = page.locator("#youhud").bounding_box()
    clip = dict(start, height=end["y"] + end["height"] - start["y"])
    page.screenshot(path=args.out / f"battlefield-turn-{turn}.png", clip=clip,
                    animations="disabled")
    print(f"Turn {turn}, Zombie pile sizes {counts}, crop {clip}")
    page.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["ui", "frames", "out", "art-map", "cache"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    art = {}
    for line in args.art_map.read_text().splitlines():
        name, normal, crop = line.split("\t")
        art[name] = (normal, crop)
    manifest = json.loads((args.frames / "manifest.json").read_text())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for frame in manifest["frames"]:
            render(browser, frame, read_frame(args.frames, frame["file"]), args, art)
        browser.close()


if __name__ == "__main__":
    main()
