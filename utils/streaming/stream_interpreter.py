import numpy as np
import pandas as pd
from enum import Enum
from stream_settings import *

class StreamInterpreterTypeEnum(Enum):
    Features = 1
    Labels = 2
    Other = 3

class StreamInterpreter():
    __stream_layout : StreamLayout
    __interpreter_type : StreamInterpreterTypeEnum
    __id_index : int 

    def __init__(self, stream_layout : StreamLayout, interpreter_type : StreamInterpreterTypeEnum):
        self.__stream_layout = stream_layout
        self.__interpreter_type = interpreter_type

        if isinstance(stream_layout.id_index, str):
            stream_layout.id_index = str.lower(stream_layout.id_index)

        match stream_layout.id_index:
            case "first": self.__id_index = 0
            case "last": self.__id_index = -1
            case "": self.__id_index = None
            case _: self.__id_index = stream_layout.id_index 


    def interpret(self, stream_content : np.ndarray) -> tuple[any, int]:
        match self.__interpreter_type:
            case StreamInterpreterTypeEnum.Features:
                return self._interpret_feature_stream(stream_content)
            case StreamInterpreterTypeEnum.Labels:
                return self._interpret_auxiliary_stream(stream_content)
            case _:
                raise Exception("stream interpretation exception: unknown interpreter type")
        

    def _interpret_feature_stream(self, stream_content : np.ndarray) -> tuple[any, int]:
        if self.__id_index is not None:
            id_index = stream_content[:, self.__id_index]
            stream_content = np.delete(stream_content, self.__id_index, axis=1)
            return stream_content, id_index
        return stream_content, None
    

    def _interpret_auxiliary_stream(self, stream_content : np.ndarray) -> tuple[any, int]:
        if self.__id_index is not None:
            id_index = stream_content[:, self.__id_index]
            stream_content = np.delete(stream_content, self.__id_index, axis=1)
        else:
            id_index = None

        start_index, end_index = self._get_target_section_start_and_end_index()
        label_data = stream_content[:, start_index:end_index]

        stream_section = self.__stream_layout.sections[self.__stream_layout.label_section]
        match stream_section.interpretation:
            case "one-to-one":
                if label_data.shape[1] > 1:
                    raise Exception(f"stream interpretation exception: 'one-to-one' mapping not possible, stream label section has more than one entry. Section: {self.__stream_layout.label_section}")
                labels = label_data
            case "index of highest":
                labels = self._select_index_of_highest(label_data)
            case "index of lowest":
                labels = self._select_index_of_lowest(label_data)
            case _:
                raise Exception(f"stream interpretation exception: unknown interpretation method. Section: {self.__stream_layout.label_section}, provided method: {stream_section.interpretation}")
            
        return labels, id_index


    def _get_target_section_start_and_end_index(self) -> tuple[int, int]:
        target_section = self.__stream_layout.label_section

        start_index = 0
        for section in self.__stream_layout.sections.values():
            if section.name == target_section:
                return start_index, start_index + section.length
            start_index += section.length
        
        raise Exception("Stream interpreter exception: could not find target section")


# -------------- Interpretation Functions --------------

    # NOTE: in the case of two or more columns having the highest value, the first column is selected
    def _select_index_of_highest(stream_content_section : np.ndarray):
        return np.argmax(stream_content_section, axis=1)

    # NOTE: in the case of two or more columns having the lowest value, the first column is selected
    def _select_index_of_lowest(stream_content_section : np.ndarray):
        return np.argmin(stream_content_section, axis=1)