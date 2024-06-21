import numpy as np
from approx_umap import ApproxUMAP

from utils.logging import logger
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod


class ApproxUmapProjMethod(IProjectionMethod):
    _method_type = ProjectionMethodEnum.UMAP_Approx
    
    _projector : ApproxUMAP
    _n_neighbors : int = 15
    _neighbour_distance_modifier = 1e-8  # Ensures the minimal distance between neighbours is never exactly 0. Set to a neglectably small value
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
            self._projector = ApproxUMAP(**self._hyperparameters)



    def get_method_type(self) -> ProjectionMethodEnum:
        return self._method_type


    def fit_new(self, **kwargs):
        data = kwargs["data"]
        labels = kwargs["labels"]

        if self._align_projections:
            if "past_projections" in kwargs and kwargs["past_projections"] is not None and len(kwargs["past_projections"]) > 0:
                self._hyperparameters["init"] = kwargs["past_projections"]
            else:
                logger.debug(" align_projections is True, but no past projections were given.")

        past_projection_count = len(kwargs["past_projections"])
        logger.debug(f"update data count: {len(data)}, past projections count: {past_projection_count}")
        new_reducer = ApproxUMAP(**self._hyperparameters)
        new_reducer.fit(X=data, y=labels)
        self._projector = new_reducer


    def fit_update(self, **kwargs):
        data = kwargs["data"]

        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        self._projector.update(data)


    def project(self, **kwargs) -> enumerate[any]:
        data = kwargs["data"]

        return self._projector.transform(data)