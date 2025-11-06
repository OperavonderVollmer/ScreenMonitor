from PIL import Image
from OperaPowerRelay import opr
import pystray
import os
import threading
import time
import sys
from typing import Callable
import datetime

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico")
ICON = Image.open(SCRIPT_PATH)
STOP_SIGNAL = threading.Event()
ICON_THREAD = None
STOP: Callable = None # pyright: ignore[reportAssignmentType]
FILEPATH: str = ""

def stop_icon() -> None:
    global STOP_SIGNAL
    global STOP

    STOP_SIGNAL.set()
    time.sleep(0.5)
    STOP()

def icon_thread(monitor) -> None:
    last_app = None
    last_elapsed = None

    def build_menu():
        return pystray.Menu(
            pystray.MenuItem("Screen Monitor", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(monitor.get_active_application(), None, enabled=False),
            pystray.MenuItem(monitor.get_elapsed_time(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Get full report", monitor.open_report),
            pystray.MenuItem("Open log folder", monitor.open_directory),
            pystray.MenuItem("Exit", stop_icon),
        )

    i = pystray.Icon("ScreenMonitor", ICON, "ScreenMonitor", menu=build_menu())
    i.run_detached()

    while not STOP_SIGNAL.is_set():
        current_app = monitor._active_application
        current_elapsed = str(datetime.datetime.now() - monitor._start_time).split('.')[0]

        if current_app != last_app or current_elapsed != last_elapsed:
            try:
                i.menu = build_menu()
            except Exception:
                time.sleep(2)

            last_app = current_app
            last_elapsed = current_elapsed

        i.title = f"ScreenMonitor - {current_app or 'None'}"
        time.sleep(1)

    i.stop()
    sys.exit(0)

def start_icon(callback: Callable, data, filepath: str) -> None:
    global ICON_THREAD
    global STOP
    global FILEPATH
    global DATA
    
    ICON_THREAD = threading.Thread(target=icon_thread, args=(data,), daemon=True)
    ICON_THREAD.start()

    STOP = callback
    FILEPATH = filepath