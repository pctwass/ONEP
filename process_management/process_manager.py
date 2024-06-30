import multiprocessing
from multiprocessing.managers import BaseManager

from projector.main_projector import Projector
from projector.projector_plot_manager import ProjectorPlotManager
from dashboard.dahsboard_settings import DashboardSettings
from projector.projector_settings import ProjectorSettings
from projector_processes import create_living_process_project, create_living_process_update_projector
from dashboard_processes import create_process_dashboard
from processing_utils import *
from utils.streaming.stream_watcher import StreamWatcher


class ProcessManager:
    _manager : BaseManager
    _locks : dict[str, multiprocessing.Lock] = {}
    _flags : dict[str, dict[str, multiprocessing.Event]] = {}
    _managed_objects : dict[str, any] = {}
    _subprocesses : dict[str, multiprocessing.Process] = {}


    def __init__(self, stream_watcher_kwarg : dict, projector_kwargs : dict, projector_plot_manager_kwargs : dict, dashboard_kwargs : dict):
        self._register_proxy_classes()
        self._manager = BaseManager()
        self._manager.start()
        self._create_locks()
        self._create_flags()
        self._create_managed_objects(stream_watcher_kwarg, projector_kwargs, projector_plot_manager_kwargs)
        self._create_subprocesses(projector_kwargs["settings"], dashboard_kwargs["settings"])


    def _register_proxy_classes(self):
        BaseManager.register('dict', dict)
        BaseManager.register('Event', multiprocessing.Event)
        BaseManager.register('Lock', multiprocessing.Lock)
        BaseManager.register("Projector", Projector)
        BaseManager.register("ProjectorPlotManager", ProjectorPlotManager)
        BaseManager.register("StreamWatcher", StreamWatcher)


    def _create_locks(self):
        self._locks[LOCK_NAME_MUTATE_PROJECTOR_DATA] = self._manager.Lock()
        self._locks[LOCK_NAME_PLOT_MANAGER] = self._manager.Lock()


    def _create_flags(self):
        self._flags = dict(
            projector_projecting = dict(
                stop = self._init_new_event(),
                pause = self._init_new_event(),
            ),
            projector_updating = dict(
                stop = self._init_new_event(),
                pause = self._init_new_event(),
            )
        )

    def _create_managed_objects(self, stream_watcher_kwarg : dict, projector_kwargs : dict, projector_plot_manager_kwargs : dict):
        if stream_watcher_kwarg != None and len(stream_watcher_kwarg) > 0:
            stream_watcher = self._manager.StreamWatcher(**stream_watcher_kwarg)
            self._managed_objects["streamWatcher"] = stream_watcher

        if projector_plot_manager_kwargs != None and len(projector_plot_manager_kwargs) > 0:
            plot_manager = self._manager.ProjectorPlotManager(**projector_plot_manager_kwargs)
            self._managed_objects["projectorPlotManager"] = plot_manager

        if projector_kwargs != None and len(projector_kwargs) > 0 and stream_watcher is not None and plot_manager is not None:
            projector_kwargs["plot_manager"] = plot_manager
            projector_kwargs["locks"] = self._locks
            projector = self._manager.Projector(**projector_kwargs)
            self._managed_objects["projector"] = projector


    def _create_subprocesses(self, projector_settings : ProjectorSettings, dashboard_settings : DashboardSettings):
        if "projector" in self._managed_objects:
            projector = self._managed_objects["projector"]
            stream_watcher = self._managed_objects["streamWatcher"]
            use_mock_data = projector_settings.use_mock_data
            self._subprocesses["projector_projecting"] = create_living_process_project(projector, stream_watcher, self._flags["projector_projecting"], self._locks, use_mock_data)
            self._subprocesses["projector_updating"] = create_living_process_update_projector(projector, self._flags["projector_updating"], self._locks)

        if "projector" in self._managed_objects and dashboard_settings is not None:
            plot_manager = self._managed_objects["projectorPlotManager"]
            projector = self._managed_objects["projector"]
            self._subprocesses["dashboard"] = create_process_dashboard(dashboard_settings, projector, plot_manager, self._flags)


    def _init_new_event(self) -> multiprocessing.Event:
        event = self._manager.Event()
        event.clear()
        return event
    

    def start_all_processes(self):
        for process in self._subprocesses.values():
            process.start()
    

    def start_process(self, process_name : str):
        self._subprocesses[process_name].start()


    def terminate_process(self, process_name : str):
        self._subprocesses[process_name].terminate()


    def stop_process(self, process_name : str):
        self._flags.get(process_name)["stop"].set()


    def pause_process(self, process_name : str):
        self._flags.get(process_name)["pause"].set()


    def unpause_process(self, process_name : str):
        self._flags.get(process_name)["pause"].clear()


    def set_flag(self, process_name : str, flag : str):
        self._flags.get(process_name)[flag].set()


    def clear_flag(self, process_name : str, flag : str):
        self._flags.get(process_name)[flag].clear()


    