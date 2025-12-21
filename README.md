# ScreenMonitor

**Ophelia Suite Plugin: Desktop Screen Monitoring and Capture**

ScreenMonitor is a modular Python plugin for the [Ophelia Suite](https://github.com/OperavonderVollmer/Ophelia), providing continuous or triggered screen observation, image capture, and basic analysis capabilities. Designed to adhere strictly to the [PluginTemplate](https://github.com/OperavonderVollmer/PluginTemplate) abstract base class, it enables seamless integration into the broader automation orchestration system.

## Features

- **Screen Capture**: Periodic or event-driven screenshots using Pillow.
- **System Tray Integration**: Minimized operation with status indicators via pystray.
- **Plugin Lifecycle Compliance**: Standard prep/execute/cleanup methods for reliable orchestration via OperaPowerRelay.
- **Extensibility**: Configurable monitoring intervals, regions of interest, and post-capture hooks.

## Installation

### As Ophelia Plugin (Recommended)

Place this repository in the Ophelia backend plugins directory and ensure dependencies are met suite-wide.

### Standalone Development

```bash
git clone https://github.com/OperavonderVollmer/ScreenMonitor.git
cd ScreenMonitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install pillow pystray git+https://github.com/OperavonderVollmer/OperaPowerRelay.git

# Editable install (if using setup.py)
pip install -e .
