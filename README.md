# ScreenMonitor

**Ophelia Suite Plugin — Application Time Logging & Foreground Activity Tracking**

ScreenMonitor is a lightweight desktop monitoring plugin that tracks application lifetimes, total runtime, and foreground usage. It is designed for unobtrusive, offline operation and integrates cleanly into the **Ophelia Suite** via a standardized plugin lifecycle.

As an Ophelia plugin, ScreenMonitor conforms to the [PluginTemplate](https://github.com/OperavonderVollmer/PluginTemplate) abstract base class (`prep → execute → cleanup`) and is orchestrated through [OperaPowerRelay](https://github.com/OperavonderVollmer/OperaPowerRelay). A system tray interface (via `pystray`) allows continuous background execution without user disruption.

---

## Key Capabilities

- **Application Lifetime Tracking**  
  Records process start/end times and total runtime per application.

- **Foreground Usage Measurement**  
  Tracks active user focus time by monitoring window state and foreground transitions.

- **Structured Logging & Reporting**  
  Outputs timestamped logs and aggregated summaries in JSON format for downstream analysis.

- **Ophelia Plugin Compliance**  
  Enforces metadata standards, lifecycle hooks, and inter-plugin communication.

- **Offline & Extensible by Design**  
  No network dependency. Easily extended with filters (e.g., application whitelists/blacklists).

---

## Project Structure
```
ScreenMonitor/
├── main.py          # Core plugin logic (monitoring and logging)
├── quickstart.py    # Standalone testing entrypoint
├── GET STARTED.bat  # Windows dependency installer and launcher
├── requirements.txt # Core dependencies
├── setup.py         # Editable package configuration
└── ScreenMonitor/    # Internal modules (refactored December 2025)
```
---

## Installation & Usage

### As an Ophelia Plugin (Recommended)

1. Install ScreenMonitor through Ophelia’s plugin setup workflow.
2. Launch Ophelia and select **START** to begin background logging.

All dependencies are handled automatically during Ophelia’s setup phase.

---

### Standalone Mode (Windows)

1. Download the repository as a ZIP and extract it to a local directory.
2. Run `GET STARTED.bat` to install required dependencies.
3. After setup completes, launch `start ScreenMonitor.bat` to begin monitoring.


---

## Notes

- ScreenMonitor is designed to run continuously with minimal overhead.
- Logged data is local-only by default.
- Intended as a foundational telemetry component within the broader Ophelia automation ecosystem.
