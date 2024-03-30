import copy
from dash import Dash, html, dcc, no_update
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform, callback_context as ctx

import logging
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import matplotlib
matplotlib.use('agg')

from projector.projector_continues_shell import ProjectorContinuesShell
from projector.main_projector import Projector
from projector.projector_plot_manager import ProjectorPlotManager
from dashboard.dahsboard_settings import DashboardSettings
from dashboard.dashboard_layout import DashboardLayout


_self = None
_plot_figure : go.Figure = no_update
_registered_projectors : dict[str, Projector | ProjectorContinuesShell] = {}
_active_projector : Projector = None
_active_plot_manager : ProjectorPlotManager = None
_model_iteration_plotted : str = 0


class Dashboard():
    _settings : DashboardSettings = DashboardSettings()
    _plot_aspect_ratio : float = None

    _paused_processes : dict[str, bool] = {
    "plot-refresh" : False,
    "projecting" : False,
    "projector-updating" : False
    }
    _paused_processes_retained : dict[str, bool]
    

    def __init__(self, settings : DashboardSettings) -> None:
        logger = logging.getLogger("werkzeug")
        logger.setLevel(logging.WARNING)

        global _settings
        _settings = settings

        global _layout
        self.app.layout = DashboardLayout(settings).get_layout()

        global _self 
        _self = self

        self._paused_processes_retained = copy.copy(self._paused_processes)


    # NOTE Multiple callbacks for single output: https://community.plotly.com/t/multiple-callbacks-for-an-output/51247
    app = DashProxy(__name__, prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    app.logger.setLevel(logging.WARNING)
    app.layout = dbc.Container()


    app.clientside_callback(
        """
        function() {
            var graph = document.getElementById("model-plot");
            var width = graph.offsetWidth;
            var height = graph.offsetHeight;
            return [width, height];
        }
        """,
        Output('plot-size-hidden-div', 'children'),
        Input('model-plot', 'id'),
        prevent_initial_call=False
    )


    @app.callback(
        Output('model-plot', 'figure'),
        Input('plot-size-hidden-div', 'children'),
        prevent_initial_call=False
    )
    def note_plot_aspect_ratio(plot_size):
        if _active_plot_manager is None:
            no_update

        plot_width = plot_size[0]
        plot_height = plot_size[1]
        plot_aspect_ratio = plot_width / plot_height
        _active_plot_manager.refresh_axis_range(plot_aspect_ratio)
        return no_update
        

# ---------------------- app mode, pausing, and refreshing ----------------------
    @app.callback(
        Output('model-plot', 'figure'),
        Input('refresh-graph-interval', 'n_intervals'),
    )
    def refresh_graph_interval(n_intervals):
        return _self._refresh_plot()
    

    @app.callback(
        [Output('application-mode-label', 'children'),
        Output('run-pause-projecting-button', 'className'),
        Output('run-pause-projecting-button', 'disabled'),
        Output('run-pause-updating-button', 'className'),
        Output('run-pause-updating-button', 'disabled'),
        Output('refresh-graph-interval', 'disabled')],
        Input('application-mode-switch', 'on')
    )
    def toggle_application_mode(toggle_on_state):
        if _active_projector_shell is None:
            if toggle_on_state:
                return "Interactive", "button-disabled", True, "button-disabled", True, True                                            
            return "Projecting", "button", False, "button", False, False

        if toggle_on_state: # implies mode is 'interactive'
            # retain if process is paused
            _self._paused_processes_retained["projecting"] = _self._paused_processes["projecting"]
            _self._paused_processes_retained["projector-updating"] = _self._paused_processes["projector-updating"]

            # pause processes
            _self._paused_processes["projecting"] = True
            _self._paused_processes["projector-updating"] = True
            _active_projector_shell.pause_projecting()
            _active_projector_shell.pause_updating_projector()

            return "Interactive", "button-disabled", True, "button-disabled", True, True                                            

        projecting_retained_pause_state = _self._paused_processes_retained["projecting"]
        _self._paused_processes["projecting"] = projecting_retained_pause_state
        if not projecting_retained_pause_state:
            _active_projector_shell.unpause_projecting()

        updating_retained_pause_state = _self._paused_processes_retained["projector-updating"]
        _self._paused_processes["projector-updating"] = updating_retained_pause_state
        if not updating_retained_pause_state:
            _active_projector_shell.unpause_updating_projector()

        return "Projecting", "button", False, "button", False, False


    @app.callback(
        [Output('run-pause-projecting-button', 'children'),
        Output('run-pause-updating-button', 'children')],
        Input('refresh-run-pause-button-text-interval', 'n_intervals'),
    )
    def set_run_pause_button_text(n_intervals):
        if _self._paused_processes["projecting"]:
            projecting_button_text = "Resume"
        else: projecting_button_text = "Pause"
        if _self._paused_processes["projector-updating"]:
            projector_updating_button_text = "Resume"
        else: projector_updating_button_text = "Pause"

        return projecting_button_text, projector_updating_button_text
    

    @app.callback(
        [Output('run-pause-projecting-button', 'n_clicks')],
        [Input('run-pause-projecting-button', 'n_clicks')],
    )
    def toggle_projecting_pausing(n_clicks):
        if _active_projector_shell is None:
            return n_clicks

        if _self._paused_processes["projecting"]:
            _self._paused_processes["projecting"] = False
            _active_projector_shell.unpause_projecting()
        else:
            _self._paused_processes["projecting"] = True
            _active_projector_shell.pause_projecting()

        return n_clicks
    

    @app.callback(
        [Output('run-pause-updating-button', 'n_clicks')],
        [Input('run-pause-updating-button', 'n_clicks')],
    )
    def toggle_updating_projector_pausing(n_clicks):
        if _active_projector_shell is None:
            return n_clicks

        if _self._paused_processes["projector-updating"]:
            _self._paused_processes["projector-updating"] = False
            _active_projector_shell.unpause_updating_projector()
        else:
            _self._paused_processes["projector-updating"] = True
            _active_projector_shell.pause_updating_projector()

        return n_clicks
    

# ---------------------- model iterations and update trigger ----------------------
    @app.callback(
        [Output('projection-model-curr-iteration', 'children'),
        Output('projection-model-latest-iteration', 'children'),
        Output('plot-new-model-button', 'disabled'),
        Output('plot-new-model-button', 'className')],
        Input('refresh-model-iteration-interval', 'n_intervals'),
    )
    def refresh_latest_available_model_iteration_display(n_intervals):
        global _model_iteration_plotted
        if _active_projector is None:
            return _model_iteration_plotted, _model_iteration_plotted, True, "button-disabled"

        latest_iteration = _active_projector.update_counter
        # account for projector automatically assigning the first model itteration
        if latest_iteration == 1:
            _model_iteration_plotted = latest_iteration

        if latest_iteration > _model_iteration_plotted:
            return _model_iteration_plotted, latest_iteration, False, "button"
        else:
            return _model_iteration_plotted, latest_iteration, True, "button-disabled"
    

    @app.callback(
        [Output('plot-new-model-button', 'disabled'),
        Output('plot-new-model-button', 'className'),
        Output('model-plot', 'figure')],
        Input('plot-new-model-button', 'n_clicks'),
    )
    def plot_new_model_iteration(n_clicks):
        latest_iteration = _active_projector.update_counter
        _active_projector.activate_latest_projector()

        global _model_iteration_plotted
        _model_iteration_plotted = latest_iteration

        plot_update = _self._refresh_plot()
        return True, "button-disabled", plot_update


# ---------------------- selection, highlighting, label assignment ----------------------
    @app.callback(
        [Output('selected-points-count-value', 'children'),
        Output('label-selection-dropdown', 'disabled'),
        Output('point-labeling-submit-button', 'disabled'),
        Output('point-labeling-submit-button', 'className'),
        Output('selection-highlight-button', 'disabled'),
        Output('selection-highlight-button', 'className'),
        Output('selection-dehighlight-button', 'disabled'),
        Output('selection-dehighlight-button', 'className'),
        Output('model-plot', 'figure')],
        [Input('model-plot', 'clickData')],
    )
    def select_data_point(click_data):
        num_selected_points = _active_plot_manager.get_count_selected_points()
        if click_data is None:
            if num_selected_points > 1:
                return num_selected_points, False, False, "button", False, "button", False, "button", no_update
            else:
                return num_selected_points, True, True, "button-disabled", True, "button-disabled", True, "button-disabled", no_update

        point = click_data['points'][0]
        point_id = point['id']

        if _active_plot_manager.is_selected_point(point_id):
            _active_plot_manager.deselect_point(point_id)
            
            plot_update = _self._refresh_plot()
            if num_selected_points <= 1:
                return num_selected_points-1, True, True, "button-disabled", True, "button-disabled", True, "button-disabled", plot_update
            return num_selected_points-1, False, False, "button", False, "button", False, "button", plot_update

        x = point['x']
        y = point['y']
        _active_plot_manager.select_point(point_id, x, y)

        plot_update = _self._refresh_plot()
        return num_selected_points+1, False, False, "button", False, "button", False, "button", plot_update
    

    @app.callback(
        [Output('selected-points-count-value', 'children'),
        Output('label-selection-dropdown', 'disabled'),
        Output('point-labeling-submit-button', 'disabled'),
        Output('point-labeling-submit-button', 'className'),
        Output('selection-highlight-button', 'disabled'),
        Output('selection-highlight-button', 'className'),
        Output('selection-dehighlight-button', 'disabled'),
        Output('selection-dehighlight-button', 'className'),
        Output('model-plot', 'figure')],
        [Input('model-plot', 'selectedData')],
    )
    def select_data_points(selected_data):
        for point in selected_data['points']:
            if 'id' not in point or point['id'] is None:
                continue

            point_id = point['id']
            x = point['x']
            y = point['y']
            _active_plot_manager.select_point(point_id, x, y)
        
        plot_update = _self._refresh_plot()
        num_selected_points = _active_plot_manager.get_count_selected_points()
        if num_selected_points > 1:
            return num_selected_points, False, False, "button", False, "button", False, "button", plot_update
        else:
            return num_selected_points, True, True, "button-disabled", True, "button-disabled", True, "button-disabled", plot_update

    @app.callback(
        [Output('selected-points-count-value', 'children'),
        Output('label-selection-dropdown', 'disabled'),
        Output('point-labeling-submit-button', 'disabled'),
        Output('point-labeling-submit-button', 'className'),
        Output('selection-highlight-button', 'disabled'),
        Output('selection-highlight-button', 'className'),
        Output('selection-dehighlight-button', 'disabled'),
        Output('selection-dehighlight-button', 'className'),
        Output('model-plot', 'figure')],
        Input('point-selection-clear-button', 'n_clicks'),
    )
    def clear_selected_datapoints(n_clicks):
        _active_plot_manager.deselect_all()
        plot_update = _self._refresh_plot()
        return 0, True, True, "button-disabled", True, "button-disabled", True, "button-disabled", plot_update

    
    @app.callback(
        Output('label-selection-dropdown', 'options'),
        Input('label-selection-dropdown', 'disabled'),
    )
    def sync_label_selection_dropdown_options(disabled):
        return _active_plot_manager.get_labels()
    

    @app.callback(
        [Output('point-labeling-submit-button', 'n_clicks'),
        Output('model-plot', 'figure')],
        [Input('label-selection-dropdown', 'value'),
        Input('point-labeling-submit-button', 'n_clicks')],
    )
    def assign_label(new_label, n_clicks):
        triggered_id = ctx.triggered[0]['prop_id']
        if triggered_id != 'point-labeling-submit-button.n_clicks':
            return n_clicks, no_update

        _active_plot_manager.update_selected_points_label(new_label)
        for point_id in _active_plot_manager.get_selected_point_ids():
            _active_projector.update_label(point_id, new_label)
        plot_update = _self._refresh_plot()
        return n_clicks, plot_update
    

    @app.callback(
        [Output('selection-highlight-button', 'n_clicks'),
        Output('model-plot', 'figure')],
        Input('selection-highlight-button', 'n_clicks'),
    )
    def highlight_selected(n_clicks):
        _active_plot_manager.highlight_selected()
        plot_update = _self._refresh_plot()
        return n_clicks, plot_update

    @app.callback(
        [Output('selection-dehighlight-button', 'n_clicks'),
        Output('model-plot', 'figure')],
        Input('selection-dehighlight-button', 'n_clicks'),
    )
    def dehighlight_selected(n_clicks):
        _active_plot_manager.dehighlight_selected()
        plot_update = _self._refresh_plot()
        return n_clicks, plot_update
    
    @app.callback(
        [Output('clear-all-highlight-button', 'n_clicks'),
        Output('model-plot', 'figure')],
        Input('clear-all-highlight-button', 'n_clicks'),
    )
    def dehighlight_all(n_clicks):
        _active_plot_manager.dehighlight_all()
        plot_update = _self._refresh_plot()
        return n_clicks, plot_update


    def register_projector(self, projector : Projector | ProjectorContinuesShell):
        _registered_projectors[projector.id] = projector

    def set_active_projector(self, projector_id : str):
        global _active_projector_shell
        global _active_projector
        global _active_plot_manager
        global _model_iteration_plotted

        _active_projector_shell = None
        target_projector = _registered_projectors[projector_id]
        if isinstance(target_projector, ProjectorContinuesShell):
            _active_projector_shell =  target_projector
            target_projector = target_projector.get_projector()

        _active_projector = target_projector
        _active_plot_manager = target_projector.get_plot_manager()
        _model_iteration_plotted = target_projector.update_counter


    def _refresh_plot(self):
        if _active_plot_manager is None:
            return no_update
        
        global _plot_figure
        _plot_figure = _active_plot_manager.get_plot()
        return _plot_figure