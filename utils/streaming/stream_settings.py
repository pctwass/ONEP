class StreamSections:
    name : str
    length : int = 1
    data_typing = float
    interpretation = 'one-to-one'

class StreamLayout:
    id_index : int|str = "first"
    data_typing = float
    label_section :str = 'ground-truth-label'
    sections : dict[str, StreamSections] = {}

class StreamSettings:
    feature_stream_name : str
    auxiliary_stream_name : str
    stream_buffer_size_s : float = 1.0

    feature_stream_layout : StreamLayout
    auxiliary_stream_layout : StreamLayout

