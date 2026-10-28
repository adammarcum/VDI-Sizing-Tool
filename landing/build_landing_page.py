"""Builds the single-file landing page (HTML) for the current release.
Run from anywhere:  python landing/build_landing_page.py
Reads the version from vdi_app.py, the release notes from CHANGELOG.md, the design defaults from vdi_engine.py and the
screenshots from landing/assets (refresh them with capture_screenshots.py). Output: landing/dist/VDI_Host_Sizer_Landing_Page.html
"""
import base64
import os
import re
import sys
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import vdi_engine as E  # noqa: E402

REPO = "https://github.com/adammarcum/VDI-Sizing-Tool"
ZIP = REPO + "/archive/refs/heads/main.zip"
MAC_CMD = "curl -fsSL https://raw.githubusercontent.com/adammarcum/VDI-Sizing-Tool/main/install_mac.sh | bash"
OUT = os.path.join(HERE, "dist", "VDI_Host_Sizer_Landing_Page.html")


def b64(path, mime="image/png"):
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


def version():
    src = open(os.path.join(ROOT, "vdi_app.py"), encoding="utf-8").read()
    return re.search(r'^APP_VERSION = "([^"]+)"', src, re.M).group(1)


def md_inline(t):
    t = escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)\*(?![\w*])", r"<em>\1</em>", t)


def releases(n=2):
    """[(version, date, intro, [bullets])] for the newest n entries of CHANGELOG.md."""
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    out = []
    for block in re.split(r"^## ", text, flags=re.M)[1:n + 1]:
        head, *body = block.splitlines()
        m = re.match(r"([\d.]+)\s*(?:\((.*?)\))?", head)
        lines = [l for l in body if l.strip()]
        out.append((m.group(1), m.group(2) or "", [l for l in lines if not l.startswith("*")],
                    [l[1:].strip() for l in lines if l.startswith("*")]))
    return out


def release_cards(ver):
    cards = ""
    for i, (v, date, intro, bullets) in enumerate(releases()):
        klass, pill = ("green", "<span class='pill'>Latest release</span>") if i == 0 else \
                      ("navy", "<span class='pill prev'>Previous release</span>")
        lis = "".join(f"<li>{md_inline(b)}</li>" for b in bullets)
        cards += (f"<div class='card release {klass}'><div class='head'><div class='label'>Version {escape(v)}"
                  f"{' · ' + escape(date) if date else ''}</div>{pill}</div><h4>What&#39;s new in {escape(v)}</h4>"
                  + (f"<p>{md_inline(' '.join(intro))}</p>" if intro else "") + f"<ul>{lis}</ul></div>")
    return cards


def class_table():
    rows = "".join(f"<tr><td>{escape(k)}</td><td>{v[0]:g} : 1</td><td>{escape(v[1])}</td></tr>" for k, v in E.CLASS_LIMITS.items())
    return f"<table><tr><th>Workload class</th><th>vCPU : pCore limit</th><th>Typical range</th></tr>{rows}</table>"


def shot(name, alt, caption):
    p = os.path.join(HERE, "assets", f"{name}.png")
    if not os.path.exists(p):
        return ""
    return (f"<figure><div class='frame'><div class='bar'><span></span><span></span><span></span></div>"
            f"<img src='{b64(p)}' alt='{escape(alt)}' loading='lazy'></div><figcaption>{caption}</figcaption></figure>")


CSS = open(os.path.join(HERE, "landing.css"), encoding="utf-8").read()
BODY = open(os.path.join(HERE, "landing_body.html"), encoding="utf-8").read()


def build():
    v = version()
    subs = {
        "VERSION": escape(v), "ZIP": ZIP, "REPO": REPO, "MAC_CMD": escape(MAC_CMD),
        "AHEAD_WHITE": b64(os.path.join(ROOT, "ahead_logo_white.png")),
        "LOCKUP": b64(os.path.join(ROOT, "vdi_sizer_logo_white.png")),
        "ICON": b64(os.path.join(ROOT, "vdi_sizer_icon.png")),
        "RELEASES": release_cards(v), "CLASS_TABLE": class_table(),
        "SHOTS": "".join([
            shot("home", "Home", "<strong>Home.</strong> Name the sizing, start fresh or load the example, and reopen saved projects from your local library."),
            shot("workloads", "Workloads", "<strong>Workloads.</strong> One row per desktop user type or RDSH farm, with names you choose: users, vCPU, memory, vGPU, disk and profile storage."),
            shot("hardware", "Hardware", "<strong>Hardware.</strong> Up to three candidate hosts side by side, with a processor picker and an optional host-count override."),
            shot("recommendation", "Recommendation", "<strong>Recommendation.</strong> The design rules, then the host count with its N+X failure tolerance and the limiting resource."),
            shot("design_check", "Design check", "<strong>Design check at N-X.</strong> vCPU:pCore, GHz per user, memory left and VMs per host with the failed hosts removed."),
            shot("report_top", "Report header", "<strong>Report.</strong> The customer-facing HTML report opens with who it is for and the headline numbers."),
            shot("report_hosts", "Report host sizing", "<strong>Report: host sizing.</strong> Each candidate side by side, labeled with the failure tolerance used."),
        ]),
        "RATIO_STAT": f"{len(E.CLASS_LIMITS)} classes",
    }
    html = BODY
    for k, val in subs.items():
        html = html.replace("{{" + k + "}}", val)
    left = re.findall(r"\{\{[A-Z_]+\}\}", html)
    assert not left, f"unfilled placeholders: {left}"
    page = (f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n<meta charset='utf-8'>\n"
            f"<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            f"<title>VDI Host Sizer | Powered by AHEAD</title>\n<link rel='icon' type='image/png' href='{subs['ICON']}'>\n"
            "<link rel='preconnect' href='https://fonts.googleapis.com'>\n<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>\n"
            "<link href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&family=PT+Serif:ital@1&display=swap' rel='stylesheet'>\n"
            f"<style>\n{CSS}\n</style>\n</head>\n<body>\n{html}\n</body>\n</html>\n")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Landing page for v{v}: {OUT} ({len(page) / 1024:,.0f} KB)")


if __name__ == "__main__":
    build()
