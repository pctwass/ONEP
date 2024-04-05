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


    def __init__(self, hyperparameters : dict[str, any], init_data : any = None):
        self._hyperparameters = hyperparameters
        n_neighbors = hyperparameters["n_neighbors"]

        self._n_neighbors = n_neighbors
        if init_data is not None:
            self.fit_new(init_data)
        else: 
            self._projector = umap.UMAP(**self._hyperparameters)


    def get_method_type(self) -> ProjectionMethodEnum:
        return self._method_type


    def fit_new(self, data: pd.DataFrame, labels = None, time_points = None):
        # time_points is unused in the umap implementation. Included in function call to adhere to the interface
        del time_points

        n_neighbors = self._n_neighbors
        if data is not None and data.shape[0] <= n_neighbors:
            n_neighbors = data.shape[0]

        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()

        new_reducer = umap.UMAP(**self._hyperparameters)
        new_reducer.fit(data, labels)

        self._projector = new_reducer

    
    def fit_update(self, data : pd.DataFrame, time_points = None):
        # time_points is unused in the umap implementation. Included in function call to adhere to the interface
        del time_points
        
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()

        print('updating model')
        self._projector.update(data)


    def project(self, data: pd.DataFrame):
        print('producing embedding')
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        return self._projector.transform(data)