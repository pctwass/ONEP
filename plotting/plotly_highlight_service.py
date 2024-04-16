import plotly.graph_objects as go

from scatter_plot_settings import ScatterPlotSettings
from plotly_plot_service import PlotlyPlotSerivce

HIGHLIGHT_TRACE_ID_PREFIX = 'scatter_highlight'
HIGHLIGHT_POINT_PREDIX = "highlight_"

class PlotlyHighlightService(PlotlyPlotSerivce):
    def init_highlight_traces(self, figure : go.Figure, highlight_settings : ScatterPlotSettings):
        label_set = highlight_settings.labels

        for label in label_set:
            figure.add_trace(go.Scatter(
                uid=f"{HIGHLIGHT_TRACE_ID_PREFIX}_{label}",
                mode="markers",
                hoverinfo='skip',
                showlegend=False,
                legendgroup=label,
                marker=dict(
                    size=highlight_settings.highlight_size,
                    color=highlight_settings.color_map[label],
                    line=dict(
                        color=highlight_settings.highlight_border_color, 
                        width=highlight_settings.highlight_border_size
                    ),
                ),
                x=[],
                y=[],
                ids=[]
            ))


    def is_highlight_id(self, point_id : str) -> bool:
        return point_id.startswith(HIGHLIGHT_POINT_PREDIX)
    

    def get_highlight_point_id(self, point_id : str) -> str:
        return(HIGHLIGHT_POINT_PREDIX + point_id)
    

    def get_highlight_traces(self, figure : go.Figure):
        return [trace for trace in figure.data if trace.uid.startswith(HIGHLIGHT_TRACE_ID_PREFIX)]
    

    def get_point_id_from_highlight_id(self, highlight_id : str) -> str:
        if not self.is_highlight_id(highlight_id):
            raise Exception(f"The provided highlight id '{highlight_id}' did not start with the highlight point prefix, cannot get point id.")
        return highlight_id[len(HIGHLIGHT_POINT_PREDIX):]
    

    def update_highlight_point_label(self, figure : go.Figure, highlight_id : str, new_label : str):
        if not self.is_highlight_id(highlight_id):
            highlight_id = self.get_highlight_point_id(highlight_id)

        curr_highlight_trace = self._get_highlight_trace_by_highlight_id(figure, highlight_id)
        new_highlight_trace = self._get_highlight_trace_by_label(figure, new_label)

        highlight_index = curr_highlight_trace.ids.index(highlight_id)
        point_x = curr_highlight_trace.x[highlight_index]
        point_y = curr_highlight_trace.y[highlight_index]

        self._remove_point(curr_highlight_trace, highlight_id)
        self._add_point(new_highlight_trace, highlight_id, point_x, point_y)


    def highlight_point(self, figure : go.Figure, point_x : float, point_y : float, point_id : str, label : str):
        highlight_trace = self._get_highlight_trace_by_label(figure, label)
        if highlight_trace is None:
            raise Exception(f"Missing highlight trace for label '{label}'.")
        
        highlight_id = self.get_highlight_point_id(point_id)
        self._add_point (highlight_trace, highlight_id, point_x, point_y)
    

    def dehighlight_point(self, figure : go.Figure, point_id : str):
        highlight_id = self.get_highlight_point_id(point_id)
        highlight_trace = self._get_highlight_trace_by_highlight_id(figure, highlight_id)
        if highlight_trace is None:
            raise Exception(f"Missing highlight trace containing highlight '{highlight_id}'.")
        
        self._remove_point(highlight_trace, highlight_id)


    def dehighlight_all(self, figure : go.Figure):
        highlight_traces = self.get_highlight_traces(figure)
        for trace in highlight_traces:
            self._clear_trace(trace)


    def _get_highlight_trace_by_highlight_id(self, figure : go.Figure, highlight_id : str) -> go.Scatter:
        return next(trace for trace in figure.data if trace.ids is not None and highlight_id in trace.ids)
    

    def _get_highlight_trace_by_label(self, figure : go.Figure, label : str) -> go.Scatter:
        highlight_trace_uid = self._get_highlight_trace_id(label)
        return next(trace for trace in figure.data if trace.uid == highlight_trace_uid)


    def _get_highlight_trace_id(self, label : str) -> str:
        return f"{HIGHLIGHT_TRACE_ID_PREFIX}_{label}"