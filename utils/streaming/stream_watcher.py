from typing import Iterable
from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher as DpStreamWatcher
import numpy as np
import pandas as pd
from stream_settings import *
from stream_interpreter import StreamInterpreter, StreamInterpreterTypeEnum

class StreamWatcher():
    __settings : StreamSettings
    __buffer_size : int
    
    feature_stream_watcher : DpStreamWatcher
    __feature_stream_interpreter : StreamInterpreter
    auxiliary_stream_watcher : DpStreamWatcher
    __auxiliary_stream_interpreter : StreamInterpreter

    __use_auxiliary_stream : bool = False
    __match_by_entry_id : bool = True

    def __init__(self, settings : StreamSettings):
        self.__settings = settings
        self.__use_auxiliary_stream = self.__use_auxiliary_stream()        
        self.__match_by_entry_id = self.__do_match_by_entry_id()

        buffer_size_s = settings.stream_buffer_size_s
        self.feature_stream_watcher = DpStreamWatcher(settings.feature_stream_name, buffer_size_s)
        self.__feature_stream_interpreter = StreamInterpreter(settings.feature_stream_layout, StreamInterpreterTypeEnum.Features)

        if self.__use_auxiliary_stream:
            self.auxiliary_stream_watcher = DpStreamWatcher(settings.auxiliary_stream_name, buffer_size_s)
            self.__auxiliary_stream_interpreter = StreamInterpreter(settings.auxiliary_stream_layout, StreamInterpreterTypeEnum.Labels)


    def __use_auxiliary_stream(self) -> bool:
        settings = self.__settings
        is_auxiliary_stream_identified = settings.auxiliary_stream_name is not None and len(settings.auxiliary_stream_name) > 0
        is_label_section_specified = settings.auxiliary_stream_layout.label_section is not None and len(settings.auxiliary_stream_layout.label_section) > 0
        return is_auxiliary_stream_identified and is_label_section_specified

    def __do_match_by_entry_id(self) -> bool:
        if self.__use_auxiliary_stream:
            return False
        
        feature_stream_has_ids = self.__settings.feature_stream_layout.id_index is not None
        auxiliary_stream_has_ids = self.__settings.auxiliary_stream_layout.id_index is not None
        return feature_stream_has_ids and auxiliary_stream_has_ids

    def connect_to_streams(self):
        try:
            self.feature_stream_watcher.connect_to_stream()
            if self.__use_auxiliary_stream:
                self.auxiliary_stream_watcher.connect_to_stream()

            self.__buffer_size = len(self.feature_stream_watcher.buffer)
        except Exception as e:
            self.feature_stream_watcher.inlet.value_type
            breakpoint()


    def read(self) -> tuple[pd.DataFrame, enumerate[float], enumerate[float]]:
        self.feature_stream_watcher.update()
        if self.__use_auxiliary_stream:
            self.auxiliary_stream_watcher.update()

        feature_data, feature_time_points = self.__read_stream_buffer(self.feature_stream_watcher)
        features, feature_data_ids = self.__feature_stream_interpreter.interpret(feature_data)

        if self.__use_auxiliary_stream:
            auxiliary_data, auxiliary_time_points = self.__read_stream_buffer(self.auxiliary_stream_watcher)
            labels, auxilaiary_data_ids = self.__auxiliary_stream_interpreter.interpret(auxiliary_data)
        else:
            self.feature_stream_watcher.n_new = 0
            return features, feature_time_points, None
        
        n_features_pre_matching = len(features)
        n_labels_pre_matching = len(labels)

        # match entries by id if possible, otherwise match entries by lsl time poitns
        if self.__match_by_entry_id:
            shared_entry_ids_or_indeces, features, time_points, labels =  self.__get_shared_features_by_id(features, feature_time_points, labels, feature_data_ids, auxilaiary_data_ids)
        else:
            shared_entry_ids_or_indeces, features, time_points, labels =  self.__get_shared_features_by_time_points(features, labels, feature_time_points, auxiliary_time_points)

        # check if all entries in the dpStreamWatcher buffers were matched
        if len(features) == n_features_pre_matching and len(labels) == n_labels_pre_matching:
            n_features_read = n_features_pre_matching
            n_labels_read = n_labels_pre_matching
        elif len(shared_entry_ids_or_indeces) == 0:
            n_features_read = 0
            n_labels_read = 0
        else:
            # do not just use the number of shared entries to update the stream watchers, this will break when there's an entry that is present in one stream but not the other
            feature_indeces = list(shared_entry_ids_or_indeces.values())
            label_indeces = list(shared_entry_ids_or_indeces.keys())

            n_features_read = feature_indeces[-1] - feature_indeces[0] + 1
            n_labels_read = label_indeces[-1] - label_indeces[0] + 1

        self.__update_buffer_trackers(self.feature_stream_watcher, n_features_read)
        self.__update_buffer_trackers(self.auxiliary_stream_watcher, n_labels_read)
        
        if labels is not None and len(labels) > 0 and isinstance(labels[0], Iterable):
            labels = np.concatenate(labels)

        return features, time_points, labels
    

    def __update_buffer_trackers(self, stream_watcher : DpStreamWatcher, n_entries_read : int):
        n_new = stream_watcher.n_new
        curr_i = stream_watcher.curr_i

        updated_n_new = n_new - n_entries_read
        if updated_n_new < 0:
            updated_n_new = 0
        updated_curr_i = (curr_i + n_entries_read) % self.__buffer_size

        stream_watcher.n_new = updated_n_new
        stream_watcher.curr_i = updated_curr_i


    def __read_stream_buffer(self, stream_watcher : DpStreamWatcher) -> tuple[pd.DataFrame|np.ndarray, float]:
        buffer = stream_watcher.buffer
        buffer_t = stream_watcher.buffer_t

        start_read = stream_watcher.curr_i
        n_to_read = stream_watcher.n_new
        end_read = start_read + n_to_read

        if n_to_read == 0:
            return [], []

        if end_read < self.__buffer_size:
            data = buffer[start_read:end_read]
            time_points = buffer_t[start_read:end_read]
        else:
            data = [buffer[start_read:], buffer[:(end_read % self.__buffer_size)]]
            time_points = [buffer_t[start_read:], buffer_t[:(end_read % self.__buffer_size)]]

            if isinstance(data[0], pd.DataFrame):
                data = pd.concat[data]
            else:
                data = np.concatenate((data[0], data[1]), axis=0)

            if isinstance(time_points[0], pd.DataFrame):
                time_points = pd.concat[time_points]
            else:
                time_points = np.concatenate((time_points[0], time_points[1]), axis=0)

        return data, time_points
    

    def __get_shared_features_by_id(self, features, time_points, labels, feature_ids, auxiliary_ids) -> tuple[list[int], pd.DataFrame, float, float|int]:
        shared_entry_ids = {i : i for i in feature_ids if i in auxiliary_ids}
        features = [features[i] for i in shared_entry_ids]
        time_points = [time_points[i] for i in shared_entry_ids]
        labels = [labels[i] for i in shared_entry_ids]
        return shared_entry_ids, features, time_points, labels
    

    def __get_shared_features_by_time_points(self, features, labels, feature_time_points, auxiliary_time_points) -> tuple[list[int], pd.DataFrame, float, float|int]:
        n_feature_entries = len(feature_time_points)
        auxiliary_stream_drift = self.__settings.auxiliary_stream_drift

        start_index = 0
        matching_indeces = {}
        for i, auxiliary_time_point in enumerate(auxiliary_time_points):
            adjusted_auxiliary_time_point = auxiliary_time_point - auxiliary_stream_drift
            smallest_dist_time = float('inf')
            smallest_j = start_index

            for j in range(start_index, n_feature_entries):
                dist_time = abs(adjusted_auxiliary_time_point - feature_time_points[j])
                if dist_time > smallest_dist_time:
                    break
                smallest_dist_time = dist_time
                smallest_j = j
            
            matching_indeces[i] = smallest_j
            start_index = smallest_j + 1
            if start_index >= n_feature_entries:
                break

        fetaure_indeces = list(matching_indeces.values())
        label_indeces = list(matching_indeces.keys())

        features = [features[i] for i in fetaure_indeces]
        time_points = [feature_time_points[i] for i in fetaure_indeces]
        labels = [labels[i] for i in label_indeces]
        return matching_indeces, features, time_points, labels