import pandas as pd
import numpy as np
import random

n_samples = 10
samples_dim = 128
last_time_stamp = 0
default_labels = [-1, 0, 1, 2]

def get_mock_data(n_samples : int = n_samples, samples_dim : int = samples_dim, generate_time_points : bool = True) -> tuple[pd.DataFrame, np.ndarray[int], np.ndarray[float]] :
    distribution = random.choice([0, 1, 2])
    
    if distribution == 0:
        norm_dist = np.random.normal(1, 1.5, size=(n_samples, samples_dim))
    elif distribution == 1:
        norm_dist = np.random.normal(2.5, 0.5, size=(n_samples, samples_dim))
    else: 
        norm_dist = np.random.normal(3, 2.8, size=(n_samples, samples_dim))

    data = pd.DataFrame(norm_dist)
    if generate_time_points:
        global last_time_stamp
        end_time_stamp = last_time_stamp + n_samples
        time_points = np.arange(last_time_stamp + 1, end_time_stamp + 1, dtype=float)
        last_time_stamp = end_time_stamp

    labels = [distribution] * n_samples
    return data, labels, time_points


def get_mock_labels(n_samples : int = n_samples, label_set = default_labels):
    return np.array(random.choices(label_set, k=n_samples))