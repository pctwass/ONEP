import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector


def create_process_project(projector : Projector) -> tuple[multiprocessing.Process, dict[str, multiprocessing.Event]]:
    process_target = _projecting_loop
    event_names = [ "stop_projecting_event", "pause_projecting_event", "updating_projector_event" ]
    kwargs = dict(projector=projector)
    subprocess, events = create_living_process(process_target, kwargs=kwargs, event_names=event_names)

    return subprocess, events


def create_process_update_projector(projector : Projector) -> tuple[multiprocessing.Process, dict[str, multiprocessing.Event]]:
    process_target = _update_projector_loop
    event_names = [ "stop_updating_event", "pause_updating_event" ]
    kwargs = dict(projector=projector)
    subprocess, events = create_living_process(process_target, kwargs=kwargs, event_names=event_names)

    return subprocess, events


def _projecting_loop(
    projector : Projector,
    stop_projecting_event: multiprocessing.Event = multiprocessing.Event(),
    pause_projecting_event: multiprocessing.Event = multiprocessing.Event(),
    updating_projector_event: multiprocessing.Event = multiprocessing.Event()
    ):

    freq_hz = projector._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not stop_projecting_event.is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while pause_projecting_event.is_set() or updating_projector_event.is_set():
                time.sleep(SLEEPING_DURATION)
            projector.project_new_data()
            tlast = now


def _update_projector_loop(
    projector : Projector,
    stop_updating_event: multiprocessing.Event = multiprocessing.Event(),
    pause_updating_event: multiprocessing.Event = multiprocessing.Event()
    ):

    freq_hz = projector._settings.model_update_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    while not stop_updating_event.is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while pause_updating_event.is_set():
                time.sleep(SLEEPING_DURATION)
            projector.update_projector()
            tlast = now