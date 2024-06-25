class StreamSections:
    name : str
    length : int = 1
    interpretation = 'one-to-one'

class StreamLayout:
    id_index : int|str = "first"
    label_section :str = 'ground-truth-label'
    sections : dict[str, StreamSections] = {}

class StreamSettings:
    feature_stream_name : str
    auxiliary_stream_name : str
    stream_buffer_size_s : float = 1.0
    
    max_time_drift : float = 10**-5
    time_point_match_window_size : int = 3

    feature_stream_layout : StreamLayout
    auxiliary_stream_layout : StreamLayout

