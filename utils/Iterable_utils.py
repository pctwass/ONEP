import pandas as pd
from pyparsing import Iterable


def scale_range(range : Iterable[float], scale_factor : float) -> Iterable[float]:
    range_mean = (range[0] + range[-1]) / 2
    return scale_and_center_range(range, scale_factor, range_mean)


def scale_and_center_range(range_obj : Iterable[float], scale_factor : float, new_mean : float) -> Iterable[float]:
    range_mean = (range_obj[0] + range_obj[-1]) / 2
    scaled_range = list((a - range_mean) * scale_factor + new_mean for a in range_obj)
    return scaled_range


def scale_and_center_pd_series(range_obj : pd.Series, scale_factor : float, new_mean : float, range_mean : float = None) -> pd.Series:
    if range_mean is None:
        range_mean = (range_obj.min() + range_obj.max()) / 2
    scaled_range = (range_obj - range_mean) * scale_factor + new_mean
    return scaled_range