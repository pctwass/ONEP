import dependency_resolver
import logging
import os
import time
import webbrowser

from configuration_resolver import ConfigurationResolver
from fire import Fire

from utils.logging import logger
from utils.streaming.stream_settings import StreamSettings
from dashboard.dahsboard_settings import DashboardSettings
from projector.projector_settings import ProjectorSettings
from projector.plot_settings import PlotSettings

from process_management.process_manager  import ProcessManager


module_paths = dependency_resolver.reference_module_paths

config_file_name: str = "config.toml"
config_folder: str = os.path.join(os.getcwd(), "configs")
config_path: str = os.path.join(config_folder, config_file_name)

process_manager : ProcessManager
configuration_resolver = ConfigurationResolver(config_path)


def init_logger():
    #logger.setLevel(10)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def launch() -> int:
    stream_settings, projector_settings, dashboard_settings = configuration_resolver.resolve_config()
    in_stream_name = configuration_resolver.get('data-stream-name')
    stream_buffer_size_s = configuration_resolver.get('stream-buffer-size-s')

    stream_watcher_kwargs = get_stream_watcher_kwargs(stream_settings)
    projector_kwargs = get_projector_kwargs(projector_settings)
    projector_plot_manager_kwargs = get_projector_plot_manager_kwargs(projector_settings.plot_settings)
    dashboard_kwargs = get_dashboard_kwargs(dashboard_settings)

    global process_manager
    process_manager = ProcessManager(stream_watcher_kwargs, projector_kwargs, projector_plot_manager_kwargs, dashboard_kwargs)

    process_manager.start_process("dashboard")

    dashboard_settings = dashboard_kwargs["settings"]
    host = dashboard_settings.host
    port = dashboard_settings.port
    webbrowser.open(f"http://{host}:{port}/")
    return 0


def start() -> int:
    process_manager.start_process("projector_projecting")
    process_manager.start_process("projector_updating")
    return 0


def stop() -> int:
    process_manager.stop_process("projector_projecting")
    process_manager.stop_process("projector_updating")
    return 0


def main() -> int:
    init_logger()
    mode = 'continuous'

    if mode == 'sequential':
        launch()
        projector = process_manager._managed_objects["projector"]

        project_new_data(projector, 20)
        projector.update_projector()
        project_new_data(projector, 100)
        projector.update_projector()
        project_new_data(projector, 10)
        project_new_data(projector, 5)
        projector.update_projector()

        time.sleep(6000)


    elif mode == 'continuous':
        launch()
        
        time.sleep(20)
        
        print("starting projector")
        start()
        
        time.sleep(6000)
        
        print("stopping projector")
        stop()
    return 0


def project_new_data(projector, repeat : int = 1):
    for i in range(repeat):
        projector.project_new_data()


def get_stream_watcher_kwargs(stream_settings : StreamSettings) -> dict[str, any]:
    return dict(
        settings = stream_settings
    )

def get_projector_kwargs(projector_settings : ProjectorSettings) -> dict[str, any]:
    return dict(
        projection_method = projector_settings.projection_method, 
        settings = projector_settings 
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

