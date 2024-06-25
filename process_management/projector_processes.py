import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector
from utils.streaming.stream_watcher import StreamWatcher
from utils.data_mocker import get_mock_data


def create_living_process_project(projector : Projector, stream_watcher : StreamWatcher, flags : dict[str, multiprocessing.Event], use_mock_data : bool = False) -> multiprocessing.Process:
    if use_mock_data:
        reader_function = get_mock_data
    else:
        reader_function = stream_watcher.read

    process_target = _projecting_loop
    kwargs = dict(projector=projector, stream_watcher=stream_watcher, reader_function=reader_function, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def create_living_process_update_projector(projector : Projector, flags : dict[str, multiprocessing.Event]) -> multiprocessing.Process:
    process_target = _update_projector_loop
    kwargs = dict(projector=projector, flags=flags)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def _projecting_loop(
    projector : Projector,
    stream_watcher : StreamWatcher,
    reader_function,
    flags : dict[str, multiprocessing.Event] = {}
    ):

    freq_hz = projector._getvalue()._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    stream_watcher.connect_to_streams()

    while not flags["stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["pause"].is_set():
                time.sleep(SLEEPING_DURATION)
            try:
                data, time_points, labels = reader_function()
                projector.project_new_data(data, time_points, labels)
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

    while not flags["stop"].is_set():
        now = time.time_ns()
        if now - tlast > dt * 10**9:
            while flags["pause"].is_set():
                time.sleep(SLEEPING_DURATION)
            try:
                projector.update_projector()
            except Exception as e:
                raise e
            tlast = now