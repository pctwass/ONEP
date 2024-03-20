import multiprocessing

SLEEPING_DURATION = 1 * 10**-3 # 1 ms

def create_living_process(target, kwargs : dict[str, any] = {}) -> multiprocessing.Process:
    process = multiprocessing.Process(
        target=target,
        kwargs=kwargs
    )
    return process