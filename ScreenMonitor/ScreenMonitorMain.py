"""
    Function
    ===========
    1. Logs the time spent on applications, taking note which applications are focused on to track the time spent on each application.

    2. Outputs the figures at predetermined intervals to a logfile, and optionally to an exit point as a module.

    
    
"""

from OperaPowerRelay import opr
import os, sys
import threading
import win32gui
import win32process
import psutil
import time
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

import  DataClasses

from TrayIcon import TrayIcon
import winotify
import os
import psutil
import win32gui
import win32process
import win32con




def list_current_applications() -> tuple[bool, list[DataClasses.Application_Info]]:

    if PLATFORM == "Windows":
        return True, windows_get_applications()

    else:
        print("Platform not supported yet :(")
        return False, []

# def _window_callback(hwnd, results):
#     try:
#         if not win32gui.IsWindowVisible(hwnd):
#             return
#         # Get process ID safely
#         process_id = win32process.GetWindowThreadProcessId(hwnd)[1]

#         # Try to resolve executable name
#         exe_name = "Unknown"
#         try:
#             process = psutil.Process(process_id)
#             exe_name = os.path.basename(process.exe())
#         except (psutil.NoSuchProcess, psutil.AccessDenied):
#             pass  # harmless, just skip if process is gone or protected

#         # Get window title
#         name = win32gui.GetWindowText(hwnd)
#         if not name:
#             return

#         # Identify active window handle
#         active_hwnd = results[0]

#         # Append tuple: (window title, exe name, PID, is_active)
#         results[1].append((name, exe_name, process_id, hwnd == active_hwnd))

#     except Exception as e:
#         opr.write_log(
#             isFrom="ScreenMonitor",
#             path=os.path.join(FILEDIR, "ScreenMonitorERROR.log"),
#             message=f"Error in _window_callback: {e}",
#             level="ERROR",
#             verbose=True
#         )

# def windows_get_applications() -> list[dc.Application_Info]:
    active_hwnd = win32gui.GetForegroundWindow()
    res: list[tuple[str, str, int, bool]] = []

    win32gui.EnumWindows(_window_callback, [active_hwnd, res])

    results: list[DataClasses.Application_Info] = [
        DataClasses.Application_Info(name=name, exe_name=exe_name, process_id = process_id, is_focused=is_active) for name, exe_name, process_id, is_active in res
    ]
    return results

KNOWN_BACKGROUND_EXE = {
    "textinputhost.exe",     # IME / PowerToys input host
    "applicationframehost.exe",  # UWP container
    "shellexperiencehost.exe",
    "searchui.exe",
    "startmenuexperiencehost.exe",
    "systemsettings.exe"
}

def _is_suspended(pid: int) -> bool:
    """Detect if a process is suspended (e.g., Notepad with green leaf)."""
    try:
        process = psutil.Process(pid)
        # STATUS_STOPPED is typical for suspended UWP apps
        return process.status() == psutil.STATUS_STOPPED
    except psutil.Error:
        return False


def _window_callback(hwnd, context):
    active_hwnd, results = context
    try:
        # 1. Must be a visible top-level window
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetParent(hwnd):  # Skip owned/child windows
            return

        # 2. Must have a non-empty title
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return

        # 3. Get process info
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == 0:
            return

        # 4. Skip suspended/background UWP apps
        if _is_suspended(pid):
            return

        # 5. Skip known system processes
        try:
            process = psutil.Process(pid)
            exe_path = process.exe().lower() # type: ignore
            exe_name = os.path.basename(exe_path)
            username = process.username().upper()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        if exe_name in KNOWN_BACKGROUND_EXE:
            return

        # if any(
        #     bad in exe_path
        #     for bad in [
        #         "\\windows\\system32",
        #         "\\windows\\servicing",
        #         "\\windows\\winsxs",
        #         "\\windows\\immersivecontrolpanel",
        #     ]
        # ):
        #     return

        # if username.startswith("NT AUTHORITY") or username.startswith("SYSTEM"):
        #     return

        # 6. Skip invisible or helper windows
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if style & win32con.WS_EX_TOOLWINDOW:
            return

        # 7. Save entry
        is_active = hwnd == active_hwnd
        results.append((title, exe_name, pid, is_active))

    except Exception as e:
        opr.write_log(
            isFrom="ScreenMonitor",
            path=os.path.join(FILEDIR, "ScreenMonitorERROR.log"),
            message=f"Error in _window_callback: {e}",
            level="ERROR",
            verbose=True
        )


def windows_get_applications() -> list[DataClasses.Application_Info]:
    """Return only applications equivalent to Task Manager’s 'Apps' section."""
    active_hwnd = win32gui.GetForegroundWindow()
    results: list[tuple[str, str, int, bool]] = []

    win32gui.EnumWindows(_window_callback, [active_hwnd, results])

    return [
        DataClasses.Application_Info(
            name=title,
            exe_name=exe_name,
            process_id=pid,
            is_focused=is_active
        )
        for title, exe_name, pid, is_active in results
    ]


INTERVAL: int = 0
FILEDIR: str = os.path.join(opr.get_special_folder_path("Documents"), "Opera Tools", "ScreenMonitor")
IS_MODULE: bool = False
PLATFORM: str = "Windows"
MONITOR: DataClasses.Mister_Monitor | None = None
STOP_SIGNAL = threading.Event()

def stop() -> None:

    global STOP_SIGNAL

    STOP_SIGNAL.set()
    opr.print_from(name="ScreenMonitor", message="Stopping...")



def main(interval: int = 0, filedir: str = "", is_module: bool = False) -> None | DataClasses.Mister_Monitor:
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
    None | dc.Mister_Monitor
        If is_module is True, returns the Mister_Monitor object.
        Otherwise, returns None.

    """
    
    opr.print_from(name="ScreenMonitor", message="Welcome to ScreenMonitor!")


    global INTERVAL
    global FILEDIR
    global IS_MODULE
    global PLATFORM
    global MONITOR

    INTERVAL = interval or 15
    FILEDIR = filedir or FILEDIR
    IS_MODULE = is_module or False
    import platform
    PLATFORM = platform.system()

    if is_module:
        return DataClasses.Mister_Monitor(interval=INTERVAL, list_current_applications=list_current_applications, stop_signal=STOP_SIGNAL, file_dir=FILEDIR)
    
    MONITOR = DataClasses.Mister_Monitor(interval=INTERVAL, list_current_applications=list_current_applications, stop_signal=STOP_SIGNAL, file_dir=FILEDIR)
    MONITOR.start()
    
    trayicon = TrayIcon.get_tray_icon(name="ScreenMonitor", icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"), menu_callback=MONITOR.menu_callback, closing_callback=stop)
    trayicon.start_icon()
    opr.send_toast_notification(app_id = "ScreenMonitor", title="ScreenMonitor", msg="Started tracking application usage in the background.", icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"), actions={"Open Logs": FILEDIR})
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
    opr.send_toast_notification(app_id = "ScreenMonitor", title="ScreenMonitor", msg="Stopped tracking application usage in the background.", icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"), actions={"Open Logs": FILEDIR})
    opr.print_from(name="ScreenMonitor", message="Thank you for using ScreenMonitor!")

        

if __name__ == "__main__":
    main()
    
