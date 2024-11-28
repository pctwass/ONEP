import plotly.graph_objects as go

from plotting.scatter_plot_settings import ScatterPlotSettings
from plotting.plotly_plot_service import PlotlyPlotSerivce

SELECTION_TRACE_ID = 'scatter_selection'
SELECTION_POINT_ID_PREFIX = 'selection_'

class PlotlySelectionService(PlotlyPlotSerivce):
    def init_selection_trace(self, figure : go.Figure, plot_settings : ScatterPlotSettings):
        figure.add_trace(go.Scatter(
            uid=SELECTION_TRACE_ID,
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


    def is_selection_id(self, point_id : str) -> bool:
        return point_id.startswith(SELECTION_POINT_ID_PREFIX)
    

    def get_selection_id(self, point_id : str) -> str:
        return(SELECTION_POINT_ID_PREFIX + point_id)
    

    def get_selection_trace(self, figure : go.Figure) -> go.Scatter:
        return next(trace for trace in figure.data if trace.uid == SELECTION_TRACE_ID)
    

    def get_point_id_from_selection_id(self, selection_id : str) -> str:
        if not self.is_selection_id(selection_id):
            raise Exception(f"The provided highlight id '{selection_id}' did not start with the highlight point prefix, cannot get point id.")
        return selection_id[len(SELECTION_POINT_ID_PREFIX):]
    

    def select_point(self, figure : go.Figure, point_x : float, point_y : float, point_id : str):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_ID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        
        selection_id = self.get_selection_id(point_id)
        self._add_point(selection_trace, selection_id, point_x, point_y)


    def deselect_point(self, figure : go.Figure, point_id : str):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_ID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        
        selection_id = self.get_selection_id(point_id)
        self._remove_point(selection_trace, selection_id)


    def deselect_all(self, figure : go.Figure):
        selection_trace = next((trace for trace in figure.data if trace.uid==SELECTION_TRACE_ID), None)
        if selection_trace is None:
            raise Exception("No selection trace was created upon creating the figure.")
        self._clear_trace(selection_trace)