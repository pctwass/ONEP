import numpy as np
from utils.streaming.stream_settings import *

class StreamMatcher():
    _label_matching_scheme : str
    _auxiliary_stream_drift : float = 0

    _last_matched_label = None
    _last_matched_label_id = None
    _last_matched_label_timestamp = None

    def __init__(self, stream_settings : StreamSettings):
        self._label_matching_scheme = stream_settings.label_feature_matching_scheme
        self._auxiliary_stream_drift = stream_settings.auxiliary_stream_drift_ms

# -------------------------------- entry id matching --------------------------------
    def get_shared_features_by_id(self, features : np.ndarray, time_points : enumerate, labels : enumerate, feature_ids : enumerate, auxiliary_ids : enumerate) -> tuple[list[int], np.ndarray, float, float|int]:
        feature_ids = feature_ids.astype(int)
        auxiliary_ids = auxiliary_ids.astype(int)
        
        match self._label_matching_scheme:
            case "match-samples": matching_indeces = self._match_entry_ids_match_samples(feature_ids, auxiliary_ids)
            case "until-next": 
                if self._last_matched_label is not None:
                    labels = np.concatenate(([self._last_matched_label], labels))
                    auxiliary_ids = np.concatenate(([self._last_matched_label_id], auxiliary_ids))
                matching_indeces = self._match_entry_ids_until_next(feature_ids, auxiliary_ids)
            case "from-previous": 
                if self._last_matched_label is not None:
                    labels = [self._last_matched_label] + labels
                    auxiliary_ids = [self._last_matched_label_id] + auxiliary_ids
                matching_indeces = self._match_entry_ids_from_previous(feature_ids, auxiliary_ids)

        matched_features = [features[i[0]] for i in matching_indeces]
        matched_time_points = [time_points[i[0]] for i in matching_indeces]
        matched_labels = [labels[i[1]] for i in matching_indeces]

        if matching_indeces is None or len(matching_indeces) == 0:
            return None, None, None, None

        self._last_matched_label = matched_labels[-1]
        self._last_matched_label_id = auxiliary_ids[matching_indeces[-1][1]]
        return matching_indeces, matched_features, matched_time_points, matched_labels
    

    # matches the auxiliary entry ids to the feature entry ids with the same value
    def _match_entry_ids_match_samples(self, feature_ids : enumerate, auxiliary_ids : enumerate) -> list[int, int]:
        matching_indeces = []

        for label_index, sample_id in enumerate(auxiliary_ids):
            matching_feature_indices = [feature_index for feature_index, feature_id in enumerate(feature_ids) if feature_id == sample_id]
            for feature_index in matching_feature_indices:
                matching_indeces.append((feature_index, label_index))

        # sort by the order of feature indices, otherwise the feature data order gets mixed up
        matching_indeces = sorted(matching_indeces, key=lambda feature_index: feature_index[0])
        return matching_indeces


    # matches the auxiliary entry ids to all feature entry ids of equal or greater value until the next auxiliary entry id
    def _match_entry_ids_until_next(self, feature_ids : enumerate, auxiliary_ids : enumerate) -> list[int, int]:
        matching_indeces = []

        label_sample_index = 0
        last_aux_index = len(auxiliary_ids) 

        for feature_sample_index, feature_sample_id in enumerate(feature_ids):
            if label_sample_index >= last_aux_index:
                # when on the final auxiliary sample match id, assign all remaining features to that one
                for remaining_feature_sample_index in range(feature_sample_index, len(feature_ids)):
                    matching_indeces.append((remaining_feature_sample_index, label_sample_index))
                    break

            if label_sample_index == 0 and feature_sample_id < auxiliary_ids[0]:
                continue

            if feature_sample_id >= auxiliary_ids[label_sample_index+1]:
                label_sample_index += 1
                if label_sample_index >= len(auxiliary_ids):
                    break

            matching_indeces.append((feature_sample_index, label_sample_index))

        return matching_indeces
        
    
    # matches the auxiliary entry id to all feature entry ids of less or equal value starting from the first feature entry id greater than the last auxiliary entry id
    def _match_entry_ids_from_previous(self, feature_ids : enumerate, auxiliary_ids : enumerate) -> list[int, int]:
        raise NotImplementedError(f"Stream matching error: matching features and labels by entry id using the scheme 'from_previous' is currently not supported.")
    
    
# -------------------------------- time point matching --------------------------------
    def get_shared_features_by_time_points(self, features : np.ndarray, labels : enumerate, feature_time_points : enumerate, auxiliary_time_points : enumerate) -> tuple[list[int], np.ndarray, float, float|int]:
        auxiliary_time_points = [auxiliary_time_point - self._auxiliary_stream_drift for auxiliary_time_point in auxiliary_time_points]
        match self._label_matching_scheme:
            case "match-samples": 
                matching_indeces = self._match_time_points_match_samples(feature_time_points, auxiliary_time_points)
            case "until-next": 
                if self._last_matched_label is not None:
                    labels = np.concatenate(([self._last_matched_label], labels))
                    auxiliary_time_points = np.concatenate(([self._last_matched_label_timestamp], auxiliary_time_points))
                matching_indeces = self._match_time_points_until_next(feature_time_points, auxiliary_time_points)
            case "from-previous": 
                if self._last_matched_label is not None:
                    labels = np.concatenate(([self._last_matched_label], labels))
                    auxiliary_time_points = np.concatenate(([self._last_matched_label_timestamp], auxiliary_time_points))
                matching_indeces = self._match_entry_ids_from_previous(feature_time_points, auxiliary_time_points)

        matched_features = [features[i[0]] for i in matching_indeces]
        matched_time_points = [feature_time_points[i[0]] for i in matching_indeces]
        matched_labels = [labels[i[1]] for i in matching_indeces]

        if matching_indeces is None or len(matching_indeces) == 0:
            return None, None, None, None
        
        self._last_matched_label = matched_labels[-1]
        self._last_matched_label_timestamp = auxiliary_time_points[matching_indeces[-1][1]]
        return matching_indeces, matched_features, matched_time_points, matched_labels
    

    def _match_time_points_match_samples(self, feature_time_points : enumerate, auxiliary_time_points : enumerate) -> list[int, int]:
        n_feature_entries = len(feature_time_points)

        start_index = 0
        matching_indeces = []
        for i, auxiliary_time_point in enumerate(auxiliary_time_points):
            adjusted_auxiliary_time_point = auxiliary_time_point - self._auxiliary_stream_drift
            smallest_dist_time = float('inf')
            smallest_j = start_index

            for j in range(start_index, n_feature_entries):
                dist_time = abs(adjusted_auxiliary_time_point - feature_time_points[j])
                if dist_time > smallest_dist_time:
                    break
                smallest_dist_time = dist_time
                smallest_j = j
            
            matching_indeces.append((smallest_j, i))
            start_index = smallest_j + 1
            if start_index >= n_feature_entries:
                break
        
        return matching_indeces
    
    
    def _match_time_points_until_next(self, feature_time_points : enumerate, auxiliary_time_points : enumerate) -> list[int, int]:
        matching_indeces = []

        label_sample_index = 0
        last_aux_index = len(auxiliary_time_points) 

        for feature_sample_index, feature_time_point in enumerate(feature_time_points):
            if label_sample_index >= last_aux_index:
                # when on the final auxiliary time stamp, assign all remaining features to that one
                for remaining_feature_sample_index in range(feature_sample_index, len(feature_time_points)):
                    matching_indeces.append((remaining_feature_sample_index, label_sample_index))
                    break

            if label_sample_index == 0 and feature_time_point < auxiliary_time_points[0]:
                continue

            if feature_time_point >= auxiliary_time_points[label_sample_index+1]:
                label_sample_index += 1
                if label_sample_index >= len(auxiliary_time_points):
                    break

            matching_indeces.append((feature_sample_index, label_sample_index))

        return matching_indeces


    def _match_time_points_from_previous(self, feature_time_points : enumerate, auxiliary_time_points : enumerate) -> list[int, int]:
        raise NotImplementedError(f"Stream matching error: matching features and labels by time point using the scheme 'from_previous' is currently not supported.")

    

# -------------------------------- util functions --------------------------------
def invert_dict(original_dict):
    inverted_dict = {}
    for key, value_list in original_dict.items():
        for item in value_list:
            inverted_dict[item] = key
    return inverted_dict