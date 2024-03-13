class PlotSettings():
    labels : list[str] = ['one', 'two', 'three', 'four']
    unclassified_label : str = 'unclassified'
    label_colors : dict[str, str] = { 'one' : 'blue', 'two' : 'red', 'three' : 'green'}
    unclassified_label_color : str = 'gray'

    scatter_point_size : float = 6
    point_selection_border_size : float = 2
    point_selection_border_color : str = 'DarkSlateGrey'
    point_highlight_size : float = 10
    point_highlight_border_size : float = 1
    point_highlight_border_color : str = 'DarkSlateGrey'

    min_opacity : float = 0.25
    opacity_thresholds : dict[float, float] = {
        1.0 : 5,
        0.75 : 5,
        0.5 : 5,
    }

    show_axis : bool = False
    xaxis_range : range | None =  None
    yaxis_range : range | None =  [-0.2, 1.2]
    xaxis_step_size : float = 0.2
    yaxis_step_size : float = 0.2
    axis_aspect_ratio : float = None

    transition_duration : int = 500 # in ms