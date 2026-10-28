# Changelog

## 1.0.1 (October 2026)
* **Mac launch.** The "VDI Host Sizer" app now tells Terminal to run the launcher directly, so macOS no longer shows "Run_on_mac.command Not Opened - Apple could not verify...". macOS may ask once to allow the app to control Terminal; click OK.
* **Mac install.** The ReadMe and landing page now show the one-line install as the only Mac route (a browser-downloaded ZIP is quarantined by macOS).

## 1.0 (October 2026)
First release of VDI Host Sizer.

* **Workloads.** Describe any number of desktop user types (you name them) and RDSH farms: concurrent users, vCPU, memory, vGPU, thick/PVS or Instant Clone/MCS disk, and profile storage.
* **Hardware.** Up to three candidate ESXi hosts side by side, with a processor picker (Intel Xeon 6 and 5th Gen, AMD EPYC 9005 and 9004), memory, GPU memory and an optional host-count override.
* **Recommendation.** Calculates the host count from CPU, memory, GPU memory and an optional VMs-per-host cap, adds N+X failure tolerance, applies the minimum cluster size and splits sizings that exceed the cluster cap. Design check at N-X: vCPU:pCore (and with hyper-threading), GHz per user, memory and GPU remaining, VMs per host.
* **Storage.** Desktop and RDSH capacity combined, with dedupe and a free-space reserve.
* **Design rules.** vCPU:pCore limits by workload class, CPU and RAM overhead reserves, growth and licensing (16-core minimum). Defaults are planning values pending AHEAD review.
* **Report.** Self-contained AHEAD-branded HTML report that names the failure tolerance (N+1, N+2...) and the settings used.
* **Projects.** Save and reopen sizings from `~/HostSizer/VDIProjects`.
* **Update check.** The sidebar shows an *Update available* card when a newer version is on GitHub. Only the version number is read; set `VDI_HOSTSIZER_NO_UPDATE_CHECK=1` to turn it off.
* **Easy Mac install.** One command installs, creates a double-click *VDI Host Sizer* app in Applications, and starts the tool, with no macOS security prompts.
