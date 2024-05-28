from plot_settings import PlotSettings
from projection_methods.projection_methods_enum import ProjectionMethodEnum

class ProjectorSettings():
    projection_method : ProjectionMethodEnum
    align_projections : bool = False

    min_training_samples_to_start_projecting : int = 5
    fit_reducer_when_initiating : bool = False   # obsolete
    stream_buffer_size_s : float = 10
    sampling_frequency : float = 1
    model_update_frequency : float = 1

    hyperparameters : dict[str, any] = {}
    plot_settings = PlotSettings()
