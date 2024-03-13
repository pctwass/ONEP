import multiprocessing
from multiprocessing.managers import BaseManager

from projector.main_projector import Projector
from projector.projector_plot_manager import ProjectorPlotManager
from process_manager.projector_processes import create_process_project, create_process_update_projector


class ProcessManager:
    _manager : BaseManager
    _managed_resources : dict[str, any] = {}
    _subprocesses : dict[str, multiprocessing.Process] = {}


    def __init__(self, projector_kwargs : dict, projector_plot_manager_kwargs : dict):
        self._register_proxy_classes()
        self._manager = BaseManager()
        self._manager.start()
        self._init_manager_resources(projector_kwargs, projector_plot_manager_kwargs)
        self._create_subprocesses()


    def _register_proxy_classes(self):
        BaseManager.register("Projector", Projector)
        BaseManager.register("ProjectorPlotManager", ProjectorPlotManager)


    def _init_manager_resources(self, projector_kwargs : dict, projector_plot_manager_kwargs : dict):
        if projector_kwargs != None and len(projector_kwargs) > 0:
            projector_proxy = self._manager.Projector(projector_kwargs)
            self._managed_resources["projector"] = projector_proxy.getvalue()

        if projector_plot_manager_kwargs != None and len(projector_plot_manager_kwargs) > 0:
            projector_plot_manager_proxy = self._manager.ProjectorPlotManager(projector_plot_manager_kwargs)
            self._managed_resources["projectorPlotManager"] = projector_plot_manager_proxy.getvalue()


    def _create_subprocesses(self):
        if "projector" in self._managed_resources:
            projector = self._managed_resources["projector"]
            self._subprocesses["projector_projecting"], _ = create_process_project(projector)
            self._subprocesses["projector_updating"], _ = create_process_update_projector(projector)