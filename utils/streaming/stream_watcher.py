from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher as DpStreamWatcher
import pandas as pd
from stream_settings import *
from stream_interpreter import StreamInterpreter, StreamInterpreterTypeEnum

class StreamWatcher():
    __settings : StreamSettings
    __time_point_match_window : list[int]
    
    __feature_stream_watcher : DpStreamWatcher
    __feature_stream_interpreter : StreamInterpreter
    __auxiliary_stream_watcher : DpStreamWatcher
    __auxiliary_stream_interpreter : StreamInterpreter

    __use_auxiliary_stream : bool = False
    __match_by_entry_id : bool = True

    def __init__(self, settings : StreamSettings):
        self.__settings = settings
        self.__use_auxiliary_stream = self.__use_auxiliary_stream()        
        self.__match_by_entry_id = self.__do_match_by_entry_id()
        self.__set_time_point_match_window(settings.time_point_match_window_size)

        buffer_size_s = settings.stream_buffer_size_s
        self.__feature_stream_watcher = DpStreamWatcher(settings.feature_stream_name, buffer_size_s)
        self.__feature_stream_interpreter = StreamInterpreter(settings.feature_stream_layout, StreamInterpreterTypeEnum.Features)

        if self.__use_auxiliary_stream:
            self.__auxiliary_stream_watcher = DpStreamWatcher(settings.auxiliary_stream_name, buffer_size_s)
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

    def __set_time_point_match_window(self, match_window_size : int):
        if match_window_size % 2 == 0:
            match_window_size += 1
        self.__settings.time_point_match_window = match_window_size

        start = -(match_window_size // 2)
        end = match_window_size // 2 + 1
        match_window = list(range(start, end))
        self.__time_point_match_window = match_window
    

    def connect_to_streams(self):
        self.__feature_stream_watcher.connect_to_stream()
        if self.__use_auxiliary_stream:
            self.__auxiliary_stream_watcher.connect_to_stream()


    def read(self) -> tuple[pd.DataFrame, enumerate[float], enumerate[float]]:
        feature_data, feature_time_points = self.__read_stream_buffer(self.__feature_stream_watcher)
        features, feature_data_ids = self.__feature_stream_interpreter.interpret(feature_data)

        if self.__use_auxiliary_stream:
            auxiliary_data, auxiliary_time_points = self.__read_stream_buffer(self.__auxiliary_stream_watcher)
            labels, auxilaiary_data_ids = self.__auxiliary_stream_interpreter.interpret(auxiliary_data)
        else:
            self.__feature_stream_watcher.n_new = 0
            return features, feature_time_points, None
        
        n_features = len(features)
        n_labels = len(labels)

        # match entries by id if possible, otherwise match entries by lsl time poitns
        if self.__match_by_entry_id:
            shared_entry_ids_or_indeces, features, time_points, labels =  self.__get_shared_features_by_id(features, feature_time_points, labels, feature_data_ids, auxilaiary_data_ids)
        else:
            shared_entry_ids_or_indeces, features, time_points, labels =  self.__get_shared_features_by_time_points(features, labels, feature_time_points, auxiliary_time_points)

        # check if all entries in the dpStreamWatcher buffers were matched and set n_new accordingly
        if len(features) == n_features and len(labels) == n_labels:
            self.__feature_stream_watcher.n_new = 0
        else:
            # do not just use the number of shared entries to update the stream watchers, this will break when there's an entry that is present in one stream but not the other
            n_entries_read = shared_entry_ids_or_indeces[-1] - shared_entry_ids_or_indeces[0] + 1
            self.__feature_stream_watcher.n_new -= n_entries_read
            self.__auxiliary_stream_watcher.n_new -= n_entries_read
        
        return features, time_points, labels


    def __read_stream_buffer(self, stream_watcher : DpStreamWatcher) -> tuple[pd.DataFrame, float]:
        stream_watcher.update()
        data = stream_watcher.unfold_buffer()
        time_points = stream_watcher.unfold_buffer_t()
        return data, time_points
    

    def __get_shared_features_by_id(self, features, time_points, labels, feature_ids, auxiliary_ids) -> tuple[list[int], pd.DataFrame, float, float|int]:
        shared_entry_ids = [i for i in feature_ids if i in auxiliary_ids]
        features = [features[i] for i in shared_entry_ids]
        time_points = [time_points[i] for i in shared_entry_ids]
        labels = [labels[i] for i in shared_entry_ids]
        return shared_entry_ids, features, time_points, labels
    

    # Tries to match feature data and aux data by comparing a window of time stamps. A pairing is made based on the closest time stamps if the difference doesn't excete the maximum defined time drift.
    def __get_shared_features_by_time_points(self, features, labels, feature_time_points, auxiliary_time_points) -> tuple[list[int], pd.DataFrame, float, float|int]:
        chunk_size = len(feature_time_points)
        match_window = self.__time_point_match_window
        max_time_drift = self.__settings.max_time_drift

        matching_indeces = ()
        for i, feature_time_point in enumerate(feature_time_points):
            window_time_diffs = {} 

            for shift_j in match_window:
                j += shift_j
                if j < 0 or j >= chunk_size or j in matching_indeces.values():
                    continue
                
                auxiliary_time_point = auxiliary_time_points[j]
                window_time_diffs[j] = abs(auxiliary_time_point - feature_time_point)

            if len(window_time_diffs) == 0:
                continue 
            closest_fit = min(window_time_diffs.items(), key=lambda item: item[1])

            if closest_fit[1] > max_time_drift:
                continue
            matching_indeces = (i, closest_fit[i])

        fetaure_indeces = [t[0] for t in matching_indeces]
        label_indeces = [t[1] for t in matching_indeces]

        features = [features[i] for i in fetaure_indeces]
        time_points = [time_points[i] for i in fetaure_indeces]
        labels = [labels[i] for i in label_indeces]
        return matching_indeces, features, time_points, labels



