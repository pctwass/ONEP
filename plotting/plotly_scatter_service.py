import plotly.graph_objects as go
import numpy as np
import itertools
from pyparsing import Iterable

from plotting.scatter_plot_settings import ScatterPlotSettings
from plotting.plotly_plot_service import PlotlyPlotSerivce
from plotting.plotly_selection_service import PlotlySelectionService
from plotting.plotly_highlight_service import PlotlyHighlightService
from utils.logging import logger


SCATTER_TRACE_UID_PREFIX = 'scatter'

class PlotlyScatterService(PlotlyPlotSerivce):
    _selection_service : PlotlySelectionService
    _highlight_service : PlotlyHighlightService


    def __init__(self) -> None:
        self._selection_service = PlotlySelectionService()
        self._highlight_service = PlotlyHighlightService()


    def create_figure(self, plot_settings : ScatterPlotSettings, x : Iterable = None, y : Iterable = None, point_ids : Iterable = None, labels : Iterable = None, texts : Iterable[str] = None, opacity_values : Iterable[float] | float = None) -> go.Figure:
        logger.info("Creating figure")
        
        label_set = plot_settings.labels
        opacity_set = [float(opacity) for opacity in plot_settings.opacity_set]

        if (texts is None or len(texts) == 0) and point_ids is not None:
            texts = [""]*len(point_ids)

        if opacity_values is None:
            if plot_settings.initial_opacity is not None:
                opacity_values = plot_settings.initial_opacity
            else: opacity_values = 1.0
        
        figure = go.Figure()
        self._set_layout(figure, plot_settings)
        self._set_legend_groups(figure, label_set, plot_settings.color_map, plot_settings.initial_opacity, x, y)
        self._highlight_service.init_highlight_traces(figure, plot_settings)
        self._selection_service.init_selection_trace(figure, plot_settings)

        # add traces for all label-opacity combindations if opacity values are set
        if opacity_set is not None:
            for label in label_set:
                color = plot_settings.color_map[label]
                for opacity in opacity_set:
                    self.__add_scatter_trace(figure, label, opacity, color)
        
        if all(var is not None for var in (x, y, point_ids, labels)):
            self.add_scatter(figure, x, y, point_ids, labels, texts, opacity_values)
        return figure


    def _set_layout(self, figure : go.Figure, plot_settings : ScatterPlotSettings):
        figure.update_layout(
            xaxis=dict(
                showticklabels=plot_settings.show_axis,
                range=plot_settings.xaxis_range,
                dtick=plot_settings.xaxis_step_size
            ),
            yaxis=dict(
                showticklabels=plot_settings.show_axis,
                range=plot_settings.yaxis_range,
                dtick=plot_settings.yaxis_step_size
            ),
            transition={
                #'duration': plot_settings.transition_duration,
                'easing': 'cubic-in-out',
            }
        )


    # Creates a set of traces containing no data, that are used to display the legend groups in the figure's legend.
    # These traces are not to be used in any other manner.    
    def _set_legend_groups(self, figure : go.Figure, labels : Iterable[str], color_mapping : dict[str,str], opacity : float = 1.0, init_x : Iterable[float] = None, init_y : Iterable[float] = None):
        if not self._is_iterable_none_or_empty(init_x) and not self._is_iterable_none_or_empty(init_y):
            x = [init_x[0]]
            y = [init_y[0]]
        else:
            x = [0]
            y = [0]
        
        for label in labels:
            color = color_mapping[label]
            figure.add_trace(go.Scatter(
                uid=self._get_legend_group_trace_uid(label),
                name=label,
                legendgroup=label,
                hoverinfo='skip',
                opacity=opacity,
                showlegend=True,
                marker=dict(
                    color=color,
                    size=0.000001
                ),
                x=x,
                y=y,
            ))
    

    '''
    Get methods
    '''
    def get_scatter_trace_uid(self, label : str, opacity : float) -> str:
        return f"{SCATTER_TRACE_UID_PREFIX}_{label}_opacity={opacity}"
    

    def get_trace(self, figure : go.Figure, label : str, opacity : float) -> go.Scatter:
        trace_uid = self.get_scatter_trace_uid(label, opacity) 
        matching_trace = self.get_trace_by_id(figure, trace_uid)
        if matching_trace is None: 
            return
        return matching_trace
        
    
    def get_trace_and_point_index(self, figure : go.Figure, point_id : str, label : str, opacity : float) -> tuple[go.Scatter, int]:
        matching_trace = self.get_point_trace(figure, label, opacity)
        if matching_trace is None:
            return None, None

        point_index = next((index for index, id_entry in enumerate(matching_trace.ids) if id_entry==point_id), None)
        return matching_trace, point_index
    

    def get_trace_by_point_id(self, figure : go.Figure, point_id : str) -> go.Scatter:
        matching_trace = next((trace for trace in figure.data if trace.ids is not None and point_id in trace.ids), None)
        if matching_trace is None: 
            return
        return matching_trace
        
    
    def get_trace_and_point_index_by_point_id(self, figure : go.Figure, point_id : str) -> tuple[go.Scatter, int]:
        matching_trace = self.get_trace_by_point_id(figure, point_id)
        if matching_trace is None:
            return None, None

        point_index = next((index for index, id_entry in enumerate(matching_trace.ids) if id_entry==point_id), None)
        return matching_trace, point_index
    

    def get_label_by_point_id(self, figure : go.Figure, point_id : str) -> str:
        matching_trace = self.get_trace_by_point_id(figure, point_id)
        if matching_trace is None:
            return None
        return matching_trace.name

    
    '''
    Add scatter methods
    '''
    def add_scatter(self, figure : go.Figure, x : Iterable[float], y : Iterable[float], point_ids : Iterable[str], labels : Iterable[str], texts : Iterable[str] = None, opacities : Iterable[float] | float = 1.0):
        if isinstance(opacities, (float, int)):
            opacities = [opacities]
        elif not isinstance(opacities, Iterable):
            raise Exception("opacity should be either of type 'Iterable[int|float]', 'int', or 'float'")
        
        if texts is None or len(texts) == 0:
            texts = [""]*len(point_ids)

        index_array_by_label = {}
        for label in set(labels):
            index_array_by_label[label] = [index for index, value in enumerate(labels) if value == label]
        
        index_array_by_opacity = {}
        for opacity in set(opacities):
            index_array_by_opacity[opacity] = [index for index, value in enumerate(opacities) if value == opacity]

        # iterate over every label - opacity pair
        for label, opacity in itertools.product(set(labels), set(opacities)):
            matching_indeces = list(set(index_array_by_label[label]) & set(index_array_by_opacity[opacity]))
            matching_x = [x[i] for i in matching_indeces]
            matching_y = [y[i] for i in matching_indeces]
            matching_point_ids = [point_ids[i] for i in matching_indeces]
            matching_texts = [texts[i] for i in matching_indeces]
            self.add_scatter_points(figure, matching_x, matching_y, matching_point_ids, label, matching_texts, opacity)


    def add_scatter_point(self, figure : go.Figure, x : float, y : float, point_id : str, label : str, text : str = None, opacity : float = 1.0):
        self.add_scatter_points(figure, [x], [y], [point_id], label, [text], opacity)

    
    def add_scatter_points(self, figure : go.Figure, x : Iterable[float], y : Iterable[float], point_ids : Iterable[str], label : str, texts : Iterable[str] = None, opacity : float = 1.0):
        trace_uid = self.get_scatter_trace_uid(label, opacity)
        target_trace : go.Scatter = self.get_trace_by_id(figure, trace_uid)
        if target_trace is None:
            label_group_trace = self.get_trace_by_id(figure, self._get_legend_group_trace_uid(label))
            color = label_group_trace.marker.color
            target_trace = self.__add_scatter_trace(figure, label, opacity, color)

        target_trace.x = np.append(target_trace.x, x).tolist()
        target_trace.y = np.append(target_trace.y, y).tolist()
        target_trace.ids = np.append(target_trace.ids, point_ids).tolist()
        
        texts = self._format_trace_text(texts)
        if texts is not None:
            target_trace.text = np.append(target_trace.text, texts).tolist()


    def __add_scatter_trace(self, figure : go.Figure, label : str, opacity : float, color : str, show_legend : bool = False) -> go.Scatter:
        if not isinstance(opacity, float):
            opacity = float(opacity)

        trace_uid = self.get_scatter_trace_uid(label, opacity)
        trace = go.Scatter(
            uid=trace_uid,
            mode='markers',
            name=label,
            legendgroup=label,
            marker=dict(color=color),
            opacity=opacity,
            showlegend=show_legend,
            x=[],
            y=[],
            ids=[],
            text=[],
            hovertemplate='%{text}<br>' + f'opacity: {opacity}'
        )
        figure.add_trace(trace)
        return self.get_trace_by_id(figure, trace_uid)

    '''
    Update methods
    '''
    def update_point_label(self, figure : go.Figure, trace : go.Scatter | str, point_index : int, new_label : str):
        if isinstance(trace, str):
            trace = self.get_trace_by_id(figure, trace)
        opacity = trace.opacity
        self.update_point(figure, trace, point_index, new_label, opacity)


    def update_point_opacity(self, figure : go.Figure, trace : go.Scatter | str, point_index : int, new_opacity : float):
        if isinstance(trace, str):
            trace = self.get_trace_by_id(figure, trace)
        label = trace.name
        self.update_point(figure, trace, point_index, label, new_opacity)


    def update_point(self, figure : go.Figure, trace : go.Scatter | str, point_index, label, opacity):
        if isinstance(trace, str):
            trace = self.get_trace_by_id(figure, trace)

        x = trace.x[point_index]
        y = trace.y[point_index]
        point_id = trace.ids[point_index]
        text = trace.text[point_index]

        self._remove_point(trace, point_id)
        self.add_scatter_point(figure, x, y, point_id, label, text, opacity)