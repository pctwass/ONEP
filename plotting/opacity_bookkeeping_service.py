    
import numpy as np
import plotly.graph_objects as go
from typing import Iterable

from plotting.plotly_scatter_service import PlotlyScatterService
from utils.logging import logger


class OpacityBookkeepingService:
    _scatter_plot_service : PlotlyScatterService
    _opacity_thresholds : dict[float, int] = {}
    _init_opacity : float = 1.0
    _points_by_opacity : dict[float, Iterable[str]]= {}


    def __init__(self, scatter_plot_service : PlotlyScatterService, opacity_thresholds : dict[float, int], init_opacity : float, points_by_opacity : dict[float, Iterable[str]]):
        self._scatter_plot_service = scatter_plot_service
        self._opacity_thresholds = opacity_thresholds
        self._init_opacity = init_opacity
        self._points_by_opacity = points_by_opacity


    def update_opacity_dict(self, new_points : Iterable[str], opacity : float | None = None):
        self._expand_opacity_dict(new_points, opacity)
        self._reduce_opacity()
    

    def update_opacity_dict_and_plot(self, figure : go.Figure, new_points : Iterable[str], opacity : float | None = None): 
        self._expand_opacity_dict(new_points, opacity)
        opacity_change_list = self._reduce_opacity()
        self._assign_opacity_updates(figure, opacity_change_list)
    

    def _expand_opacity_dict(self, new_points : Iterable[str], opacity : float | None = None):
        if opacity is None:
            opacity = self._init_opacity
        self._points_by_opacity[opacity].extend(new_points)


    def _reduce_opacity(self) -> list[tuple[float, float]]:
        opacity_change_list = list()
        for i, (opacity, points) in enumerate(self._points_by_opacity.items()):
            # if there is no opacity threshold defined or the selected opacity level is the lowerst/final opacity level, continue
            opacity_threshold = self._opacity_thresholds[opacity]
            if np.isnan(opacity_threshold) or i >= len(self._points_by_opacity)-1:
                continue
            
            # if there are fewer points in the opacity level than are maximally allowed, continue
            num_points_to_reduce_opacity = len(points) - opacity_threshold
            if num_points_to_reduce_opacity < 1:
                continue

            reduced_opacity = list(self._points_by_opacity.keys())[i+1]
            for point_index in range(num_points_to_reduce_opacity):
                point_id = points[point_index]
                opacity_change_list.append((point_id, reduced_opacity))
                self._points_by_opacity[reduced_opacity].append(point_id)

            # remove all points of the old opacity value that were assigned a lower opacity value
            del points[:num_points_to_reduce_opacity]
        return opacity_change_list

    
    def _assign_opacity_updates(self, figure : go.Figure, opacity_change_list : list[tuple[float, float]] = []):
        for point_id, new_opacity in opacity_change_list:
            scatter_trace, point_scatter_index = self._scatter_plot_service.get_trace_and_point_index_by_point_id(figure, point_id)
            if scatter_trace is None or point_scatter_index is None:
                logger.warning(f"could not find point in figure when attempting to reduce opacity. Point:{point_id}")
                # logger.warning(f"could not find point in figure when attempting to reduce opacity. Point:{point_id}")
                continue
            self._scatter_plot_service.update_point_opacity(figure, scatter_trace, point_scatter_index, new_opacity)
