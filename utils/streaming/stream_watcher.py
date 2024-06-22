from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher as DpStreamWatcher
import pandas as pd
from stream_settings import *
from stream_interpreter import StreamInterpreter, StreamInterpreterTypeEnum

class StreamWatcher():
    __settings : StreamSettings
    
    __feature_stream_watcher : DpStreamWatcher
    __feature_stream_interpreter : StreamInterpreter
    __auxiliary_stream_watcher : DpStreamWatcher
    __auxiliary_stream_interpreter : StreamInterpreter

    __use_auxiliary_stream : bool = False
    __match_by_entry_id : bool = True

    def __init__(self, settings : StreamSettings):
        self.__settings = settings
        self.__use_auxiliary_stream = settings.auxiliary_section_to_label is not None and len(settings.auxiliary_section_to_label) > 0         
        self.__match_by_entry_id = self._do_match_by_entry_id(settings)

        buffer_size_s = settings.stream_buffer_size_s
        self.__feature_stream_watcher = DpStreamWatcher(settings.feature_stream_name, buffer_size_s)
        self.__feature_stream_interpreter = StreamInterpreter(settings.feature_stream_layout, StreamInterpreterTypeEnum.Features)

        if self.__use_auxiliary_stream:
            self.__auxiliary_stream_watcher = DpStreamWatcher(settings.auxiliary_stream_name, buffer_size_s)
            self.__auxiliary_stream_interpreter = StreamInterpreter(settings.auxiliary_stream_layout, StreamInterpreterTypeEnum.Labels)


    def _do_match_by_entry_id(self, settings : StreamSettings):
        if self.__use_auxiliary_stream:
            return False
        
        feature_stream_has_ids = settings.feature_stream_layout.id_as_first_index
        auxiliary_stream_has_ids = settings.auxiliary_stream_layout.id_as_first_index
        return feature_stream_has_ids and auxiliary_stream_has_ids


    def read(self) -> tuple[pd.DataFrame, enumerate[float], enumerate[float]]:
        feature_data, time_points = self._read_stream_buffer(self.__feature_stream_watcher)
        features, feature_data_ids = self.__feature_stream_interpreter.interpret(feature_data)

        if self.__use_auxiliary_stream:
            auxiliary_data, auxiliary_time_points = self._read_stream_buffer(self.__auxiliary_stream_watcher)
            labels, auxilaiary_data_ids = self.__auxiliary_stream_interpreter.interpret(auxiliary_data)
        else:
            self.__feature_stream_watcher.n_new = 0
            return features, time_points, None
        
        n_features = len(features)
        n_labels = len(labels)

        # match entries by id if possible, otherwise match entries by lsl time poitns
        if self.__match_by_entry_id:
            shared_entry_ids, features, time_points, labels =  self._get_shared_features_by_id(features, labels, feature_data_ids, auxilaiary_data_ids)
        else:
            # TODO: match by time point
            shared_entry_ids, features, time_points, labels =  self._get_shared_features_by_id(features, labels, feature_data_ids, auxilaiary_data_ids)

        # check if all entries in the dpStreamWatcher buffers were matched and set n_new accordingly
        if len(features) == n_features and len(labels) == n_labels:
            self.__feature_stream_watcher.n_new = 0
        else:
            # do not just use the number of shared entries to update the stream watchers, this will break when there's an entry that is present in one stream but not the other
            n_entries_read = shared_entry_ids[-1] - shared_entry_ids[0] + 1
            self.__feature_stream_watcher.n_new -= n_entries_read
            self.__auxiliary_stream_watcher.n_new -= n_entries_read
        
        return features, time_points, labels


    def _read_stream_buffer(self, stream_watcher : DpStreamWatcher) -> tuple[pd.DataFrame, float]:
        stream_watcher.update()
        data = stream_watcher.unfold_buffer()
        time_points = stream_watcher.unfold_buffer_t()
        return data, time_points
    

    def _get_shared_features_by_id(features, time_points, labels, feature_ids, auxiliary_ids) -> tuple[list[int], pd.DataFrame, float, float|int]:
        shared_entry_ids = [i for i in feature_ids if i in auxiliary_ids]
        features = [features[i] for i in shared_entry_ids]
        time_points = [time_points[i] for i in shared_entry_ids]
        labels = [labels[i] for i in shared_entry_ids]
        return shared_entry_ids, features, time_points, labels
