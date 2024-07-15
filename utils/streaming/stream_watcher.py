from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher as DpStreamWatcher
import numpy as np
import pandas as pd
from stream_settings import *
from stream_interpreter import StreamInterpreter, StreamInterpreterTypeEnum
from stream_matcher import StreamMatcher

class StreamWatcher():
    _settings : StreamSettings
    _get_labels_from_auxiliary_stream : bool = False
    _steam_matcher : StreamMatcher

    feature_stream_watcher : DpStreamWatcher
    _feature_stream_interpreter : StreamInterpreter
    auxiliary_stream_watcher : DpStreamWatcher
    _auxiliary_stream_interpreter : StreamInterpreter


    def __init__(self, settings : StreamSettings):
        self._settings = settings
        self._get_labels_from_auxiliary_stream = settings.watch_labels and settings.labels_from_auxiliary_stream        
        self._validate_stream_settings(settings)

        buffer_size_s = settings.stream_buffer_size_s
        self.feature_stream_watcher = DpStreamWatcher(settings.feature_stream_name, buffer_size_s)
        self._feature_stream_interpreter = StreamInterpreter(settings, settings.feature_stream_layout, StreamInterpreterTypeEnum.Features)

        if self._get_labels_from_auxiliary_stream:
            if settings.auxiliary_stream_name is None or settings.auxiliary_stream_name == "":
                raise Exception(f"Stream Exception: ")
            
            self._steam_matcher = StreamMatcher(settings)
            self.auxiliary_stream_watcher = DpStreamWatcher(settings.auxiliary_stream_name, buffer_size_s)
            self._auxiliary_stream_interpreter = StreamInterpreter(settings, settings.auxiliary_stream_layout, StreamInterpreterTypeEnum.Auxiliary)


    def _validate_stream_settings(self, settings : StreamSettings):
        if settings.feature_stream_name is None or settings.feature_stream_name == "":
            raise Exception("Stream Exception: the feature stream name is empty.")
        if settings.feature_section is None or settings.feature_section == "":
            raise Exception("Stream Exception: no feature section is specified.")
        
        if settings.watch_labels:
            if settings.label_section is None or settings.label_section == "":
                raise Exception("Stream Exception: asked to watch for labels, but no label section is specified.")
            if settings.label_interpretation_method is None or settings.label_interpretation_method == "":
                raise Exception("Stream Exception: asked to watch for labels, but no label interpretation method is specified.")
        
        if self._get_labels_from_auxiliary_stream:
            if settings.auxiliary_stream_name is None or settings.auxiliary_stream_name == "":
                raise Exception("Stream Exception: asked to watch for labels from auxiliary stream, but the auxiliary stream name is empty.")
            if settings.label_feature_matching_scheme is None or settings.label_feature_matching_scheme == "":
                raise Exception("Stream Exception: asked to watch for labels from auxiliary stream, but no matching scheme specified to relate the labels to the features.")
            
            if settings.match_by_entry_id:
                if settings.feature_stream_layout.id_index is None or settings.feature_stream_layout.id_index == "":
                    raise Exception("Stream Exception: asked to match features and labels using ids, but no index for the ids is specified for the feature stream.")
                if settings.auxiliary_stream_layout.id_index is None or settings.auxiliary_stream_layout.id_index == "":
                    raise Exception("Stream Exception: asked to match features and labels using ids, but no index for the ids is specified for the auxiliary stream.")

    def connect_to_streams(self):
        try:
            self.feature_stream_watcher.connect_to_stream()
            if self._get_labels_from_auxiliary_stream:
                self.auxiliary_stream_watcher.connect_to_stream()

            self._buffer_size = len(self.feature_stream_watcher.buffer)
        except Exception as e:
            self.feature_stream_watcher.inlet.value_type


    def read(self) -> tuple[np.ndarray, enumerate[float], enumerate[float]]:
        feature_data, feature_time_points = self._read_stream_buffer(self.feature_stream_watcher)
        if feature_data is None or len(feature_data) == 0:
            return None, None, None
        feature_data_ids, features, labels = self._feature_stream_interpreter.interpret(feature_data)
    
        if not self._get_labels_from_auxiliary_stream:
            self._update_buffer_trackers(self.feature_stream_watcher, n_entries_read=len(features))
            return features, feature_time_points, labels

        auxiliary_data, auxiliary_time_points = self._read_stream_buffer(self.auxiliary_stream_watcher)
        if auxiliary_data is None or len(auxiliary_data) == 0:
            return None, None, None
        auxilaiary_data_ids, _, labels = self._auxiliary_stream_interpreter.interpret(auxiliary_data)
        
        n_features_pre_matching = len(features)
        n_labels_pre_matching = len(labels)

        # match entries by id if possible, otherwise match entries by lsl time poitns
        if self._settings.match_by_entry_id:
            matched_indeces, features, time_points, labels =  self._steam_matcher.get_shared_features_by_id(features, feature_time_points, labels, feature_data_ids, auxilaiary_data_ids)
        else:
            matched_indeces, features, time_points, labels =  self._steam_matcher.get_shared_features_by_time_points(features, labels, feature_time_points, auxiliary_time_points)

        if matched_indeces is None or len(matched_indeces) == 0:
            return None, None, None

        # check if all entries in the dpStreamWatcher buffers were matched
        if len(matched_indeces) == 0:
            n_features_read = 0
            n_labels_read = 0
        elif len(features) == n_features_pre_matching and len(labels) == n_labels_pre_matching:
            n_features_read = n_features_pre_matching
            n_labels_read = n_labels_pre_matching
        else:
            # do not just use the number of shared entries to update the stream watchers, this will break when there's an entry that is present in one stream but not the other
            n_features_read = max(matched_indeces, key=lambda x: x[0])[0] + 1
            n_labels_read = max(matched_indeces, key=lambda x: x[1])[1] + 1

        self._update_buffer_trackers(self.feature_stream_watcher, n_features_read)
        self._update_buffer_trackers(self.auxiliary_stream_watcher, n_labels_read)
        
        return features, time_points, labels
    

    def _update_buffer_trackers(self, stream_watcher : DpStreamWatcher, n_entries_read : int):
        n_new = stream_watcher.n_new
        curr_i = stream_watcher.curr_i

        updated_n_new = n_new - n_entries_read
        if updated_n_new < 0:
            updated_n_new = 0
        updated_curr_i = (curr_i + n_entries_read) % self._buffer_size

        stream_watcher.n_new = updated_n_new
        stream_watcher.curr_i = updated_curr_i


    def _read_stream_buffer(self, stream_watcher : DpStreamWatcher) -> tuple[np.ndarray, float]:
        stream_watcher.update()

        buffer = stream_watcher.buffer
        buffer_t = stream_watcher.buffer_t

        start_read = stream_watcher.curr_i
        n_to_read = stream_watcher.n_new
        end_read = start_read + n_to_read

        if n_to_read == 0:
            return None, None

        if end_read < self._buffer_size:
            data = buffer[start_read:end_read]
            time_points = buffer_t[start_read:end_read]
        else:
            data = [buffer[start_read:], buffer[:(end_read % self._buffer_size)]]
            time_points = [buffer_t[start_read:], buffer_t[:(end_read % self._buffer_size)]]
            data = np.concatenate((data[0], data[1]), axis=0)
            time_points = np.concatenate((time_points[0], time_points[1]), axis=0)

        return data, time_points
