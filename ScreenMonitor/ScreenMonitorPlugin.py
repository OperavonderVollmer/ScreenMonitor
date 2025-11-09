from PluginTemplate import PluginTemplate
from ScreenMonitor import DataClasses, ScreenMonitor
from OperaPowerRelay import opr
import threading 
import queue
import datetime
from typing import Iterator
from TrayIcon import TrayIcon
import os
import pystray

class plugin(PluginTemplate.ophelia_plugin):
    def __init__(self):
        super().__init__(
            name="ScreenMonitor",
            command_map={
                "START": self.handle_start("START"),
                "ADVANCED": self.handle_start("ADVANCED"),
            },
            git_repo="https://github.com/OperavonderVollmer/ScreenMonitor.git",
        )
        
        self._data_thread: threading.Thread = None # pyright: ignore[reportAttributeAccessIssue]
        self._running = threading.Event()
        self._running_operations: str = "STOP"
        self._past_data: list[str] = []
        self._data_queue: queue.Queue = queue.Queue(maxsize=1)
        self.processed_message: str = "Nothing to report."
        self._icon_flag: bool = False
        self.tray_icon = TrayIcon.get_tray_icon(name="ScreenMonitor", icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"), menu_callback=self.menu_callback, closing_callback=self.icon_stop)

        self._screen_monitor = DataClasses.Mister_Monitor(interval=15, list_current_applications=ScreenMonitor.list_current_applications, stop_signal=self._running, file_dir=ScreenMonitor.FILEDIR)

    def handle_start(self, command: str):    
        if self._running_operations == "START" or self._running_operations == "ADVANCED":
            opr.print_from(name=self._meta["name"], message="Already running")
            return
        self.icon_start()

        if command.upper() == "ADVANCED":
            self._data_thread = threading.Thread(target=self.generate_data, daemon=True)
            self._data_thread.start()
            self._running_operations = "ADVANCED"
        else:
            self._screen_monitor.start()
            self._running_operations = "START"
            return

    def handle_stop(self):
        if self._running_operations == "STOP":
            return
        self.tray_icon.stop_icon()
        self._screen_monitor.stop()
        self._running_operations = "STOP"

    def menu_callback(self):
        
        menu = pystray.Menu(
            pystray.MenuItem("Screen Monitor", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._screen_monitor.get_active_application(), None, enabled=False),
            pystray.MenuItem(self._screen_monitor.get_elapsed_time(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Get full report", self._screen_monitor.open_report),
            pystray.MenuItem("Open log folder", self._screen_monitor.open_directory),
            pystray.MenuItem("Exit", self.icon_stop),
        )
        return self._screen_monitor.get_active_application(), menu

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

    def handle_commands(self, command: str):
        
        for c in command.split(" "):

            if c.upper() == "START" or c.upper() == "ADVANCED":
                if self._running_operations == "START" or self._running_operations == "ADVANCED":
                    opr.print_from(name=self._meta["name"], message="Already running")
                    return
                self.icon_start()

                if c.upper() == "ADVANCED":
                    self._data_thread = threading.Thread(target=self.generate_data, daemon=True)
                    self._data_thread.start()
                    self._running_operations = "ADVANCED"
                else:
                    self._screen_monitor.start()
                    self._running_operations = "START"
                    return
            elif c.upper() == "STOP":
                if self._running_operations == "STOP":
                    return
                
                if self._icon_flag:
                    self.icon_stop()
                    self._icon_flag = False
                    self._screen_monitor.save_log(datetime.datetime.now(), manual=True)

                if self._running_operations == "START":
                    self._screen_monitor.stop()

                elif self._running_operations == "ADVANCED":
                    self._running.clear()
                    if self._data_thread and self._data_thread.is_alive():
                        self._data_thread.join(timeout=2)
                        
            elif c.upper() == "SUMMARY":
                opr.print_from(name=self._meta["name"], message=self.processed_message)
            elif c.upper() == "REPORT":
                try:
                    self._screen_monitor.open_report()
                except IndexError:
                    opr.print_from(name=self._meta["name"], message="No data to report")
            elif c.upper() == "DIRECTORY":
                self._screen_monitor.open_directory()
        


    def get_operation(self) -> str:
        opr.list_choices(choices=self._meta["commands"], title=self._meta["name"], after_return_count=1)
        # answer = opr.input_timed_r(name=self._meta["name"], message="Select an option (Autostart in 10 seconds)", wait_time=10)
        answer = opr.input_from(name=self._meta["name"], message="Select an option")
        clean_answer, log_message = opr.sanitize_text(answer or "")

        if log_message:
            opr.print_from(name=self._meta["name"], message=log_message)
            return ""

        comm = ""
        if not clean_answer or clean_answer == "1":
            comm = "START"
        elif clean_answer == "2":
            comm = "ADVANCED"
        elif clean_answer == "3":
            comm = "STOP"
        elif clean_answer == "4":
            comm = "SUMMARY"
        elif clean_answer == "5":
            comm = "REPORT"
        elif clean_answer == "6":
            comm = "DIRECTORY"
        else:
            opr.print_from(name=self._meta["name"], message=f"Invalid input: {clean_answer}")

        
            

    def execute(self):
        # self.handle_commands(self.get_operation())
        return self.run_command()

    def direct_execute(self, *args, **kwargs):
        return super().direct_execute(*args, **kwargs)
    
    def clean_up(self, *args, **kwargs):     
        self.handle_stop()

def get_plugin(): return plugin()


"""

Notes: Tray icons are a mess
Here's what I want to do:
> Start > Icon shows
> Stop > Icon disappears
> Clean up > Checks if Icon is on > Icon disappears

"""