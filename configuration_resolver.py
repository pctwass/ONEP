import os
import tomllib
from dashboard.dahsboard_settings import DashboardSettings
from projector.plot_settings import PlotSettings
from projector.projector_settings import ProjectorSettings
from projector.projection_methods.projection_methods_enum import ProjectionMethodEnum


class ConfigurationResolver:
    _config : dict[str, any] = {}

    def __init__(self, config_path) -> None:
        self._config = tomllib.load(open(config_path, "rb"))


    def get(self, section_name):
        section = self._config.get(section_name)
        return section


    def resolve_config(self) -> (ProjectorSettings, DashboardSettings):
        projector_settings = self.get_projector_settings_from_config()
        dashboard_settings = self.get_dashboard_settings_from_config()
        return projector_settings, dashboard_settings


    def get_projector_settings_from_config(self) -> ProjectorSettings:
        projector_config_section = self._config.get('projector-settings')
    
        projector_settings = ProjectorSettings()
        method_string = projector_config_section.get("projection-method")
        projector_settings.projection_method = ProjectionMethodEnum.from_string(method_string)
        projector_settings.align_projections = projector_config_section.get("align-projection")

        projector_settings.min_training_samples_to_start_projecting = projector_config_section.get('min-training-samples-to-start-projecting')
        projector_settings.stream_buffer_size_s = projector_config_section.get('stream-buffer-size-s')
        projector_settings.sampling_frequency = projector_config_section.get('max-sampling-frequency')
        projector_settings.model_update_frequency = projector_config_section.get('max-model-update-frequency')

        projector_settings.hyperparameters = self.get_hyperparameters_from_config(method_string)

        projector_settings.plot_settings = self.get_plot_settings_from_config()

        return projector_settings


    def get_hyperparameters_from_config(self, method_string: str) -> dict[str, any]:
        hyperparameter_folder = self._config.get('hyperparameter-config-folder')
        hyperparameter_file_name = self._config.get('hyperparameter-config-files')[method_string]
        hyperparameter_config_path = os.path.join(os.getcwd(), hyperparameter_folder, hyperparameter_file_name)
        
        hyperparameter_config = tomllib.load(open(hyperparameter_config_path, "rb"))
        return hyperparameter_config


    def get_plot_settings_from_config(self) -> PlotSettings:
        plot_config_section = self._config.get('plot-settings')

        plot_settings = PlotSettings()
        plot_settings.labels = self._config.get('labels')
        plot_settings.label_colors = plot_config_section.get('label-colors')
        plot_settings.unclassified_label = self._config.get('unclassified-label')
        plot_settings.unclassified_label_color = plot_config_section.get('unclassified-label-color')

        plot_settings.scatter_point_size = plot_config_section.get('scatter-point-size')
        plot_settings.point_selection_border_size = plot_config_section.get('point-selection-border-size')
        plot_settings.point_selection_border_color = plot_config_section.get('point-selection-border-color')
        plot_settings.point_highlight_size = plot_config_section.get('point-highlight-size')
        plot_settings.point_highlight_border_size = plot_config_section.get('point-highlight-border-size')
        plot_settings.point_highlight_border_color = plot_config_section.get('point-highlight-border-color')

        plot_settings.min_opacity = plot_config_section.get('min-opacity')
        opacity_thresholds = plot_config_section.get('opacity-thresholds')
        plot_settings.opacity_thresholds = {float(key): value for key, value in opacity_thresholds.items()}

        plot_settings.show_axis = plot_config_section.get('show-axis')
        plot_settings.transition_duration = plot_config_section.get('transition-duration')

        default_x_range_config_section = plot_config_section.get('default-x-range')
        if default_x_range_config_section is None:
            plot_settings.default_x_range = None
        else:
            plot_settings.default_x_range = [default_x_range_config_section['start'], default_x_range_config_section['end']]

        default_y_range_config_section = plot_config_section.get('default-y-range')
        if default_y_range_config_section is None:
            plot_settings.default_y_range = None
        else:
            plot_settings.default_y_range = [default_y_range_config_section['start'], default_y_range_config_section['end']]

        return plot_settings


    def get_dashboard_settings_from_config(self) -> DashboardSettings:
        dashboard_config_section = self._config.get('dashboard-settings')
        plot_config_section = self._config.get('plot-settings')

        dashboar_settings = DashboardSettings()
        dashboar_settings.graph_refresh_frequency = dashboard_config_section.get('graph-refresh-frequency')
        dashboar_settings.host = self._config.get('dashboard-host')
        dashboar_settings.port = self._config.get('dashboard-port')
        dashboar_settings.transition_duration = plot_config_section.get('transition-duration')

        return dashboar_settings