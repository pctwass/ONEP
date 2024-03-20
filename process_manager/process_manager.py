import multiprocessing
from multiprocessing.managers import BaseManager

from projector.main_projector import Projector
from projector.projector_plot_manager import ProjectorPlotManager
from process_manager.projector_processes import create_process_project, create_process_update_projector


class ProcessManager:
    _manager : BaseManager
    _locks : dict[str, multiprocessing.Lock] = {}
    _flags : dict[str, dict[multiprocessing.Event]] = {}
    _managed_objects : dict[str, any] = {}
    _subprocesses : dict[str, multiprocessing.Process] = {}


    def __init__(self, projector_kwargs : dict, projector_plot_manager_kwargs : dict):
        self._register_proxy_classes()
        self._manager = BaseManager()
        self._manager.start()
        self._create_locks()
        self._create_flags()
        self._create_managed_objects(projector_kwargs, projector_plot_manager_kwargs)
        self._create_subprocesses()

        try:
            s = self._managed_objects["projector"]
            a = s._getvalue("_settings")
            a=a
        except Exception as e:
            s=s 

        try:
            s = self._managed_objects["projector"]
            a = s.get_plot_manager()
            a=a
        except Exception as e:
            s=s 



    def _register_proxy_classes(self):
        BaseManager.register('Lock', multiprocessing.Lock)
        BaseManager.register("Projector", Projector)
        BaseManager.register("ProjectorPlotManager", ProjectorPlotManager)


    def _create_locks(self):
        self._locks["write_projector_historic_df"] = self._manager.Lock() # referenced by key string in Projector


    def _create_flags(self):
        # flags are refenced by key string.
        self._flags["projector_projecting"] = {
            "stop" : self._init_new_event(),
            "pause" : self._init_new_event(),
            "updating_projector" : self._init_new_event()
        }
        self._flags["projector_updating"] = {
            "stop" : self._init_new_event(),
            "pause" : self._init_new_event()
        }


    def _create_managed_objects(self, projector_kwargs : dict, projector_plot_manager_kwargs : dict):
        if projector_plot_manager_kwargs != None and len(projector_plot_manager_kwargs) > 0:
            self._managed_objects["projectorPlotManager"] = self._manager.ProjectorPlotManager(**projector_plot_manager_kwargs)

        if projector_kwargs != None and len(projector_kwargs) > 0:
            projector_kwargs["plot_manager"] = self._managed_objects["projectorPlotManager"]
            projector_kwargs["locks"] = self._locks
            # projector_kwargs["events"] = dict(updating_projector_event = self._flags["projector_projecting"]["projector_projecting"])
            self._managed_objects["projector"] = self._manager.Projector(**projector_kwargs)


    def _create_subprocesses(self):
        if "projector" in self._managed_objects:
            projector = self._managed_objects["projector"]
            self._subprocesses["projector_projecting"] = create_process_project(projector, self._flags["projector_projecting"])
            self._subprocesses["projector_updating"] = create_process_update_projector(projector, self._flags["projector_updating"])


    def _init_new_event(self) -> multiprocessing.Event:
        event = multiprocessing.Event()
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
        self._flags[process_name]["stop"].set()


    def pause_process(self, process_name : str):
        self._flags[process_name]["pause"].set()


    def unpause_process(self, process_name : str):
        self._flags[process_name]["pause"].clear()


    def set_flag(self, process_name : str, flag : str):
        self._flags[process_name][flag].set()


    def clear_flag(self, process_name : str, flag : str):
        self._flags[process_name][flag].clear()


    