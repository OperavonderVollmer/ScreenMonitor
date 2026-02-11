from PluginTemplate import PluginTemplate, DSL
import os, sys
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)
import ScreenMonitorMain, DataClasses
from OperaPowerRelay import opr, trayicon as TrayIcon
import threading 
import queue
import datetime
from typing import Iterator
import os
import datetime


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



        # Only START, STOP, REPORT, DIRECTORY commands are available for Ortlinde. The other commands are for internal use and only accessible using terminal commands and the tray icon.

        super().__init__(
            name="ScreenMonitor",
            description= "ScreenMonitor is a plugin that quantifies the time spent on applications, filtering background noise from the data. It also outputs the data to a logfile located in your 'Documents/Opera Tools' folder, and optionally to an exit point as a module.",
            prompt="NOTE: The plugin's logs are located inside the computer's Documents folder and are inaccessible from this interface.",
            command_map={ 
                "START": self.handle_start,
                "STOP": self.handle_stop,
                "DEBUG": self.handle_debug,
                "REPORT": self.handle_report,
                "JSON": self.handle_json,
                "DIRECTORY": self.handle_directory,
            },
            git_repo="https://github.com/OperavonderVollmer/ScreenMonitor.git",
        )
        
        
    def handle_debug(self):    
        if self._running_operations == "RUNNING":
            opr.print_from(name=self._meta["name"], message="Already running")
            return False
        
        self._running_operations = "RUNNING"
        self._screen_monitor.start()
        self.tray_icon.start_icon({
            "app_id": "ScreenMonitor",
            "title": "ScreenMonitor",
            "msg": "Started tracking application usage in the background.",
            "icon_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"),
            "actions": {
                "Open Logs": ScreenMonitorMain.FILEDIR
            }
        })
        return True
    
    def handle_start(self):
        message = ""
        if self._running_operations == "RUNNING":
            opr.print_from(name=self._meta["name"], message="Already running")
            message = "Couldn't start ScreenMonitor. ScreenMonitor is already running."
        else:
            self._running_operations = "RUNNING"
            self._data_thread = threading.Thread(target=self.generate_data, daemon=True)
            self._data_thread.start()
            self.tray_icon.start_icon({
                "app_id": "ScreenMonitor",
                "title": "ScreenMonitor",
                "msg": "Started tracking application usage in the background.",
                "icon_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"),
                "actions": {
                    "Open Logs": ScreenMonitorMain.FILEDIR
                }
            })
            message = "ScreenMonitor STARTED successfully."
            
        return super().input_scheme(
            root=DSL.JS_Div(
                id="ScreenMonitor",
                children=[
                    DSL.JS_Label(
                        id="ScreenMonitor_Reply",
                        text=message,
                    )
                ]
            ), form=False, serialize=True)
        

    def handle_stop(self):
        message=""
        if self._running_operations == "STOP":
            opr.print_from(name=self._meta["name"], message="Already stopped")
            message = "Couldn't stop ScreenMonitor. ScreenMonitor is already stopped."
        else:
            self._running_operations = "STOP"
            self.tray_icon.stop_icon({
                "app_id": "ScreenMonitor",
                "title": "ScreenMonitor",
                "msg": "Stopped tracking application usage in the background.",
                "icon_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ScreenMonitor_logo.ico"),
                "actions": {
                    "Open Logs": ScreenMonitorMain.FILEDIR
                }
            })
            self._screen_monitor.stop()
            message = "ScreenMonitor STOPPED successfully."
        return super().input_scheme(
            root=DSL.JS_Div(
                id="ScreenMonitor",
                children=[
                    DSL.JS_Label(
                        id="ScreenMonitor_Reply",
                        text=message,
                    )
                ]
            ), form=False, serialize=True
        )


    


    def handle_report(self):

        def transmute_report(raw: dict) -> dict:
            report = raw.get("report", {})
            entries = raw.get("entries", [])

            clean_entries = []
            for e in entries:
                clean_entries.append({
                    "app": e["name"],
                    "exe": e["exe_name"],
                    "pid": e["process_id"],
                    "time_seconds": float(e["time"]),
                    "focused_seconds": float(e["focused_time"]),
                    "active": bool(e["is_active"]),
                    "elapsed_ratio": float(e.get("elapsed_ratio", 0)),
                    "focused_ratio": float(e.get("focused_ratio", 0)),
                    "start": e["start_time"],
                    "end": None if e["end_time"] == "STILL ACTIVE" else e["end_time"],
                })

            return {
                "meta": {
                    "timestamp": report.get("timestamp"),
                    "total_time_seconds": report.get("total_time_seconds"),
                    "most_active": report.get("most_active"),
                    "top5": report.get("top5", []),
                },
                "entries": clean_entries,
            }

        _ = self._screen_monitor.open_report(open_json=False)
        if _ is None:
            return super().input_scheme(
                root=DSL.JS_Div(
                    id="ScreenMonitor_Report",
                    children=[
                        DSL.JS_Label(
                            id="ScreenMonitor_NoReport",
                            text="No report found. Please run ScreenMonitor first.",
                        )
                    ]
                ), form=False, serialize=True
            )
        report = transmute_report(_) # type: ignore

        top5_children = []
        for i, app in enumerate(report["meta"]["top5"], start=1):
            top5_children.append(
                DSL.JS_Header_Div(
                    id=f"Top5_App_{i}",
                    header=f"{i}. {app['name']}",
                    header_level=4,
                    child=DSL.JS_Label(
                        id=f"Top5_App_{i}_Time",
                        classes="whiteText",
                        text=opr.clean_time(datetime.timedelta(seconds=app["time_seconds"]))
                    )
                )
            )

        entries_children = []
        for i, app in enumerate(report["entries"], start=1):
            entries_children.append(
                DSL.JS_Header_Div(
                    id=f"Entries_App_{i}",
                    header=f"{i}. {app['app']}",
                    header_level=4,
                    child=DSL.JS_Label(
                        id=f"Entries_App_{i}_Time",
                        classes="whiteText",
                        text=opr.clean_time(datetime.timedelta(seconds=app["time_seconds"]))
                    )
                )
        )

        report_dsl = DSL.JS_Header_Div(
            id="ScreenMonitor_Report",
            header="Report for " + datetime.datetime.fromisoformat(str(report["meta"]["timestamp"])).strftime("%B %d, %Y at %H:%M:%S"),
            header_level=1,
            header_classes="bold",
            child=DSL.JS_Div(
                id="ScreenMonitor_Report_Content",
                children=[                
                    DSL.JS_Header_Div(
                        id="ScreenMonitor_TotalTime",
                        header="Elapsed Time",
                        header_level=2,
                        child=DSL.JS_Label(
                            id="ScreenMonitor_TotalTime_Text",
                            classes="whiteText",
                            text=opr.clean_time(datetime.timedelta(seconds=report["meta"]["total_time_seconds"])),
                        )
                    ),
                    DSL.JS_Div( # Most Active
                        id="ScreenMonitor_MostActive",
                        classes="divHorizontal divRaised compensateMarginRight",
                        children=[
                            DSL.JS_Header_Div(
                                id="ScreenMonitor_MostActive_App",
                                header="Most Active App",
                                header_level=4,
                                div_classes="divCentered",
                                child=DSL.JS_Label(
                                    id="ScreenMonitor_MostActive_App_Text",
                                    classes="noInputFieldDefaults whiteText",
                                    text=report["meta"]["most_active"]["name"],
                                )
                            ),
                            DSL.JS_Header_Div(
                                id="ScreenMonitor_MostActive_Time",
                                header="Elapsed Time",
                                header_level=4,
                                div_classes="divCentered",
                                child=DSL.JS_Label(
                                    id="ScreenMonitor_MostActive_Time_Text",
                                    classes="noInputFieldDefaults whiteText",
                                    text=opr.clean_time(datetime.timedelta(seconds=report["meta"]["most_active"]["time_seconds"])),
                                )
                            ),
                            DSL.JS_Header_Div(
                                id="ScreenMonitor_MostActive_FocusedTime",
                                header="Focused Time",
                                header_level=4,
                                div_classes="divCentered",
                                child=DSL.JS_Label(
                                    id="ScreenMonitor_MostActive_FocusedTime_Text",
                                    classes="noInputFieldDefaults whiteText",
                                    text=f"{opr.clean_time(datetime.timedelta(seconds=report['meta']['most_active']['focused_seconds']))} ({report['meta']['most_active']['focus_ratio']*100:.2f}%)"
                                )
                            ),
                        ],
                    ),
                    DSL.JS_Header_Div(
                        id="ScreenMonitor_Top5",
                        header="Top 5 Apps",
                        header_level=2,
                        header_classes="bold",
                        child=DSL.JS_Div(
                            id="ScreenMonitor_Top5_List",
                            children=top5_children,
                        )
                    ),
                    DSL.JS_Header_Div(
                        id="ScreenMonitor_AllEntries",
                        header="All Recorded Entries",
                        header_level=2,
                        header_classes="bold",
                        child=DSL.JS_Div(
                            id="ScreenMonitor_AllEntries_List",
                            children=entries_children,
                        )
                    )
                ]
            )
        )

        return super().input_scheme(root=report_dsl, form=False, serialize=True)
    
    
    def handle_directory(self):
        self._screen_monitor.open_directory()
        return super().input_scheme(
            root=DSL.JS_Div(
                id="ScreenMonitor",
                children=[
                    DSL.JS_Label(
                        id="ScreenMonitor_Reply",
                        text="Opened ScreenMonitor log directory on host machine.",
                    )
                ]
            ), form=False, serialize=True
        )
    
    def handle_json(self):
        self._screen_monitor.open_report()
        return True

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
        report = data.get("report", {})
        raw_timestamp = report.get("timestamp", "Unknown time")
        session_duration = report.get("total_time_seconds", 0.0)

        # Format the timestamp into human-readable
        try:
            date_obj = datetime.datetime.strptime(raw_timestamp, "%Y-%m-%dT%H:%M:%S")
            formatted_date = date_obj.strftime("%B %d, %Y at %H:%M:%S")
        except ValueError:
            formatted_date = raw_timestamp

        most_active = report.get("most_active", {})
        top5 = report.get("top5", [])

        all_apps = data.get("entries", [])
        total_apps = len(all_apps)
        active_apps = sum(1 for app in all_apps if app.get("is_active", False))

        most_name = most_active.get("name", "Unknown")
        most_focus_ratio = most_active.get("focus_ratio", 0.0)
        most_focus_percent = f"{most_focus_ratio*100:.1f}%" if most_active else "N/A"

        # Format top 5 neatly
        if top5:
            formatted_top5 = "\n".join(
                [
                    f"   {i+1}. {app['name']} — "
                    f"Time: {app['time_seconds']:.2f}s | "
                    f"Focused: {app['focused_seconds']:.2f}s ({app['focus_ratio']*100:.1f}%)"
                    for i, app in enumerate(top5)
                ]
            )
        else:
            formatted_top5 = "   (No recorded applications.)"

        summary = (
            f"Since {formatted_date} (session length: {session_duration:.2f}s), "
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
                pass
            except queue.Empty:
                pass
            except Exception as e:
                opr.error_pretty(exc=e, name=self._meta["name"], message=f"Error processing data: {e}")
                break

            if not self._running.is_set():
                break
            
        self._running.clear()

   
    def input_scheme(self, root = None, form = True, serialize: bool = True):
        scheme = super().input_scheme(root= DSL.JS_Div(
                id="screenmonitor-div",
                children=[
                    DSL.JS_Select(
                        id="screenmonitor-select",
                        label="Select an option",      
                        options= ["START", "STOP", "REPORT", "DIRECTORY"],
                    )
                ]
            ), form=form, serialize=True)
        return scheme

    def execute(self, **kwargs):
        if kwargs.get("command", None):
            return self.direct_execute(kwargs["command"])
        elif kwargs.get("screenmonitor-select", None):
            return self.direct_execute(kwargs["screenmonitor-select"])        
        elif kwargs.get("generic_input", None):
            return self.direct_execute(kwargs["generic_input"])
        else:
            return super().run_command()

    def direct_execute(self, command):
        if command in self._meta["command_map"]:
            return self._meta["command_map"][command]()
    
    def clean_up(self, *args, **kwargs):     
        self.handle_stop()

def get_plugin(): return plugin()
