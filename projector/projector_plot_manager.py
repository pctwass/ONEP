import time
import random
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import matplotlib.colors as mcolors

from pyparsing import Iterable

from utils.logging import logger
from utils.dataframe_utils import *
from utils.Iterable_utils import *
from plot_settings import PlotSettings
from plotly_services.plotly_scatter_service import PlotlyScatterService
from plotly_services.plotly_selection_service import PlotlySelectionService
from plotly_services.plotly_highlight_service import PlotlyHighlightService
from plotly_services.scatter_plot_settings import ScatterPlotSettings


class ProjectorPlotManager():
    name : str
    _model_plot : go.Figure
    _settings : PlotSettings
    _scatter_plot_service : PlotlyScatterService
    _selection_plot_service : PlotlySelectionService
    _highlight_plot_service : PlotlyHighlightService

    _labels_dict : dict[int, str] = {}
    _color_map : dict[str, str] = {}
    _opacity_thresholds : dict[float, int] = {}
    _points_by_opacity : dict[float, Iterable[str]]= {}
    _init_opacity : float = 1.0

    _selected_points : dict[str, tuple[float, float]] = {}
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

        scatter_plot_settings = self._resolve_scatter_plot_settings()
        self._model_plot = self._scatter_plot_service.create_figure(scatter_plot_settings)

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
        return ScatterPlotSettings(
            self.get_labels(),
            self._color_map,
            self._init_opacity,
            list(self._settings.opacity_thresholds.keys()),

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
    

    def get_plot(self) -> go.Figure:
        return self._model_plot


    def get_labels(self) -> list[str]:
        labels = [self._settings.unclassified_label]
        labels.extend(self._settings.labels)
        return labels
    

    def get_point_uid_from_point_id(self, point_id : str) -> str:
        while point_id is None:
            break
        return self._scatter_plot_service.get_point_uid_from_point_id(point_id)


    def get_trace_uid_by_point_id(self, id : float) -> str:
        trace = self._scatter_plot_service.get_point_trace_by_id(self._model_plot, id)
        return trace.uid


    def get_trace_label(self, uid : str) -> str:
        return self._scatter_plot_service.get_trace_by_uid(self._model_plot, uid).name
    

    def get_selected_point_ids(self) -> list[str]:
        return self._selected_points.keys()


    def get_count_selected_points(self) -> int:
        return len(self._selected_points)
    

    def is_selected_point(self, id : str) -> bool:
        return id in self._selected_points

    def select_point(self, id : str, x : float = None, y :float = None):
        if id is not None and not self._scatter_plot_service.is_scatter_trace_point(id):
            return

        if self._highlight_plot_service.is_highlight_point(id):
            time_point = self._scatter_plot_service.get_point_uid_from_point_id(id)
            id = next(id for id in self._highlighted_points_ids if id.endswith(time_point))
        
        if id is None:
            raise Exception("Point id cannot be None.")

        if id in self._selected_points:
            return
        
        if x is None or y is None:
            trace, point_index = self._scatter_plot_service.get_point_trace_and_index_by_id(id)
            x = trace.x[point_index]
            y = trace.y[point_index]
        self._selected_points[id] = (x, y)
        self._selection_plot_service.select_point(self._model_plot, x, y, id)

    def deselect_point(self, id : str):
        if self._highlight_plot_service.is_highlight_point(id):
            time_point = self._scatter_plot_service.get_point_uid_from_point_id(id)
            id = next(id for id in self._highlighted_points_ids if id.endswith(time_point))

        self._selected_points.pop(id, None)
        self._selection_plot_service.deselect_point(self._model_plot, id)

    def deselect_all(self):
        self._selected_points.clear()
        self._selection_plot_service.deselect_all(self._model_plot)


    def highlight_selected(self):
        for point_id, point_cords in self._selected_points.items():
            self.highlight_point(point_id, point_cords[0], point_cords[1])

    def highlight_point(self, id : str, x : float = None, y :float = None):
        if id in self._highlighted_points_ids:
            return

        if x is None or y is None:
            trace, point_index = self._scatter_plot_service.get_point_trace_and_index_by_id(id)
            x = trace.x[point_index]
            y = trace.y[point_index]
        self._highlighted_points_ids.append(id)
        self._highlight_plot_service.highlight_point(self._model_plot, x, y, id)

    def dehighlight_selected(self):
        for point_id, _ in self._selected_points.items():
            self.dehighlight_point(point_id)

    def dehighlight_point(self, id : str):
        if id not in self._highlighted_points_ids:
            return

        self._highlight_plot_service.dehighlight_point(self._model_plot, id)
        self._highlighted_points_ids.remove(id)

    def dehighlight_all(self):
        self._highlighted_points_ids.clear()
        self._highlight_plot_service.dehighlight_all(self._model_plot)


    def update_selected_points_label(self, new_label : str):
        for selected_point_id in list(self._selected_points.keys()):
            self.update_point_label(selected_point_id, new_label)


    def update_point_label(self, id : str, new_label : str) -> str:
        trace, point_index = self._scatter_plot_service.get_point_trace_and_index_by_id(self._model_plot, id)
        updated_point_id = self._scatter_plot_service.update_point_label(self._model_plot, trace, point_index, new_label)

        if updated_point_id is None:
            raise Exception(f"Something went wrong while assigning point {id} with new label {new_label}, new id was None.")

        if id in self._highlighted_points_ids:
            self._highlight_plot_service.update_highlight_point_label(self._model_plot, id, new_label)
            highlighted_point_id_index = self._highlighted_points_ids.index(id)
            self._highlighted_points_ids[highlighted_point_id_index] = updated_point_id

        if id in self._selected_points:
            self._selected_points[updated_point_id] = self._selected_points.pop(id)
        
        return updated_point_id
            
    
    def refresh_axis_range(self, plot_aspect_ratio : float):
        x_range = self._settings.xaxis_range
        y_range = self._settings.yaxis_range

        if x_range is None and y_range is not None and plot_aspect_ratio is not None:
            y_range_mean = (y_range[0] + y_range[-1]) / 2
            x_range = scale_and_center_range(y_range, plot_aspect_ratio, y_range_mean)
            self._settings.xaxis_range = x_range
            self._model_plot.update_xaxes(range=x_range)
        if x_range is not None and y_range is None and plot_aspect_ratio is not None:
            x_range_mean = (x_range[0] + x_range[-1]) / 2
            y_range = scale_and_center_range(x_range, plot_aspect_ratio, x_range_mean)
            self._settings.yaxis_range = y_range
            self._model_plot.update_yaxes(range=y_range)


    def plot(self, data : pd.DataFrame, time_points : Iterable[float], labels : Iterable[int] | None = None):
        start_time = time.time()

        data = self._resolve_data(data)
        labels = self._resolve_labels(labels, len(time_points))
        self._normalize_data(data)
        ids = self._scatter_plot_service.add_scatter(
            self._model_plot,
            data[0],
            data[1],
            time_points,
            labels
        )

        self._track_points_by_opacity(ids)
        self._reduce_opacity()

        print(f"Plotting projection took: {time.time() - start_time}")


    def update_plot(self, data : pd.DataFrame, time_points : Iterable[float], labels : Iterable[int] | None = None):
        if len(data) != len(time_points):
            raise Exception(f"There should be an equal amount of data points and time points. Data entries: {len(data)}. Time point entries: {len(time_points)}")

        start_time = time.time()
        data = self._resolve_data(data)
        labels = self._resolve_labels(labels, len(time_points))

        # check if there are any newly added points
        num_new_points = len(data) - self._get_num_plotted_points()
        if num_new_points > 1:
            if labels is None: 
                new_labels = [self._settings.unclassified_label] * num_new_points
            else:
                new_labels = labels[:num_new_points]

            new_time_points = time_points[:num_new_points] 
            new_point_ids = [self._scatter_plot_service._get_point_id(new_labels[i], self._init_opacity, new_time_points[i]) for i in range(num_new_points)]
            self._track_points_by_opacity(new_point_ids, self._init_opacity)

        self._update_axis_edge_values(data)
        scatter_plot_settings = self._resolve_scatter_plot_settings()
        opacity_values = self._get_opacity_values_chronoligical_order()
        self._normalize_data(data)
        new_figure = self._scatter_plot_service.create_figure(
            scatter_plot_settings,
            data[0],
            data[1],
            time_points,
            labels,
            opacity_values
        )
        
        self._update_highlight(new_figure, data, time_points)
        self._update_selection(new_figure, data, time_points)
        self._model_plot = new_figure
        if num_new_points > 1:
            self._reduce_opacity()
        # print(f"Plotting update took: {time.time() - start_time}")


    def _update_highlight(self, new_figure : go.Figure, data : pd.DataFrame, time_points : Iterable[float]):
        for highlight_point_id in self._highlighted_points_ids:
            time_point = float(highlight_point_id.split("_")[-1])
            point_index = time_points.index(time_point)
            x = data[0][point_index]
            y = data[1][point_index]

            self._highlight_plot_service.highlight_point(new_figure, x, y, highlight_point_id)

    def _update_selection(self, new_figure : go.Figure, data : pd.DataFrame, time_points : Iterable[float]):
        for selected_point_id in self._selected_points:
            time_point = float(selected_point_id.split("_")[-1])
            point_index = time_points.index(time_point)
            x = data[0][point_index]
            y = data[1][point_index]

            self._selection_plot_service.select_point(new_figure, x, y, selected_point_id)
            self._selected_points[selected_point_id] = (x, y)


    def _track_points_by_opacity(self, ids : Iterable[str], opacity : float | None = None):
        if opacity is None:
            opacity = list(self._opacity_thresholds.keys())[0]
        self._points_by_opacity[opacity].extend(ids)


    def _reduce_opacity(self):
        # print("Reducing opacity")
        for i, (opacity, points) in enumerate(self._points_by_opacity.items()):
            opacity_threshold = self._opacity_thresholds[opacity]
            if np.isnan(opacity_threshold) or i >= len(self._points_by_opacity)-1:
                continue
            
            num_points_to_reduce_opacity = len(points) - opacity_threshold
            if num_points_to_reduce_opacity < 1:
                continue

            reduced_opacity = list(self._points_by_opacity.keys())[i+1]
            for point_index in range(num_points_to_reduce_opacity):
                point_id = points[point_index]
                scatter, point_scatter_index = self._scatter_plot_service.get_point_trace_and_index_by_id(self._model_plot, point_id)
                if scatter is None or point_scatter_index is None:
                    print(f"could not find point in figure when attempting to reduce opacity. Point: {point_id}")
                    # logger.warning(f"could not find point in figure when attempting to reduce opacity. Point:{point_id}")
                    continue

                new_id = self._scatter_plot_service.update_point_opacity(self._model_plot, scatter, point_scatter_index, reduced_opacity)
                if new_id is not None:
                    self._points_by_opacity[reduced_opacity].append(new_id)

                if point_id in self._selected_points:
                    point_coords = self._selected_points.pop(point_id)
                    if new_id is not None:
                        self._selected_points[new_id] = point_coords
                if point_id in self._highlighted_points_ids:
                    self._highlighted_points_ids.pop(point_coords)
                    if new_id is not None:
                        self._highlighted_points_ids.append(new_id)

            del points[:num_points_to_reduce_opacity]


    def _resolve_data(self, data : Iterable) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            return pd.DataFrame(data)
        return data


    def _normalize_data(self, data : pd.DataFrame):
        x_span = self._xaxis_edge_values[1] - self._xaxis_edge_values[0]
        y_span = self._yaxis_edge_values[1] - self._yaxis_edge_values[0]
        x_range_mean = (self._xaxis_edge_values[1] + self._xaxis_edge_values[0]) / 2
        y_range_mean = (self._yaxis_edge_values[1] + self._yaxis_edge_values[0]) / 2
        normalized_range_mean = 0.5

        if x_span > y_span:
            normalization_factor = 1 / x_span
        else:
            normalization_factor = 1 / y_span

        data[0] = scale_and_center_pd_series(data[0], normalization_factor, normalized_range_mean, x_range_mean)
        data[1] = scale_and_center_pd_series(data[1], normalization_factor, normalized_range_mean, y_range_mean)


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
            raise Exception('all colors available to plotly are already being used')

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
    

    def _update_axis_edge_values(self, data : pd.DataFrame):
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

        
