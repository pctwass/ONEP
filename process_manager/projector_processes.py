import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector


projector_projecting_expacted_flags = [ "stop", "pause", "updating_projector" ]
projector_updating_expacted_flags = [ "stop", "pause" ]


def create_process_project(projector : Projector, flags : dict[str, multiprocessing.Event]) -> multiprocessing.Process:
    if not all(flag in flags.keys() for flag in projector_projecting_expacted_flags):
        raise Exception(f"Expected the following flags: {projector_projecting_expacted_flags}, got {flags.keys()}")
    
    process_target = _projecting_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_living_process(process_target, kwargs=kwargs)

    return subprocess


def create_process_update_projector(projector : Projector, flags : dict[str, multiprocessing.Event]) -> multiprocessing.Process:
    if not all(flag in flags.keys() for flag in projector_updating_expacted_flags):
        raise Exception(f"Expected the following flags: {projector_updating_expacted_flags}, got {flags.keys()}")

    process_target = _update_projector_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_living_process(process_target, kwargs=kwargs)

    return subprocess


def _projecting_loop(
    projector : Projector,
    flags : dict[multiprocessing.Event] = {}
    ):

    freq_hz = projector._getvalue()._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not flags["stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["pause"].is_set() or flags["updating_projector"].is_set():
                time.sleep(SLEEPING_DURATION)
            projector.project_new_data()
            tlast = now


def _update_projector_loop(
    projector : Projector,
    flags : dict[multiprocessing.Event] = {}
    ):

    freq_hz = projector._getvalue()._settings.model_update_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not flags["stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["pause"].is_set():
                time.sleep(SLEEPING_DURATION)
            projector.update_projector()
            tlast = now