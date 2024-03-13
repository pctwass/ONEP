import plotly.graph_objects as go
import numpy as np
from pyparsing import Iterable

from plotly_services.scatter_plot_settings import ScatterPlotSettings
from plotly_services.plotly_plot_service import PlotlyPlotSerivce
from plotly_services.plotly_selection_service import PlotlySelectionService
from plotly_services.plotly_highlight_service import PlotlyHighlightService

SCATTER_TRACE_UID_PREFIX = 'scatter'

class PlotlyScatterService(PlotlyPlotSerivce):
    _selection_service : PlotlySelectionService
    _highlight_service : PlotlyHighlightService


    def __init__(self) -> None:
        self._selection_service = PlotlySelectionService()
        self._highlight_service = PlotlyHighlightService()


    def create_figure(self, plot_settings : ScatterPlotSettings, x : Iterable = None, y : Iterable = None, ids : Iterable = None, labels : Iterable = None, opacity_values : Iterable[float] | float = None) -> go.Figure:
        label_set = plot_settings.labels
        opacity_set = [float(opacity) for opacity in plot_settings.opacity_set]

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
                    self._add_scatter_trace(figure, label, opacity, color)

        if all(var is not None for var in (x, y, ids, labels)):
            self.add_scatter(figure, x, y, ids, labels, opacity_values)

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
                'duration': plot_settings.transition_duration,
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
    

    def is_scatter_trace_point(self, point_id : str) -> bool:
        return point_id.startswith(f"{SCATTER_TRACE_UID_PREFIX}_")


    def get_scatter_trace_uid(self, label : str, opacity : float) -> str:
        return f"{SCATTER_TRACE_UID_PREFIX}_{label}_{opacity}"
    

    def get_point_trace_by_id(self, figure : go.Figure, id : float) -> go.Scatter:
        label, opacity, _ = self._disect_point_id(id)

        trace_uid = self.get_scatter_trace_uid(label, opacity) 
        matching_trace = self.get_trace_by_uid(figure, trace_uid)
        if matching_trace is None: 
            return
        return matching_trace
        
    
    def get_point_trace_and_index_by_id(self, figure : go.Figure, id : float) -> (go.Scatter, int):
        matching_trace = self.get_point_trace_by_id(figure, id)
        if matching_trace is None:
            return None, None

        point_index = next((index for index, id_entry in enumerate(matching_trace.ids) if id_entry==id), None)
        return matching_trace, point_index
    

    '''
    Note that point_uids are different from the point ids. The uid of a point is its identifyer outside the scope of the figure, this uid is transformed into the figre specific uid
    '''
    def add_scatter(self, figure : go.Figure, x : Iterable[float], y : Iterable[float], point_uids : Iterable[float], labels : Iterable[str], opacity : Iterable[float] | float = 1.0) -> Iterable[str]:
        if isinstance(opacity, Iterable):
            select_opacity = True
        elif isinstance(opacity, (float, int)):
            select_opacity = False
        else: raise Exception("opacity should be either of type 'Iterable[float]' or 'float'")

        ids = []
        for i, label in enumerate(labels):
            selected_x = [x[i]]
            selected_y = [y[i]]
            selected_time_points = [point_uids[i]]

            if select_opacity: 
                selected_opacity = opacity[i]
            else: selected_opacity = opacity
            
            ids_subset = self.add_scatter_points(figure, selected_x, selected_y, selected_time_points, label, selected_opacity)
            if ids_subset is not None:
                ids = np.append(ids, ids_subset)

        return ids
    
    
    '''
    Note that point_uid is different from the point id. The uid of a point is its identifyer outside the scope of the figure, this uid is transformed into the figre specific uid
    '''
    def add_scatter_point(self, figure : go.Figure, x : float, y : float, point_uid : float, label : str, opacity : float = 1.0) -> str:
        scatter_point_ids = self.add_scatter_points(figure, [x], [y], [point_uid], label, opacity)
        if scatter_point_ids is None or len(scatter_point_ids) == 0:
            return None
        return scatter_point_ids[0]

    
    '''
    Note that point_uids are different from the point ids. The uid of a point is its identifyer outside the scope of the figure, this uid is transformed into the figre specific uid
    '''
    def add_scatter_points(self, figure : go.Figure, x : Iterable[float], y : Iterable[float], point_uids : Iterable[float], label : str, opacity : float = 1.0) -> Iterable[str]:
        trace_uid = self.get_scatter_trace_uid(label, opacity)
        target_trace : go.Scatter = self.get_trace_by_uid(figure, trace_uid)
        if target_trace is None:
            label_group_trace = self.get_trace_by_uid(figure, self._get_legend_group_trace_uid(label))
            color = label_group_trace.marker.color
            target_trace = self._add_scatter_trace(figure, label, opacity, color)
        
        if isinstance(target_trace, str):
            print(f"Warning: {trace_uid} returned as a string.")
            return []

        ids = self._point_uids_to_point_ids(target_trace.name, target_trace.opacity, point_uids)
        text = self._get_trace_text(point_uids)

        target_trace.x = np.append(target_trace.x, x).tolist()
        target_trace.y = np.append(target_trace.y, y).tolist()
        target_trace.ids = np.append(target_trace.ids, ids).tolist()
        target_trace.text = np.append(target_trace.text, text).tolist()

        return ids


    def update_point_label(self, figure : go.Figure, trace : go.Scatter | str, point_index, new_label) -> str:
        if isinstance(trace, str):
            trace = self.get_trace_by_uid(figure, trace)
        opacity = trace.opacity
        return self.update_point(figure, trace, point_index, new_label, opacity)


    def update_point_opacity(self, figure : go.Figure, trace : go.Scatter | str, point_index, new_opacity) -> str:
        if isinstance(trace, str):
            trace = self.get_trace_by_uid(figure, trace)
        label = trace.name
        return self.update_point(figure, trace, point_index, label, new_opacity)


    def update_point(self, figure : go.Figure, trace : go.Scatter | str, point_index, label, opacity) -> str:
        if isinstance(trace, str):
            trace = self.get_trace_by_uid(figure, trace)

        x = trace.x[point_index]
        y = trace.y[point_index]
        id = trace.ids[point_index]

        point_uid = self.get_point_uid_from_point_id(id)
        new_id = self.add_scatter_point(figure, x, y, point_uid, label, opacity)
        self._remove_point(trace, id)
        return new_id


    def _add_scatter_trace(self, figure : go.Figure, label : str, opacity : float, color : str, show_legend : bool = False) -> go.Scatter:
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
        return self.get_scatter_trace_uid(figure, trace_uid)
    

    def _get_point_id(self, label : str, opacity : float, uid : float) -> str:
        return f"{SCATTER_TRACE_UID_PREFIX}_{label}_{opacity}_{uid}"


    def _point_uids_to_point_ids(self, label : str, opacity : float, uids : Iterable[float]) -> Iterable[str]:
        return [self._get_point_id(label, opacity, time_point) for time_point in uids]
    

    def _disect_point_id(self, point_id :str) -> (str, float, str):
        id_sections = point_id.split('_')
        label = id_sections[1]
        opacity = id_sections[2]
        uid = id_sections[3]
        return label, opacity, uid