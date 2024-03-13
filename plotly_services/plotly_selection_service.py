import plotly.graph_objects as go

from plotly_services.scatter_plot_settings import ScatterPlotSettings
from plotly_services.plotly_plot_service import PlotlyPlotSerivce

SELECTION_TRACE_UID = 'scatter_selection'

class PlotlySelectionService(PlotlyPlotSerivce):
    def init_selection_trace(self, figure : go.Figure, plot_settings : ScatterPlotSettings):
        figure.add_trace(go.Scatter(
            uid=SELECTION_TRACE_UID,
            mode="markers",
            hoverinfo='skip',
            showlegend=False,
            opacity=0.8,
            marker=dict(
                color='rgba(0, 0, 0, 0)',
                line=dict(
                    color=plot_settings.selection_border_color, 
                    width=plot_settings.selection_border_size
                ),
            ),
            x=[],
            y=[],
            ids=[]
        ))


    def get_selection_trace(self, figure : go.Figure) -> go.Scatter:
        return next(trace for trace in figure.data if trace.uid == SELECTION_TRACE_UID)
    

    def select_point(self, figure : go.Figure, point_x : float, point_y : float, point_id : str):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_UID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        
        selection_id = self._get_selection_id(point_id)
        self._add_point(selection_trace, selection_id, point_x, point_y)


    def deselect_point(self, figure : go.Figure, point_id : str):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_UID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        
        selection_id = self._get_selection_id(point_id)
        self._remove_point(selection_trace, selection_id)


    def deselect_all(self, figure : go.Figure):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_UID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        self._clear_trace(selection_trace)
    

    def _get_selection_id(self, point_id : str) -> str:
        return(f"selection_{self.get_point_uid_from_point_id(point_id)}")