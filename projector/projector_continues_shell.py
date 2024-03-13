import threading
import time
import matplotlib.pyplot as pyplot

from utils.logging import logger
from projector.main_projector import Projector
from projector_settings import ProjectorSettings
from projection_methods.projection_methods_enum import ProjectionMethodEnum

SLEEPING_DURATION = 1 * 10**-3 # 1 ms

class ProjectorContinuesShell:
    _embedding_projector : Projector
    _events : dict[str, threading.Event] = {}
    
    _projecting_thread : threading.Thread
    _projecting_stop_event : threading.Event
    _projector_update_thread : threading.Thread
    _projector_update_stop_event : threading.Event

    id : str

    def __init__(self, projection_method : ProjectionMethodEnum, stream_name: str = "mock_EEG_stream", projector_settings : ProjectorSettings = ProjectorSettings()):
        self._embedding_projector = Projector(projection_method, stream_name, projector_settings, self._events)
        self.id = self._embedding_projector.id


    def get_projector(self):
        return self._embedding_projector
        
   
    def start_projecting(self) -> tuple[threading.Thread, threading.Event]:
        process_target = self._projecting_loop
        event_names = [ "stop_projecting_event", "pause_projecting_event", "updating_projector_event" ]
        thread, events = self._create_living_process(process_target, (), event_names)

        stop_event = events[event_names[0]]

        self._projecting_thread = thread
        self._projecting_stop_event = stop_event
        return thread, stop_event

    def stop_projecting(self):
        self._projecting_stop_event.set()

    def pause_projecting(self):
        if "pause_projecting_event" in self._events:
            self._events["pause_projecting_event"].set()
        else:
            logger.error("could not pause projectoring, pause_projecting_event flag does not exist")

    def unpause_projecting(self):
        if "pause_projecting_event" in self._events:
            self._events["pause_projecting_event"].clear()
        else:
            logger.error("could not unpause projectoring, pause_projecting_event flag does not exist")


    def start_updating_projector(self) -> tuple[threading.Thread, threading.Event]:
        process_target = self._update_projector_loop
        event_names = [ "stop_updating_event", "pause_updating_event" ]
        thread, events = self._create_living_process(process_target, (), event_names)

        stop_event = events[event_names[0]]

        self._projector_update_thread = thread
        self._projector_update_stop_event = stop_event
        return thread, stop_event

    def stop_updating_projector(self):
        self._projector_update_stop_event.set()

    def pause_updating_projector(self):
        if "pause_updating_event" in self._events:
            self._events["pause_updating_event"].set()
        else:
            logger.error("could not pause updating projector, pause_updating_event flag does not exist")

    def unpause_updating_projector(self):
        if "pause_updating_event" in self._events:
            self._events["pause_updating_event"].clear()
        else:
            logger.error("could not unpause updating projector, pause_updating_event flag does not exist")


    def _projecting_loop(
        self,
        stop_projecting_event: threading.Event = threading.Event(),
        pause_projecting_event: threading.Event = threading.Event(),
        updating_projector_event: threading.Event = threading.Event()
        ):

        freq_hz = self._embedding_projector._settings.sampling_frequency
        dt = 1 / freq_hz
        tlast = time.time_ns()

        while not stop_projecting_event.is_set():
            now = time.time_ns()
            if now - tlast > dt * 10**9:
                while pause_projecting_event.is_set() or updating_projector_event.is_set():
                    time.sleep(SLEEPING_DURATION)
                self._embedding_projector.project_new_data()
                tlast = now


    def _update_projector_loop(
        self,
        stop_updating_event: threading.Event = threading.Event(),
        pause_updating_event: threading.Event = threading.Event()
        ):

        freq_hz = self._embedding_projector._settings.model_update_frequency
        dt = 1 / freq_hz
        tlast = time.time_ns()

        while not stop_updating_event.is_set():
            now = time.time_ns()
            if now - tlast > dt * 10**9:
                while pause_updating_event.is_set():
                    time.sleep(SLEEPING_DURATION)
                self._embedding_projector.update_projector()
                tlast = now


    def _create_living_process(self, target, args, event_names : list[str], kwargs : dict[str, any] = None) -> tuple[threading.Thread, dict[str, threading.Event]]:
        events = {}
        for event_name in event_names:
            event = self._init_new_event()
            events[event_name] = event

        if kwargs is not None:
            kwargs.update(events)
        else:
            kwargs = events

        thread = threading.Thread(
            target=target,
            args=args,
            kwargs=kwargs
        )
        self._events |= events

        thread.start()
        logger.debug(f"Created {thread}")
        return thread, events


    def _init_new_event(self) -> threading.Event:
        event = threading.Event()
        event.clear()
        return event