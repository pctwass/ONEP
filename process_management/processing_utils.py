import multiprocessing

SLEEPING_DURATION = 1 * 10**-3 # 1 ms
LOCK_NAME_PROJECTOR_HISTORIC_DATA = "projector_historic_data"
LOCK_NAME_PLOT_MANAGER = "plot_manager"

def create_subprocess(target, kwargs : dict[str, any] = {}) -> multiprocessing.Process:
    process = multiprocessing.Process(
        target=target,
        kwargs=kwargs
    )
    return process