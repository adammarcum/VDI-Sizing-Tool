"""
VDI Host Sizer - Powered by AHEAD
Sizes VMware ESXi hosts for virtual desktops (VDI) and RDSH using the AHEAD VDI Sizing Estimator method.

Files:  vdi_engine.py (sizing math, no Streamlit) · vdi_report.py (HTML report) · cpu_catalog.py (processors)
        vdi_app.py (this file: Streamlit UI)
"""
import json
import os
import re
import sys
from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

import vdi_engine as E
from cpu_catalog import CPU_BY_LABEL, CPU_CUSTOM, CPU_OPTIONS
from vdi_report import cand_label, data_uri, generate_report, tb

APP_TITLE = "VDI Host Sizer"
APP_VERSION = "1.0.1"
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Update check: reads only the version line of vdi_app.py on GitHub. Nothing about the user or their data is
# sent. Set VDI_HOSTSIZER_NO_UPDATE_CHECK=1 to turn it off.
REPO_URL = "https://github.com/adammarcum/VDI-Sizing-Tool"
UPDATE_SOURCE_URL = os.environ.get("VDI_HOSTSIZER_UPDATE_URL",
                                   "https://raw.githubusercontent.com/adammarcum/VDI-Sizing-Tool/main/vdi_app.py")
UPDATE_ZIP_URL = REPO_URL + "/archive/refs/heads/main.zip"
UPDATE_NOTES_URL = REPO_URL + "/blob/main/CHANGELOG.md"
MAC_INSTALL_CMD = "curl -fsSL https://raw.githubusercontent.com/adammarcum/VDI-Sizing-Tool/main/install_mac.sh | bash"
LOGO_WHITE = os.path.join(APP_DIR, "vdi_sizer_logo_white.png")
ICON = os.path.join(APP_DIR, "vdi_sizer_icon.png")
PROJECTS_DIR = os.path.expanduser(os.environ.get("HOSTSIZER_VDI_PROJECTS", os.path.join("~", "HostSizer", "VDIProjects")))
PROJECT_EXT = ".vdiproj"
MIN_STREAMLIT = (1, 50)
MAX_CANDIDATES = 3
RAM_OPTIONS = [256, 512, 768, 1024, 1536, 2048, 3072, 4096]

THEME_MARKER = "# Managed by VDI Host Sizer (vdi_app.py)."
THEME_TOML = THEME_MARKER + """ Delete this line to stop automatic updates.
[theme]
base = "light"
primaryColor = "#1C4CBF"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#EBF0F2"
textColor = "#2A2A2A"
linkColor = "#1C4CBF"
borderColor = "#D6DEE3"
showWidgetBorder = true
baseRadius = "0.6rem"
buttonRadius = "full"
font = "Poppins:https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap, Verdana, sans-serif"
headingFontWeights = [700, 600, 600, 600, 600, 600]
dataframeHeaderBackgroundColor = "#EBF0F2"
blueColor = "#009FDC"
greenColor = "#00B388"

[theme.sidebar]
backgroundColor = "#102033"
secondaryBackgroundColor = "#1B2E45"
textColor = "#FFFFFF"
primaryColor = "#67C3E9"
borderColor = "#2B3F58"

[browser]
gatherUsageStats = false
"""

APP_CSS = """<style>
.hs-brand { padding: 2px 2px 18px; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,.12); }
.hs-brand img.lockup { width: 100%; max-width: 230px; height: auto; display: block; }
.hs-brand .name { font-size: 26px; font-weight: 700; color: #FFFFFF; line-height: 1.05; }
.hs-brand .pb { margin-top: 7px; font-size: 12px; color: rgba(255,255,255,.8); }
.hs-label { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: #8C9BAB; font-weight: 600; margin: 12px 0 2px; }
.hs-eyebrow { font-size: 11px; letter-spacing: .18em; text-transform: uppercase; color: #1C4CBF; font-weight: 600; margin-bottom: 4px; }
.hs-big { font-size: 32px; font-weight: 700; color: #123A61; line-height: 1.15; }
.hs-big small { font-size: 15px; font-weight: 500; color: #333333; }
.hs-sub { font-size: 13.5px; color: #333333; line-height: 1.55; margin-top: 6px; }
.hs-kv { width: 100%; border-collapse: collapse; font-size: 14px; }
.hs-kv td { padding: 8px 0; border-bottom: 1px solid #EBF0F2; vertical-align: top; }
.hs-kv tr:last-child td { border-bottom: 0; }
.hs-kv td:first-child { color: #333333; width: 48%; padding-right: 12px; }
.hs-kv td:last-child { color: #123A61; font-weight: 500; text-align: right; }
.hs-kv td.red, .hs-over { color: #C62828 !important; font-weight: 700; }
.hs-cmp { width: 100%; border-collapse: collapse; font-size: 14px; }
.hs-cmp th { background: #123A61; color: #FFFFFF; font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
             font-weight: 500; text-align: left; padding: 11px 14px; }
.hs-cmp td { padding: 10px 14px; border-bottom: 1px solid #EBF0F2; color: #333333; }
.hs-cmp tr:last-child td { border-bottom: 0; }
.hs-cmp td:first-child { color: #123A61; font-weight: 500; }
.hs-update { background: rgba(0,179,136,.16); border: 1px solid rgba(110,206,178,.45); border-radius: 12px;
             padding: 12px 14px; margin: 4px 0 10px; color: #FFFFFF; font-size: 13px; line-height: 1.45; }
.hs-update .t { font-weight: 600; color: #6ECEB2; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
.hs-update .v { margin: 4px 0 10px; color: rgba(255,255,255,.88); }
.hs-update a { display: inline-block; text-decoration: none; font-weight: 500; font-size: 12.5px; border-radius: 9999px; }
.hs-update a.dl { background: #00B388; color: #FFFFFF; padding: 6px 14px; margin-right: 8px; }
.hs-update a.nt { color: #67C3E9; }
.hs-update .mac { margin-top: 8px; font-size: 11.5px; color: rgba(255,255,255,.7); }
.hs-tile-name { font-size: 15px; font-weight: 600; color: #123A61; word-break: break-all; }
</style>"""

# ----------------------------------------------------------------------------- state
CLASS_NAMES = list(E.CLASS_LIMITS)
DESKTOP_COLS = ["name", "cls", "users", "vcpu", "mem", "gpu", "disk", "image", "clone_pct", "profile"]
RDSH_COLS = ["name", "cls", "users", "users_per_server", "vcpu", "mem", "gpu", "disk", "image", "clone_pct", "profile"]
HOST_FIELDS = ["cpu_model", "sockets", "cores", "clock", "mem", "gpu", "override"]
PARAM_KEYS = ["ha_nodes", "min_hosts", "max_hosts", "cpu_overhead", "ram_overhead", "max_vms_per_host", "dedupe",
              "storage_reserve", "growth_pct", "years", "ht_factor", "rdsh_weight"] + [f"lim_{c}" for c in CLASS_NAMES]

BLANK_DESKTOPS = [{"name": "", "cls": E.DEFAULT_DESKTOP_CLASS, "users": 0, "vcpu": 2, "mem": 8, "gpu": 0, "disk": 0,
                   "image": 0, "clone_pct": 0, "profile": 0}]
BLANK_RDSH = [{"name": "", "cls": E.DEFAULT_RDSH_CLASS, "users": 0, "users_per_server": 15, "vcpu": 4, "mem": 32,
               "gpu": 0, "disk": 0, "image": 150, "clone_pct": 25, "profile": 10}]
DEFAULT_HOST = {"cpu_model": CPU_CUSTOM, "sockets": 2, "cores": 32, "clock": 2.5, "mem": 1024, "gpu": 0, "override": 0}

# Reproduces the AHEAD VDI Sizing Estimator sample (overheads off so the numbers match the spreadsheet exactly).
SAMPLE = {
    "customer": "Sample customer", "project": "Sample - persistent desktops",
    "desktops": [{"name": "Traders", "cls": "Power user", "users": 250, "vcpu": 8, "mem": 32, "gpu": 0, "disk": 512,
                  "image": 0, "clone_pct": 0, "profile": 0}],
    "rdsh": [],
    "hosts": [{"cpu_model": [c for c in CPU_BY_LABEL if "6747P" in c][0], "sockets": 2, "cores": 48, "clock": 2.7,
               "mem": 1536, "gpu": 0, "override": 8}],
    "params": {"cpu_overhead": 0, "ram_overhead": 0, "ha_nodes": 1, "dedupe": 1.5, "storage_reserve": 0},
}


def default_params():
    d = E.DEFAULT_PARAMS
    out = {k: d[k] for k in PARAM_KEYS if k in d}
    out.update({f"lim_{c}": E.CLASS_LIMITS[c][0] for c in CLASS_NAMES})
    return out


def load_state(desktops=None, rdsh=None, hosts=None, params=None, customer="My Customer", project="New VDI sizing"):
    ss = st.session_state
    ss.ver = ss.get("ver", 0) + 1                          # new editor keys so tables reload cleanly
    ss.desktops = pd.DataFrame(desktops or BLANK_DESKTOPS, columns=DESKTOP_COLS)
    ss.rdsh = pd.DataFrame(rdsh or BLANK_RDSH, columns=RDSH_COLS)
    for k in ("desktops_key", "rdsh_key"):               # force the editors to re-seed from the loaded tables
        ss.pop(k, None)
    hosts = hosts or [DEFAULT_HOST]
    ss.n_hosts = len(hosts)
    for i in range(MAX_CANDIDATES):
        h = {**DEFAULT_HOST, **(hosts[i] if i < len(hosts) else {})}
        for k in HOST_FIELDS:
            ss[f"h{i}_{k}"] = h[k]
    for k, v in {**default_params(), **(params or {})}.items():
        ss[k] = v
    ss.customer, ss.project, ss.saved_path = customer, project, None
    ss.cust_logo = None


def init_state():
    if "ver" not in st.session_state:
        load_state()


def current_inputs():
    ss = st.session_state
    return {
        "customer": ss.customer, "project": ss.project, "app_version": APP_VERSION,
        "desktops": ss.desktops.to_dict("records"), "rdsh": ss.rdsh.to_dict("records"),
        "hosts": [{k: ss[f"h{i}_{k}"] for k in HOST_FIELDS} for i in range(ss.n_hosts)],
        "params": {k: ss[k] for k in PARAM_KEYS},
    }


def engine_inputs():
    """Translate widget state into engine arguments."""
    ss = st.session_state
    ins = current_inputs()
    params = {
        "ha_nodes": int(ss.ha_nodes), "min_hosts": int(ss.min_hosts), "max_hosts": int(ss.max_hosts),
        "cpu_overhead": ss.cpu_overhead, "ram_overhead": ss.ram_overhead, "max_vms_per_host": int(ss.max_vms_per_host),
        "dedupe": float(ss.dedupe), "storage_reserve": ss.storage_reserve, "growth_pct": float(ss.growth_pct),
        "years": int(ss.years), "ht_factor": float(ss.ht_factor), "rdsh_weight": float(ss.rdsh_weight),
        "class_limits": {c: float(ss[f"lim_{c}"]) for c in CLASS_NAMES},
    }
    hosts = [{"model": (CPU_BY_LABEL[h["cpu_model"]]["name"] if h["cpu_model"] in CPU_BY_LABEL else f"Host {i + 1}"),
              "sockets": h["sockets"], "cores": h["cores"], "clock": h["clock"], "mem": h["mem"], "gpu": h["gpu"],
              "override": h["override"]} for i, h in enumerate(ins["hosts"])]
    return ins["desktops"], ins["rdsh"], hosts, params


def run_sizing():
    return E.compute(*engine_inputs())


# ----------------------------------------------------------------------------- projects
def slug(name):
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip() or "project"


def save_project():
    ss = st.session_state
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    path = os.path.join(PROJECTS_DIR, slug(ss.project) + PROJECT_EXT)
    data = {**current_inputs(), "saved": datetime.now().isoformat(timespec="seconds")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    ss.saved_path = path
    return path


def open_project(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    load_state(d.get("desktops"), d.get("rdsh"), d.get("hosts"), d.get("params"), d.get("customer", ""), d.get("project", ""))
    st.session_state.saved_path = path


def list_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    out = []
    for fn in os.listdir(PROJECTS_DIR):
        if fn.endswith(PROJECT_EXT):
            p = os.path.join(PROJECTS_DIR, fn)
            try:
                with open(p, encoding="utf-8") as fh:
                    d = json.load(fh)
                out.append((p, d))
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda x: x[1].get("saved", ""), reverse=True)


# ----------------------------------------------------------------------------- UI helpers
def eyebrow(t):
    st.html(f"<div class='hs-eyebrow'>{escape(t)}</div>")


def big_value(v, unit="", sub=""):
    st.html(f"<div class='hs-big'>{escape(str(v))} <small>{escape(unit)}</small></div>"
            + (f"<div class='hs-sub'>{escape(sub)}</div>" if sub else ""))


def section_title(eb, title):
    st.html(f"<div style='margin-top:22px'><div class='hs-eyebrow'>{escape(eb)}</div></div>")
    st.markdown(f"### {title}")


def kv_html(rows):
    return "<table class='hs-kv'>" + "".join(
        f"<tr><td>{escape(str(a))}</td><td class='{'red' if bad else ''}'>{escape(str(b))}</td></tr>" for a, b, bad in rows) + "</table>"


def badge(ok, t_ok, t_bad):
    return f":green-badge[:material/check: {t_ok}]" if ok else f":red-badge[:material/warning: {t_bad}]"


def page_header(title, subtitle=""):
    ss = st.session_state
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    with c1:
        st.markdown(f"# {title}")
        if subtitle:
            st.caption(subtitle)
    with c2:
        saved = ss.get("saved_path")
        if st.button("Save project", icon=":material/save:", type="primary", width="stretch"):
            save_project()
            st.toast(f"Saved to {PROJECTS_DIR}", icon=":material/check:")
        st.caption(f":green[Saved] · {ss.project}" if saved else ":gray[Not saved yet]")


# ----------------------------------------------------------------------------- pages
def page_home():
    ss = st.session_state
    hour = datetime.now().hour
    page_header(f"Good {'morning' if hour < 12 else 'afternoon' if hour < 17 else 'evening'}",
                "Size ESXi hosts for VDI and RDSH desktops from user counts and desktop specs.")
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown("#### This sizing")
        ss.customer = st.text_input("Customer name", ss.customer)
        ss.project = st.text_input("Project name", ss.project)
        st.caption("Next: describe the desktops on **Workloads**, the host on **Hardware**, then read the **Recommendation**.")
        st.page_link(PAGES["work"], label="Go to Workloads", icon=":material/groups:")
    with c2, st.container(border=True):
        st.markdown("#### Start over or try an example")
        st.caption("The example reproduces the AHEAD VDI Sizing Estimator sample (250 persistent desktops, 8-host cluster) "
                   "with overhead reserves off, so the numbers match the spreadsheet.")
        b = st.columns(2)
        b[0].button("New sizing", icon=":material/add:", width="stretch", on_click=load_state)
        b[1].button("Load example", icon=":material/science:", width="stretch",
                    on_click=lambda: load_state(SAMPLE["desktops"], SAMPLE["rdsh"], SAMPLE["hosts"], SAMPLE["params"],
                                                SAMPLE["customer"], SAMPLE["project"]))
    section_title("Your project library", "Saved sizings")
    projects = list_projects()
    if not projects:
        st.caption(f"Nothing saved yet. Projects are stored on this computer in {PROJECTS_DIR}.")
    for row in range(0, len(projects), 3):
        for col, (path, d) in zip(st.columns(3), projects[row:row + 3]):
            with col, st.container(border=True):
                st.html(f"<div class='hs-tile-name'>{escape(d.get('project', os.path.basename(path)))}</div>")
                users = sum(float(x.get("users") or 0) for x in d.get("desktops", []) + d.get("rdsh", []))
                st.caption(f"{d.get('customer', '')} · {users:,.0f} concurrent users · saved {d.get('saved', '')[:16].replace('T', ' ')}")
                b1, b2 = st.columns(2)
                b1.button("Open", key=f"open_{path}", icon=":material/arrow_forward:", type="primary", width="stretch",
                          on_click=open_project, args=(path,))
                b2.button("Delete", key=f"del_{path}", icon=":material/delete:", width="stretch",
                          on_click=lambda p=path: os.remove(p))


def num_cfg(label, help=None, fmt=None, step=None, minv=0):
    return st.column_config.NumberColumn(label, min_value=minv, help=help, format=fmt, step=step)


def stable_editor(name, **kwargs):
    """data_editor that keeps its rows when you leave the page and come back.
    Streamlit forgets an editor's edits once its page is not drawn, so the table is re-seeded from the saved
    copy (ss[name]) on entry. While you stay on the page the seed and key stay fixed, so typing is never reset."""
    ss = st.session_state
    key = ss.get(f"{name}_key")
    if key is None or key not in ss:                      # first draw on this page visit (or after a project load)
        ss[f"{name}_n"] = ss.get(f"{name}_n", 0) + 1
        ss[f"{name}_seed"] = ss[name].copy()
        key = ss[f"{name}_key"] = f"ed_{name}_{ss.ver}_{ss[f'{name}_n']}"
    ss[name] = st.data_editor(ss[f"{name}_seed"], key=key, **kwargs)


def page_workloads():
    ss = st.session_state
    page_header("Workloads", "Describe each desktop type and RDSH farm. Names are yours to choose; add or delete rows as needed.")
    cls_help = ("Sets the vCPU:pCore design limit used to size CPU. Limits are editable on Recommendation > Design rules. "
                + "; ".join(f"{k} {v[0]:g}:1" for k, v in E.CLASS_LIMITS.items()))
    with st.container(border=True):
        st.markdown("#### Desktop workloads (VDI)")
        st.caption("One row per user type. **Thick/PVS** disk is a full-clone desktop disk; **Image/Clone %** is an Instant Clone or MCS "
                   "desktop (image size x clone disk %). Both add the desktop's RAM for the swap file. Leave unused disk columns at 0.")
        stable_editor(
            "desktops", num_rows="dynamic", hide_index=True, width="stretch",
            column_order=DESKTOP_COLS,
            column_config={
                "name": st.column_config.TextColumn("User type", help="Your own name, e.g. Traders, Developers, Task Workers.", width="medium"),
                "cls": st.column_config.SelectboxColumn("Workload class", options=CLASS_NAMES, required=True, help=cls_help, width="medium"),
                "users": num_cfg("Concurrent desktops", "Peak concurrent desktops, not named users.", "%d", 1),
                "vcpu": num_cfg("vCPU", None, "%d", 1), "mem": num_cfg("Memory (GB)", None, "%g"),
                "gpu": num_cfg("vGPU profile (GB)", "vGPU framebuffer per desktop. 0 = no GPU.", "%g"),
                "disk": num_cfg("Thick/PVS disk (GB)", "Full-clone or PVS VM disk size.", "%g"),
                "image": num_cfg("Clone image (GB)", "Instant Clone / MCS parent image size.", "%g"),
                "clone_pct": num_cfg("Clone disk %", "Share of the image each clone consumes.", "%g"),
                "profile": num_cfg("Profile / user (GB)", None, "%g")})
    with st.container(border=True):
        st.markdown("#### RDSH workloads (session hosts)")
        st.caption("Servers = concurrent users ÷ users per server, rounded up. Disk = (thick + clone) per server, plus profile per user.")
        stable_editor(
            "rdsh", num_rows="dynamic", hide_index=True, width="stretch", column_order=RDSH_COLS,
            column_config={
                "name": st.column_config.TextColumn("Farm", width="medium"),
                "cls": st.column_config.SelectboxColumn("Workload class", options=CLASS_NAMES, required=True, help=cls_help, width="medium"),
                "users": num_cfg("Concurrent users", None, "%d", 1),
                "users_per_server": num_cfg("Users / server", None, "%g"),
                "vcpu": num_cfg("vCPU / server", None, "%d", 1), "mem": num_cfg("Memory / server (GB)", None, "%g"),
                "gpu": num_cfg("vGPU / server (GB)", None, "%g"),
                "disk": num_cfg("Thick/PVS disk (GB)", None, "%g"), "image": num_cfg("Clone image (GB)", None, "%g"),
                "clone_pct": num_cfg("Clone disk %", None, "%g"), "profile": num_cfg("Profile / user (GB)", None, "%g")})

    dem = E.demand(ss.desktops.to_dict("records"), ss.rdsh.to_dict("records"), E.DEFAULT_PARAMS | engine_inputs()[3])
    section_title("What you've entered", "Workload demand")
    c = st.columns(5)
    c[0].metric("Concurrent users", f"{dem['d_users'] + dem['r_users']:,.0f}", border=True)
    c[1].metric("Total VMs", f"{dem['vms']:,.0f}", border=True)
    c[2].metric("vCPU", f"{dem['cores']:,.0f}", border=True)
    c[3].metric("Memory", f"{dem['mem']:,.0f} GB", border=True)
    c[4].metric("Storage after dedupe", tb(dem["storage_net"]), border=True)
    if dem["gpu"]:
        st.caption(f"vGPU memory required: {dem['gpu']:,.0f} GB")


def _apply_cpu(i):
    ss = st.session_state
    c = CPU_BY_LABEL.get(ss[f"h{i}_cpu_model"])
    if c:
        ss[f"h{i}_cores"], ss[f"h{i}_clock"] = c["cores"], c["ghz"]
        ss[f"h{i}_sockets"] = min(ss[f"h{i}_sockets"], c["max_sockets"])


def _cpu_edited(i):
    ss = st.session_state
    c = CPU_BY_LABEL.get(ss[f"h{i}_cpu_model"])
    if c and (ss[f"h{i}_cores"] != c["cores"] or round(ss[f"h{i}_clock"], 2) != round(c["ghz"], 2)):
        ss[f"h{i}_cpu_model"] = CPU_CUSTOM


def _ram_entered(i):
    ss = st.session_state
    raw = str(ss[f"h{i}_mem"]).replace(",", "").lower().replace("gb", "").strip()
    try:
        v = int(float(raw))
        ss[f"h{i}_mem"] = min(max(v, 64), 8192)
    except ValueError:
        ss[f"h{i}_mem"] = 1024


def page_hardware():
    ss = st.session_state
    page_header("Hardware", "Define up to three candidate ESXi hosts to compare side by side.")
    cols = st.columns(ss.n_hosts)
    for i, col in enumerate(cols):
        with col, st.container(border=True):
            st.markdown(f"#### Candidate {i + 1}")
            st.selectbox("Processor", CPU_OPTIONS, key=f"h{i}_cpu_model", on_change=_apply_cpu, args=(i,),
                         help="Picking a processor fills cores per socket and base clock. Type to search (e.g. 6747P).")
            c = st.columns(2)
            c[0].number_input("Sockets", 1, 4, key=f"h{i}_sockets")
            c[1].number_input("Cores / socket", 4, 256, key=f"h{i}_cores", on_change=_cpu_edited, args=(i,))
            c = st.columns(2)
            c[0].number_input("Base clock (GHz)", 1.0, 5.0, key=f"h{i}_clock", format="%.2f", on_change=_cpu_edited, args=(i,))
            try:
                ss[f"h{i}_mem"] = int(ss[f"h{i}_mem"])
            except (TypeError, ValueError):
                ss[f"h{i}_mem"] = 1024
            opts = sorted(set(RAM_OPTIONS) | {ss[f"h{i}_mem"]})
            c[1].selectbox("Memory (GB)", opts, key=f"h{i}_mem", accept_new_options=True, on_change=_ram_entered, args=(i,),
                           format_func=lambda v: f"{int(v):,}")
            c = st.columns(2)
            c[0].number_input("GPU memory / host (GB)", 0, 4096, key=f"h{i}_gpu", help="Total vGPU framebuffer across the host's GPUs. 0 = no GPU.")
            c[1].number_input("Host count override", 0, 256, key=f"h{i}_override",
                              help="0 = let the tool calculate. Enter a number to test a fixed cluster size, like the spreadsheet's Node Count (N).")
            cpu = CPU_BY_LABEL.get(ss[f"h{i}_cpu_model"])
            if cpu and ss[f"h{i}_sockets"] > cpu["max_sockets"]:
                st.markdown(f":orange-badge[:material/warning: {cpu['name']} supports {cpu['max_sockets']} socket(s)]")
            st.caption(f"Host: {ss[f'h{i}_sockets'] * ss[f'h{i}_cores']} cores · {int(ss[f'h{i}_mem']):,} GB · "
                       f"{ss[f'h{i}_sockets'] * ss[f'h{i}_cores'] * ss[f'h{i}_clock']:,.0f} GHz total")
    b = st.columns([1, 1, 4])
    b[0].button("Add candidate", icon=":material/add:", disabled=ss.n_hosts >= MAX_CANDIDATES,
                on_click=lambda: ss.update(n_hosts=ss.n_hosts + 1))
    b[1].button("Remove last", icon=":material/remove:", disabled=ss.n_hosts <= 1,
                on_click=lambda: ss.update(n_hosts=ss.n_hosts - 1))


def render_rules():
    ss = st.session_state
    with st.container(border=True):
        st.markdown("#### Design rules")
        st.caption(":orange[Best-guess planning defaults, to be reviewed.] vCPU:pCore limits are industry rules of thumb, not "
                   "vendor-mandated; confirm with your Horizon design standards or a pilot and set your own below.")
        t = st.tabs([":material/rule: Availability & overhead", ":material/speed: vCPU:pCore limits",
                     ":material/storage: Storage", ":material/trending_up: Growth", ":material/tune: Method constants"])
        with t[0]:
            c = st.columns(3)
            c[0].number_input("Failure tolerance, X (hosts)", 0, 4, key="ha_nodes", help="N+X: hosts that can fail while the workload still fits.")
            c[1].number_input("Minimum cluster size", 1, 64, key="min_hosts")
            c[2].number_input("Maximum hosts per cluster", 2, 96, key="max_hosts",
                              help="If the total exceeds this the sizing is split across clusters, each with X spare hosts. vSphere allows up to 96.")
            c = st.columns(3)
            c[0].slider("CPU overhead reserve (%)", 0, 50, key="cpu_overhead", help="Hypervisor, vSAN and agents. Set 0 to match the spreadsheet.")
            c[1].slider("RAM overhead reserve (%)", 0, 50, key="ram_overhead", help="Hypervisor, vSAN and per-VM overhead. Set 0 to match the spreadsheet.")
            c[2].number_input("Max VMs per host (0 = none)", 0, 1024, key="max_vms_per_host")
        with t[1]:
            st.caption("Maximum virtual CPUs per physical core (before hyper-threading credit), used to size host CPU. "
                       "CPU hosts needed = Σ(vCPU ÷ class limit) ÷ usable cores per host.")
            cols = st.columns(len(CLASS_NAMES))
            for col, name in zip(cols, CLASS_NAMES):
                col.number_input(name, 0.5, 30.0, step=0.5, key=f"lim_{name}", help=E.CLASS_LIMITS[name][1])
        with t[2]:
            c = st.columns(2)
            c[0].number_input("Dedupe / optimisation (X:1)", 1.0, 10.0, step=0.1, key="dedupe",
                              help="Applied to desktop and RDSH storage. The sample uses 1.5:1.")
            c[1].slider("Free-space reserve (%)", 0, 50, key="storage_reserve", help="Added on top of the post-dedupe capacity.")
        with t[3]:
            c = st.columns(3)
            c[0].number_input("Annual user growth (%)", 0.0, 100.0, key="growth_pct", help="0 = no future sizing shown.")
            c[1].number_input("Years", 1, 10, key="years")
        with t[4]:
            c = st.columns(2)
            c[0].number_input("Hyper-threading uplift (x)", 1.0, 2.0, step=0.1, key="ht_factor",
                              help="Spreadsheet standard is 1.3. Used for the 'with HT' vCPU:pCore figure.")
            c[1].number_input("RDSH session weight in GHz/user", 0.0, 1.0, step=0.05, key="rdsh_weight",
                              help="An RDSH session counts as this fraction of a VDI desktop, per the spreadsheet (0.3).")
            st.button("Reset all rules to defaults", icon=":material/restart_alt:",
                      on_click=lambda: [ss.__setitem__(k, v) for k, v in default_params().items()])


def host_card(res, c, future=False):
    fc = c["future"] if future else c
    ev = fc["eval"]
    d = res["future"] if future else res["day1"]
    with st.container(border=True):
        eyebrow((f"Future · {res['params']['years']} years" if future else "Recommended today") + " · " + c["spec"]["model"])
        if fc["solve"]["unsized"]:
            big_value("n/a", "", ev["checks"][0][1])
            return
        hosts = fc["hosts"]
        big_value(hosts, "hosts", f"For {d['d_users'] + d['r_users']:,.0f} concurrent users and {d['vms']:,.0f} VMs.")
        tags = [f":blue-badge[N+{res['params']['ha_nodes']}]", f":gray-badge[{fc['solve']['constraint']} bound]"]
        if fc["forced"]:
            tags.append(f":orange-badge[:material/lock: Manual (calculated {fc['solve']['calc_hosts']})]")
        if fc["solve"]["min_applied"]:
            tags.append(":gray-badge[Minimum cluster applied]")
        if fc["solve"]["clusters"] > 1 and not fc["forced"]:
            tags.append(f":orange-badge[{fc['solve']['clusters']} clusters of {fc['solve']['per_cluster']}]")
        st.markdown(" ".join(tags))
        need = fc["solve"]["need"]
        st.caption("Hosts needed (before HA): " + " · ".join(f"{k} {v}" for k, v in need.items()))
        for bad, text in ev["checks"]:
            st.markdown(f":{'red' if bad else 'green'}[{text}]")


def page_recommendation():
    ss = st.session_state
    page_header("Recommendation", "Host count for each candidate, checked with the failed hosts removed (N-X).")
    render_rules()
    res = run_sizing()
    d, p = res["day1"], res["params"]
    if not res["candidates"]:
        st.info("Add a candidate host with cores and memory on Hardware.")
        return
    if d["vms"] == 0:
        st.info("Enter concurrent users on Workloads to size hosts.")
        return
    section_title("The short answer", "Sizing recommendation")
    for c, col in zip(res["candidates"], st.columns(len(res["candidates"]))):
        with col:
            host_card(res, c)
            if res["grown"]:
                host_card(res, c, future=True)

    section_title("Host utilization", f"Design check at N-{p['ha_nodes']} (same measures as the spreadsheet)")
    rows = [("Host", lambda c, e: cand_label(c)), ("Hosts used (N)", lambda c, e: f"{c['hosts']}"),
            (f"Active hosts (N-{p['ha_nodes']})", lambda c, e: f"{e.get('active', '-')}"),
            (f"Usable cores, N-{p['ha_nodes']}", lambda c, e: f"{e['n_usable_cores']:,.0f}" if "n_usable_cores" in e else "-"),
            (f"Usable GHz, N-{p['ha_nodes']}", lambda c, e: f"{e['n_ghz']:,.0f}" if "n_ghz" in e else "-"),
            (f"Usable memory, N-{p['ha_nodes']}", lambda c, e: f"{e['n_mem']:,.0f} GB" if "n_mem" in e else "-"),
            ("vCPU:pCore (CPU overcommit)", lambda c, e: f"{e['overcommit']:.2f}:1" if "overcommit" in e else "-"),
            (f"vCPU:pCore with HT (x{p['ht_factor']:g})", lambda c, e: f"{e['ht_overcommit']:.2f}:1" if "overcommit" in e else "-"),
            ("GHz per user", lambda c, e: f"{e['ghz_per_user']:.2f}" if "ghz_per_user" in e else "-"),
            ("Memory remaining", lambda c, e: f"{e['mem_remaining']:,.0f} GB" if "mem_remaining" in e else "-"),
            ("GPU memory remaining", lambda c, e: f"{e['gpu_remaining']:,.0f} GB" if "gpu_remaining" in e else "-"),
            ("VMs per host", lambda c, e: f"{e['vms_per_host']}" if "vms_per_host" in e else "-"),
            ("Licensed cores", lambda c, e: f"{c['lic_cores']:,}"),
            ("Result", lambda c, e: "Passes" if e.get("ok") else "Fails")]
    head = "".join(f"<th>{escape(h)}</th>" for h in ["Metric"] + [c["spec"]["model"] for c in res["candidates"]])
    body = ""
    for label, fn in rows:
        cells = ""
        for c in res["candidates"]:
            e = c["eval"]
            bad = (label == "Result" and not e.get("ok")) or (label == "Memory remaining" and e.get("mem_remaining", 0) < 0)
            cells += f"<td class='{'hs-over' if bad else ''}'>{escape(str(fn(c, e)))}</td>"
        body += f"<tr><td>{escape(label)}</td>{cells}</tr>"
    with st.container(border=True):
        st.html(f"<table class='hs-cmp'><tr>{head}</tr>{body}</table>")
        st.caption(f"vCPU:pCore blended design limit for this mix: {d['blended_limit']:.1f}:1 across {d['cores']:,.0f} vCPU "
                   f"({d['core_need']:,.0f} physical cores needed). Overcommit uses usable cores after the {p['cpu_overhead']}% overhead reserve; "
                   f"GHz per user = usable GHz ÷ (desktops + {p['rdsh_weight']:g} × RDSH users + RDSH servers).")

    section_title("Capacity", "Storage")
    c = st.columns(4)
    c[0].metric("Thick / PVS (incl. swap)", tb(d["disk_thick"]), border=True)
    c[1].metric("Instant clone / MCS (incl. swap)", tb(d["disk_clone"]), border=True)
    c[2].metric("Profiles", tb(d["disk_profile"]), border=True)
    c[3].metric("Total pre-optimisation", tb(d["disk"]), border=True)
    c = st.columns(3)
    c[0].metric(f"After {p['dedupe']:g}:1 dedupe", tb(d["storage_net"]), border=True)
    c[1].metric(f"With {p['storage_reserve']:g}% reserve", tb(d["storage_reserve"]), border=True)
    c[2].metric("Desktops / RDSH split", f"{tb(d['d_disk'])} / {tb(d['r_disk'])}", border=True)
    st.caption("Capacity only. Storage performance (IOPS) is not sized here and should be confirmed during design.")

    section_title("How the number was reached", "Sizing logic")
    with st.container(border=True):
        c0 = next((c for c in res["candidates"] if not c["solve"]["unsized"]), None)
        if c0 is None:
            st.caption("No candidate can host this workload (for example, vGPU memory needed but the host has no GPU).")
            return
        s = c0["solve"]
        st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate([
            f"Workload: {d['cores']:,.0f} vCPU, {d['mem']:,.0f} GB memory"
            + (f" and {d['gpu']:,.0f} GB vGPU" if d["gpu"] else "") + f" across {d['vms']:,.0f} VMs.",
            f"Usable host ({c0['spec']['model']}): {c0['spec']['eff_cores']:.1f} cores and {c0['spec']['eff_mem']:,.0f} GB after "
            f"{p['cpu_overhead']}% / {p['ram_overhead']}% overhead.",
            "Hosts needed: " + ", ".join(f"{k} {v}" for k, v in s["need"].items()) + f" → {s['constraint']} bound, {s['raw']} active hosts.",
            f"Final: {s['raw']} + {p['ha_nodes']} HA = {s['raw'] + p['ha_nodes']}"
            + (f", raised to the {p['min_hosts']}-host minimum." if s["min_applied"] else ".")
            + (f" Split into {s['clusters']} clusters to stay within {p['max_hosts']} hosts." if s["clusters"] > 1 else ""),
            "Design check: re-tested with the HA hosts failed (N-X) against the same limits."], 1)))


def page_report():
    ss = st.session_state
    page_header("Report", "AHEAD-branded HTML report. Self-contained: open it in any browser, email it, or print to PDF.")
    c1, c2 = st.columns([2, 1])
    with c1, st.container(border=True, height="stretch"):
        st.markdown("#### Report settings")
        ss.customer = st.text_input("Customer name", ss.customer)
        ss.project = st.text_input("Project name", ss.project)
        f = st.file_uploader("Customer logo (optional)", type=["png", "jpg", "jpeg"], key="logo_up")
        if f is not None:
            ss.cust_logo = {"bytes": f.getvalue(), "type": f.type or "image/png"}
    with c2, st.container(border=True, height="stretch"):
        st.markdown("#### Customer logo")
        if ss.cust_logo:
            st.image(ss.cust_logo["bytes"], width=180)
        else:
            st.caption("No logo uploaded. The customer name is shown instead.")
    res = run_sizing()
    if not res["candidates"] or res["day1"]["vms"] == 0:
        st.info("Enter workloads and at least one host first.")
        return
    import base64
    logo = (f"data:{ss.cust_logo['type']};base64,{base64.b64encode(ss.cust_logo['bytes']).decode()}" if ss.cust_logo else None)
    html = generate_report(res, ss.customer, logo, ss.project)
    st.download_button("Download report", html, file_name=f"{re.sub(r'[^A-Za-z0-9 _-]+', '', ss.customer).strip() or 'Customer'}-VDI-AHEAD Sizing.html",
                       mime="text/html", icon=":material/download:", type="primary")
    section_title("Preview", "What the customer will see")
    if hasattr(st, "iframe"):
        st.iframe(html, height=1500)
    else:
        import streamlit.components.v1 as components
        components.html(html, height=1500, scrolling=True)


# ----------------------------------------------------------------------------- setup + entry
PAGES = {}


def ensure_theme_config():
    path = os.path.join(APP_DIR, ".streamlit", "config.toml")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                cur = fh.read()
            if cur == THEME_TOML or not cur.startswith(THEME_MARKER):
                return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(THEME_TOML)
        return True
    except OSError:
        return False


def ensure_streamlit_credentials():
    path = os.path.join(os.path.expanduser("~"), ".streamlit", "credentials.toml")
    try:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('[general]\nemail = ""\n')
    except OSError:
        pass


def keep_alive():
    """Streamlit drops widget state for widgets not drawn on the current page; re-assigning keeps it."""
    ss = st.session_state
    for k in PARAM_KEYS + [f"h{i}_{f}" for i in range(MAX_CANDIDATES) for f in HOST_FIELDS]:
        if k in ss:
            ss[k] = ss[k]


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4])


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _fetch_latest_version():
    """Newest APP_VERSION on GitHub. Raises on failure, so failures aren't cached."""
    import urllib.request
    req = urllib.request.Request(UPDATE_SOURCE_URL, headers={"Range": "bytes=0-8191",
                                                             "User-Agent": f"VDIHostSizer/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        head = resp.read(8192).decode("utf-8", "ignore")
    return re.search(r'^APP_VERSION = "([^"]+)"', head, re.M).group(1)


def latest_version():
    """Newest version on GitHub, or None when disabled, offline or blocked (3 s timeout)."""
    if os.environ.get("VDI_HOSTSIZER_NO_UPDATE_CHECK"):
        return None
    try:
        return _fetch_latest_version()
    except Exception:  # noqa: BLE001 - offline, proxy, GitHub down: just skip the notice
        return None


def render_update_notice(container):
    latest = latest_version()
    if not latest or version_tuple(latest) <= version_tuple(APP_VERSION):
        return
    container.html(
        f"<div class='hs-update'><div class='t'>Update available</div>"
        f"<div class='v'>Version {escape(latest)} is out. You have {escape(APP_VERSION)}.</div>"
        f"<a class='dl' href='{UPDATE_ZIP_URL}' target='_blank' rel='noopener'>Download update</a>"
        f"<a class='nt' href='{UPDATE_NOTES_URL}' target='_blank' rel='noopener'>What's new</a>"
        + ("<div class='mac'>On a Mac, update by running the install command in Terminal again (see the ReadMe).</div>"
           if sys.platform == "darwin" else "") + "</div>")
    if not st.session_state.get("_update_toast"):
        st.session_state._update_toast = True
        st.toast(f"{APP_TITLE} {latest} is available. See About in the sidebar to download it.", icon=":material/system_update:")


def render_sidebar():
    sb = st.sidebar
    logo = data_uri(LOGO_WHITE)
    sb.html(f"<div class='hs-brand'>" + (f"<img class='lockup' src='{logo}' alt='{APP_TITLE} - Powered by AHEAD'>" if logo else
            f"<div class='name'>{APP_TITLE}</div><div class='pb'>Powered by AHEAD</div>") + "</div>")
    sb.html("<div class='hs-label'>Workspace</div>")
    for key, label, icon in (("home", "Home", "home"), ("work", "Workloads", "groups"), ("hw", "Hardware", "dns"),
                             ("rec", "Recommendation", "insights"), ("report", "Report", "description")):
        sb.page_link(PAGES[key], label=label, icon=f":material/{icon}:")
    sb.html("<div class='hs-label'>Current sizing</div>")
    sb.caption(f"{st.session_state.customer} · {st.session_state.project}")
    sb.html("<div class='hs-label'>About</div>")
    sb.caption(f"{APP_TITLE} v{APP_VERSION} · VMware ESXi")
    render_update_notice(sb)


def main():
    st.set_page_config(page_title=f"{APP_TITLE} | AHEAD", layout="wide",
                       page_icon=ICON if os.path.exists(ICON) else ":material/desktop_windows:")
    version = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
    if version < MIN_STREAMLIT:
        st.error(f"{APP_TITLE} needs Streamlit {'.'.join(map(str, MIN_STREAMLIT))} or newer; this computer has {st.__version__}.")
        st.stop()
    if ensure_theme_config():
        st.toast("AHEAD theme installed. Restart the app to apply it.", icon=":material/palette:")
    init_state()
    keep_alive()
    st.html(APP_CSS)
    PAGES.update({
        "home": st.Page(page_home, title="Home", icon=":material/home:", url_path="home", default=True),
        "work": st.Page(page_workloads, title="Workloads", icon=":material/groups:", url_path="workloads"),
        "hw": st.Page(page_hardware, title="Hardware", icon=":material/dns:", url_path="hardware"),
        "rec": st.Page(page_recommendation, title="Recommendation", icon=":material/insights:", url_path="recommendation"),
        "report": st.Page(page_report, title="Report", icon=":material/description:", url_path="report"),
    })
    nav = st.navigation(list(PAGES.values()), position="hidden")
    render_sidebar()
    nav.run()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        ensure_theme_config()
        ensure_streamlit_credentials()
        print("AHEAD theme config is in place.")
    else:
        main()
