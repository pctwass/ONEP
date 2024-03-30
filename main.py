import dependency_resolver
import logging
import os
import time
import webbrowser
from configuration_resolver import ConfigurationResolver

from fire import Fire

from dashboard.dashboard import Dashboard
from dashboard.dashboard_thread import DashboardThread
from dashboard.dahsboard_settings import DashboardSettings

from utils.logging import logger
from utils.stream_watcher import StreamWatcher

from projector.projector_continues_shell import ProjectorContinuesShell
from projector.main_projector import Projector
from projector.projector_settings import ProjectorSettings
from projector.projector_plot_manager import ProjectorPlotManager
from projector.plot_settings import PlotSettings

from process_management.process_manager  import ProcessManager


module_paths = dependency_resolver.reference_module_paths

config_file_name: str = "config.toml"
config_folder: str = os.path.join(os.getcwd(), "configs")
config_path: str = os.path.join(config_folder, config_file_name)

stream_watcher : StreamWatcher
projector_shell : ProjectorContinuesShell
configuration_resolver = ConfigurationResolver(config_path)


def init_logger():
    logger.setLevel(20)
    logger.addHandler(logging.StreamHandler())


def init_dashboard(settings : DashboardSettings, projector : Projector | ProjectorContinuesShell) -> Dashboard:
    dashboard_host = configuration_resolver.get('dashboard-host')
    dashboard_port = configuration_resolver.get('dashboard-port')
    
    dashboard_thread = DashboardThread(settings, host=dashboard_host, port=dashboard_port) 
    dashboard = dashboard_thread.dashboard

    dashboard.register_projector(projector)
    dashboard.set_active_projector(projector.id)
    
    dashboard_thread.start()
    webbrowser.open('http://127.0.0.1:8007/')
    return dashboard


def launch() -> int:
    projector_settings, dashboard_settings = get_settings_from_config()
    projection_method = projector_settings.projection_method
    stream_name = configuration_resolver.get('data-stream-name')

    global projector_shell
    logger.info('Initiating embedding projector')
    projector_shell = ProjectorContinuesShell(projection_method, stream_name, projector_settings)
    init_dashboard(dashboard_settings, projector_shell)

    webbrowser.open('http://127.0.0.1:8007/')
    return 0


def start() -> int:
    projector_shell.start_projecting()
    projector_shell.start_updating_projector()
    return 0


def stop() -> int:
    projector_shell.stop_projecting()
    projector_shell.stop_updating_projector()
    return 0


def main() -> int:
    init_logger()

    projector_settings, dashboard_settings = get_settings_from_config()
    mode = 'continuous'

    in_stream_name = configuration_resolver.get('data-stream-name')
    projector_kwargs = get_projector_kwargs(projector_settings, in_stream_name)
    projector_plot_manager_kwargs = get_projector_plot_manager_kwargs(projector_settings.plot_settings)
    dashboard_kwargs = get_dashboard_kwargs(dashboard_settings)

    if mode == 'sequential':
        plot_manager = ProjectorPlotManager(**projector_plot_manager_kwargs)
        projector_kwargs["plot_manager"] = plot_manager
        projector = Projector(**projector_kwargs)
        init_dashboard(dashboard_settings, projector)

        project_new_data(projector, 10)
        projector.update_projector()
        project_new_data(projector, 100)
        projector.update_projector()
        project_new_data(projector, 10)
        project_new_data(projector, 5)
        projector.update_projector()

        time.sleep(6000)


    elif mode == 'continuous':
        process_manager = ProcessManager(projector_kwargs, projector_plot_manager_kwargs, dashboard_kwargs)
        #init_dashboard(dashboard_settings, projector_shell)

        process_manager.start_all_processes()
        webbrowser.open('http://127.0.0.1:8007/')
        # process_manager.start_process("projector_projecting")
        # process_manager.start_process("projector_updating")
        time.sleep(6000)
        process_manager.stop_process("projector_projecting")
        process_manager.stop_process("projector_updating")
    return 0


def get_settings_from_config() -> tuple[ProjectorSettings, DashboardSettings]:
    projector_settings = configuration_resolver.get_projector_settings_from_config()
    dashboard_settings = configuration_resolver.get_dashboard_settings_from_config()
    return projector_settings, dashboard_settings


def project_new_data(projector, repeat : int = 1):
    for i in range(repeat):
        projector.project_new_data()


def get_projector_kwargs(projector_settings : ProjectorSettings, in_stream_name) -> dict[str, any]:
    return dict(
        projection_method = projector_settings.projection_method, 
        stream_name = in_stream_name, 
        projector_settings = projector_settings 
    )


def get_projector_plot_manager_kwargs(plot_settings : PlotSettings) -> dict[str, any]:
    return dict(
        name = "plot manager",
        settings = plot_settings
    )


def get_dashboard_kwargs(dashboard_settings : DashboardSettings) -> dict[str, any]:
    return dict(
        settings = dashboard_settings
    )



if __name__ == "__main__":

    Fire(main)

