import plotly.graph_objects as go

from plotly_services.scatter_plot_settings import ScatterPlotSettings
from plotly_services.plotly_plot_service import PlotlyPlotSerivce

HIGHLIGHT_TRACE_UID_PREFIX = 'scatter_highlight'

class PlotlyHighlightService(PlotlyPlotSerivce):
    def init_highlight_traces(self, figure : go.Figure, highlight_settings : ScatterPlotSettings):
        label_set = highlight_settings.labels

        for label in label_set:
            figure.add_trace(go.Scatter(
                uid=f"{HIGHLIGHT_TRACE_UID_PREFIX}_{label}",
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

    
    def get_highlight_trace(self, figure : go.Figure, label : str) -> go.Scatter:
        highlight_trace_uid = self._get_highlight_trace_uid(label)
        return next(trace for trace in figure.data if trace.uid == highlight_trace_uid)
    

    def get_highlight_traces(self, figure : go.Figure):
        return [trace for trace in figure.data if trace.uid.startswith(HIGHLIGHT_TRACE_UID_PREFIX)]
    

    def update_highlight_point_label(self, figure : go.Figure, point_id : str, new_label : str):
        point_label = self._get_scatter_point_label(point_id)
        curr_highlight_trace = self.get_highlight_trace(figure, point_label)
        new_highlight_trace = self.get_highlight_trace(figure, new_label)

        highlight_id = self._get_highlight_point_id(point_label, point_id)
        highlight_index = curr_highlight_trace.ids.index(highlight_id)
        point_x = curr_highlight_trace.x[highlight_index]
        point_y = curr_highlight_trace.y[highlight_index]

        new_highlight_id = self._get_highlight_point_id(new_label, point_id)
        self._add_point(new_highlight_trace, new_highlight_id, point_x, point_y)
        self._remove_point(curr_highlight_trace, highlight_id)


    def is_highlight_point(self, point_id : str) -> bool:
        return point_id.startswith("highlight_")


    def highlight_point(self, figure : go.Figure, point_x : float, point_y : float, point_id : str):
        label = self._get_scatter_point_label(point_id)
        highlight_trace = self.get_highlight_trace(figure, label)
        if highlight_trace is None:
            raise Exception(f"No highlight trace was created upon creating the figure for label {label}.")
        
        highlight_id = self._get_highlight_point_id(label, point_id)
        self._add_point (highlight_trace, highlight_id, point_x, point_y)
    

    def dehighlight_point(self, figure : go.Figure, point_id : str):
        label = self._get_scatter_point_label(point_id)
        highlight_trace = self.get_highlight_trace(figure, label)
        if highlight_trace is None:
            raise Exception(f"No highlight trace was created upon creating the figure for label {label}.")
        
        highlight_id = self._get_highlight_point_id(label, point_id)
        self._remove_point(highlight_trace, highlight_id)


    def dehighlight_all(self, figure : go.Figure):
        highlight_traces = self.get_highlight_traces(figure)
        for trace in highlight_traces:
            self._clear_trace(trace)


    def _get_highlight_trace_uid(self, label : str) -> str:
        return f"{HIGHLIGHT_TRACE_UID_PREFIX}_{label}"
    

    def _get_highlight_point_id(self, label : str,  point_id : str) -> str:
        return(f"highlight_{label}_{self.get_point_uid_from_point_id(point_id)}")