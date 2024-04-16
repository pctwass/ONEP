import numpy as np
import plotly.graph_objects as go
from pyparsing import Iterable

LEGEND_GROUP_TRACE_UID_PREFIX = "legend_group"

class PlotlyPlotSerivce():
    def get_trace_by_id(self, figure : go.Figure, uid : str) -> go.Scatter:
        return next((trace for trace in figure.data if trace.uid==uid), None)


    def _add_point(self, trace : go.Trace, point_id : str | float, point_x : float, point_y : float, point_text : str = None):
        trace.x = np.append(trace.x, point_x).tolist()
        trace.y = np.append(trace.y, point_y).tolist()
        trace.ids = np.append(trace.ids, point_id).tolist()
        if point_text is not None:
            trace.text = np.append(trace.text, point_text).tolist()
    

    def _remove_point(self, trace : go.Trace, point_id : str | float):
        point_index = next((index for index, id in enumerate(trace.ids) if id==point_id), None)
        if point_index is None:
            return 
        
        trace.x = np.delete(trace.x, point_index).tolist()
        trace.y = np.delete(trace.y, point_index).tolist()
        trace.ids = np.delete(trace.ids, point_index).tolist()
        if trace.text is not None and len(trace.text) > 0:
            trace.text = np.delete(trace.text, point_index).tolist()


    def _clear_trace(self, trace : go.Trace):
        trace.x = []
        trace.y = []
        trace.ids = []
        trace.text = []


    def _get_trace_text(self, point_ids : Iterable[str]) -> Iterable[str]:
        return [f"time: {time_point}" for time_point in point_ids]    
    

    def _get_legend_group_trace_uid(self, label : str) -> str:
        return f"{LEGEND_GROUP_TRACE_UID_PREFIX}_{label}"
    

    def _is_iterable_none_or_empty(self, iterable : Iterable):
        return iterable is None or len(iterable) < 1