import numpy as np
import pandas as pd
import umap
import umap.plot

from sklearn.neighbors import NearestNeighbors

from utils.logging import logger
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod

class UmapApproxWrapper(IProjectionMethod):
    _method_type = ProjectionMethodEnum.UMAP_Approx
    
    _projector : umap.UMAP
    _n_neighbors : int = 15
    _knn : NearestNeighbors
    _neighbour_distance_modifier = 1e-8  # Ensures the minimal distance between neighbours is never exactly 0. Set to a neglectably small value
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
        
        knn = NearestNeighbors(n_neighbors=n_neighbors)
        knn.fit(data)

        self._projector = new_reducer
        self._knn = knn

    
    def fit_update(self, data : pd.DataFrame, time_points = None):
        # time_points is unused in the umap implementation. Included in function call to adhere to the interface
        del time_points
        
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()

        print('updating model')
        self._projector.update(data)
        self._knn.fit(data)


    def produce_projection(self, new_data: pd.DataFrame, existing_data: pd.DataFrame = None):
        if existing_data is None:
            return self._compute_projection(new_data)
        else:
            return self._approximate_projections(new_data, existing_data)
    

    def _compute_projection(self, data: pd.DataFrame):
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data = data.dropna()
        return self._projector.transform(data)
    

    def _approximate_projections(self, new_data: pd.DataFrame, existing_data: pd.DataFrame):
        n_neighbors = self._n_neighbors
        existing_projections = self._projector.embedding_
        if existing_projections.shape[0] < n_neighbors:
            n_neighbors = existing_projections.shape[0]

        neighbors_indeces_list = self._knn.kneighbors(new_data, return_distance=False)

        approx_projections = []
        for data_index, data_point in enumerate(new_data.values):
            neighbors_indeces = neighbors_indeces_list[data_index]
            neighboring_points_data_space = existing_data.values[neighbors_indeces]
            neighboring_embedding = existing_projections[neighbors_indeces]

            distances_data_space = calc_euclidean_distances(data_point, neighboring_points_data_space)
            summed_inverse_distances_data_space = sum(1/(distance + self._neighbour_distance_modifier) for distance in distances_data_space)

            approx_projection = [0, 0]
            for neighbor in range(n_neighbors):
                neighbor_distance = distances_data_space[neighbor]
                neighbor_projection = neighboring_embedding[neighbor]
                approx_projection_partial = 1 / (neighbor_distance + self._neighbour_distance_modifier) / summed_inverse_distances_data_space * neighbor_projection
                approx_projection += approx_projection_partial
            approx_projections.append(approx_projection)
        return np.asarray(approx_projections)


def calc_euclidean_distances(data_point, neighboring_data_points) -> list[float]:
    euclidean_distances = []
    for neighbor in neighboring_data_points:
        euclidean_distances.append(np.linalg.norm(data_point - neighbor))
    return euclidean_distances


