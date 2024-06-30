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
    stream_buffer_size_s : float = 1
    
    auxiliary_stream_drift : float = None

    feature_stream_layout : StreamLayout
    auxiliary_stream_layout : StreamLayout