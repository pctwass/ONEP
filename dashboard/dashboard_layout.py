from dash import html, dcc
import dash_bootstrap_components as dbc 
import dash_daq as daq
from dashboard.dahsboard_settings import DashboardSettings


class DashboardLayout():
    _settings : DashboardSettings
    
    def __init__(self, settings : DashboardSettings):
        self._settings = settings

    def get_layout(self):
        return dbc.Container([
            html.Link(
                rel='stylesheet',
                href='./assets/styling.css'
            ),

            html.Div(className="graph-column", id="graph-column",
                children=[
                    dcc.Interval(id="refresh-graph-interval", disabled=False, interval=self._settings.graph_refresh_rate_per_ms),
                    dcc.Graph(className='graph', id='model-plot', figure={}, config={'staticPlot': False}),
                    html.Div(id="plot-size-hidden-div", style={'display': 'none'})
                ]
            ),

            html.Div(className="interface-column",
                children=[
                    html.Div(className="application-mode-container", id="application-mode-container", children=[
                        html.H3("Toggle application mode."),
                        html.Div(className="flex-div", children=[
                            daq.BooleanSwitch(
                                id="application-mode-switch",
                                on=False,
                                color="#E6E6E6",
                                persistence=True
                            ),
                            html.Div("Current mode:", className="text"),
                            html.Div("Projecting", className="application-mode-label", id="application-mode-label"),
                        ]),
                    ]),
                    


                    html.Div(className="interface-section-container", children=[
                        dcc.Interval(id="refresh-run-pause-button-text-interval", disabled=False, interval=100),

                        html.H3("Toggle a process to pause or resume.", className="primary-buttons-h3"),
                        html.Div(className="flex-div", children=[
                            html.Div(className="primary-buttons-text-column", children=[
                            html.Div("Projecting", className="primary-buttons-text-row"),
                            html.Div("Model updating", className="primary-buttons-text-row"),
                            ]),

                            html.Div(className="primary-buttons-button-column", children=[
                                html.Div(className="primary-buttons-button-row", children=[html.Button('Pause', className='button', id='run-pause-projecting-button', n_clicks=0)]),
                                html.Div(className="primary-buttons-button-row", children=[html.Button('Pause', className='button', id='run-pause-updating-button', n_clicks=0)]),
                            ]),
                        ]),
                    ]),

                    html.Div(className="interface-section-container", children=[
                        html.H3("Projector model iterations."),
                        dcc.Interval(id="refresh-model-iteration-interval", disabled=False, interval=100), 

                        html.Div([
                            html.Div("Currently plotted", className="text"),
                            html.Div("0", className="pmu-value", id="projection-model-curr-iteration"),
                        ], className="projection-model-updating-subcontainer"),

                        html.Div([
                            html.Div("Latest available", className="text"),
                            html.Div("0", className="pmu-value", id="projection-model-latest-iteration"),
                        ], className="projection-model-updating-subcontainer"),

                        html.Button("Update Displayed Model", className="button-disabled", disabled=True, id="plot-new-model-button")
                    ]),

                    html.Div(className="interface-section-container", children=[
                        html.H3("Select a point in the graph to set its label."),

                        html.Div([
                            html.Div("Number of selected points :", className="text"),
                            html.Div("0", id="selected-points-count-value", className="psc-value"),
                        ], className="point-selection-subcontainer-small-margin"),

                        html.Div([
                            html.Button("Clear Selection", className="button", id="point-selection-clear-button")
                        ], className="point-selection-subcontainer"),

                        html.Div("Set new Label", className="text"),
                        html.Div([
                            dcc.Dropdown(
                                options=[],
                                id = "label-selection-dropdown",
                                className="psc-label-selection-dropdown",
                                disabled=True,
                            ),
                            html.Button("Submit", className="button-disabled", id="point-labeling-submit-button", disabled=True)
                        ], className="point-selection-subcontainer"),

                        html.Div([
                            html.Button("Highlight", className="button-disabled", id="selection-highlight-button", disabled=True),
                            html.Button("Remove Highlight", className="button-disabled", id="selection-dehighlight-button", disabled=True),
                            html.Button("Clear All Highlight", className="button-dangerous", id="clear-all-highlight-button")
                        ], className="point-selection-subcontainer"),
                    ]),
                ]
            ),
        ])