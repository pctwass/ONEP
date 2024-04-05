import numpy as np
import pandas as pd
import time

from utils.logging import logger
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod
from projection_methods.submodules.CEBRA.cebra import CEBRA

class CebraProjMethod(IProjectionMethod):
    _projector : CEBRA
    _method_type = ProjectionMethodEnum.CEBRA
    _hyperparameters : dict[str, any] = {}

    def __init__(self, hyperparameters : dict[str, any], init_data : pd.DataFrame = None, init_labels = None, init_time_points = None):
        self._hyperparameters = hyperparameters
        self._hyperparameters["optimizer_kwargs"] = tuple(hyperparameters["optimizer_kwargs"].items())

        if init_data is not None:
            self.fit_new(init_data, init_labels, init_time_points)
        else: 
            self._projector = CEBRA(distance=hyperparameters["distance"])
   

    def get_method_type(self) -> ProjectionMethodEnum:
        return self._method_type


    def fit_new(self, **kwargs):
        data = kwargs["data"]
        labels = kwargs["labels"]
        time_points = kwargs["time_points"]
        
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()

        new_projector = CEBRA(distance=self._hyperparameters["distance"])
        if labels is not None:
            new_projector.fit(data, np.array(labels))
        else:
            new_projector.fit(data, np.array(time_points))
        self._projector = new_projector


    def project(self, **kwargs):
        data = kwargs["data"]

        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        return self._projector.transform(data)
    


