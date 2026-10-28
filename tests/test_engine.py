import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vdi_engine as e

DESK = [{"name":"Traders","vcpu":8,"mem":32,"gpu":0,"disk":512,"image":0,"clone_pct":0,"profile":0,"users":250,"cls":"Power user"}]
HOST = [{"model":"6747P","sockets":2,"cores":48,"clock":2.7,"mem":1536,"gpu":0,"override":8}]
P0 = {"cpu_overhead":0,"ram_overhead":0}

def test_spreadsheet_parity():
    r = e.compute(DESK, [], HOST, P0)
    d, c = r["day1"], r["candidates"][0]["eval"]
    assert d["cores"] == 2000 and d["mem"] == 8000 and d["disk"] == 136000
    assert round(d["storage_net"], 2) == 90666.67
    assert c["hosts"] == 8 and c["active"] == 7
    assert round(c["overcommit"], 4) == 2.9762 and round(c["ht_overcommit"], 4) == 2.2894
    assert round(c["ghz_per_user"], 4) == 7.2576
    assert c["mem_remaining"] == 2752 and c["vms_per_host"] == 36 and c["ok"]

def test_rdsh_and_clone_formulas():
    rd = [{"name":"RDSH","vcpu":4,"mem":32,"gpu":0,"users_per_server":15,"disk":0,"image":150,"clone_pct":25,"profile":10,"users":100}]
    r = e.demand([], rd, {**e.DEFAULT_PARAMS})
    x = r["rdsh"][0]
    assert x["servers"] == 7 and x["clone_per"] == 69.5
    assert x["disk"] == 69.5 * 7 + 10 * 100
    assert r["user_equiv"] == 0.3 * 100 + 7
    # desktop instant clone: image*clone% + RAM
    dd = e.desktop_row({"vcpu":2,"mem":8,"image":100,"clone_pct":20,"profile":5,"users":10})
    assert dd["clone_per"] == 28 and dd["disk"] == (28 + 5) * 10

def test_solver_and_split():
    r = e.compute(DESK, [], [{**HOST[0], "override":0}], P0)
    c = r["candidates"][0]
    # Power user 4:1 -> 500 cores / 96 = 6 hosts; RAM 8000/1536 -> 6 hosts; +1 HA
    assert c["solve"]["raw"] == 6 and c["hosts"] == 7
    assert e.split_clusters(40, 1, 32) == (2, 20, 42)
    assert e.split_clusters(10, 1, 32) == (1, 10, 11)

def test_gpu_and_unsized():
    d = [{"vcpu":4,"mem":16,"gpu":8,"users":50,"cls":"Heavy / graphics"}]
    r = e.compute(d, [], [{"model":"x","sockets":2,"cores":32,"clock":2.5,"mem":1024,"gpu":0}], P0)
    assert r["candidates"][0]["solve"]["unsized"] and not r["candidates"][0]["eval"]["ok"]
    r = e.compute(d, [], [{"model":"x","sockets":2,"cores":32,"clock":2.5,"mem":1024,"gpu":96}], P0)
    assert r["candidates"][0]["solve"]["need"]["GPU"] == 5

def test_growth_and_empty():
    r = e.compute(DESK, [], HOST, {**P0, "growth_pct":10, "years":3})
    assert r["grown"] and r["future"]["d_users"] == 333
    r = e.compute([], [], HOST, P0)
    assert r["candidates"][0]["hosts"] == 8  # override still honoured; no demand
