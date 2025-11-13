from PluginTemplate import PluginTemplate
import os, sys
from . import ScreenMonitorMain, DataClasses


from OperaPowerRelay import opr
import threading 
import queue
import datetime
from typing import Iterator
from TrayIcon import TrayIcon
import os
class plugin(PluginTemplate.ophelia_plugin):
    def __init__(self):

        self._data_thread: threading.Thread = None # pyright: ignore[reportAttributeAccessIssue]
        self._running = threading.Event()
        self._running_operations: str = "STOP"
        self._past_data: list[str] = []
        self._data_queue: queue.Queue = queue.Queue(maxsize=1)
        self.processed_message: str = "Nothing to report."
        self._icon_flag: bool = False        
        self._screen_monitor = DataClasses.Mister_Monitor(interval=15, list_current_applications=ScreenMonitorMain.list_current_applications, stop_signal=self._running, file_dir=ScreenMonitorMain.FILEDIR)
        self.tray_icon = TrayIcon.get_tray_icon(name="ScreenMonitor", icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"), menu_callback=self._screen_monitor.menu_callback, closing_callback=self.handle_stop)




        super().__init__(
            name="ScreenMonitor",
            command_map={
                "START": self.handle_start,
                "ADVANCED": self.handle_adv,
                "STOP": self.handle_stop,
                "REPORT": self._screen_monitor.open_report,
                "DIRECTORY": self._screen_monitor.open_directory,
            },
            git_repo="https://github.com/OperavonderVollmer/ScreenMonitor.git",
        )
        
        
    def handle_start(self):    
        if self._running_operations == "START" or self._running_operations == "ADVANCED":
            opr.print_from(name=self._meta["name"], message="Already running")
            return
        
        self._screen_monitor.start()
        self._running_operations = "START"
        self.tray_icon.start_icon()
        return
    
    def handle_adv(self):
        if self._running_operations == "START" or self._running_operations == "ADVANCED":
            opr.print_from(name=self._meta["name"], message="Already running")
            return
        
        self._data_thread = threading.Thread(target=self.generate_data, daemon=True)
        self._data_thread.start()
        self._running_operations = "ADVANCED"
        self.tray_icon.start_icon()
        return

    def handle_stop(self):
        if self._running_operations == "STOP":
            return
        self._screen_monitor.stop()
        self._running_operations = "STOP"
        if not self.tray_icon._stop_signal.is_set():
            self.tray_icon.stop_icon()

    def stream_data(self) -> Iterator:

        while self._running.is_set():
            try:
                data = self._data_queue.get(timeout=1)
                yield data, self.processed_message
            except queue.Empty:
                continue

    def put_data(self, data):
        if self._data_queue.full():
            self._data_queue.get_nowait()
        self._data_queue.put(data)

    def process_data(self, data):
        report = data.get("Report", {})
        raw_date = report.get("Date", "Unknown time")
        session_duration = report.get("Total Time", "an unknown duration")

        # Format the timestamp into something human-readable
        try:
            date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%d-%H-%M-%S")
            formatted_date = date_obj.strftime("%B %d, %Y at %H:%M:%S")
        except ValueError:
            formatted_date = raw_date

        top5 = report.get("Top 5 Applications", [])
        most_active = report.get("Most Active Application", "Unknown")

        all_apps = data.get(next(iter([k for k in data if k != "Report"]), ""), [])
        total_apps = len(all_apps)
        active_apps = sum(1 for app in all_apps if app.get("is_active"))

        most_name = most_active.split(" | ")[-1].strip()
        most_focus_percent = most_active.split("|")[2].strip() if "|" in most_active else "N/A"

        # Format top 5 neatly
        formatted_top5 = "\n".join(
            [f"   {i+1}. {app}" for i, app in enumerate(top5)]
        ) if top5 else "   (No recorded applications.)"

        summary = (
            f"Since {formatted_date} (session length: {session_duration}), "
            f"you have opened {total_apps} applications, "
            f"{active_apps} of which are active as of this log.\n\n"
            f"The most focused application is **{most_name}**, "
            f"used {most_focus_percent} of the time during this period.\n\n"
            f"Top 5 applications:\n{formatted_top5}"
        )

        return summary



    def generate_data(self):
        self._running.set()
        for apps in self._screen_monitor._monitor(as_iterator=True): # type: ignore
            
            try:
                self.processed_message = self.process_data(apps)
                self.put_data(apps)
            except queue.Empty:
                pass
            except Exception as e:
                opr.error_pretty(exc=e, name=self._meta["name"], message=f"Error processing data: {e}")
                break

            if not self._running.is_set():
                break
            
        self._running.clear()

   

    def execute(self):
        # self.handle_commands(self.get_operation())
        return super().run_command()

    def direct_execute(self, *args, **kwargs):
        return super().direct_execute(*args, **kwargs)
    
    def clean_up(self, *args, **kwargs):     
        self.handle_stop()

def get_plugin(): return plugin()


import sys

def accomodate_ophelia(port):
    import socket, time, pickle

    error_count = 5
    while error_count > 0:
        opr.print_from(name="ScreenMonitor", message=f"Sending in {error_count} seconds...")
        time.sleep(1)
        error_count -= 1
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        for attempt in range(5):
            try:
                sock.connect(("127.0.0.1", port))
                opr.print_from(name="ScreenMonitor", message=f"Connected to 127.0.0.1:{port}")
                break
            except ConnectionRefusedError:
                time.sleep(1)
        else:
            opr.print_from(name="ScreenMonitor", message=f"Failed to connect to 127.0.0.1:{port}")
            return
        

        sock.sendall(("PING").encode("utf-8"))
        reply = sock.recv(1024)
        if reply.decode("utf-8") == b"PONG":
            opr.print_from(name="ScreenMonitor", message=f"Received: {reply}")
            
            for attempt in range(5):
                raw_plugin = plugin
                pickled_plugin = pickle.dumps(raw_plugin)
                sock.sendall(pickled_plugin)
                reply = sock.recv(1024)
                if reply.decode("utf-8") == "PING":
                    break               
                sock.sendall(("PONG").encode("utf-8"))
                time.sleep(0.5) 
            else:
                opr.print_from(name="ScreenMonitor", message=f"Failed to send plugin: {reply}")

    opr.print_from(name="ScreenMonitor", message="Plugin subprocess exiting.")
    sys.exit(0)


if len(sys.argv) > 1:    
    accomodate_ophelia(int(sys.argv[1]))      




"""

Notes: Tray icons are a mess
Here's what I want to do:
> Start > Icon shows
> Stop > Icon disappears
> Clean up > Checks if Icon is on > Icon disappears

"""