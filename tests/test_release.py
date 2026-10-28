import os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
read = lambda f: open(os.path.join(ROOT, f), encoding="utf-8").read()


def app_version():
    return re.search(r'^APP_VERSION = "([^"]+)"', read("vdi_app.py"), re.M).group(1)


def test_version_line_is_readable_by_installer_and_update_check():
    v = app_version()
    assert re.fullmatch(r"\d+(\.\d+){1,2}", v)
    sed = subprocess.run(["sed", "-n", r's/^APP_VERSION = "\(.*\)"/\1/p', os.path.join(ROOT, "vdi_app.py")],
                         capture_output=True, text=True).stdout.split()[0]
    assert sed == v


def test_changelog_top_entry_matches_version():
    m = re.search(r"^## ([\d.]+)", read("CHANGELOG.md"), re.M)
    assert m and m.group(1) == app_version()


def test_update_urls_point_at_the_repo():
    src = read("vdi_app.py")
    assert "adammarcum/VDI-Sizing-Tool" in src and "adammarcum/VDI-Sizing-Tool" in read("install_mac.sh")
