# Releasing a new version

Every revision ships with: the app files, an updated `CHANGELOG.md`, and a **new landing page**.

1. **Bump the version.** Edit `APP_VERSION = "x.y"` in `vdi_app.py` (keep that exact line format: the installer and the
   update check read it).
2. **Write the release notes.** Add a `## x.y (Month YYYY)` section at the top of `CHANGELOG.md`, one `*` bullet per change.
   The landing page's "What's new" shows the newest two sections.
3. **Run the tests.** `python -m pytest tests` (includes a check that the version and the changelog agree).
4. **Refresh the screenshots** (when the screens changed): `pip install playwright pillow && playwright install chromium`, then
   `python landing/capture_screenshots.py`.
5. **Build the landing page.** `python landing/build_landing_page.py` writes
   `landing/dist/VDI_Host_Sizer_Landing_Page.html` (single file, publish it as a new version of the Roost prototype).
6. **Publish.** Commit and push to `main` on GitHub. The update notice in everyone's app, the Mac one-line installer and the
   ZIP download all read from `main`, so pushing is the release.

Nothing else needs editing: the landing page takes the version, release notes, vCPU:pCore defaults and screenshots from the
repo.
