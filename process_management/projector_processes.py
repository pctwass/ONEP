import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector


def create_living_process_project(projector : Projector, flags : dict[str, bool]) -> multiprocessing.Process:
    process_target = _projecting_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def create_living_process_update_projector(projector : Projector, flags : dict[str, bool]) -> multiprocessing.Process:
    process_target = _update_projector_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def _projecting_loop(
    projector : Projector,
    flags : dict[str, bool] = {}
    ):

    freq_hz = projector._getvalue()._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not flags.get("projecting_stop"):
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags.get("projecting_pause"):
                s = flags.items()
                time.sleep(SLEEPING_DURATION)
            try:
                s = flags.items()
                projector.project_new_data()
            except Exception as e:
                raise e
            tlast = now


def _update_projector_loop(
    projector : Projector,
    flags : dict[multiprocessing.Event] = {}
    ):

    freq_hz = projector._getvalue()._settings.model_update_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not flags.get("updating_stop"):
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags.get("updating_pause"):
                time.sleep(SLEEPING_DURATION)
            projector.update_projector()
            tlast = now