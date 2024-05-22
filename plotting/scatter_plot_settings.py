class ScatterPlotSettings:
    labels : list[str]
    color_map : dict[str,str]
    initial_opacity : float
    opacity_set : list[float] | None

    selection_border_size : float
    selection_border_color : str

    highlight_size : float
    highlight_border_size : float
    highlight_border_color : str

    show_axis : bool
    xaxis_range : range
    yaxis_range : range
    xaxis_step_size : float
    yaxis_step_size : float

    transition_duration : int

    
    def __init__(self,
        labels : list[str],
        color_map : dict[str,str],
        initial_opacity : float = 1,
        opacity_set : list[float] | None = None,
        selection_border_size : float = 0.8,
        selection_border_color : str = 'gray',
        highlight_size : float = 10,
        highlight_border_size : float= 1,
        highlight_border_color : str = 'DarkSlateGrey',
        show_axis : bool = False,
        xaxis_range : range = None,
        yaxis_range : range = None,
        xaxis_step_size : float = 0.2,
        yaxis_step_size : float = 0.2,
        transition_duration : int = 500
    ):
        self.labels = labels
        self.color_map = color_map
        self.initial_opacity = initial_opacity
        self.opacity_set = opacity_set
        self.selection_border_size = selection_border_size
        self.selection_border_color = selection_border_color
        self.highlight_size = highlight_size
        self.highlight_border_size = highlight_border_size
        self.highlight_border_color = highlight_border_color
        self.show_axis = show_axis
        self.xaxis_range = xaxis_range
        self.yaxis_range = yaxis_range
        self.xaxis_step_size = xaxis_step_size
        self.yaxis_step_size = yaxis_step_size
        self.transition_duration = transition_duration

