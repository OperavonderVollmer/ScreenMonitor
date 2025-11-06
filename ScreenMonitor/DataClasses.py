from OperaPowerRelay import opr
import os
from abc import ABC
import threading
import datetime
import win32gui
import win32process
import psutil
import time
from ScreenMonitor import trayicon
from typing import Iterator
class Application_Info:
    def __init__(self, name: str, exe_name: str, process_id: int, is_focused: bool) -> None:
        self._name: str = name
        self._exe_name: str = exe_name
        self._process_id: int = process_id
        self._is_focused = is_focused

    def dump(self) -> dict:
        return {"name": self._name, "exe_name": self._exe_name, "process_id": self._process_id, "is_focused": self._is_focused}


class IApplication(ABC):
    def __init__(self, name: str, exe_name: str, process_id: int) -> None:
        self._name: str = name
        self._exe_name: str = exe_name
        self._process_id: int = process_id
        self._time: float = 0
        self._focused_time: float = 0
        self._is_active: bool = True
        self._snap_time: datetime.datetime | None = None
        self._start_time: datetime.datetime = datetime.datetime.now() 
        self._end_time: datetime.datetime | str = "STILL ACTIVE"

    @property
    def name(self) -> str: return self._name    
    @name.setter
    def name(self, value: str) -> None: self._name = value
    @property
    def exe_name(self) -> str: return self._exe_name
    @property
    def process_id(self) -> int: return self._process_id
    @property
    def time(self) -> float: return self._time
    @property
    def focused_time(self) -> float: return self._focused_time
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def start_time(self) -> datetime.datetime: return self._start_time
    @property
    def end_time(self) -> datetime.datetime | str: return self._end_time
   
    def deliberate(self, snapped_time: datetime.datetime, is_focused: bool, is_active: bool, as_iterator: bool) -> None:
        
        if not is_active:
            self._end_time = datetime.datetime.now()
            self._is_active = False
            if not as_iterator:
                opr.print_from(name="ScreenMonitor", message=f"Application {self._name} is no longer active")
            return
        
        self.add_time(snapped_time, is_focused=is_focused, as_iterator=as_iterator)
    def add_time(self, snapped_time: datetime.datetime, is_focused: bool = False, as_iterator: bool = False) -> None:

        if self._snap_time is None:
            self._snap_time = snapped_time
            return

        delta = snapped_time - self._snap_time
        time = delta.total_seconds()

        self._time += time
        if is_focused:
            self._focused_time += time

        self._snap_time = snapped_time

        if not as_iterator:
            self.show_time()
        
    def show_time(self) -> None:
        opr.print_from(name="ScreenMonitor", message=f"@ {self.time:.2f}s | Focused @ {self._focused_time:.2f}s | {self._name} | {self._exe_name} | {self._process_id}")

    def dump(self) -> dict:
        return {
            "name": self._name,
            "process_id": self._process_id,
            "time": self._time,
            "focused_time": self._focused_time,
            "is_active": self._is_active,
            "start_time": self._start_time.strftime("%Y-%m-%d-%H-%M-%S"),
            "end_time": self._end_time.strftime("%Y-%m-%d-%H-%M-%S") if isinstance(self._end_time, datetime.datetime) else self._end_time,
        }

    def clean_dump(self) -> dict:
        return {
            "name": self._name,
            "exe_name": self._exe_name,
            "process_id": self._process_id,
            "time": self._time,
            "focused_time": self._focused_time,
            "is_active": self._is_active,
            "start_time": self._start_time.strftime("%Y-%m-%d-%H-%M-%S"),
            "end_time": self._end_time.strftime("%Y-%m-%d-%H-%M-%S") if isinstance(self._end_time, datetime.datetime) else self._end_time,
        }

class Mister_Monitor:
    
    def __init__(self, interval: int, list_current_applications: callable, stop_signal: threading.Event, file_dir) -> None: # type: ignore
        self._applications: dict[int, IApplication] = {}
        self._interval: int = interval          
        self._is_running: bool = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._next_log_time = datetime.datetime.now() + datetime.timedelta(minutes=self._interval)
        self._active_application = ""
        self._start_time = datetime.datetime.now()
        self._total_time = 0
        self._list_current_applications = list_current_applications
        self._stop_signal = stop_signal
        self._file_dir = file_dir
        

    def save_log(self, snapped_time: datetime.datetime, manual: bool = True) -> None:
        if not manual:
            self._next_log_time = datetime.datetime.now() + datetime.timedelta(minutes=self._interval)

        export = self.make_log(snapped_time=snapped_time, manual=manual)
        
        opr.save_json(
            is_from="ScreenMonitor",
            path=self._file_dir,
            filename=f"ScreenMonitor{snapped_time.date().isoformat()}.json",
            dump=export
        )


    def make_log(self, snapped_time: datetime.datetime, manual: bool = True) -> dict:
        dump = [app.clean_dump() for app in self._applications.values()]
        duration = (snapped_time - self._start_time).total_seconds()

        if manual:
            opr.print_from(
                name="ScreenMonitor",
                message=f"Interval Report for {snapped_time.strftime('%Y-%m-%d-%H-%M-%S')} "
                        f"================== Time elapsed {duration:.2f}s",
                return_count=2
            )

        for app in dump:
            elapsed_percentage = min((app["time"] / duration) * 100, 100.0) if duration > 0 else 0
            focused_elapsed_percentage = min((app["focused_time"] / duration) * 100, 100.0) if duration > 0 else 0

            app['remark'] = (
                f"{app['name']} is {'ACTIVE' if app['is_active'] else 'INACTIVE'} | "
                f"Time elapsed {app['time']:.2f}s ({elapsed_percentage:.1f}%) | "
                f"Focused Time {app['focused_time']:.2f}s ({focused_elapsed_percentage:.1f}%)"
            )
            if manual:
                opr.print_from(name="ScreenMonitor", message=app['remark'])

        most_active = sorted(dump, key=lambda x: x["focused_time"], reverse=True)
        top5_list = sorted(dump, key=lambda x: x["time"], reverse=True)[:5]
        top5 = [f"{app['time']:.2f}s | Focused: {app['focused_time']:.2f}s | {app['name']}" for app in top5_list]
        most_active_focused_percentage = (
            min((most_active[0]["focused_time"] / duration) * 100, 100.0) if duration > 0 else 0
        )

        report = {
            "Date": snapped_time.strftime("%Y-%m-%d-%H-%M-%S"),
            "Total Time": str(snapped_time - self._start_time),
            "Most Active Application": (
                f"{most_active[0]['time']:.2f}s | Focused: {most_active[0]['focused_time']:.2f}s | "
                f"{most_active_focused_percentage:.1f}% | "
                f"{most_active[0]['name']}"
            ),
            "Top 5 Applications": top5,
        }
        export = {
            "Report": report, 
            str(datetime.date.today().isoformat()): dump
        }
        if manual:
            opr.print_from(name="ScreenMonitor", message=f"{self._file_dir} | ScreenMonitor{snapped_time.date().isoformat()}.json")
        return export
    

    def open_report(self) -> None:
        now = datetime.datetime.now()
        self.save_log(now, manual=True)
        path = os.path.join(self._file_dir, f"ScreenMonitor{now.date().isoformat()}.json")
        if os.path.exists(path):
            os.startfile(path)

    def open_directory(self) -> None:
        path = self._file_dir
        if os.path.exists(path):
            os.startfile(path)

    def _monitor(self, as_iterator: bool) -> Iterator | None:
        self._is_running = True
        exception_count = 0
        self._start_time = datetime.datetime.now()
        print(f"Iterator: {as_iterator} | Start time: {self._start_time}")
        while not self._stop_event.is_set():
            try:
                # opr.wipe(False)
                success, list_of_apps = self._list_current_applications()

                if not success:
                    print("Could not list applications")
                    return

                with self._lock:
                    snapped_time = datetime.datetime.now()
                    for app_info in list_of_apps:
                        info = app_info.dump()
                        if info["is_focused"]:
                            self._active_application = info["name"]
                        exe_name = info["exe_name"]
                        process_id = info["process_id"]

                        # print(process_id, self._applications.keys())

                        if process_id not in self._applications.keys():
                            self._applications[process_id] = IApplication(name=info["name"], exe_name=exe_name, process_id=process_id)                        

                        if not self._applications[process_id].name == info["name"]:
                            self._applications[process_id].name = info["name"]
                            

                        # Update the app
                        if not self._applications[process_id]._snap_time == snapped_time:
                            self._applications[process_id].deliberate(
                                snapped_time=snapped_time,
                                is_focused=info["is_focused"],
                                is_active=True,
                                as_iterator=as_iterator
                            )


                    active_process_ids = {app.dump()["process_id"] for app in list_of_apps}
                    for process_id, app in list(self._applications.items()):
                        if process_id not in active_process_ids:
                            app.deliberate(snapped_time=snapped_time, is_focused=False, is_active=False, as_iterator=as_iterator)

                    if as_iterator:                        
                        yield self.make_log(snapped_time, manual=False)

                    if datetime.datetime.now() > self._next_log_time:                    
                        self.save_log(snapped_time, manual=False)                            

                if not as_iterator:
                    opr.print_from(name="ScreenMonitor", message=f"Applications: {len(self._applications)} | {self.get_elapsed_time()} | Press Ctrl+C to stop ==================", return_count=2, after_return_count= 2)
                
                self._stop_event.wait(0.5)

            except Exception as e:
                opr.error_pretty(e)
                exception_count += 1
                if exception_count > 5:
                    break
        
            finally:
                if as_iterator:
                    yield self.make_log(snapped_time, manual=False)
                self._is_running = False

    def _run_monitor_thread(self, as_iterator: bool | None = False):
        for _ in self._monitor(as_iterator=as_iterator): # type: ignore
            pass

    def start(self, as_iterator: bool | None = False) -> None:
        
        if self._is_running:
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_monitor_thread, args=(as_iterator,), daemon=True)
        self._thread.start()
        opr.print_from(name="ScreenMonitor", message="Started")

    def stop(self) -> None:
        self.make_log(datetime.datetime.now())
        self._stop_event.set()
        self._stop_signal.set()
        if self._thread is not None:
            self._thread.join() 
        opr.print_from(name="ScreenMonitor", message="Stopped")

    def get_active_application(self) -> str:
        return f"Active: {self._active_application or 'None'}"
    
    def get_elapsed_time(self) -> str:
        return f"Elapsed: {str(datetime.datetime.now() - self._start_time).split('.')[0] or 'None'}"
    




    