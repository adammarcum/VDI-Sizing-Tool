"""
VDI sizing engine - pure Python, no Streamlit. Unit-testable.

Method follows the AHEAD "VDI Sizing Estimator" spreadsheet:
  Desktop workloads : cores = vCPU x users, mem = RAM x users, GPU mem = profile x users,
                      disk per desktop = (thick disk + RAM) + (image x clone% + RAM) + profile,
                      all x concurrent desktops.
  RDSH workloads    : servers = ceil(users / users per server); cores/mem/GPU per server x servers;
                      disk = (thick + clone) x servers + profile x users.
  Storage           : (desktop + RDSH) pre-optimisation total / dedupe ratio.
  Hosts             : evaluated on N-X (failed hosts removed): overcommit, hyper-threaded overcommit
                      (x1.3), GHz per user, memory and GPU remaining, VMs per host.
Additions over the spreadsheet (all adjustable, all defaults are best-guess and flagged for review):
  * solves for the host count (CPU, memory, GPU and optional max VMs per host) instead of only checking one,
  * per-workload-class vCPU:pCore design limits, CPU / RAM overhead reserve, minimum cluster size,
    maximum hosts per cluster, growth, free-space reserve for storage, per-core licensing.
"""
import math

EPS = 1e-9
HT_FACTOR = 1.3               # hyper-threading uplift used by the spreadsheet
RDSH_SESSION_WEIGHT = 0.3     # an RDSH session counts as 30% of a VDI desktop in GHz-per-user
LIC_MIN_CORES_PER_SOCKET = 16

# Workload classes: (name, max vCPU:pCore design limit, note).  BEST-GUESS industry rules of thumb, to be
# reviewed. Limits apply to the physical-core ratio (the spreadsheet's "CPU Overcommit").
CLASS_LIMITS = {
    "Task / light": (10.0, "Light, few apps. Often sized 8-12:1."),
    "Knowledge worker": (6.0, "Office, browser, collaboration. A common starting point is about 6:1."),
    "Power user": (4.0, "Heavier apps, multi-monitor. Typically 3-5:1."),
    "Heavy / graphics": (2.0, "CAD, trading, engineering, vGPU. Typically 1.5-3:1."),
    "RDSH server": (2.0, "Session-host VMs are already consolidated. Typically 1-3:1."),
}
DEFAULT_DESKTOP_CLASS = "Knowledge worker"
DEFAULT_RDSH_CLASS = "RDSH server"

DEFAULT_PARAMS = {
    "ha_nodes": 1,            # X, failure tolerance
    "min_hosts": 3,           # minimum cluster size (3 keeps vSAN / maintenance workable)
    "max_hosts": 32,          # best-guess cluster cap (vSphere allows 96); above this the sizing is split
    "cpu_overhead": 10,       # % of host cores reserved (hypervisor, vSAN, management agents)
    "ram_overhead": 10,       # % of host RAM reserved (hypervisor, vSAN, per-VM overhead)
    "max_vms_per_host": 0,    # 0 = no limit
    "dedupe": 1.5,            # X:1 storage optimisation
    "storage_reserve": 20,    # % free-space reserve on top of post-dedupe capacity
    "growth_pct": 0.0,        # annual growth in concurrent users
    "years": 3,
    "ht_factor": HT_FACTOR,
    "rdsh_weight": RDSH_SESSION_WEIGHT,
    "class_limits": {k: v[0] for k, v in CLASS_LIMITS.items()},
}


def ceil_div(a, b):
    if b <= 0:
        return 0 if a <= 0 else math.inf
    return int(math.ceil(a / b - EPS)) if a > 0 else 0


def f(x, d=0.0):
    try:
        v = float(x)
        return d if math.isnan(v) else v
    except (TypeError, ValueError):
        return d


# ----------------------------------------------------------------------------- workloads
def desktop_row(row, mult=1.0):
    """One desktop user type -> per-desktop disk and totals. Mirrors spreadsheet columns F, I, L-O."""
    vcpu, mem, gpu = f(row.get("vcpu")), f(row.get("mem")), f(row.get("gpu"))
    thick, image, clone = f(row.get("disk")), f(row.get("image")), f(row.get("clone_pct"))
    profile = f(row.get("profile"))
    users = f(row.get("users")) * mult
    users = math.ceil(users - EPS) if mult != 1.0 else users
    thick_per = 0.0 if thick == 0 else thick + mem              # F = IF(E=0,0,E+C)
    clone_per = 0.0 if image == 0 else image * clone / 100 + mem  # I = IF(G=0,0,G*(H/100)+C)
    return {
        "name": str(row.get("name") or "").strip() or "Unnamed",
        "cls": row.get("cls") or DEFAULT_DESKTOP_CLASS,
        "users": users, "vcpu": vcpu, "mem": mem, "gpu": gpu,
        "thick_per": thick_per, "clone_per": clone_per, "profile": profile,
        "cores": vcpu * users, "mem_total": mem * users, "gpu_total": gpu * users,
        "disk_thick": thick_per * users, "disk_clone": clone_per * users, "disk_profile": profile * users,
        "disk": (thick_per + clone_per + profile) * users,
    }


def rdsh_row(row, mult=1.0):
    """One RDSH farm row. Mirrors spreadsheet columns G, J, M-Q."""
    vcpu, mem, gpu = f(row.get("vcpu")), f(row.get("mem")), f(row.get("gpu"))
    per_server = f(row.get("users_per_server"))
    thick, image, clone = f(row.get("disk")), f(row.get("image")), f(row.get("clone_pct"))
    profile = f(row.get("profile"))
    users = f(row.get("users")) * mult
    users = math.ceil(users - EPS) if mult != 1.0 else users
    servers = ceil_div(users, per_server) if per_server > 0 else 0
    thick_per = 0.0 if thick == 0 else thick + mem
    clone_per = 0.0 if image == 0 else image * clone / 100 + mem
    return {
        "name": str(row.get("name") or "").strip() or "Unnamed",
        "cls": row.get("cls") or DEFAULT_RDSH_CLASS,
        "users": users, "servers": servers, "users_per_server": per_server,
        "vcpu": vcpu, "mem": mem, "gpu": gpu,
        "thick_per": thick_per, "clone_per": clone_per, "profile": profile,
        "cores": vcpu * servers, "mem_total": mem * servers, "gpu_total": gpu * servers,
        "disk_thick": thick_per * servers, "disk_clone": clone_per * servers, "disk_profile": profile * users,
        "disk": (thick_per + clone_per) * servers + profile * users,
    }


def demand(desktops, rdsh, p, mult=1.0):
    """Total workload demand (optionally grown by `mult`)."""
    ds = [desktop_row(r, mult) for r in desktops if f(r.get("users")) > 0]
    rs = [rdsh_row(r, mult) for r in rdsh if f(r.get("users")) > 0]
    limits = p["class_limits"]
    rows = ds + rs
    core_need = sum(x["cores"] / max(f(limits.get(x["cls"]), 1.0), EPS) for x in rows)   # physical cores at design limits
    cores = sum(x["cores"] for x in rows)
    d = {
        "desktops": ds, "rdsh": rs,
        "d_users": sum(x["users"] for x in ds), "r_users": sum(x["users"] for x in rs),
        "r_servers": sum(x["servers"] for x in rs),
        "cores": cores, "mem": sum(x["mem_total"] for x in rows), "gpu": sum(x["gpu_total"] for x in rows),
        "d_cores": sum(x["cores"] for x in ds), "r_cores": sum(x["cores"] for x in rs),
        "d_mem": sum(x["mem_total"] for x in ds), "r_mem": sum(x["mem_total"] for x in rs),
        "d_gpu": sum(x["gpu_total"] for x in ds), "r_gpu": sum(x["gpu_total"] for x in rs),
        "core_need": core_need,                       # physical cores needed to stay within each class limit
        "blended_limit": cores / core_need if core_need else 0.0,
        "disk_thick": sum(x["disk_thick"] for x in rows), "disk_clone": sum(x["disk_clone"] for x in rows),
        "disk_profile": sum(x["disk_profile"] for x in rows),
        "d_disk": sum(x["disk"] for x in ds), "r_disk": sum(x["disk"] for x in rs),
    }
    d["vms"] = d["d_users"] + d["r_servers"]
    d["disk"] = d["d_disk"] + d["r_disk"]                       # pre-optimisation, combined
    d["storage_net"] = d["disk"] / p["dedupe"] if p["dedupe"] > 0 else d["disk"]
    d["storage_reserve"] = d["storage_net"] * (1 + p["storage_reserve"] / 100)
    d["user_equiv"] = d["d_users"] + p["rdsh_weight"] * d["r_users"] + d["r_servers"]   # GHz/user denominator
    return d


# ----------------------------------------------------------------------------- hosts
def host_spec(h, p):
    sockets, cps = f(h.get("sockets"), 2), f(h.get("cores"))
    cores = sockets * cps
    return {
        "model": str(h.get("model") or "").strip() or "Host",
        "sockets": int(sockets), "cores_per_socket": cps, "cores": cores, "clock": f(h.get("clock")),
        "mem": f(h.get("mem")), "gpu": f(h.get("gpu")),
        "override": int(f(h.get("override"))),
        "eff_cores": cores * (1 - p["cpu_overhead"] / 100),
        "eff_mem": f(h.get("mem")) * (1 - p["ram_overhead"] / 100),
        "lic_cores": int(sockets * max(cps, LIC_MIN_CORES_PER_SOCKET)),
    }


def split_clusters(active_total, ha, cap):
    """Smallest number of clusters (each with `ha` spare hosts) so no cluster exceeds `cap` hosts."""
    if active_total <= 0:
        return 1, 0, 0
    k = 1
    while True:
        per = ceil_div(active_total, k)
        if per + ha <= cap or per <= 1 or k > 200:
            return k, per, k * (per + ha)
        k += 1


def size_hosts(dem, hs, p):
    """Solve the host count for one candidate host against one demand set."""
    ha, need = p["ha_nodes"], {}
    need["CPU"] = ceil_div(dem["core_need"], hs["eff_cores"]) if hs["eff_cores"] else math.inf
    need["RAM"] = ceil_div(dem["mem"], hs["eff_mem"]) if hs["eff_mem"] else math.inf
    if dem["gpu"] > 0:
        need["GPU"] = ceil_div(dem["gpu"], hs["gpu"])
    if p["max_vms_per_host"] > 0:
        need["VMs"] = ceil_div(dem["vms"], p["max_vms_per_host"])
    raw = max(need.values()) if need else 0
    unsized = raw == math.inf
    top = [k for k, v in need.items() if v == raw]
    constraint = top[0] if len(top) == 1 and raw > 0 else ("Balanced" if raw > 0 else "None")
    if unsized:
        return {"need": need, "raw": raw, "constraint": [k for k, v in need.items() if v == math.inf][0],
                "calc_hosts": 0, "clusters": 0, "per_cluster": 0, "min_applied": False, "unsized": True}
    solo = max(raw + ha, p["min_hosts"]) if raw > 0 else 0
    k, per, total = split_clusters(max(raw, p["min_hosts"] - ha), ha, p["max_hosts"]) if raw > 0 else (0, 0, 0)
    return {"need": need, "raw": raw, "constraint": constraint, "calc_hosts": max(total, solo) if raw else 0,
            "clusters": k, "per_cluster": per + ha if raw else 0,
            "min_applied": raw > 0 and raw + ha < p["min_hosts"], "unsized": False}


def evaluate(dem, hs, hosts, p):
    """Spreadsheet 'Host Utilization' columns for a given host count, plus pass/fail checks."""
    ha = p["ha_nodes"]
    active = hosts - ha
    out = {"hosts": hosts, "active": active}
    if active <= 0 or hs["cores"] <= 0:
        out.update(ok=False, checks=[(True, f"{hosts} host(s) leaves no active capacity with N+{ha}.")])
        return out
    raw_cores, usable_cores = active * hs["cores"], active * hs["eff_cores"]
    usable_mem, usable_gpu = active * hs["eff_mem"], active * hs["gpu"]
    out.update(
        n_cores=raw_cores, n_usable_cores=usable_cores, n_ghz=usable_cores * hs["clock"],
        n_mem=usable_mem, n_gpu=usable_gpu,
        overcommit=dem["cores"] / usable_cores,                                    # N-X, after overhead reserve
        ht_overcommit=dem["cores"] / (usable_cores * p["ht_factor"]),
        overcommit_all=dem["cores"] / (hosts * hs["eff_cores"]),                   # all hosts up
        ghz_per_user=(usable_cores * hs["clock"]) / dem["user_equiv"] if dem["user_equiv"] else 0.0,
        mem_remaining=usable_mem - dem["mem"], mem_use=dem["mem"] / usable_mem if usable_mem else 0.0,
        gpu_remaining=usable_gpu - dem["gpu"], gpu_use=(dem["gpu"] / usable_gpu) if usable_gpu else None,
        vms_per_host=ceil_div(dem["vms"], active), cpu_use=dem["core_need"] / usable_cores,   # >100% = beyond class limits
    )
    c = []
    if hosts < p["min_hosts"]:
        c.append((True, f"{hosts} hosts is below the {p['min_hosts']}-host minimum cluster size."))
    if out["cpu_use"] > 1 + EPS:
        c.append((True, f"CPU: {dem['cores']:,.0f} vCPU needs {dem['core_need']:,.0f} cores at the class limits "
                        f"(blended {dem['blended_limit']:.1f}:1) but only {usable_cores:,.0f} usable cores remain with {ha} host(s) failed."))
    if out["mem_use"] > 1 + EPS:
        c.append((True, f"RAM: {dem['mem']:,.0f} GB needed vs {usable_mem:,.0f} GB usable with {ha} host(s) failed."))
    if dem["gpu"] > 0 and (usable_gpu <= 0 or dem["gpu"] > usable_gpu + EPS):
        c.append((True, f"GPU: {dem['gpu']:,.0f} GB of vGPU memory needed vs {usable_gpu:,.0f} GB available."))
    if p["max_vms_per_host"] > 0 and out["vms_per_host"] > p["max_vms_per_host"]:
        c.append((True, f"{out['vms_per_host']} VMs per host exceeds the {p['max_vms_per_host']} limit."))
    if hosts > p["max_hosts"]:
        c.append((True, f"{hosts} hosts is above the {p['max_hosts']}-host cluster cap; split across clusters."))
    if not c:
        c.append((False, f"{hosts} hosts meets CPU, memory{', GPU' if dem['gpu'] > 0 else ''} limits with N+{ha}: "
                         f"{out['overcommit']:.2f}:1 vCPU:pCore, {out['mem_use']:.0%} of usable RAM."))
    out.update(checks=c, ok=not any(bad for bad, _ in c))
    return out


def size_candidate(dem, h, p):
    hs = host_spec(h, p)
    s = size_hosts(dem, hs, p)
    hosts = hs["override"] if hs["override"] > 0 else s["calc_hosts"]
    res = {"spec": hs, "solve": s, "hosts": hosts, "forced": hs["override"] > 0}
    if s["unsized"]:
        res["eval"] = {"ok": False, "hosts": 0, "active": 0, "checks": [(True, f"This host has no {s['constraint']} capacity "
                                                                              "but the workload needs it.")]}
    else:
        res["eval"] = evaluate(dem, hs, hosts, p)
    res["lic_cores"] = hosts * hs["lic_cores"]
    return res


def compute(desktops, rdsh, hosts, params=None):
    """Top level. Returns demand (Day 1 and future) and one sized result per candidate host."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    p["class_limits"] = {**DEFAULT_PARAMS["class_limits"], **(p.get("class_limits") or {})}
    day1 = demand(desktops, rdsh, p)
    grow = (1 + p["growth_pct"] / 100) ** p["years"]
    fut = demand(desktops, rdsh, p, grow) if abs(grow - 1) > EPS else day1
    cands = []
    for h in hosts:
        if f(h.get("cores")) <= 0 or f(h.get("mem")) <= 0:
            continue
        a = size_candidate(day1, h, p)
        a["future"] = size_candidate(fut, {**h, "override": 0}, p) if fut is not day1 else a
        cands.append(a)
    return {"params": p, "day1": day1, "future": fut, "grown": fut is not day1, "growth_mult": grow, "candidates": cands}
