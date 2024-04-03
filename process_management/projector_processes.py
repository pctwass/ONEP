import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector


def create_living_process_project(projector : Projector, flags : dict[str, multiprocessing.Event]) -> multiprocessing.Process:
    process_target = _projecting_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def create_living_process_update_projector(projector : Projector, flags : dict[str, multiprocessing.Event]) -> multiprocessing.Process:
    process_target = _update_projector_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def _projecting_loop(
    projector : Projector,
    flags : dict[str, multiprocessing.Event] = {}
    ):

    freq_hz = projector._getvalue()._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not flags["projecting_stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["projecting_pause"].is_set():
                time.sleep(SLEEPING_DURATION)
            try:
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

    while not flags["updating_stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["updating_pause"].is_set():
                time.sleep(SLEEPING_DURATION)
            try:
                projector.update_projector()
            except Exception as e:
                raise e
            tlast = now