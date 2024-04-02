import multiprocessing

from processing_utils import *
from dashboard.dashboard import Dashboard
from dashboard.dahsboard_settings import DashboardSettings
from projector.main_projector import Projector
from projector.projector_plot_manager import ProjectorPlotManager


dashbaord_expacted_flags = [ ]


def create_process_dashboard(dashboard_settings : DashboardSettings, projector : Projector, plot_manger : ProjectorPlotManager, flags : dict[str, multiprocessing.Event] = {}) -> multiprocessing.Process:
    if not all(flag in flags.keys() for flag in dashbaord_expacted_flags):
        raise Exception(f"Expected the following flags: {dashbaord_expacted_flags}, got {flags.keys()}")
    
    process_target = _create_and_run_dashboard
    kwargs = dict(
        dashboard_settings=dashboard_settings, 
        projector=projector,
        plot_manger=plot_manger,
        flags=flags
    )
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def _create_and_run_dashboard(dashboard_settings : DashboardSettings, projector : Projector, plot_manger : ProjectorPlotManager, flags : dict[str, multiprocessing.Event] = {}):
    dashboard = Dashboard(dashboard_settings, projector, plot_manger, flags)
    dashboard.app.run(dashboard_settings.host, dashboard_settings.port)
