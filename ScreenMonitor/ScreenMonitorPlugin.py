from PluginTemplate import PluginTemplate
from ScreenMonitor import ScreenMonitor, DataClasses, trayicon
from OperaPowerRelay import opr
import threading 
import queue
import datetime
from typing import Iterator

class plugin(PluginTemplate.ophelia_plugin):
    def __init__(self):
        super().__init__(
            name="ScreenMonitor",
            commands=["START", "ADVANCED START", "STOP", "SUMMARY", "OPEN REPORT", "OPEN DIRECTORY",],
            git_repo="https://github.com/OperavonderVollmer/ScreenMonitor.git",
        )
        
        self._data_thread: threading.Thread = None # pyright: ignore[reportAttributeAccessIssue]
        self._running = threading.Event()
        self._running_operations: str = "STOP"
        self._past_data: list[str] = []
        self._data_queue: queue.Queue = queue.Queue(maxsize=1)
        self.processed_message: str = "Nothing to report."
        self._icon_flag: bool = False

        self._screen_monitor = DataClasses.Mister_Monitor(interval=15, list_current_applications=ScreenMonitor.list_current_applications, stop_signal=self._running, file_dir=ScreenMonitor.FILEDIR)


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
        
    def icon_start(self):
        if self._icon_flag:
            return
        
        self._icon_flag = True
        print("Starting tray icon...")
        trayicon.start_icon(callback=self.clean_up, data=self._screen_monitor, filepath=ScreenMonitor.FILEDIR)
    
    def icon_stop(self):
        if not self._icon_flag:
            return
        
        self._icon_flag = False
        print("Stopping tray icon...")
        trayicon.stop_icon()


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
        return comm
            

    def execute(self):
        self.handle_commands(self.get_operation())

    def direct_execute(self, *args, **kwargs):
        return super().direct_execute(*args, **kwargs)
    
    def clean_up(self, *args, **kwargs):
        
        
        self.handle_commands("STOP")

def get_plugin(): return plugin()


"""

Notes: Tray icons are a mess
Here's what I want to do:
> Start > Icon shows
> Stop > Icon disappears
> Clean up > Checks if Icon is on > Icon disappears

"""