"""
    Function
    ===========
    1. Logs the time spent on applications, taking note which applications are focused on to track the time spent on each application.

    2. Outputs the figures at predetermined intervals to a logfile, and optionally to an exit point as a module.

    
    
"""

from OperaPowerRelay import opr
import os
from abc import ABC
import threading
import datetime
import win32gui
import win32process
import psutil
import time
from ScreenMonitor import trayicon, DataClasses as dc
import winotify

def send_toast_notification(message: str) -> None:
    toast = winotify.Notification(
        app_id="ScreenMonitor",
        title="ScreenMonitor",
        msg=message,
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"),
        
    )
    toast.set_audio(winotify.audio.Default, loop=False)
    toast.add_actions(label="Open Logs", launch=FILEDIR)
    toast.show()

def list_current_applications() -> tuple[bool, list[dc.Application_Info]]:

    if PLATFORM == "Windows":
        return True, windows_get_applications()

    else:
        print("Platform not supported yet :(")
        return False, []

def _window_callback(hwnd, results):
    try:
        if not win32gui.IsWindowVisible(hwnd):
            return

        # Get process ID safely
        process_id = win32process.GetWindowThreadProcessId(hwnd)[1]

        # Try to resolve executable name
        exe_name = "Unknown"
        try:
            process = psutil.Process(process_id)
            exe_name = os.path.basename(process.exe())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # harmless, just skip if process is gone or protected

        # Get window title
        name = win32gui.GetWindowText(hwnd)
        if not name:
            return

        # Identify active window handle
        active_hwnd = results[0]

        # Append tuple: (window title, exe name, PID, is_active)
        results[1].append((name, exe_name, process_id, hwnd == active_hwnd))

    except Exception as e:
        opr.write_log(
            isFrom="ScreenMonitor",
            path=os.path.join(FILEDIR, "ScreenMonitorERROR.log"),
            message=f"Error in _window_callback: {e}",
            level="ERROR",
            verbose=True
        )


def windows_get_applications() -> list[dc.Application_Info]:
    active_hwnd = win32gui.GetForegroundWindow()
    res: list[tuple[str, str, int, bool]] = []

    win32gui.EnumWindows(_window_callback, [active_hwnd, res])

    results: list[dc.Application_Info] = [
        dc.Application_Info(name=name, exe_name=exe_name, process_id = process_id, is_focused=is_active) for name, exe_name, process_id, is_active in res
    ]
    return results

INTERVAL: int = 0
FILEDIR: str = ""
IS_MODULE: bool = False
PLATFORM: str = "Windows"
MONITOR: dc.Mister_Monitor | None = None
STOP_SIGNAL = threading.Event()

def stop() -> None:

    global STOP_SIGNAL

    STOP_SIGNAL.set()
    opr.print_from(name="ScreenMonitor", message="Stopping...")

def main(interval: int = 0, filedir: str = "", is_module: bool = False, headless: bool = False) -> None | dc.Mister_Monitor:
    """
    Parameters
    ===========
    interval: int
        The interval in minutes at which to log the screen usage.

    logfile: str
        The path to the logfile to log the screen usage to.

    is_module: bool
        Whether to log the screen usage to the logfile as a module.

    Returns
    ===========
    bool
        True if ScreenMonitor runs successfully, False otherwise.

    """
    
    opr.print_from(name="ScreenMonitor", message="Welcome to ScreenMonitor!")


    global INTERVAL
    global FILEDIR
    global IS_MODULE
    global PLATFORM
    global MONITOR

    INTERVAL = interval or 15
    FILEDIR = filedir or os.path.join(opr.get_special_folder_path("Documents"), "Opera Tools")
    IS_MODULE = is_module or False
    import platform
    PLATFORM = platform.system()

    if is_module:
        return dc.Mister_Monitor(interval=INTERVAL, list_current_applications=list_current_applications, stop_signal=STOP_SIGNAL, file_dir=FILEDIR)

    MONITOR = dc.Mister_Monitor(interval=INTERVAL, list_current_applications=list_current_applications, stop_signal=STOP_SIGNAL, file_dir=FILEDIR)
    MONITOR.start()
    trayicon.start_icon(callback=stop, data=MONITOR, filepath=FILEDIR)
    send_toast_notification(message="Now tracking application usage in the background.")
    while not STOP_SIGNAL.is_set():
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            MONITOR.stop()
            break
        except Exception as e:
            opr.write_log(isFrom="ScreenMonitor", path=os.path.join(FILEDIR, "ScreenMonitorERROR.log"), message=f"Error in main: {e}", level="ERROR", verbose=True)
            break

    trayicon.stop_icon()
    send_toast_notification(message="Stopped tracking application usage in the background.")
    opr.print_from(name="ScreenMonitor", message="Thank you for using ScreenMonitor!")

        

if __name__ == "__main__":
    main()
    