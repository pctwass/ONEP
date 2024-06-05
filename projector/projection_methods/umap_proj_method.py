import numpy as np
import pandas as pd
import umap
import umap.plot

from utils.logging import logger
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod

class UmapProjMethod(IProjectionMethod):
    _method_type = ProjectionMethodEnum.UMAP
    
    _projector : umap.UMAP
    _n_neighbors : int = 15
    _hyperparameters : dict[str, any] = {}
    _align_projections : bool = False


    def __init__(self, hyperparameters : dict[str, any], init_data : any = None, align_projections : bool = False):
        self._align_projections = align_projections
        self._hyperparameters = hyperparameters
        n_neighbors = hyperparameters["n_neighbors"]

        self._n_neighbors = n_neighbors
        if init_data is not None:
            self.fit_new(init_data)
        else: 
            self._projector = umap.UMAP(**self._hyperparameters)


    def get_method_type(self) -> ProjectionMethodEnum:
        return self._method_type


    def fit_new(self, **kwargs):
        data = kwargs["data"]
        labels = kwargs["labels"]

        if self._align_projections:
            if "past_projections" not in kwargs or kwargs["past_projections"] is None or len(kwargs["past_projections"]) == 0:
                logger.debug("align_projections is True, but no past projections were given.")
            self._hyperparameters["init"] = kwargs["past_projections"]

        new_reducer = umap.UMAP(**self._hyperparameters)
        new_reducer.fit(data, labels)

        self._projector = new_reducer

    
    def fit_update(self, **kwargs):
        data = kwargs["data"]
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        self._projector.update(data)


    def project(self, **kwargs):
        data = kwargs["data"]
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        return self._projector.transform(data)