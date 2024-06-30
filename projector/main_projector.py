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
from projector_settings import ProjectorSettings
from projector_plot_manager import ProjectorPlotManager
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from projection_methods.projection_method_interface import IProjectionMethod
from projector.projection_methods.umap_proj_method import UmapProjMethod
from projector.projection_methods.approx_umap_proj_method import ApproxUmapProjMethod
from projector.projection_methods.cebra_proj_method import CebraProjMethod
from projection_methods.projection_methods_enum import ProjectionMethodEnum
from process_management.processing_utils import *


# currently none of the underlying projection methods (UMAP and CEBRA) support the training of hybrid models, as a result this functionality is disabled (see if statement below)
# TODO configure this dynamically per method in the configs
SUPPORTS_HYBRID_MODEL = False


class Projector():
    _projection_model_curr : IProjectionMethod = None
    _projection_model_latest : IProjectionMethod = None
    _plot_manager : ProjectorPlotManager
    _settings : ProjectorSettings

    _recent_data : list[pd.DataFrame]
    _recent_ids : list[str]
    _recent_labels : list[float]
    _recent_time_points : list[float]
    _historic_df : pd.DataFrame
    _projections : np.ndarray[float]
    _last_time_stamp : int = 0

    _flags : dict[str, multiprocessing.Event]
    _locks : dict[str, multiprocessing.Lock]
    _processes_pausing_projections : int = 0

    _projecting_data : bool = False

    id : str
    update_count : int = 0


    def __init__(
            self, 
            projection_method : ProjectionMethodEnum, 
            plot_manager : ProjectorPlotManager,
            settings : ProjectorSettings = ProjectorSettings(), 
            flags : dict[str, multiprocessing.Event] = {},
            locks : dict[str, multiprocessing.Lock] = {}
            ):
        
        self.id = f"{projection_method.name}_{str(uuid.uuid4())}"
        self._plot_manager = plot_manager
        self._settings = settings
        self._flags = flags
        self._locks = locks
        
        self._projections = []
        self._init_historic_and_recent_data_objects()
        self._resolve_projection_method(projection_method)

    def _init_historic_and_recent_data_objects(self):
        self._recent_data = list[pd.DataFrame]()
        self._recent_ids = list[str]()
        self._recent_labels = list[int]()
        self._recent_time_points = list[float]()

        self._historic_df = pd.DataFrame()
        self._historic_df['ids'] = ""
        self._historic_df['time points'] = np.nan
        self._historic_df['labels'] = np.nan

    def _resolve_projection_method(self, projection_method : ProjectionMethodEnum):
        logger.info(f'Creating projector of method: {projection_method}')

        match projection_method.value:
            case ProjectionMethodEnum.UMAP.value:
                self._projection_model_latest = UmapProjMethod(self._settings.hyperparameters, align_projections=self._settings.align_projections)
            case ProjectionMethodEnum.UMAP_Approx.value:
                self._projection_model_latest = ApproxUmapProjMethod(self._settings.hyperparameters, align_projections=self._settings.align_projections)
            case ProjectionMethodEnum.CEBRA.value:
                self._projection_model_latest = CebraProjMethod(self._settings.hyperparameters)
            case _: 
                raise Exception(f"The projection method {projection_method.name} is not supported.")


    # -------------- end of init functions --------------
            
    def set_plotter_name(self):
        self._plot_manager.set_name("test")
        

    def get_plot_manager(self) -> ProjectorPlotManager:
        return self._plot_manager
    

    def get_update_count(self) -> int:
        return self.update_count
    

    def update_label(self, id : str, new_label : str):
        # map labels from string to int
        label_int_str_map = self._plot_manager.get_label_mapping()
        new_label : int = next(label_int for label_int, label_str in label_int_str_map.items() if label_str == new_label)

        # check if the datapoint is still in recent data otherwise assign the historic df
        try:
            index = self._recent_ids.index(id)
            self._recent_labels[index] = new_label
        except ValueError:
            self._historic_df.loc[self._historic_df['ids'] == id, "labels"] = new_label


    def project_new_data(self, data : pd.DataFrame, time_points : list[float], labels : list[int] = None):
        logger.debug('Creating new projections')
        self._projecting_data = True
        
        if data is None or len(data) == 0:
            return
        
        if labels is not None and isinstance(labels[0], str):
            labels = [self._settings.labels_map[str_label] for str_label in labels]
        elif labels is None:
            labels = [np.NaN] * len(data)

        new_last_time_stamp = self._last_time_stamp + len(data)
        ids_range = range(self._last_time_stamp+1, new_last_time_stamp+1)
        ids = [str(id) for id in ids_range]
        self._last_time_stamp = new_last_time_stamp

        projections = None
        if self._projection_model_curr is not None:
            logger.debug(f"Plotting new projections. Taking {len(ids)} points. Last point: {ids[-1]}. ")
            projections = self.project_data(data)
            print(f"Plotting points.")
            logger.debug(f"Plotting points.")
            self._plot_manager.plot(projections, ids, time_points, labels)

        self.aquire_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------
        self._recent_data.extend(data)
        self._recent_ids.extend(ids)
        self._recent_time_points.extend(time_points)
        self._recent_labels.extend(labels)

        if projections is not None:
            self._projections = np.append(self._projections, projections, axis=0)
        self.release_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------

        self._projecting_data = False


    def project_data(self, data, use_latest : bool = False):
        if use_latest:
            projection_model = self._projection_model_latest
        else:
            projection_model = self._projection_model_curr

        historic_data = self._historic_df
        if historic_data is not None:
            historic_data = historic_data.drop(['labels', 'time points'], axis=1)

        projections = projection_model.project(data=data, existing_data=historic_data)
        return projections

    
    # Data selection priority: update_data parameter -> historic data
    def update_projector(self, update_data: pd.DataFrame = None, labels : Iterable[int] = None, time_points : Iterable[float] = None):
        print(f"updating... new itteration: {self.update_count}")
        logger.debug(f"updating... new itteration: {self.update_count}")
        start_time = time.time()
        last_time = start_time

        #get update data if not provided
        if update_data is None:
            print("aquiring lock, update_projector")
            logger.debug("Waiting for current projection to finish")
            self.aquire_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA)
            historic_data, update_data, _, labels, time_points = self.get_updated_historic_data()
            self._historic_df = historic_data

            projections = self._projections
            self.release_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA)
            print("released lock, update_projector")

            # Only update the projection model when there are a minimum number of data points to train on
            if historic_data.empty or len(historic_data) < self._settings.min_training_samples_to_start_projecting:
                return
        else:
            projections = self._projections

        # Check if the update_data and number of projections match, if not, this causes an error when aligning the projections.
        projection_count = len(projections)
        if self._settings.align_projections and self.update_count > 0 and len(update_data) > projection_count:
            logger.warn(f"(alignment) number of datapoints for updating model is greater than the number of projections, turncating update data. Count : {projection_count}")
            update_data = update_data[:projection_count]
            labels = labels[:projection_count]
            time_points = time_points[:projection_count]


        contains_labeled_data = labels is not None and np.isnan(labels).any()
        contains_unlabeled_data = labels is None or any(label != np.NaN for label in labels)
        is_hybrid_data = contains_labeled_data and contains_unlabeled_data

        print(f"Fitting new model. Using {len(update_data)} samples.")
        logger.info(f"Fitting new model. Using {len(update_data)} samples.")
        if is_hybrid_data and SUPPORTS_HYBRID_MODEL:
            # BUG fit new fails when the data is split in such a way that there is only one labeled data entry
            labeled_df, unlabeled_df = split_hybrid_data(update_data, labels, time_points)
            labeled_data, _, labeled_labels, _ = unpack_dataframe(labeled_df)
            self._projection_model_latest.fit_new(data=labeled_data, labels=labeled_labels, time_points=time_points, past_projections=projections)
            unlabeled_data, _, _, unlabeled_time_points = unpack_dataframe(unlabeled_df)
            self._projection_model_latest.fit_update(unlabeled_data, unlabeled_time_points)
        elif contains_unlabeled_data:
            self._projection_model_latest.fit_new(data=update_data, labels=None, time_points=time_points, past_projections=projections)
        else:
            self._projection_model_latest.fit_new(data=update_data, labels=labels, time_points=time_points, past_projections=projections)
        print("Completted fitting new model")
        logger.info("Completted fitting new model")

        if self._projection_model_curr is None:
            self.activate_latest_projector()
        self.update_count += 1

        track_time(start_time, last_time, "updating model")


    def activate_latest_projector(self):
        logger.debug("Waiting for current projection to finish")
        self.aquire_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------
        logger.debug(f'Getting historic data for updating plot')

        historic_df, data, ids, labels, time_points = self.get_updated_historic_data()
        self._historic_df = historic_df
        self.release_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------
        
        logger.info(f"projecting the following quanities: data={len(data)}, time points={len(time_points)}, labels={len(labels)}")
        latest_projections = self.project_data(data, use_latest=True)
        
        self.aquire_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------
        if len(self._projections) == 0:
            self._projections = latest_projections
        elif len(self._projections) >= len(latest_projections): 
            # make sure only to overwrite the first n entries, otherwise, novel projections added to self._projections between the updating of the historic data~
            # and this assignment are lost, causing errors when fitting a new model.
            self._projections[:len(latest_projections), :latest_projections.shape[1]] = latest_projections
        else:
            self._projections = latest_projections
        
        self._projection_model_curr = copy.deepcopy(self._projection_model_latest)
        self.release_lock(LOCK_NAME_MUTATE_PROJECTOR_DATA) # --------------------------------------
        
        logger.info(f"Plotting new model. Taking {len(ids)} points")
        try:
            self._plot_manager.update_plot(latest_projections, ids, time_points, labels)
            
        except Exception as e:
            logger.error(f"Projector Plotting Exception: {str(e)}")


    def get_updated_historic_data(self, clear_recent : bool = True) -> tuple[pd.DataFrame, pd.DataFrame, list[any], list[float]]:
        # Copy and clear recent data to minimize data loss
        recent_data_copy = self._recent_data.copy()
        recent_ids_copy = self._recent_ids.copy()
        recent_labels_copy = self._recent_labels.copy()
        recent_time_points_copy = self._recent_time_points.copy()

        if clear_recent:
            self._recent_data.clear()
            self._recent_ids.clear()
            self._recent_labels.clear()
            self._recent_time_points.clear()

        if not isinstance(recent_data_copy, pd.DataFrame):
            recent_data_copy = pd.DataFrame(recent_data_copy)

        historic_data_data_columns = self._historic_df.drop(['ids', 'labels', 'time points'], axis=1)
        update_data = pd.concat([historic_data_data_columns, recent_data_copy], ignore_index=True)
        updated_ids = list(pd.concat([self._historic_df['ids'], pd.Series(recent_ids_copy)], ignore_index=True))
        updated_labels = list(pd.concat([self._historic_df['labels'], pd.Series(recent_labels_copy)], ignore_index=True))
        updated_time_points = list(pd.concat([self._historic_df['time points'], pd.Series(recent_time_points_copy)], ignore_index=True))

        updated_historic_df = pack_dataframe(update_data, updated_ids, updated_labels, updated_time_points)
        return updated_historic_df, update_data, updated_ids, updated_labels, updated_time_points
    

    def _wait_for_curr_projection_to_finish(self):
        time.sleep(0.005)
        wait_counter = 1
        while self._projecting_data:
            time.sleep(0.001) # wait for 1 ms
            if wait_counter % 1000 == 0:
                logger.debug(f"Still waiting for curr projection to finish.. {wait_counter}")
            wait_counter =+ 1


    def aquire_lock(self, lock_name : str):
        if lock_name in self._locks:
            self._locks[lock_name].acquire()

    def release_lock(self, lock_name : str):
        if lock_name in self._locks:
            self._locks[lock_name].release()


def split_hybrid_data(data, labels, time_points) -> tuple[pd.DataFrame, pd.DataFrame]:
    hybrid_df = pack_dataframe(data, labels, time_points)
    labeled_df = hybrid_df[~np.isnan(hybrid_df['labels'])]
    unlabeled_df = hybrid_df[np.isnan(hybrid_df['labels'])]
    return labeled_df, unlabeled_df


def get_NaN_list(length) -> list[float]:
    return [np.NaN] * length


def track_time(start_time, last_time, msg):
    time_now = time.time()
    logger.debug(f"{msg}: {time_now-last_time}, {time_now-start_time}")
    return time_now