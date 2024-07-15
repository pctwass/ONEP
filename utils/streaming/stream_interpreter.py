import numpy as np
import pandas as pd
from enum import Enum
from stream_settings import *

class StreamInterpreterTypeEnum(Enum):
    Features = 1
    Auxiliary = 2
    Other = 3

class StreamInterpreter():
    _stream_settings : StreamSettings
    _stream_layout : StreamLayout
    _interpreter_type : StreamInterpreterTypeEnum
    _id_index : int 
    _interpret_labels : bool = False
    _label_interpretation_method : str

    _feature_section : StreamSection
    _label_section : StreamSection
    _contains_sample_index = False


    def __init__(self, stream_settings : StreamSettings, stream_layout : StreamLayout, interpreter_type : StreamInterpreterTypeEnum):
        self._stream_settings = stream_settings
        self._stream_layout = stream_layout
        self._interpreter_type = interpreter_type

        if isinstance(stream_layout.id_index, str):
            stream_layout.id_index = str.lower(stream_layout.id_index)

        if stream_layout.id_index is not None and stream_layout.id_index != '':
            self._contains_sample_index = True
            match stream_layout.id_index:
                case "first": self._id_index = 0
                case "last": self._id_index = -1
                case _: self._id_index = stream_layout.id_index 
        else:
            self._contains_sample_index = False

        if stream_settings.labels_from_auxiliary_stream and interpreter_type is StreamInterpreterTypeEnum.Auxiliary:
            self._interpret_labels = True
        elif not stream_settings.labels_from_auxiliary_stream and interpreter_type is StreamInterpreterTypeEnum.Features:
            self._interpret_labels = True

        if self._interpreter_type is StreamInterpreterTypeEnum.Features:
            self._feature_section = self._stream_layout.sections[self._stream_settings.feature_section]

        if self._interpret_labels:
            self._label_interpretation_method = stream_settings.label_interpretation_method
            self._label_section = self._stream_layout.sections[self._stream_settings.label_section]

    def interpret(self, stream_content : np.ndarray) -> tuple[enumerate[int], enumerate[any], enumerate[int|str]]:
        if stream_content is None or len(stream_content) == 0:
            return None, None, None
        
        ids = None
        if self._contains_sample_index:
            ids = stream_content[:, self._id_index]

        features = None
        if self._interpreter_type is StreamInterpreterTypeEnum.Features:
            start_index = self._feature_section.start_index
            features = stream_content[:, start_index : start_index + self._feature_section.length]

        labels = None
        if self._interpret_labels:
            start_index = self._label_section.start_index
            label_data = stream_content[:, start_index : start_index + self._label_section.length]
            labels = self._interpret_label_data(label_data)

        return ids, features, labels
        

    def _interpret_label_data(self, label_data : enumerate) -> enumerate:
        interpretation_method = self._stream_settings.label_interpretation_method
        match interpretation_method:
            case "one-to-one":
                labels = select_one_to_one(label_data)
            case "index of highest":
                labels = select_index_of_highest(label_data)
            case "index of lowest":
                labels = select_index_of_lowest(label_data)
            case _:
                raise Exception(f"stream interpretation exception: unknown interpretation method. Section: {self._stream_settings.label_section}, provided method: {interpretation_method}")
        
        return labels


# -------------- Interpretation Functions --------------

def select_one_to_one(stream_content_section : np.ndarray):
    if stream_content_section.shape[1] > 1:
        raise Exception(f"stream interpretation exception: 'one-to-one' mapping not possible, stream label section has more than one entry.")
    content = stream_content_section
    # reshape np.ndarray to a list
    return [item for sublist in content for item in sublist]

# NOTE: in the case of two or more columns having the highest value, the first column is selected
def select_index_of_highest(stream_content_section : np.ndarray):
    return np.argmax(stream_content_section, axis=1)

# NOTE: in the case of two or more columns having the lowest value, the first column is selected
def select_index_of_lowest(stream_content_section : np.ndarray):
    return np.argmin(stream_content_section, axis=1)