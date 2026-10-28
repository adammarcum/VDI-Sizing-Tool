"""Self-contained, AHEAD-branded HTML report for a VDI sizing (works offline / emailed)."""
import base64
import os
from datetime import date
from html import escape

import vdi_engine as E

APP_DIR = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--blue:#009FDC;--bright:#1C4CBF;--green:#00B388;--navy:#123A61;--deep:#102033;--surface:#EBF0F2;--char:#2A2A2A;--red:#C62828;--amber:#B26A00}
*{box-sizing:border-box}body{margin:0;font-family:Poppins,Verdana,sans-serif;color:var(--char);background:#fff;-webkit-font-smoothing:antialiased}
.wrap{max-width:1140px;margin:0 auto;padding:0 32px}
.top{background:var(--deep);position:sticky;top:0;z-index:5}.top .wrap{display:flex;align-items:center;gap:26px;height:60px}
.top img{height:18px}.top a{color:rgba(255,255,255,.85);text-decoration:none;font-size:13px}.top button{margin-left:auto;background:var(--bright);color:#fff;border:0;border-radius:9999px;padding:9px 20px;font:500 13px Poppins,sans-serif;cursor:pointer}
.hero{background:linear-gradient(69deg,var(--deep),var(--navy));color:#fff;padding:48px 0 40px}
.eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--blue);font-weight:600}.hero .eyebrow{color:#67C3E9}
h1{font-size:34px;margin:8px 0 6px;font-weight:700}.hero p{margin:0;color:rgba(255,255,255,.8);font-size:14px}
.chip{display:inline-flex;align-items:center;gap:10px;margin-top:16px;background:rgba(255,255,255,.1);border-radius:9999px;padding:6px 16px;font-size:13px}.chip img{height:22px;background:#fff;border-radius:4px;padding:2px 6px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:28px}.stat{background:rgba(255,255,255,.08);border-radius:14px;padding:16px 18px}
.stat .v{font-size:30px;font-weight:700}.stat .v small{font-size:14px;font-weight:500;opacity:.8}.stat .l{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#67C3E9;margin-top:2px}
section{padding:38px 0 6px}h2{color:var(--navy);font-size:24px;margin:4px 0 14px}h3{color:var(--navy);font-size:16px;margin:18px 0 8px}
.card{border:1px solid #D6DEE3;border-radius:14px;padding:18px 20px;margin-bottom:16px;background:#fff}
table{width:100%;border-collapse:collapse;font-size:13.5px}th{background:var(--navy);color:#fff;font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:500;text-align:left;padding:10px 12px}
td{padding:9px 12px;border-bottom:1px solid var(--surface)}td.n,th.n{text-align:right}tr.tot td{font-weight:600;color:var(--navy);background:var(--surface)}
.ok{color:var(--green);font-weight:600}.bad{color:var(--red);font-weight:700}.warn{color:var(--amber);font-weight:600}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}.muted{color:#5b6b7b;font-size:12.5px}
.badge{display:inline-block;border-radius:9999px;padding:2px 12px;font-size:12px;font-weight:600}.b-ok{background:rgba(0,179,136,.14);color:#00805f}.b-bad{background:rgba(198,40,40,.12);color:var(--red)}
ol.m{padding-left:18px;font-size:13.5px;line-height:1.6}ul.s{padding-left:18px;font-size:13.5px;line-height:1.6}
footer{margin-top:40px;background:var(--deep);color:#8C9BAB;font-size:12px;padding:22px 0}
@media print{.top{display:none}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}section{break-inside:avoid}}
"""


def data_uri(path, mime="image/png"):
    try:
        with open(path, "rb") as fh:
            return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()
    except OSError:
        return ""


def n0(x):
    return f"{x:,.0f}"


def tbl(head, rows, num_from=1, total_last=False):
    h = "".join(f"<th class='{'n' if i >= num_from else ''}'>{escape(c)}</th>" for i, c in enumerate(head))
    body = ""
    for ri, r in enumerate(rows):
        cls = " class='tot'" if total_last and ri == len(rows) - 1 else ""
        body += f"<tr{cls}>" + "".join(f"<td class='{'n' if i >= num_from else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return f"<table><tr>{h}</tr>{body}</table>"


def cand_label(c):
    return f"{c['spec']['model']} ({c['spec']['sockets']} x {c['spec']['cores_per_socket']:.0f} c, {c['spec']['clock']:.2f} GHz, {c['spec']['mem']:,.0f} GB)"


def fmt_status(ok, t_ok="Within limits", t_bad="Exceeds limits"):
    return f"<span class='badge {'b-ok' if ok else 'b-bad'}'>{t_ok if ok else t_bad}</span>"


def tb(gb):
    """Capacity as GB (matches the spreadsheet) with TB alongside for larger amounts."""
    return f"{gb:,.0f} GB ({gb / 1024:,.1f} TB)" if gb >= 1024 else f"{gb:,.0f} GB"


def generate_report(res, customer="My Customer", customer_logo_uri=None, project=""):
    p, d, fut = res["params"], res["day1"], res["future"]
    cands = res["candidates"]
    ahead_logo = data_uri(os.path.join(APP_DIR, "ahead_logo_white.png"))
    best = next((c for c in cands if c["eval"].get("ok")), cands[0] if cands else None)
    chip = (f"<img src='{customer_logo_uri}' alt=''>" if customer_logo_uri else "") + f"Prepared for {escape(customer)}"

    stats = [(n0(d["d_users"] + d["r_users"]), "", "Concurrent users"), (n0(d["vms"]), "", "Virtual machines"),
             (str(best["hosts"]) if best else "-", " hosts", "Recommended" if best else "No host selected"),
             (tb(d["storage_net"]), "", "Storage after dedupe")]
    stat_html = "".join(f"<div class='stat'><div class='v'>{v}<small>{escape(u)}</small></div><div class='l'>{l}</div></div>"
                        for v, u, l in stats)

    # workloads
    wl = [[escape(x["name"]), escape(x["cls"]), n0(x["users"]), f"{x['vcpu']:g}", f"{x['mem']:g} GB",
           f"{x['gpu']:g} GB" if x["gpu"] else "-", n0(x["cores"]), n0(x["mem_total"]) + " GB", tb(x["disk"])] for x in d["desktops"]]
    wl_html = ""
    if wl:
        wl.append(["Total desktops", "", n0(d["d_users"]), "", "", "", n0(d["d_cores"]), n0(d["d_mem"]) + " GB", tb(d["d_disk"])])
        wl_html += "<h3>Desktop workloads</h3>" + tbl(["User type", "Class", "Concurrent", "vCPU", "Memory", "vGPU", "Total vCPU", "Total memory", "Disk (pre-opt.)"], wl, 2, True)
    rw = [[escape(x["name"]), escape(x["cls"]), n0(x["users"]), f"{x['users_per_server']:g}", n0(x["servers"]), n0(x["cores"]),
           n0(x["mem_total"]) + " GB", tb(x["disk"])] for x in d["rdsh"]]
    if rw:
        rw.append(["Total RDSH", "", n0(d["r_users"]), "", n0(d["r_servers"]), n0(d["r_cores"]), n0(d["r_mem"]) + " GB", tb(d["r_disk"])])
        wl_html += "<h3>RDSH workloads</h3>" + tbl(["Farm", "Class", "Concurrent users", "Users / server", "Servers", "Total vCPU", "Total memory", "Disk (pre-opt.)"], rw, 2, True)
    if not wl_html:
        wl_html = "<p class='muted'>No workloads entered.</p>"

    # hosts
    host_html = ""
    x = p["ha_nodes"]
    if cands:
        head = ["Metric"] + [escape(c["spec"]["model"]) for c in cands]

        def row(label, fn):
            return [label] + [fn(c) for c in cands]
        ev = lambda c: c["eval"]
        rows = [
            row("Host", lambda c: escape(cand_label(c))),
            row(f"Calculated hosts (N+{x})", lambda c: str(c["solve"]["calc_hosts"]) if not c["solve"]["unsized"] else "n/a"),
            row("Hosts used" , lambda c: "n/a" if c["solve"]["unsized"] else f"{c['hosts']}" + (" (manual)" if c["forced"] else "")),
            row("Limiting resource", lambda c: escape(c["solve"]["constraint"])),
            row("Clusters", lambda c: "n/a" if c["solve"]["unsized"] else (str(c["solve"]["clusters"]) if not c["forced"] else "1")),
            row(f"vCPU:pCore, N-{x}", lambda c: f"{ev(c)['overcommit']:.2f}:1" if "overcommit" in ev(c) else "-"),
            row(f"vCPU:pCore with HT (x{p['ht_factor']:.1f}), N-{x}", lambda c: f"{ev(c)['ht_overcommit']:.2f}:1" if "ht_overcommit" in ev(c) else "-"),
            row(f"GHz per user, N-{x}", lambda c: f"{ev(c)['ghz_per_user']:.2f}" if "ghz_per_user" in ev(c) else "-"),
            row(f"Memory remaining, N-{x}", lambda c: f"{ev(c)['mem_remaining']:,.0f} GB" if "mem_remaining" in ev(c) else "-"),
            row("GPU memory remaining", lambda c: f"{ev(c)['gpu_remaining']:,.0f} GB" if "gpu_remaining" in ev(c) else "-"),
            row(f"VMs per host, N-{x}", lambda c: str(ev(c)["vms_per_host"]) if "vms_per_host" in ev(c) else "-"),
            row("Licensed cores", lambda c: "n/a" if c["solve"]["unsized"] else n0(c["lic_cores"])),
            row("Design check", lambda c: fmt_status(ev(c)["ok"], "Passes", "Fails")),
        ]
        if res["grown"]:
            rows.insert(3, row(f"Future hosts ({p['years']} yrs, {p['growth_pct']:g}%/yr)",
                               lambda c: str(c["future"]["solve"]["calc_hosts"]) if not c["future"]["solve"]["unsized"] else "n/a"))
        host_html = tbl(head, rows, 1)
        host_html += "<h3>Design check detail</h3><ul class='s'>" + "".join(
            f"<li><b>{escape(c['spec']['model'])}</b>: " + " ".join(
                f"<span class='{'bad' if bad else 'ok'}'>{escape(t)}</span>" for bad, t in c["eval"]["checks"]) + "</li>" for c in cands) + "</ul>"
    else:
        host_html = "<p class='muted'>No candidate host defined.</p>"

    # storage
    st_rows = [["Thick / PVS desktop disks (incl. swap)", tb(d["disk_thick"])],
               ["Instant clone / MCS disks (incl. swap)", tb(d["disk_clone"])],
               ["Profile storage", tb(d["disk_profile"])],
               ["Total pre-optimisation (desktops + RDSH)", tb(d["disk"])],
               [f"After {p['dedupe']:g}:1 dedupe", tb(d["storage_net"])],
               [f"With {p['storage_reserve']:g}% free-space reserve", tb(d["storage_reserve"])]]
    storage_html = tbl(["Storage", "Capacity"], st_rows, 1, True)

    limits = "".join(f"<tr><td>{escape(k)}</td><td class='n'>{v:g}:1</td></tr>" for k, v in p["class_limits"].items())
    assump = f"""
    <div class='grid2'><div class='card'><h3>Settings used</h3><ul class='s'>
      <li>Failure tolerance: N+{p['ha_nodes']}; minimum cluster {p['min_hosts']} hosts; cluster cap {p['max_hosts']} hosts</li>
      <li>Reserved for hypervisor and overhead: {p['cpu_overhead']}% CPU, {p['ram_overhead']}% RAM</li>
      <li>Hyper-threading uplift {p['ht_factor']:.1f}x; RDSH session weight {p['rdsh_weight']:.1f} in GHz per user</li>
      <li>Dedupe {p['dedupe']:g}:1; storage free-space reserve {p['storage_reserve']:g}%</li>
      <li>Growth {p['growth_pct']:g}% per year for {p['years']} years</li>
      {f"<li>Maximum {p['max_vms_per_host']} VMs per host</li>" if p['max_vms_per_host'] else ""}</ul></div>
    <div class='card'><h3>vCPU:pCore design limits by class</h3><table>{limits}</table>
    <p class='muted'>Planning defaults pending AHEAD review; adjust per customer.</p></div></div>"""

    method = ["<b>Workload:</b> concurrent desktops x vCPU, memory and vGPU memory per desktop. RDSH servers = users / users per server, then the same per server.",
              "<b>Usable host:</b> cores and memory per host less the CPU and RAM overhead reserved for the hypervisor.",
              "<b>Host count:</b> the largest of CPU (cores needed to keep each class within its vCPU:pCore limit), memory, GPU memory and optional VMs per host; HA hosts (X) are added, then the minimum cluster size and cluster cap are applied.",
              f"<b>Checks:</b> evaluated with {p['ha_nodes']} host(s) failed (N-{p['ha_nodes']}): vCPU:pCore (and with hyper-threading), GHz per user, memory and GPU memory remaining, VMs per host.",
              "<b>Storage:</b> desktop and RDSH disk, swap space and profiles, combined, then divided by the dedupe ratio, with an optional free-space reserve."]
    method_html = "<ol class='m'>" + "".join(f"<li>{m}</li>" for m in method) + "</ol>"
    note = ("This is a planning estimate based on the inputs provided. Storage performance (IOPS), network, application licensing and "
            "user-experience testing (e.g., a pilot) are not included and should be confirmed during design.")

    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{escape(customer)} - VDI Host Sizing | AHEAD</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<link href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap' rel='stylesheet'><style>{CSS}</style></head><body>
<div class='top'><div class='wrap'>{f"<img src='{ahead_logo}' alt='AHEAD'>" if ahead_logo else "<b style='color:#fff'>AHEAD</b>"}
<a href='#workloads'>Workloads</a><a href='#hosts'>Hosts</a><a href='#storage'>Storage</a><a href='#method'>Method</a>
<button onclick='window.print()'>Print / Save PDF</button></div></div>
<div class='hero'><div class='wrap'><div class='eyebrow'>VDI host sizing</div><h1>{escape(project or customer)}</h1>
<p>Virtual desktop infrastructure on VMware ESXi. Prepared {date.today():%B %d, %Y}.</p><div class='chip'>{chip}</div>
<div class='stats'>{stat_html}</div></div></div>
<div class='wrap'>
<section id='workloads'><div class='eyebrow'>Demand</div><h2>Workloads</h2><div class='card'>{wl_html}</div></section>
<section id='hosts'><div class='eyebrow'>Recommendation</div><h2>Host sizing</h2><div class='card'>{host_html}</div></section>
<section id='storage'><div class='eyebrow'>Capacity</div><h2>Storage</h2><div class='card'>{storage_html}</div></section>
<section id='assumptions'><div class='eyebrow'>Inputs</div><h2>Assumptions</h2>{assump}</section>
<section id='method'><div class='eyebrow'>How it was done</div><h2>Sizing method</h2><div class='card'>{method_html}<p class='muted'>{escape(note)}</p></div></section>
</div><footer><div class='wrap'>Confidential to AHEAD and {escape(customer)} &middot; Accelerate Your Impact</div></footer></body></html>"""
