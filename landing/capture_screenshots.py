"""Capture fresh screenshots of the running app and report for the landing page.
Needs Playwright with Chromium:  pip install playwright && playwright install chromium
Usage (from the repo root):  python landing/capture_screenshots.py
"""
import asyncio
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(HERE, "assets")
sys.path.insert(0, ROOT)


def free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def example_report_html():
    import vdi_engine as E
    import vdi_report as R
    desk = [{"name": "Traders", "cls": "Power user", "users": 250, "vcpu": 8, "mem": 32, "disk": 512}]
    hosts = [{"model": "Intel Xeon 6747P", "sockets": 2, "cores": 48, "clock": 2.7, "mem": 1536, "override": 8}]
    res = E.compute(desk, [], hosts, {"cpu_overhead": 0, "ram_overhead": 0, "storage_reserve": 0})
    return R.generate_report(res, "Sample customer", None, "Sample - persistent desktops")


async def main():
    from playwright.async_api import async_playwright
    os.makedirs(ASSETS, exist_ok=True)
    port = free_port()
    env = dict(os.environ, VDI_HOSTSIZER_NO_UPDATE_CHECK="1")
    subprocess.run([sys.executable, os.path.join(ROOT, "vdi_app.py"), "--setup"], cwd=ROOT, capture_output=True)
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "vdi_app.py", "--server.headless", "true",
                             "--server.port", str(port)], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 1440, "height": 900})
            await pg.goto(f"http://localhost:{port}/"); await pg.wait_for_timeout(4000)
            await pg.get_by_role("button", name="Load example").click(); await pg.wait_for_timeout(2500)
            await pg.screenshot(path=f"{ASSETS}/home.png", clip={"x": 0, "y": 0, "width": 1440, "height": 760})
            for key, link in (("workloads", "Workloads"), ("hardware", "Hardware")):
                await pg.get_by_role("link", name=link).first.click(); await pg.wait_for_timeout(3500)
                await pg.screenshot(path=f"{ASSETS}/{key}.png", clip={"x": 0, "y": 0, "width": 1440, "height": 900 if key == "workloads" else 760})
            await pg.get_by_role("link", name="Recommendation").first.click(); await pg.wait_for_timeout(4500)
            await pg.set_viewport_size({"width": 1440, "height": 1000})
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=f"{ASSETS}/recommendation.png")
            el = pg.get_by_text("Design check at N-").first
            await el.scroll_into_view_if_needed(); await pg.evaluate("document.querySelector('[data-testid=stMain]').scrollBy(0, -20)")
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=f"{ASSETS}/design_check.png")
            rp = await b.new_page(viewport={"width": 1300, "height": 900})
            await rp.set_content(example_report_html()); await rp.wait_for_timeout(1200)
            await rp.screenshot(path=f"{ASSETS}/report_top.png", full_page=True, clip={"x": 0, "y": 0, "width": 1300, "height": 900})
            sec = await rp.locator("#hosts").bounding_box()
            await rp.screenshot(path=f"{ASSETS}/report_hosts.png", full_page=True, clip={"x": 0, "y": int(sec["y"]) - 20, "width": 1300, "height": 880})
            await b.close()
    finally:
        proc.terminate()
    # shrink the PNGs so the landing page stays light
    from PIL import Image
    for fn in os.listdir(ASSETS):
        if fn.endswith(".png"):
            path = os.path.join(ASSETS, fn)
            im = Image.open(path).convert("RGB")
            im = im.resize((1200, int(im.height * 1200 / im.width)), Image.LANCZOS)
            im.quantize(colors=128, method=Image.MEDIANCUT).save(path, optimize=True)
    print("screenshots in", ASSETS)


if __name__ == "__main__":
    asyncio.run(main())
