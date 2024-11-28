import random
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import matplotlib.colors as mcolors

from pyparsing import Iterable

from utils.logging import logger
from utils.dataframe_utils import *
from utils.Iterable_utils import *
from projector.plot_settings import PlotSettings
from plotting.plotly_scatter_service import PlotlyScatterService
from plotting.plotly_selection_service import PlotlySelectionService
from plotting.plotly_highlight_service import PlotlyHighlightService
from plotting.scatter_plot_settings import ScatterPlotSettings
from plotting.opacity_bookkeeping_service  import OpacityBookkeepingService


class ProjectorPlotManager():
    name : str
    _plot_figure : go.Figure
    _settings : PlotSettings
    _scatter_plot_service : PlotlyScatterService
    _selection_plot_service : PlotlySelectionService
    _highlight_plot_service : PlotlyHighlightService
    _opacity_bookkeeping_service : OpacityBookkeepingService

    _labels_dict : dict[int, str] = {}
    _color_map : dict[str, str] = {}
    _opacity_thresholds : dict[float, int] = {}
    _init_opacity : float = 1.0

    _points_by_opacity : dict[float, Iterable[str]]= {}

    _points : dict[str, str] = {} # keyval: point_id, label
    _selected_points : dict[str, tuple[float, float]] = {} # keyval: point_id, (x_cord, y_cord)
    _highlighted_points_ids : list[str] = []


    # greatest and smallest axis values used for determing axis range
    _xaxis_edge_values : Iterable[float] = None
    _yaxis_edge_values : Iterable[float] = None


    def __init__(self, name : str, settings : PlotSettings):
        self.name = name
        self._settings = settings
        self._resolve_label_settings()
        self._resolve_opacity_settings()

        self._scatter_plot_service = PlotlyScatterService()
        self._selection_plot_service = PlotlySelectionService()
        self._highlight_plot_service = PlotlyHighlightService()
        self._opacity_bookkeeping_service = OpacityBookkeepingService(
            self._scatter_plot_service,
            self._opacity_thresholds,
            self._init_opacity,
            self._points_by_opacity,
        )

        scatter_plot_settings = self._resolve_scatter_plot_settings()
        self._plot_figure = self._scatter_plot_service.create_figure(scatter_plot_settings)

    def set_name(self, name : str):
        self.name = name

    def _resolve_label_settings(self):
        self._labels_dict[-1] = self._settings.unclassified_label
        for i, label in enumerate(self._settings.labels):
            self._labels_dict[i] = label

        self._color_map[self._settings.unclassified_label] = self._settings.unclassified_label_color
        self._color_map.update(self._settings.label_colors)
        for label in self.get_labels(): 
            if label not in self._color_map:
                self._color_map[label] = self._get_random_plotly_color()

    def _resolve_opacity_settings(self):
        self._opacity_thresholds = {float(opacity): threshold for opacity, threshold in self._settings.opacity_thresholds.items()}
        self._opacity_thresholds[self._settings.min_opacity] = np.NaN
        for opacity in self._opacity_thresholds.keys():
            if not isinstance(opacity, float):
                opacity = float(opacity)
            self._points_by_opacity[opacity] = []
        self._init_opacity = list(self._opacity_thresholds.keys())[0]

    def _resolve_scatter_plot_settings(self) -> ScatterPlotSettings:
        opacity_values = list(self._settings.opacity_thresholds.keys())
        if self._settings.min_opacity not in opacity_values:
            opacity_values.append(self._settings.min_opacity)

        return ScatterPlotSettings(
            self.get_labels(),
            self._color_map,
            self._init_opacity,
            opacity_values,

            self._settings.point_selection_border_size,
            self._settings.point_selection_border_color,
            self._settings.point_highlight_size,
            self._settings.point_highlight_border_size,
            self._settings.point_highlight_border_color,

            self._settings.show_axis,
            self._settings.xaxis_range,
            self._settings.yaxis_range,
            self._settings.xaxis_step_size,
            self._settings.yaxis_step_size,

            self._settings.transition_duration,
        )
    
    '''
    Get methods
    '''
    def get_plot(self) -> go.Figure:
        return self._plot_figure


    def get_labels(self) -> list[str]:
        labels = [self._settings.unclassified_label]
        labels.extend(self._settings.labels)
        return labels
    

    def get_label_mapping(self) -> dict[int, str]:
        return self._labels_dict


    def get_trace_id_by_point_id(self, point_id : float) -> str:
        trace = self._scatter_plot_service.get_trace_by_point_id(self._plot_figure, point_id)
        return trace.uid


    def get_label_by_point_id(self, point_id : str) -> str:
        if point_id in self._points:
            return self._points[point_id]
        logger.warn(f"{point_id} could not be found in the tracked list of points, searching for id in figure. Bad Bookkeeping.")
        return self._scatter_plot_service.get_label_by_point_id(self._plot_figure, point_id)
    
    def get_selected_point_ids(self):
        return self._selected_points.keys()

    def get_count_selected_points(self) -> int:
        return len(self._selected_points)
    
    '''
    Point selection
    '''
    def is_selected_point(self, point_id : str) -> bool:
        return point_id in self._selected_points


    def select_point(self, point_id : str, x : float = None, y :float = None):
        point_id = self._ensure_id_is_point_id(point_id)

        # return when the point is already selected            
        if point_id in self._selected_points:
            return
        
        if x is None or y is None:
            trace, point_index = self._scatter_plot_service.get_trace_and_point_index_by_point_id(point_id)
            x = trace.x[point_index]
            y = trace.y[point_index]
        self._selection_plot_service.select_point(self._plot_figure, x, y, point_id)
        self._selected_points[point_id] = (x, y)


    def deselect_point(self, point_id : str):
        point_id = self._ensure_id_is_point_id(point_id)
        self._selection_plot_service.deselect_point(self._plot_figure, point_id)
        self._selected_points.pop(point_id, None)


    def deselect_all(self):
        self._selection_plot_service.deselect_all(self._plot_figure)
        self._selected_points.clear()


    '''
    Point highlighting
    '''
    def highlight_selected(self):
        for point_id, point_cords in self._selected_points.items():
            self.highlight_point(point_id, point_cords[0], point_cords[1])


    def highlight_point(self, point_id : str, x : float = None, y :float = None):
        point_id = self._ensure_id_is_point_id(point_id)

        # return if the point is already highlighted
        if point_id in self._highlighted_points_ids:
            return

        if x is None or y is None:
            trace, point_index = self._scatter_plot_service.get_trace_and_point_index_by_point_id(point_id)
            if trace is None or point_index is None:
                return
            x = trace.x[point_index]
            y = trace.y[point_index]

        label = self.get_label_by_point_id(point_id)
        self._highlight_plot_service.highlight_point(self._plot_figure, x, y, point_id, label)
        self._highlighted_points_ids.append(point_id)


    def dehighlight_selected(self):
        for point_id, _ in self._selected_points.items():
            self.dehighlight_point(point_id)


    def dehighlight_point(self, point_id : str):
        point_id = self._ensure_id_is_point_id(point_id)
        
        if point_id not in self._highlighted_points_ids:
            return

        self._highlight_plot_service.dehighlight_point(self._plot_figure, point_id)
        self._highlighted_points_ids.remove(point_id)


    def dehighlight_all(self):
        self._highlight_plot_service.dehighlight_all(self._plot_figure)
        self._highlighted_points_ids.clear()


    '''
    Point updating
    '''
    def update_selected_points_label(self, new_label : str):
        for point_id in list(self._selected_points.keys()):
            self.update_point_label(point_id, new_label)


    def update_point_label(self, point_id : str, new_label : str) -> str:
        point_id = self._ensure_id_is_point_id(point_id)
        
        trace, point_index = self._scatter_plot_service.get_trace_and_point_index_by_point_id(self._plot_figure, point_id)
        self._scatter_plot_service.update_point_label(self._plot_figure, trace, point_index, new_label)
        self._points[point_id] = new_label

        if point_id in self._highlighted_points_ids:
            self._highlight_plot_service.update_highlight_point_label(self._plot_figure, point_id, new_label)
            

    '''
    General public methods
    '''
    def refresh_axis_range(self, plot_aspect_ratio : float):
        x_range = self._settings.xaxis_range
        y_range = self._settings.yaxis_range

        if x_range is None and y_range is not None and plot_aspect_ratio is not None:
            y_range_mean = (y_range[0] + y_range[-1]) / 2
            x_range = scale_and_center_range(y_range, plot_aspect_ratio, y_range_mean)
            self._settings.xaxis_range = x_range
            self._plot_figure.update_xaxes(range=x_range)
        if x_range is not None and y_range is None and plot_aspect_ratio is not None:
            x_range_mean = (x_range[0] + x_range[-1]) / 2
            y_range = scale_and_center_range(x_range, plot_aspect_ratio, x_range_mean)
            self._settings.yaxis_range = y_range
            self._plot_figure.update_yaxes(range=y_range)


    def plot(self, data : pd.DataFrame, point_ids : Iterable[str], time_points : Iterable[float], labels : Iterable[int] | None = None):
        data = self._resolve_data(data)
        time_point_texts = [f"time: {str(time_point)}" for time_point in time_points]
        labels = self._resolve_labels(labels, len(point_ids))
        self._normalize_data(data)

        logger.debug("add scatter")
        self._scatter_plot_service.add_scatter(
            self._plot_figure,
            data[0],
            data[1],
            point_ids,
            labels,
            time_point_texts
        )

        self._points.update({point_id: label for point_id, label in zip(point_ids, labels)})
        logger.debug("uodating opacity bookkeeping")
        self._opacity_bookkeeping_service.update_opacity_dict_and_plot(self._plot_figure, point_ids)


    def update_plot(self, data : pd.DataFrame, point_ids : Iterable[str], time_points : Iterable[float], labels : Iterable[int] | None = None):
        logger.info("Updating plot..")

        data = self._resolve_data(data)
        time_point_texts = [f"time: {str(time_point)}" for time_point in time_points]
        labels = self._resolve_labels(labels, len(point_ids))

        # check if there are any newly added points
        num_new_points = len(data) - self._get_num_plotted_points()
        if num_new_points > 1:
            new_point_ids = point_ids[:num_new_points] 
            self._opacity_bookkeeping_service.update_opacity_dict(new_point_ids)

        self._update_axis_ranges(data)
        scatter_plot_settings = self._resolve_scatter_plot_settings()
        opacity_values = self._get_opacity_values_chronoligical_order()
        self._normalize_data(data)
        new_figure = self._scatter_plot_service.create_figure(
            scatter_plot_settings,
            data[0],
            data[1],
            point_ids,
            labels,
            time_point_texts,
            opacity_values
        )
        

        self._points = {point_id: label for point_id, label in zip(point_ids, labels)}
        self._update_highlight(new_figure, data, point_ids)
        self._update_selection(new_figure, data, point_ids)
        logger.warn(f"assign new figure. {len(new_figure.data)}")
        self._plot_figure = new_figure


    '''
    General private methods
    '''
    def _ensure_id_is_point_id(self, id : str) -> str:
        if self._highlight_plot_service.is_highlight_id(id):
            return self._highlight_plot_service.get_point_id_from_highlight_id(id)
        if self._selection_plot_service.is_selection_id(id):
            return self._selection_plot_service.get_point_id_from_selection_id(id)
        return id


    def _update_highlight(self, new_figure : go.Figure, data : pd.DataFrame, point_ids : Iterable[str]):
        for point_id in self._highlighted_points_ids:
            point_index = point_ids.index(point_id)
            x = data[0][point_index]
            y = data[1][point_index]

            label = self.get_label_by_point_id(point_id)
            self._highlight_plot_service.highlight_point(new_figure, x, y, point_id, label)


    def _update_selection(self, new_figure : go.Figure, data : pd.DataFrame, ids : Iterable[int]):
        for point_id in self._selected_points:
            point_index = ids.index(point_id)
            x = data[0][point_index]
            y = data[1][point_index]

            self._selection_plot_service.select_point(new_figure, x, y, point_id)
            self._selected_points[point_id] = (x, y)


    def _expand_opacity_dict(self, ids : Iterable[int], opacity : float | None = None):
        if opacity is None:
            opacity = list(self._opacity_thresholds.keys())[0]
        self._points_by_opacity[opacity].extend(ids)


    def _reduce_opacity(self):
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
                scatter_trace, point_scatter_index = self._scatter_plot_service.get_trace_and_point_index_by_point_id(self._plot_figure, point_id)
                if scatter_trace is None or point_scatter_index is None:
                    logger.warn(f"could not find point in figure when attempting to reduce opacity. Point:{point_id}")
                    continue

                self._scatter_plot_service.update_point_opacity(self._plot_figure, scatter_trace, point_scatter_index, reduced_opacity)
                self._points_by_opacity[reduced_opacity].append(point_id)

            # remove all points of the old opacity value that were assigned a lower opacity value
            del points[:num_points_to_reduce_opacity]


    def _resolve_data(self, data : Iterable) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            return pd.DataFrame(data)
        return data


    def _normalize_data(self, data : pd.DataFrame):
        x_span = self._xaxis_edge_values[1] - self._xaxis_edge_values[0]
        x_mean = (self._xaxis_edge_values[1] + self._xaxis_edge_values[0]) / 2
        y_span = self._yaxis_edge_values[1] - self._yaxis_edge_values[0]
        y_mean = (self._yaxis_edge_values[1] + self._yaxis_edge_values[0]) / 2

        normalized_range_mean = 0.5

        if x_span > y_span:
            normalization_factor = 1 / x_span
        else:
            normalization_factor = 1 / y_span

        data[0] = scale_and_center_pd_series(data[0], normalization_factor, normalized_range_mean, x_mean)
        data[1] = scale_and_center_pd_series(data[1], normalization_factor, normalized_range_mean, y_mean)


    # label count is only needed when labels is None, this will set the labels to the unclassified label
    def _resolve_labels(self, labels : Iterable[int] | None, label_count : int | None = None) -> Iterable[str]:
        if labels is None:
            if label_count is None:
                raise Exception("Error processing labels: When labels is none, label_count needs to be provided.")
            return [self._settings.unclassified_label] * label_count
        
        labels = np.nan_to_num(labels, nan=-1)
        labels = list(map(lambda label: self._labels_dict[label], labels))
        return labels
    

    def _get_random_plotly_color(self):
        colors_in_use = list(self._color_map.values())
        named_colors_list = list(mcolors.CSS4_COLORS.keys())
        if colors_in_use is not None and set(named_colors_list).issubset(set(colors_in_use)):
            raise Exception('All colors available to plotly are already being used.')

        random_color = random.choice(named_colors_list)
        while colors_in_use is not None and random_color in colors_in_use:
            random_color = random.choice(named_colors_list)
        return random_color
    

    def _get_num_plotted_points(self):
        return sum([len(points) for points in self._points_by_opacity.values()])
    

    def _get_opacity_values_chronoligical_order(self):
        opacity_values = []
        for opacity, points in reversed(self._points_by_opacity.items()):
            opacity_values.extend([opacity] * len(points))
        return opacity_values
    

    def _update_axis_ranges(self, data : pd.DataFrame):
        if data is None or len(data) < 1:
            return

        highest_x = data[0].max()
        lowest_x = data[0].min()
        highest_y = data[1].max()
        lowest_y = data[1].min()

        if self._xaxis_edge_values is None or self._yaxis_edge_values is None:
            self._xaxis_edge_values = [lowest_x, highest_x]
            self._yaxis_edge_values = [lowest_y, highest_y]
            return

        self._xaxis_edge_values[1] = highest_x
        self._xaxis_edge_values[0] = lowest_x
        self._yaxis_edge_values[1] = highest_y
        self._yaxis_edge_values[0] = lowest_y

        
