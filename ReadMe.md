# VDI Host Sizer (v1.0.1)

Sizes VMware ESXi hosts for VDI (full clone, Instant Clone / MCS, PVS) and RDSH desktops, using the AHEAD
VDI Sizing Estimator method. Powered by AHEAD. Same look and launch pattern as the Host Sizer.

## Run it
* **Mac (easiest, no security prompts):** open Terminal, paste this line and press Return:
  ```
  curl -fsSL https://raw.githubusercontent.com/adammarcum/VDI-Sizing-Tool/main/install_mac.sh | bash
  ```
  It installs to `~/HostSizer/vdi-app`, adds a **VDI Host Sizer** app to your Applications folder (also in Launchpad and
  Spotlight), and starts the tool. Next time, just open that app (if macOS asks to let it control Terminal, click OK). Run the same line again to update; saved projects are kept.
  (A ZIP downloaded in a browser is flagged by macOS and `Run_on_mac.command` is blocked; use the line above instead.)
* **Windows:** unzip into a folder, double-click `Run_on_windows.bat` (if SmartScreen appears: More info, then Run anyway).
* **Developer:** `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run vdi_app.py`
* Tests: `pip install pytest && python -m pytest tests`

## Using it
1. **Workloads** - one row per desktop user type (you name them) and per RDSH farm: concurrent users, vCPU, memory, vGPU, disk, profile.
2. **Hardware** - up to three candidate hosts (processor picker, sockets, memory, GPU memory). Set a host count override to test a fixed cluster.
3. **Recommendation** - calculated hosts (N+X), the N-X design check, storage, and the design rules.
4. **Report** - AHEAD-branded, self-contained HTML. Save projects with **Save project** (`~/HostSizer/VDIProjects`).
5. **Home > Load example** reproduces the spreadsheet sample (250 desktops, 8 hosts: 2.98:1, 2.29:1 with HT, 7.26 GHz/user, 2,752 GB memory left, 36 VMs/host, 90,667 GB).

## Updates
The sidebar (About) shows an **Update available** card when a newer version is on GitHub. It reads only the version number.
Turn it off with `VDI_HOSTSIZER_NO_UPDATE_CHECK=1`. See `CHANGELOG.md` for what changed.

## Method (from the spreadsheet)
* Desktops: cores = vCPU x users; memory = RAM x users; GPU = profile x users.
  Disk per desktop = (thick disk + RAM) + (image x clone % + RAM) + profile; storage = disk / dedupe.
* RDSH: servers = ceil(users / users per server); disk = (thick + clone) x servers + profile x users.
* Hosts (on N-X): vCPU:pCore, with HT (x1.3), GHz per user = GHz / (desktops + 0.3 x RDSH users + RDSH servers),
  memory and GPU remaining, VMs per host.

## Additions (defaults are best-guess planning values, pending AHEAD review)
* Solves the host count (CPU, memory, GPU, optional VMs per host) plus X HA hosts, minimum cluster size, and a cluster cap that splits the sizing into clusters.
* vCPU:pCore limits per workload class (Task 10, Knowledge 6, Power 4, Heavy/graphics 2, RDSH servers 2), CPU / RAM overhead reserve (10%), storage free-space reserve (20%), growth, per-core licensing (16-core minimum).
* Set overhead to 0 and the reserve to 0 to match the spreadsheet exactly.

## Not included
Storage IOPS, network, vSAN sizing, application licensing, hypervisors other than ESXi, Citrix-specific infrastructure.

## Files
`install_mac.sh` (Mac one-command installer), `vdi_app.py` (UI), `vdi_engine.py` (math, no Streamlit), `vdi_report.py` (HTML report),
`cpu_catalog.py` (processors), `requirements.txt`, launchers, logos, `tests/`, `CHANGELOG.md`, `RELEASING.md`, `landing/` (landing page builder).
