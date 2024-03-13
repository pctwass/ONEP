import multiprocessing

SLEEPING_DURATION = 1 * 10**-3 # 1 ms

def create_living_process(target, event_names : list[str], kwargs : dict[str, any] = None) -> tuple[multiprocessing.Process, dict[str, multiprocessing.Event]]:
    events = {}
    for event_name in event_names:
        event = _init_new_event()
        events[event_name] = event

    if kwargs is not None:
        kwargs.update(events)
    else:
        kwargs = events

    process = multiprocessing.Process(
        target=target,
        kwargs=kwargs
    )
    return process, events


def _init_new_event(self) -> multiprocessing.Event:
    event = multiprocessing.Event()
    event.clear()
    return event