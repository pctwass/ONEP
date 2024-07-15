class StreamSection:
    name : str
    start_index : int 
    length : int

class StreamLayout:
    id_index : int|str
    sections : dict[str, StreamSection] = {}

class StreamSettings:
    feature_stream_name : str
    auxiliary_stream_name : str
    stream_buffer_size_s : float = 1

    feature_section : str

    watch_labels : bool = True
    label_section : str
    labels_from_auxiliary_stream : bool = False
    label_interpretation_method = "one-to-one"
    
    match_by_entry_id = False
    label_feature_matching_scheme = "match-samples"

    auxiliary_stream_drift_ms : float = 0

    feature_stream_layout : StreamLayout
    auxiliary_stream_layout : StreamLayout