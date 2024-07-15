import multiprocessing
import time

from processing_utils import *
from utils.logging import logger
from projector.main_projector import Projector
from utils.streaming.stream_watcher import StreamWatcher
from utils.data_mocker import get_mock_data_norm_dist, get_mock_data_arrays


def create_living_process_project(projector : Projector, stream_watcher : StreamWatcher, flags : dict[str, multiprocessing.Event], locks : dict[str, multiprocessing.Lock], use_mock_data : bool = False) -> multiprocessing.Process:
    if use_mock_data:
        reader_function = get_mock_data_norm_dist
        connect_to_stream = False
    else:
        reader_function = stream_watcher.read
        connect_to_stream = True

    process_target = _projecting_loop
    kwargs = dict(projector=projector, stream_watcher=stream_watcher, reader_function=reader_function, flags=flags, locks=locks, connect_to_stream=connect_to_stream)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def create_living_process_update_projector(projector : Projector, flags : dict[str, multiprocessing.Event], locks : dict[str, multiprocessing.Lock]) -> multiprocessing.Process:
    process_target = _update_projector_loop
    kwargs = dict(projector=projector, flags=flags, locks=locks)
    subprocess = create_subprocess(process_target, kwargs=kwargs)

    return subprocess


def _projecting_loop(
    projector : Projector,
    stream_watcher : StreamWatcher,
    reader_function,
    flags : dict[str, multiprocessing.Event] = {},
    locks : dict[str, multiprocessing.Lock] = {},
    connect_to_stream = True
    ):

    freq_hz = projector._getvalue()._settings.sampling_frequency
    dt = 1 / freq_hz
    tlast = time.time_ns()

    if connect_to_stream:
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
                print(f"projecting exception: {e}")
                logger.error(e)
                _release_locks(locks)
            tlast = now


def _update_projector_loop(
    projector : Projector,
    flags : dict[multiprocessing.Event] = {},
    locks : dict[str, multiprocessing.Lock] = {}
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
                print(f"projector updating exception: {e}")
                logger.error(e)
                _release_locks(locks)
            tlast = now


def _release_locks(locks : dict[str, multiprocessing.Lock]):
    for lock in locks.values():
        if lock.acquire(block=False):
            lock.release()