import copy
from math import nan
import multiprocessing
import uuid
import pandas as pd
import numpy as np
import time

from utils.logging import logger
from utils.data_mocker import *
from utils.dataframe_utils import *
from utils.stream_watcher import StreamWatcher
from projector_settings import ProjectorSettings
from projector_plot_manager import ProjectorPlotManager
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod
from projection_methods.umap_wrapper import UmapWrapper
from projection_methods.umap_approx_wrapper import UmapApproxWrapper
from projection_methods.cebra_wrapper import CebraWrapper
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from process_management.processing_utils import LOCK_NAME_PROJECTOR_HISTORIC_DATA


# currently none of the underlying projection methods (UMAP and CEBRA) support the training of hybrid models, as a result this functionality is disabled (see if statement below)
# TODO configure this dynamically per method in the configs
SUPPORTS_HYBRID_MODEL = False


class Projector():
    _projection_model_curr : IProjectionMethod = None
    _projection_model_latest : IProjectionMethod = None
    _stream_watcher : StreamWatcher
    _plot_manager : ProjectorPlotManager
    _settings : ProjectorSettings

    _recent_data : list[pd.DataFrame]
    _recent_labels : list[float]
    _recent_time_points : list[float]
    _historic_df : pd.DataFrame

    _flags : dict[str, multiprocessing.Event]
    _locks : dict[str, multiprocessing.Lock]
    _projections_count : int = 0
    _processes_pausing_projections : int = 0

    _projecting_data : bool = False

    id : str
    update_count : int = 0


    def __init__(
            self, 
            projection_method : ProjectionMethodEnum, 
            plot_manager : ProjectorPlotManager,
            stream_name: str = "mock_EEG_stream", 
            projector_settings : ProjectorSettings = ProjectorSettings(), 
            flags : dict[str, multiprocessing.Event] = {},
            locks : dict[str, multiprocessing.Lock] = {}
            ):
        
        self.id = f"{projection_method.name}_{str(uuid.uuid4())}"
        self._plot_manager = plot_manager
        self._settings = projector_settings
        self._flags = flags
        self._locks = locks
        
        self._init_historic_and_recent_data_objects()
        # self._init_stream_watcher(stream_name)
        self._resolve_projection_method(projection_method)

    def _init_historic_and_recent_data_objects(self):
        self._recent_data = list[pd.DataFrame]()
        self._recent_labels = list[int]()
        self._recent_time_points = list[float]()
        self._historic_df = pd.DataFrame()
        self._historic_df['time points'] = np.nan
        self._historic_df['labels'] = np.nan

    def _init_stream_watcher(self, stream_name: str):
        logger.info(f'Watching stream: {stream_name}')
        buffer_size_s = self._settings.stream_buffer_size_s
        self._stream_watcher = StreamWatcher(stream_name, buffer_size_s)
        self._stream_watcher.connect_to_stream()

    def _resolve_projection_method(self, projection_method : ProjectionMethodEnum):
        logger.info(f'Creating projector of method: {projection_method}')

        match projection_method.value:
            case ProjectionMethodEnum.UMAP.value:
                self._projection_model_latest = UmapWrapper(self._settings.hyperparameters)
            case ProjectionMethodEnum.UMAP_Approx.value:
                self._projection_model_latest = UmapApproxWrapper(self._settings.hyperparameters)
            case ProjectionMethodEnum.CEBRA.value:
                self._projection_model_latest = CebraWrapper(self._settings.hyperparameters)
            case _: 
                raise Exception(f"The projection method {projection_method.name} is not supported.")

    # -------------- end of init functions --------------
            
    def set_plotter_name(self):
        self._plot_manager.set_name("test")
        

    def get_plot_manager(self) -> ProjectorPlotManager:
        return self._plot_manager
    

    def get_update_count(self) -> int:
        return self.update_count
    

    def update_label(self, time_point : float | str, new_label : str):
        if isinstance(time_point, str):
            time_point = float(time_point)     

        # map labels from string to int
        label_int_str_map = self._plot_manager.get_label_mapping()
        new_label : int = next(label_int for label_int, label_str in label_int_str_map.items() if label_str == new_label)

        # check if the datapoint is still in recent data otherwise assign the historic df
        try:
            index = self._recent_time_points.index(time_point)
            self._recent_labels[index] = new_label
        except ValueError:
            self._historic_df.loc[self._historic_df['time points'] == time_point, "labels"] = new_label


    def project_new_data(self):
        print("projecting...")
       
        logger.info('Creating new projections')
        self._projecting_data = True

        # if self._settings.auto_update_stream_on_projection:
        #    self._stream_watcher.update()
        data, labels, time_points = get_mock_data(1) #self._stream_watcher.read_buffer()

        if self._projection_model_curr is not None:
            projections = self.project_data(data)
            print(f"Plotting new projections. Taking {len(time_points)} time points.")
            logger.info(f"Plotting new projections. Taking {len(time_points)} time points.")
          
            self._plot_manager.plot(projections, time_points, labels)
            self._projections_count += len(projections)

        self.aquire_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)
        self._recent_data.append(data)
        self._recent_labels.extend(labels)
        self._recent_time_points.extend(time_points)
        self.release_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)

        self._projecting_data = False


    def project_data(self, data, use_latest : bool = False):
        if use_latest:
            projection_model = self._projection_model_latest
        else:
            projection_model = self._projection_model_curr

        method_type = projection_model.get_method_type()

        # estimating the projections for approximate UMAP will fail if there is not historic data (yet), in this case use standard method to obtain projections
        if method_type.value is ProjectionMethodEnum.UMAP_Approx.value and self.update_count != 0:
            # only take the data columns of the historic data, leave out the labels and time points
            historic_data = self._historic_df.drop(['labels', 'time points'], axis=1)
            print("projecting.. produicing projection")
            projections = projection_model.produce_projection(data, historic_data)
        else:
            print("projecting.. produicing projection")
            projections = projection_model.produce_projection(data)

        print("projecting.. obtained projection")
        return projections

    
    # Data selection priority: update_data parameter -> historic data
    def update_projector(self, update_data: pd.DataFrame = None, labels : Iterable[int] = None, time_points : Iterable[float] = None):
        print("updating...")
        start_time = time.time()
        last_time = start_time

        #get update data if not provided
        if update_data is None:
            print(f"Getting data for update. Update: {self.update_count}")

            print("Waiting for current projection to finish")
            self.aquire_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)
            historic_data, update_data, labels, time_points = self.get_updated_historic_data()
            self._historic_df = historic_data
            self.release_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)

            # Only update the projection model when there are a minimum number of data points to train on
            if historic_data.empty or len(historic_data) < self._settings.min_training_samples_to_start_projecting:
                return

        contains_labeled_data = labels is not None and np.isnan(labels).any()
        contains_unlabeled_data = labels is None or any(label != np.NaN for label in labels)
        is_hybrid_data = contains_labeled_data and contains_unlabeled_data

        print(f"Fitting new model. Using {len(update_data)} samples.")
        if is_hybrid_data and SUPPORTS_HYBRID_MODEL:
            # BUG fit new fails when the data is split in such a way that there is only one labeled data entry
            labeled_df, unlabeled_df = split_hybrid_data(update_data, labels, time_points)
            labeled_data, labeled_labels, _ = unpack_dataframe(labeled_df)
            self._projection_model_latest.fit_new(labeled_data, labeled_labels)
            unlabeled_data, _, unlabeled_time_points = unpack_dataframe(unlabeled_df)
            self._projection_model_latest.fit_update(unlabeled_data, unlabeled_time_points)
        elif contains_unlabeled_data:
            self._projection_model_latest.fit_new(update_data, None, time_points)
        else:
            self._projection_model_latest.fit_new(update_data, labels, time_points)
        print("Completted fitting new model")

        if self._projection_model_curr is None:
            self.activate_latest_projector()
        self.update_count += 1

        track_time(start_time, last_time, "updating model")


    def activate_latest_projector(self):
        print("Waiting for current projection to finish")
        self.aquire_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)
        print(f'Getting historic data for updating plot')

        historic_df, data, labels, time_points = self.get_updated_historic_data()
        self._historic_df = historic_df
        self.release_lock(LOCK_NAME_PROJECTOR_HISTORIC_DATA)
        
        print(f"projecting the following quanities: data={len(data)}, time points={len(time_points)}, labels={len(labels)}")
        new_projections = self.project_data(data, use_latest=True)
        
        print(f"Plotting new model. Taking {len(time_points)} points")
        try:
            self._plot_manager.update_plot(new_projections, time_points, labels)
            self._projection_model_curr = copy.deepcopy(self._projection_model_latest)
            
        except Exception as e:
            print(f"Projector Plotting Exception: {str(e)}")


    def get_updated_historic_data(self, clear_recent : bool = True):
        # Copy and clear recent data to minimize data loss
        recent_data_copy = self._recent_data.copy()
        recent_labels_copy = self._recent_labels.copy()
        recent_time_points_copy = self._recent_time_points.copy()

        if clear_recent:
            self._recent_data.clear()
            self._recent_labels.clear()
            self._recent_time_points.clear()

        historic_data_data_columns = self._historic_df.drop(['labels', 'time points'], axis=1)
        update_data = concact_dataframes(historic_data_data_columns, recent_data_copy, True)
        updated_labels = list(pd.concat([self._historic_df['labels'], pd.Series(recent_labels_copy)], ignore_index=True))
        updated_time_points = list(pd.concat([self._historic_df['time points'], pd.Series(recent_time_points_copy)], ignore_index=True))

        updated_historic_df = pack_dataframe(update_data, updated_labels, updated_time_points)
        return updated_historic_df, update_data, updated_labels, updated_time_points
    

    def _wait_for_curr_projection_to_finish(self):
        time.sleep(0.005)
        wait_counter = 1
        while self._projecting_data:
            time.sleep(0.001) # wait for 1 ms
            if wait_counter % 1000 == 0:
                print(f"Still waiting for curr projection to finish.. {wait_counter}")
            wait_counter =+ 1


    def aquire_lock(self, lock_name : str):
        if lock_name in self._locks:
            self._locks[lock_name].acquire()

    def release_lock(self, lock_name : str):
        if lock_name in self._locks:
            self._locks[lock_name].release()


def split_hybrid_data(data, labels, time_points):
    hybrid_df = pack_dataframe(data, labels, time_points)
    labeled_df = hybrid_df[~np.isnan(hybrid_df['labels'])]
    unlabeled_df = hybrid_df[np.isnan(hybrid_df['labels'])]
    return labeled_df, unlabeled_df


def get_NaN_list(length):
    return [np.NaN] * length


def track_time(start_time, last_time, msg):
    time_now = time.time()
    print(f"{msg}: {time_now-last_time}, {time_now-start_time}")
    return time_now