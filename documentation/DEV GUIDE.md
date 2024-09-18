This document provides an overview and explanation of the Online Neurodata and Embedding Projector (ONEP) from a development perspective. The following content focuses on the general structure of the project as well as the implementation details of core features/classes. It is recommended to read the user guide, particularly the terminology and launch steps sections.


## Tips for Debugging
### Running ONEP without the Server or Console and Sequentially
It is possible to avoid the need to send commands to the ONEP server entry point or use the console interface when running ONEP. By running main.py, ONEP can be started directly. The sequence of events mimics the use of the LAUNCH command, followed directly by START_PROJECTOR. Additionally, at the top of the main function, there is a variable called mode. This variable is used to determine how to run ONE from the main file. It can be assigned either `continuous` or `sequential`. Continues mode runs ONEP identically to how it is run when running the program normally. Sequential mode requires direct calls to the projector rather than running the projector updating and projection processes. This allows for more convenient control over when the projection of new data or training of the model takes place. 

**Using mock Data**<br>
By setting the config value `use-mock-data` to true, the projection subprocess will not make an attempt to read data from the input stream but instead generate mock data.

**Disable Subprocess**<br>
A subprocess may be excluded from running by removing/commenting out two lines of code. 
1. In `processmanagement/process_manager.py`, remove/comment the call to create the subprocess in `_create_subprocessess()`, E.g.  
	"self._subprocesses["dashboard"] = create_process_dashboard(...)"
2. In `main,py`, remove/comment the call to start the process either in `launch()` for the dashboard process, or in `start()` for the projector processes. E.g.
	`process_manager.start_process("dashboard")`
3. (optionally - only for projector processes) In `main.py`,  remove/comment the call to strop the process in `stop()`. E.g.
`process_manager.stop_process("projector_projecting")`


## General Structure

The application is split up into three major parts; the projector, plotting, and the dashboard. Some additional code segments are separate from these three parts, such as the API, main class, and some utility functions. The flow chart below shows how the sections of the code interact. The sections shown here will occasionally be referred to as subprocesses in this document.

<picture>
    <source srcset="./assets/flowchart.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/flowchart.png">
</picture>


## User Interface

**Projector**<br>
The functionality of the projector is primarily implemented in the `Projector` class. Additionally, the Projector maintains an instance of a projection method class that implements `IProjectionMethod` as interface. The projection method class acts as a wrapper for the implementation of the projection method functionality, which is primarily training and updating a model and projecting novel datapoints.

**Plotting**<br>
Creating, adapting, and maintaining the plot/figure is done by the `ProjectorPlotManager` class. This figure is a standard `plotly.graph_objects.Figure`. A handful of additional service classes are used by the `ProjectorPlotManager` to interact with the plot. These are contained in the `./plotly_serivces` folder. These services are designed to be general-purpose services that depend on the Plotly framework to support dynamic and continuous plotting functionalities.

**Dashboard**<br>
The dashboard flow is managed by the `Dashboard` and `DashboardLayout` classes. Where the Dashboard class implements the callback logic and the `DashboardLayout` class implements the page layout and elements. It utilizes a number of style sheets for this purpose.

**Class Structure**<br>
The flowchart above provides a general impression of the class structure, however, many aspects of the actual class structure are left out and/or simplified. Below is a full image of the class structure. The most notable inclusion is the `ProcessManager` class, which manages the `projection`, `projector update`, and `dashboard` processes. Additionally, the chart below demonstrates that the `ProjectorPlotManager`, the class primarily responsible for the plotting functionality, is actually managed by the Projector.

## User Interface
<picture>
    <source srcset="./assets/class-diagram.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/class-diagram.png">
</picture>


## Configuration

A number of settings classes are used at various points of the application’s lifetime. These setting classes contain multiple configurable settings that may be needed to create an instance of a class or object. The following settings classes are used:

- `StreamSettings` 
- `ProjectorSettings`
- `PlotSettings`
- `DashboardSettings`
- `ScatterPlotSettings`

**Configuration files**<br>
Most of the settings in these classes are derived from the configuration toml file in the `./configs` folder. Additionally, the property hyperparameters in `ProjectorSettings` is filled using the projection-method-specific values stored in the relevant hyperparameter config file found in the `./config/hyperparameter` folder. For an overview and explanation of the configuration values see the [Configuration File] section of the user guide.

**Resolving configurations, initiating settings**<br>
When launching the application, an instance of each settings class, excluding `ScatterPlotSettings`, is created by the `ConfigurationResolver`. This class reads the content of the config and hyperparameter config files and uses it to build the settings classes instances. Note that during this process, an instance of `PlotSettings` is embedded into the instance of `ProjectorSettings` instead of being returned separately. 

**ScatterPlotSettings**<br>
The `ScatterPlotSettings` class is initiated and used in a different manner than the other settings classes. Due to the Plotly services being static and not retaining an instance of a figure, when creating a new scatter plot an instance of `ScatterPlotSettings` must always be passed to the `create_figure()` method. Additionally, some of the properties of a plot may require to differ from that of the previous figure, resulting in the scatter plot settings changing throughout the application’s lifecycle. To handle this, a new instance of `ScatterPlotSettings` is created each time the `ProjectorPlotManager` needs to create a new scatter plot. To create this instance, the values contained in `PlotSettings` are used by the `ProjectorPlotManager`. This is resolved in the `_resolve_scatter_plot_settings()` function, which returns a new instance of `ScatterPlotSettings`. At the moment, only the x-axis range may change over time.
Despite only a single property differing between instances of `ScatterPlotSettings`, the current implementation recreates these settings regularly. This implementation was chosen because settings classes are supposed to be static, therefore, utilizing only a single instance of `ScatterPlotSettings` and changing it over time would not comply with this convention.


## Stream Watcher

In order to handle various input streams, ONEP uses a multiclass stream watcher implementation. This implementation is comprised of three components, the `StreamWatcher`,  `StreamInterpreter`, and `StreamMatcher`.

**StreamWatcher**<br> 
The `StreamWatcher` is the main class for reading data from the inpu stream(s). It handles the connecting to the streams and reading from their buffers. To read from a stream, the `StreamWatcher` implements a stream watcher class from the dareplane-utils package. It creates an instance of these Dareplane stream watchers for both the feature and auxiliary stream, assuming the auxiliary stream is used. 

When initializing the `StreamWatcher` an instance of `StreamSettings` is required, which contains the stream names to watch, if labels should be read, how to interpret the streams, and how to match them. Note, that not all the settings in the `StreamSettings` class are required, for example, the matching scheme is unnecessary if the auxiliary stream is unused. 

The dareplane-utils stream watchers that are used by the `StreamWatcher` make use of a circular buffer. To keep track of where on the buffer new samples should be written and where data should be read from, the `StreamWatcher` needs to update two properties of the dareplane-utils stream watchers, `n_new` and `curr_i`. `n_new` represents how many unread samples there are in the buffer and `curr_i` represens which position in the buffer the `StreamWatcher` should start reading from. In the code, these two properties are referred to as the buffer trackers. They are updated whenever new samples are read and, if required, matched by calling the private function `_update_buffer_trackers()`. The new values of the buffer trackers can be determined based on the number of samples read from the corresponding stream. 

The `StreamWatcher` applies the following flow when the read() method is called:
1. Read from the feature stream. 
* If the read data is None or empty, return None for the features, timestamps, and labels. Otherwise, continue to step 2.
2. Interpret the data read from the feature stream. 
* If no labels should be read or the labels are in the feature stream, update the buffer trackers and return the features, timestamps, and labels as interpreted by the feature-stream `StreamInterpreter`. Otherwise, continue to step 3. 
3. Read from the auxiliary stream.
* If the read auxiliary is None or empty, return None for the features, timestamps, and labels. Otherwise, continue to step 4.
4. Interpret the data read from the auxiliary stream.
5. Match the stream.
6. Determine how many features and labels have been read.
7. Update the buffer trackers of both streams based on the number of features and labels read.
8. Return the features and timepoints as interpreted by the feature-stream `StreamInterpreter` and the labels as interpreted by the auxiliary-stream `StreamInterpreter`.

**StreamInterpreter**<br> 
A separate instance of the `StreamInterpreter` class is used for both streams. Along with their initialization, `StreamInterpreterTypeEnum` is passed to determine the type of the stream that needs to be interpreted.  Depending on the stream settings and this type, the interpreter can resolve if it needs to interpret the feature section, label section, or both whenever its `interpret()` function is called. Interpretation of the features from a set of stream samples is limited to selecting the section of the sample arrays as defined in the setting for the feature section. Interpreting the label section requires a translation of the label section in accordance with the interpretation method that is set in the setting. Additionally, the stream interpreter extracts the label match ids from the passed samples if these are used. 

**StreamMatcher**<br> 
Only one instance of the `StreamMatcher` is initialized by the `StreamWatcher`. It tries to match the samples read and interpreted from the feature and auxiliary streams. Upon initiation, the stream matcher resolves which matching scheme to use. 
To add new matching schemes, a function should be added to the `StreamMatcher` that should return a list of tuples, where each tuple represents a pair of matching indices of the feature and auxiliary stream. For example, the output [(0, 0), (1,0), (2,2)] indicates that the first and second feature samples should be matched to the first label sample, and the third feature sample should be matched to the third label sample. The private variables `_last_matched_sample_id` and `_last_matched_timestamp` can be used to retrain the previous sample match id or timestamp that a feature and label were matched for. This allows for the matching of samples between reads that use schemes such as “until-next”.


## Process Manager

Creation and management of ONEP’s subprocesses are done by the `ProcessManager` class, located in `process_management/process_manager.py`. The manager implements a `multiprocessing.managers.BaseManager` instance that controls a set of proxy objects that are utilized in the three subprocesses, which are documented in the section below. The `ProcessManager` also creates a set of flags and locks that are passed to the subprocesses and the `Projector` proxy object. 

### Processes
The `ProcessManager` initializes and controls the following three living processes.

**Projection Process**<br>
Requires an instance of the following proxy objects: `Projector`, and `StreamWatcher`. 
Connects to the streams then repeatedly attempts to read from the stream. If data was read from the stream it calls `Projector.project_new_data()`.
Has access to a ‘pause’ and ‘stop’ flag to pause or terminate the process.

The following steps are taken by `Projector.project_new_data()`:
1. Resolve the labels. If labels are of type string, translate strings to integers according to the label order as defined in the config. If labels are none or empty, create a list of numpy.NaN values.
2. Create a list of unique ids for each sample.
3. If there is a projection model available, project the novel data.
4. Track data as recent and, if the data was projected, append the projections (requires the `Mutate_Porjector_Data` lock).

**Update Projector Process**<br>
Requires an instance of the following proxy objects: `Projector`. 
Repeatedly calls `Projector.update_projector()`.
Has access to a ‘pause’ and ‘stop’ flag to pause or terminate the process.

The following steps are taken by `Projector.update_projector()`:
1. Merges recent data to historic data and acquires all historic data (requires the `Mutate_Porjector_Data` lock).
2. Updates the existing model or trains a new model on the novel data.
3. If no projection model has been activated yet, set the updated/newly trained model as the current model (call `.activate_latest_projector()`).

**Dashboard Process**<br>
Requires an instance of the following proxy objects: `Projector`, `PlotManager`. 
Initializes the `Dashboard` class and runs the dashboard app.

### Flags
All processes are passed a set of flags. These flags are used to pause/resume and stop the projector processes (project and update projector). Their values may be set via the dashboard or through commands to the server or in the terminal interface. 

### Locks
At the time of writing, ONEP only functionally utilizes a single lock,`Mutate_Porjector_Data`. This lock is used by the two projector processes when altering the recent data lists or the historic data frame that the projector uses for bookkeeping. These locks are used to avoid race conditions between the two projector processes.


## Projector

The projector subprocesses depend primarily on two classes. These classes are the `Projector` and a projection method wrapper class that implements the `IProjectionMethod`. Through the `ProcessManager` class, an instance of the `Projector` is created as a proxy object. The functionality of the proxy object is utilized by the living processes defined in `./process_managemnt/projector_processes.py`. The `Projector` class itself creates an object of the projection method wrapper class and of `ProjectorPlotManager`. The latter is used for the plotting. To support the initialization of the `Projector`, an instance of `PlotSettings` is passed by Main to the `ProcessManager`. This `ProjectorSettings` object contains multiple settings needed for the `Projector`, including the … field which is assigned a value of `ProjectionMethodEnum`. This enum value is used to resolve which projection method class should be used by the `Projector`.

### Projector
The `Projector` is the core of the projector subprocess. It makes calls to the plotting subprocess, tracks the data used for projecting (features, timestamps, labels, and data point ids), and directs the projection method instance to create new projections or train a new instance of the projection model. 

To keep track of the provided data, the `Projector` stores three lists and a data frame. The data frame `_historic_df` contains the data from the data stream, labels, and time points of all data entries that have been used to train the latest projection model iteration. Additionally, `_recent_data`, `_recent_labels`, and `_recent_timepoints` contain similar information, however, this is only for the data entries that have been read from the data stream but have not been used yet for training a projection model. The historic data frame and recent data lists are kept separate due to the `_recent_data` list being a list of data frames. With the `_recent_data` being updated each time a data entry gets projected, which should be at a rate of a few milliseconds ideally, it would be too slow to instead express the list as a singular data frame that constantly gets appended or merged with a new data frame. Instead, the recent data lists are only added to the historic data frame each time a new projection model iteration is trained.

There are three main functions that are implemented by the Projector: `project_new_data()`, `update_projector()`, and `activate_latest_projector()`.

- **project_new_data():**<br>
This method is repeatedly called by the Projection subprocess defined in `process_management/projection_processes.py`.
It expect a set of datapoints, timestamps, and, optionally, labels.
As mentioned in the Process Manager section, it performs the following operations:
1. Resolve the labels. If labels are of type string, translate strings to integers according to the label order as defined in the config. If labels are none or empty, create a list of numpy.NaN values.
2. Create a list of unique ids for each sample.
3. If there is a projection model available, project the novel data.
4. Track data as recent and, if the data was projected, append the projections (requires the `Mutate_Porjector_Data` lock).

- **update_projector():**<br>
This method is repeatedly called by the Update Projector subprocess defined in `process_management/projection_processes.py`.
The method requires no arguments.
As mentioned in the Process Manager section, it performs the following operations:
1. Merges recent data to historic data and acquires all historic data  (requires the `Mutate_Porjector_Data` lock).
2. Updates the existing model or trains a new model on the novel data.
3. If no projection model has been activated yet, set the updated/newly trained model as the current model (call `activate_latest_projector()`).

- **activate_latest_projector():**<br>
This method is called initially by `update_projector()` and afterward by the Dashboard following an action taken by the user.
The method requires no arguments.
It performs the following operations:
1. Merges recent data to historic data and acquires all historic data (requires the Mutate_Porjector_Data` lock - lock remains acquired until step 4).
2. Projects all data using the latest model iteration.
3. Updates the stored projections with the new projections.
4. Overwrites the current model iteration with the latest model iteration (releases `Mutate_Porjector_Data` lock).
5. Calls `ProjectioPlotManager.update_plot()` in order to update the visualization.

**Projection model iterations**<br>
The Projector stores two projection model iterations, an active iteration and a latest iteration. These model iterations are stored in the private variables `_projection_model_curr` and `_projection_model_latest`. This split is made due to it being desirable that the updating of the in-use projection model is triggered manually by the user. Whenever this happens, the `activate_latest_projector()` method is called, setting the active projector equal to the latest projector. Additionally, whenever the first data is read from the data stream and no projection model has been trained yet, the active projection model will automatically be assigned whenever the first model iteration is done training, rather than this benign triggered by the user. Note that the training of the first projection model iteration is postponed until there is a user-defined number of data entries available to train on. This logic is contained in the `update_projector()` method.

*Note, none of the currently implemented projection methods support hybrid model training (training on both labeled and unlabeled data). As a result, a constant boolean has been declared in `Projector`, `SUPPORTS_HYBRID_MODEL`, that suppresses hybrid training as long as it is set to false. If the labeling of the data frame is hybrid, the data is treated as unlabeled. At the moment it is not possible to configure this boolean per projection method.

### Projection Method Wrapper Classes
In order to allow for new projection methods to be implemented in the program, a minimal design is used where only a wrapper class needs to be implemented along with a few other operations. To see how to implement a new projection method, check the user guide section “Implementing a Projection Method”. 

Each projection method wrapper class implements the `IProjectionMethod` interface. Using an interface construction ensures each wrapper class includes to the required function calls and allows for the Projection class to use a typed variable for the projection method wrapper without needing separate implementations for each of them. The `IProjectionMethod` interface contains four method calls: `get_method_type()`, `fit_new()`, `fit_update()`, and `produce_projection()`. 

- **get_method_type():**<br>
Returns the `ProjectionMethodEnum` value matching the method.

- **fit_new():**<br>
Creates a new instance of the projection model, trained on the provided data. It takes labels and time points as optional arguments. Note that time points may be an unneeded variable for a new projection method, in this case simply add it to the function call regardless and either drop it or ignore it. It is included due to some methods, such as CEBRA, needing it.

- **fit_update():**<br>
A currently unused method that may be required by some projection methods for hybrid fitting of a model. Some methods cannot fit a model using labeled and unlabeled data in a single operation. To enable hybrid fitting, an initial fit using `fit_new()` is done with labels followed by a call to this method that fits the model produced by `fit_new()` without labels.
It is recommended to implement this function to throw a “not implemented” exception if this functionality is not desired or cannot be implemented.

- **produce_projection():**<br>
Transforms the provided data using the projection method stored by the wrapper class.

It might be the case that one of the above methods requires an additional argument to function for a new projection method. Such is the case for the UMAP_approx method. At the moment there is no proper way of handling this. A workaround has been implemented for UMAP_approx in the Projector class, which is also highlighted in the user guide. This is not an ideal solution and will be resolved in a future version.

Hyperparameters required by the projection can be passed as a dictionary in the initiation call. These hyperparameters are extracted from the hyperparameter config file and stored in the hyperparameter field of ProjectorSettings. It is recommended to pass this dictionary to the wrapper class in its initiation call and store it as a private variable. Alternatively, each hyperparameter may be passed separately in the initiation call by touching upon the key-value pairs of the dictionary in the `Projector` class. 


## Plotting

The plotting subprocess is controlled by the `ProjectorPlotManager` which gets called by the `Projector` and `Dashboard`. `ProjectorPlotManager` keeps track of the plot figure and performs the logic specific to the application. For most of the figure mutations, the plot manager relies on the Plotly services. The operations performed by the Plotly services are not specifically tailored to the application, instead, being designed to function as repurposable and reusable services.

Plotly is used to create and alter the plot, which is an instance of `plotly.graph_objects.Figure`

**Traces, points, and ids**<br>
The figure is implemented such that traces are dedicated to one of four functions: displaying projection points, displaying selections, displaying highlights, or producing a correct legend. By adhering to this convention it becomes a lot simpler to mutate and manage the traces required to produce the dynamic plot required for the application. Each trace is a scatter trace, however, they differ in some key aspects that will be covered below. Most of the trace logic is handled in the Plotly services.

*Projection Traces*<br>
The majority of the traces in the figure are used for plotting projection points. These reflect the projected data produced by the projector. Each such point may have a color, which is linked to the projection’s label, and an opacity value. Given that both of these are determined on trace level in the Plotly framework, it is possible to create one trace per label/color and opacity. All projections with a matching color and opacity combination will be plotted into the same trace. Each point in these projection traces contains an id. This id is obtained from the Projector when it calls the `plot()` or `update_plot()` method of the ProjectorPlotManager. Although the ids are integers in the `Projector`, they are stored as strings in the projection traces. This is due to the ids of the other trace types using a string format. 

*Selection and Highlight Traces*<br>
The selection and highlighting of points are also linked to the plotted projection points. However, instead of altering the data of the projection point traces, selections and highlights are instead plotted over these points. This will mean that there is more data contained in the plot, which is suboptimal, however, it allows for a much more convenient mutation of the data in the figure. To avoid confusion for the user the hover info of these points has been disabled. 
Only a single trace is required for the selection of points. Whenever a point is selected, a transparent scatter point is plotted over it (achieved by setting the color to be transparent rather than opacity) and giving the point a visible border. This point has the same size as a projection point, meaning it practically just adds a border to the projection point. Given that there is only one selection trace, it is simply given the id “scatter_selection”. Points in this trace have the id “selection_{point id}”, where the point id matches the id of the point in the projection trace at the same coordinates, i.e. the point that is selected.
A single highlight trace exists per label, meaning that the color of highlights differs depending on the trace (matching the color assigned to the label), however, their opacity is consistent, being 1. Whenever a projection point is highlighted a new point is added to the highlight trace matching the projection point’s label. Highlight traces are given the following id “scatter_highlight_{label}” and highlights points are given the id “highlight_{label}_{point id}”, where the point id matches the id of the point in the projection trace at the same coordinates, i.e. the point that is highlighted.

*Legend Traces*<br>
Lastly, there are traces dedicated to managing the legend. With the figure being dynamic, causing points to constantly be added or removed and labels and opacities to be changed, creating a legend is a bit trickier than usual when using Plotly. The legend refers to the properties of a trace to display a legend element for that trace. The desired behavior, however, is to only display a legend entry per label and not per trace. To accomplish this we do not display any of the traces mentioned above in the legend, instead, a special trace is added to the figure for each label. These are referred to as highlight traces. For each highlight trace, only a single point is plotted. This point is set to a trivially small size and has its hover info hidden such that it is practically invisible. However, because it is fully opacity and has a non-transparent color, it is still displayed in the legend. The legend will use the opacity value, which is set to 1, color, and text of the trace, the latter two are determined by the label. To ensure this legend are is connected to all traces with the same label, each label-specific trace is assigned to a group matching its label. This allows for legend interactions, such as hiding all points of a legend entry.

**Plotly services**<br>
As mentioned earlier, the plotly services are not tailored specifically to this project, instead, they are made to be reusable across different dynamic plotting applications. There are four Plotly services being used in this project `PlotlyScatterService`, `PlotlySelectionService`, `PlotlyHighlightService`, and `PlotlyPlotService`. 
Each of these services implements a specific functionality that may be required for a dynamic figure, utilizing the trace logic as explained in the above section. Each service is responsible for creating the relevant traces and may add points to a trace, move points between traces, or remove a point from a trace. Altering the points belonging to a trace can be done by modifying three lists of the trace: ids, x, and y. 
`PlotlyScatterService` is a bit more extensive than the other three services. It is able to create a scatter plot figure with initial data and all the relevant traces. To accomplish this it maintains an instance of `PlotlySelectionService` and `PlotlyHighlightService`, calling upon them to create the selection and highlight traces. When creating a figure, `PlotlyScatterService` requires an instance of `SactterPlotSettings` to be passed as an argument. These settings are resolved in the `ProjectorPlotManager` using `PlotSettings`. 
`PlotlyPlotService` is not called directly by the `ProjectorPlotManager`, instead, it is inherited by each of the other Plotly services. The `PlotlyPlotService` contains a number of general-purpose functions that are of use to each of the Plotly services. 

On a final note. It is important to highlight that none of the Plotly services retain an instance of a Figure object. As static services, they will require a figure to be passed in their method calls.

**Plot updating**<br>
Through the dashboard, the user may manually trigger a projection model update. This means assigning the latest projection model iteration as the current one. Doing so triggers a process in the projector which calls the `update_plot()` method in `ProjectorPlotManager`. This method does not update the current figure managed by the plot manager, but instead creates a new scatter plot figure through the `PlotlyScatterService`. Afterward, it will also shift the selection and highlights to fit the new projection points. The new coordinates of the projection points are provided by the projector, although, the plot manager does normalize these coordinates to a range between 0 and 1. The new figure is returned to the dashboard where it overwrites the figure stored in the `dcc.graph` object.

**Opacity**<br>
The application supports the feature to reduce the opacity of points over time as new projections are plotted according to some user-defined opacity levels and thresholds. This is implemented in the `ProjectorPlotManager`. Internally, the class keeps track of a dictionary of which scatter point belongs to which opacity level. Whenever new projection points are plotted, the plot manager adds these points to this dictionary. Afterward, it inspects the dictionary, checking for all opacity levels, except the final one, if there are more points registered to be in that level than there should be according to the user-defined threshold. If this is the case, the opacity level of the oldest point is adjusted and the dictionary is updated. This process cascades down the opacity levels. 

**Data normalization**<br>
To allow the axis range of the figure to remain constant (a requirement for the transition animation of the dashboard), the coordinates of the projection points are normalized to a value between 0 and 1. This is applied to each point that is newly added or when a new scatter plot figure is created. 

To perform the normalization operation, the plot manager needs to track the edge values of the projections in the x and y dimensions. To accomplish this, `_update_axis_edge_values()` is called whenever the plot is updated. It is not called upon plotting a new point due to the normalization factors needing to be consistent across all points otherwise the form of the data will be twisted. `_update_axis_edge_values()` simply assigns the highest and lowest coordinate in either dimension to a private variable of the plot manager. Then, whenever the data is normalized, a normalization factor is determined based on the dimension with the greatest range. The normalization factor should be equal in both directions otherwise the shape of the data gets stretched by the normalization.

**Axes ranges**<br>
As stated in the user guide, whenever the range of the x-axis or y-axis is not specified in the config, the application will autoscale the non-defined axis range to match that of the defined axis such that the rendered space between steps along both axes is equal. This operation is handled by the dashboard and `ProjectorPlotManager`. The dashboard will provide the aspect ratio of the horizontal and vertical dimensions of the rendered graph component and the plot manager will use this aspect ratio to rescale one of the axes. The rescaling is done by performing an operation directly on the Figure object, one of the few times this is done in the plot manager without making a call to one of the Plotly services.

**Resolving labels**<br>
The labels used by the plot are expressed in strings. This is preferable due to them needing to be displayed as text in the legend and hover info of the figure. Additionally, the labels are used in certain settings for the plot such as the labels color map. However, the projector uses integers to keep track of the labels. Therefore, whenever a label or multiple labels are passed to the plot manager, a function is called to translate the integer labels to their string counterparts. This is the `_resolve_labels()` method. Upon initiating the plot manager, a dictionary is created mapping the string labels as defined in the config to an integer, where the unclassified label is assigned -1.  `_resolve_labels()` will use this dictionary to map the labels to their string values. Any None and NaN values provided are mapped to the unclassified label.

**Highlighting and Selection**<br>
It is already explained how selections and highlights are incorporated as traces in the [Traces, points, and ids] section. That section detailed how selections and highlights are stored within the figure does but not describe how they are altered and mutated in the `ProjectorPlotManager`. All projection points that are either selected or highlighted are tracked in the plot manager in a list. These lists contain the ids of the projection points that are selected or highlighted. Whenever a point gets (de)selected or its highlight is added/removed, the dashboard will pass the projection point id. This id is queried in the lists to see if the point is already selected or highlighted and the list will get updated accordingly. This does require the selection and highlight lists to be updated whenever a point’s label or opacity is changed. Any changes made to the selection or highlight traces are made through the `PlotlySelectionService` and `PlotlyHighlightService`.


## Dashboard

The dashboard is comprised of the `Dashboard` and `DashboardLayout` classes in addition to the style sheets in the `./dashbaord/assets` folder. It uses the Dash framework to create an interactive web app. Note that it uses the `DashProx` and `MultiplexerTransform` extensions to allow the same component to be targeted as an output in multiple callbacks. Additionally, the dashboard requires an instance of `Projector`, and `ProjectorPlotManager` to perform certain functions. 

**Dashboard layout**<br>
A separate class exists that contains the layout of the dashboard, `DashboardLayout`. An instance of this class is created upon initiation of `Dashboard`. The layout references the style sheets contained in `./dashbaord/assets`. Simply adding a new style sheet to that folder allows the Dash framework to apply it to the layout.

**Plot refreshing**<br>
The main component of the dashboard is the `dcc.Graph` object that contains the Plotly figure of the scatter plot. This graph object needs to constantly be refreshed in order to update the figure. This is done by the `refresh_graph_interval()` callback that is triggered by the interval component `refresh-graph-interval`. The callback uses the private function `_refresh_plot()` to request an up-to-date figure from the `ProjectorPlotManager`. 
`refresh-graph-interval` is disabled when switching to interactive mode, seizing the background refreshing of the plot. However, any callback that causes a change to the plot, such as selecting a point, will still call `_refresh_plot()` such that the `dcc.Graph` object matches the backend figure.

**Buttons**<br> 
Buttons can be disabled by certain callbacks. To reflect this in their style, the class of the button element is changed from “button” to “button-disabled”. Additionally, due to button text not being retained between page refreshes, there is a separate callback, `set_run_pause_button_text()` that is triggered by the `refresh-run-pause-button-text-interval` element. It ensures that the pause-refresh buttons have the correct text, “pause” or “resume”. The callback references a private variable called `_paused_processes` which is a dictionary tracking which projector processes are paused by the dashboard.

**Toggling Application Mode**<br>
The toggling of the application mode is relatively straightforward. The dashboard has been passed a dictionary containing multiprocessing.Event objects by the `ProcessManager` upon initiation. These event objects are used by the `Projecting` and `Updating Projector` events to pause their living processes. Whenever the application mode is toggled by the user, the `toggle_application_mode()` callback method will either set or clear pause flags for both of the subprocesses. If a subprocess was already paused prior to the application mode being switched to “interactive”, it remains paused upon switching back to “projecting” mode.


## General Remarks
- Please note that a hybrid mode of fitting the model of a projection method is currently disabled due to it not being functional for any of the implemented projection methods. If this feature is desired, it can be switched on but should be done so exclusively for the desired projection method. See [Projector -> projector] for more details.











### Projector

The `Projector` is the core of the projector subprocess. It makes calls to the plotting subprocess, reads data from the data stream, keeps track of said data, and directs the projection method wrapper instance to create new projections or train a new instance of the projection model. 

To keep track of the provided data, the `Projector` stores three lists and a data frame. The data frame `_historic_df` contains the data from the data stream, labels, and time points of all data entries that have been used to train the latest projection model iteration. Additionally, `_recent_data`, `_recent_labels`, and `_recent_timepoints` contain similar information, however, this is only for the data entries that have been read from the data stream but have not been used yet for training a projection model. The historic data frame and recent data lists are kept separate due to the `_recent_data` list being a list of data frames. With the `_recent_data` being updated each time a data entry gets projected, which should be at a rate of a few milliseconds ideally, it would be too slow to instead express the list as a singular data frame that constantly gets appended or merged with a new data frame. Instead, the recent data lists are only added to the historic data frame each time a new projection model iteration is trained.

There are three main functions that are implemented by the `Projector`: `project_new_data()`, `update_projector()`, and `activate_latest_projector()`. 

- **project_new_data():**<br> 
This method may be called by `ProjectorContinuesShell` or `Main`.
It starts by reading new data, time points, and labels from the data stream. These variables are then passed to the `project_data()` function which simply calls the projection method wrapper class to use the data to create new projections. The labels and time points are not used for this. The returned projections are then passed to `ProjectionPlotManager` to be plotted as a 2D point in the figure. Finally, the input data, labels, and time points are added to the recent data and the projections count is increased by the number of produced projections.
Before calling the projection method wrapper class, the method first checks if there is an active projection model. If there isn’t, the creation of the projections, plotting of the projections, and increasing the projection counter will be skipped.


- **update_projector():**<br>
This method may be called by `ProjectorContinuesShell` or `Main`.  
Firstly, the historic data frame will be updated using the content of the recent data lists. Afterward, the method determines if the updated historic data frame contains labeled, unlabeled, or hybrid data*. Depending on this, the method trains a new iteration of the projection model. This step takes by far the longest of all operations in the projector subprocess and will dominate its time complexity. When the new iteration has finished training, it is assigned to the  `_projection_model_latest` variable of the `Projector` and the update counter is increased by 1. 
If there is no active projection model set, the new model iteration is automatically assigned to be active.

> **Note.** the currently implemented projection methods, UMAP and CEBRA, do not support hybrid model training. As a result, a constant boolean has been declared in `Projector`, `SUPPORTS_HYBRID_MODEL`, that suppresses hybrid training as long as it is set to false. If the labeling of the data frame is hybrid, the data is treated as unlabeled. At the moment it is not possible to configure this boolean per projection method.

- **activate_latest_projector():**<br>
This method is called by `Dashboard` following an action taken by the user.
The method assigns the latest projection model to the active projection model. Then, using this model iteration, the entire content of the historical data frame is passed to the projection method wrapper class to create new projections. This functionally reprojects all data points using an updated projection model. Once these new projections are obtained, they, along with the labels and time points, are passed to the `ProjectorPlotManager` to create a new scatter plot figure with the new projections.

As mentioned in the above method descriptions, the `Projector` contains two projection model iterations, an active iteration and a latest iteration. These model iterations are stored in the private variables `_projection_model_curr` and `_projection_model_latest`. This split is made due to it being desirable that the updating of the in-use projection model is triggered manually by the user. Whenever this happens, the `activate_latest_projector()` method is called, setting the active projector equal to the latest projector. Additionally, whenever the first data is read from the data stream and no projection model has been trained yet, the active projection model will automatically be assigned whenever the first model iteration is done training, rather than this benign triggered by the user. Note that the training of the first projection model iteration is postponed until there is a user-defined number of data entries available to train on. This logic is contained in the `update_projector()` method.

Lastly, the `Projector` makes use of the pause flags provided by the `ProjectorContinuesShell` to avoid overlapping a projection operation with certain steps of model update operations. Whenever `project_new_data()` is called, an internal boolean called `_projecting_data` is set to true. This boolean is set to false just before the method returns. This boolean is used as a flag for the `update_projector()` and `activate_latest_projector()` methods to await the projecting of a new data point to be finished. Both methods do so whenever updating the historic data frame. Additionally, this is done in `activate_latest_projector()` when creating projections using the updated historic data frame and creating the new scatter plot. Whenever these methods are done awaiting the current projection call to finish, they set the pause flag for the projection thread of the `ProjectorContinuesShell` such that no new projection operations are started until this flag is unset, which occurs later down the line in these methods.


### Projector Continues Shell

The `ProjectorContinuesShell` mainly servers to allow the projector processes to be performed using multi-threading. To achieve this, upon initiating it creates one threat for projecting data, which will continuesly call the `Projector` method `project_new_data()`, and one threat for updating the projector model, which calls `update_projector()`. The frequency at which the threats will call these `Projector` methods depends on the `sampling_frequency` and `model_update_frequency` settings contained in `ProjectorSettings`. 

Upon initiating  `ProjectorContinuesShell` the threads are created but not started. To start the threats a separate call must be made to `start_projecting()` or `start_updating()`. These calls are made when launching the application through the Dareplane Control Room. Similarly, there is a pause and stop method call for both threads.

To manage the pausing and stopping of the threads, `ProjectorContinuesShell` has a number of events: `stop_updating_event`, `pause_updating_event`, `stop_projecting_event`, `pause_projecting_event`, and `updating_projector_event`. The first four are rather self-explanatory and used exclusively by the dashboard. The last event, `updating_projector_event` exists for the Projector to set or unset when updating the projection model or assigning the active projector model. The details of which are explained above in the previous section. 


### Projection Method Wrapper Classes

In order to allow for new projection methods to be implemented in the program, a minimal design is used where only a wrapper class needs to be implemented along with a few other operations. To see how to implement a new projection method, check the user guide section “Implementing a Projection Method”. 

Each projection method wrapper class implements the `IProjectionMethod` interface. Using an interface construction ensures each wrapper class adheres to the required function calls and allows for the Projection class to use a typed variable for the projection method wrapper without needing separate implementations for each of them. The `IProjectionMethod` interface contains four method calls: `get_method_type()`, `fit_new()`, `fit_update()`, and `produce_projection()`. 

- **get_method_type():**<br>
Returns the `ProjectionMethodEnum` value matching the method.

- **fit_new():**<br>
Creates a new instance of the projection model, trained on the provided data. It takes labels and time points as optional arguments. Note that time points may be an unneeded variable for a new projection method, in this case simply add it to the function call regardless and either drop it or ignore it. It is included due to some methods, such as CEBRA, needing it.

- **fit_update():**<br>
A currently unused method that may be required by some projection methods for hybrid fitting of a model. Some methods cannot fit a model using labeled and unlabeled data in a single operation. To enable hybrid fitting, an initial fit using `fit_new()` is done with labels followed by a call to this method that fits the model produced by `fit_new()` without labels.
It is recommended to implement this function to throw a “not implemented” exception if this functionality is not desired or cannot be implemented.

- **produce_projection():**<br>
Transforms the provided data using the projection method stored by the wrapper class.


It might be the case that one of the above methods requires an additional argument to function for a new projection method. Such is the case for the UMAP\_approx method. At the moment there is no proper way of handling this. A workaround has been implemented for UMAP\_approx in the `Projector` class, which is also highlighted in the user guide. This is not an ideal solution and will be resolved in a future version.

Hyperparameters required by the projection can be passed as a dictionary in the initiation call. These hyperparameters are extracted from the hyperparameter config file and stored in the hyperparameter field of `ProjectorSettings`. It is recommended to pass this dictionary the the wrapper class in its initiation call and store it as a private variable. Alternatively, each hyperparameter may be passed separately in the initiation call by touching upon the key-value pairs of the dictionary in the `Projector` class. 


## Plotting

The plotting subprocess is controlled by the `ProjectorPlotManager` which gets called by the `Projector` and Dashboard. `ProjectorPlotManager` keeps track of the plot figure and performs the logic specific to the application. For most of the figure mutations, the plot manager relies on the Plotly services. The operations performed by the Plotly services are not specifically tailored to the application, instead, being designed to function as repurposable and reusable services.

Plotly is used to create and alter the plot, which is an instance of `plotly.graph_objects.Figure`.

<br>**Traces, points, and ids**<br>
The figure is implemented such that traces are dedicated to one of four functions: displaying projection points, displaying selections, displaying highlights, or producing a correct legend. By adhering to this convention it becomes a lot simpler to mutate and manage the traces required to produce the dynamic plot required for the application. Each trace is a scatter trace, however, they differ in some key aspects that will be covered below. Most of the trace logic is handled in the Plotly services.

The majority of the traces in the figure are used for plotting projection points. These reflect the projected data produced by the projector. Each such point may have a color, which is linked to the projection’s label, and an opacity value. Given that both of these are determined on trace level in the Plotly framework, it is possible to create one trace per label/color and opacity. All projections with a matching color and opacity combination will be plotted into the same trace. As a result, the trace is given the following id “scatter\_{label}\_{opacity}”, where “scatter” is simply a prefix used for all traces dedicated to plotting projection points. Additionally, each point in the trace is given an id “{label}\_{opacity}\_{point uid}”. The uid of the point is the way the data of the point is identified outside of the plotting context. This is the time stamp of the original data used to create the projection.

The selection and highlighting of points are also linked to the plotted projection points. However, instead of altering the data of the projection point traces, selections and highlights are instead plotted over these points. This will mean that there is more data contained in the plot, which is suboptimal, however, it allows for a much more convenient mutation of the data in the figure. To avoid confusion for the user the hover info of these points has been disabled. As a result, only a single trace is required for the selection of points. Whenever a point is selected, a transparent scatter point is plotted over it (achieved by setting the color to be transparent rather than opacity) and giving the point a visible border. This point has the same size as a projection point, meaning it practically just adds a border to the projection point. Given that there is only one selection trace, it is simply given the id “scatter\_selection”. Points in this trace have the id “selection\_{point uid}”. Where the point uid once again is the time stamp.

Highlight traces will not differ in opacity, however, they each have a different color matching the label of the highlighted data points. This results in a single highlight trace for each label. Whenever a projection point is highlighted a new point is added to the highlight trace matching the projection point’s label. Highlight traces are given the following id “scatter\_highlight\_{label}” and highlights points are given the id “highlight\_{label}\_{point uid}”.

Lastly, there are traces dedicated to managing the legend. With the figure being dynamic, with points constantly being added or removed and labels and opacities being changed, creating a legend is a bit trickier than expected in Plotly. The legend will refer to the properties of a trace to display a legend element for that trace. The desired behavior, however, is to only display a legend entry for each label. To accomplish this, none of the previously mentioned traces are displayed in the legend. Instead, a special trace is added to the figure for each label which has a single point plotted. This point is set to a trivially small size and has its hover info hidden such that it is practically invisible, but will still show up in the legend. The legend will then take the opacity value, which is set to 1, color, and text of the trace, the latter two are determined by the label, to display an entry. To ensure this legend entry is connected to all traces with the same label, each trace with a label property is linked to a legend group referring to that label. This allows for legend interactions, such as hiding all points of a legend entry, to function as expected.

<br>**Plotly services**<br>
As mentioned earlier, the plotly services are not tailored specifically to this project, instead, they are made to be reusable across different dynamic plotting applications. There are three Plotly services being used in this project `PlotlyScatterService`, `PlotlySelectionService`, and `PlotlyHighlightService`. They each implement specific functionality that may be required for a dynamic figure, utilizing the trace logic as explained in the above section. Each service is responsible for creating the relevant traces and may add points to a trace, move points between traces, or remove a point from a trace. Altering the points belonging to a trace is as simple as modifying the ids, x, and y lists of a trace. `PlotlyScatterService` is a bit more extensive than the other two services. It is able to create a scatter plot figure with initial data and all the relevant traces. To accomplish this it maintains an instance of `PlotlySelectionService` and `PlotlyHighlightService`, calling upon them to create the selection and highlight traces. When creating a figure, `PlotlyScatterService` requires an instance of `SactterPlotSettings` to be passed as an argument. These settings are resolved in the `ProjectorPlotManager` using `PlotSettings`. 

There exists a fourth Plotly service, `PlotlyPlotService`, that is also used in the application. This service is not called directly, instead, it is inherited by each of the other Plotly services. The `PlotlyPlotService` contains a number of general-purpose functions that are of use to each of the Plotly services. 

On a final note. It is important to highlight that none of the Plotly services retain an instance of a `Figure` object. As static services, they will require a figure to be passed in their function calls.

<br>**Plot updating**<br>
Through the dashboard, the user may manually trigger a projection model update. This means assigning the latest projection model iteration as the current one. Doing so triggers a process in the projector which calls the `update_plot()` method in `ProjectorPlotManager`. This method does not update the current figure managed by the plot manager, but instead creates a new scatter plot figure through the `PlotlyScatterService`. Afterward, it will also shift the selection and highlights to fit the new projection points. The new coordinates of the projection points are provided by the projector, although, the plot manager does normalize these coordinates to a range between 0 and 1.  The new figure is returned to the dashboard where it overwrites the figure stored in the `dcc.graph` object.

Note that the plot manager isn’t aware whether it can or cannot receive projections of data points that haven’t been projected yet when `update_plot()` is called. To handle the scenario where this is the case, all new projections are assigned to the highest opacity level and a call to `_reduce_opacity()` is made in the case there were new projection points.

<br>**Opacity**<br> 
The application supports the feature to reduce the opacity of points over time as new projections are plotted according to some user-defined opacity levels and thresholds. This is implemented in the `ProjectorPlotManager`. Internally, the class keeps track of a dictionary of which scatter point belongs to which opacity level. Whenever new projection points are plotted, the plot manager adds these points to this dictionary. Afterward, it inspects the dictionary, checking for all opacity levels except the final one if there are more points registered to be in that level than there should be according to the user-defined threshold. If this is the case, the opacity level of the oldest point is adjusted and the dictionary is updated. This process cascades down the opacity levels. 

<br>**Data normalization**<br>
To allow the axis range of the figure to remain constant (a requirement for the transition animation of the dashboard), the coordinates of the projection points are normalized to a value between 0 and 1. This is applied to each point that is newly added or when a new scatter plot figure is created. 

To perform the normalization operation, the plot manager needs to track the edge values of the projections in the x and y dimensions. To accomplish this, `_update_axis_edge_values()` is called whenever the plot is updated. It is not called upon plotting a new point due to the normalization factors needing to be consistent across all points otherwise the form of the data will be twisted. `_update_axis_edge_values()` simply assigns the highest and lowest coordinate in either dimension to a private variable of the plot manager. Then, whenever the data is normalized, a normalization factor is determined based on the dimension with the greatest range. The normalization factor should be equal in both directions otherwise the shape of the data gets stretched by the normalization.

<br>**Axes ranges**<br>
As stated in the user guide, whenever the range of the x-axis or y-axis is not specified in the config, the application will autoscale the non-defined axis range to match that of the defined axis such that the rendered space between steps along both axes is equal. This operation is handled by the dashboard and `ProjectorPlotManager`. The dashboard will provide the aspect ratio of the horizontal and vertical dimensions of the rendered graph component and the plot manager will use this aspect ratio to rescale one of the axes. The rescaling is done by performing an operation directly on the Figure object, one of the few times this is done in the plot manager without making a call to one of the Plotly services.

<br>**Resolving labels**<br>
The labels used by the plot are expressed in strings. This is preferable due to them needing to be displayed as text in the legend and hover info of the figure. Additionally, the labels are used in certain settings for the plot such as the labels color map. However, the projector uses integers to keep track of the labels. Therefore, whenever a label or multiple labels are passed to the plot manager, a function is called to translate the integer labels to their string counterparts. This is the `_resolve_labels()` method. Upon initiating the plot manager, a dictionary is created mapping the string labels as defined in the config to an integer, where the unclassified label is assigned -1.  `_resolve_labels()` will use this dictionary to map the labels to their string values. Any `None` and `NaN` values provided are mapped to the unclassified label.

<br>**Highlighting and Selection**<br>
It is already explained how selections and highlights are incorporated as traces in the “Traces, points, and ids” section. That section detailed how selections and highlights are stored within the figure does but not describe how they are altered and mutated in the `ProjectorPlotManager`. All projection points that are either selected or highlighted are tracked in the plot manager in a list. These lists contain the ids of the projection points that are selected or highlighted. Whenever a point gets (de)selected or its highlight is added/removed, the dashboard will pass the projection point id. This id is queried in the lists to see if the point is already selected or highlighted and the list will get updated accordingly. This does require the selection and highlight lists to be updated whenever a point’s label or opacity is changed. Any changes made to the selection or highlight traces are made through the `PlotlySelectionService` and `PlotlyHighlightService`.


## Dashboard

The dashboard is comprised of the `Dashboard`, `DashboardThread`, and `DashboardLayout` classes in addition to the style sheets in the `./dashbaord/assets` folder. It uses the Dash framework to create an interactive web app. Note that it uses the DashProx and MultiplexerTransform extensions to allow the same component to be targeted as an output in multiple callbacks. The `DashboardThread` class only acts as a shell class for creating the dashboard thread, other than that it does not add any functionality.

**Registered and active projectors**<br>
The dashboard requires an instance of `ProjectorContinuesShell`, Projector, and `ProjectorPlotManager` to perform certain functions. Instead of passing an instance of these objects, the `Dashboard` class requires a projector to be registered and activated. A projector can be registered by calling the `register_projector()` method by passing either a Projector or `ProjectorContinuesShell` instance. Note that some functionalities only work when passing a `ProjectorContinuesShell` instance. Multiple projectors can be registered at a time. This allows for future scalability if it’s ever desired to run the dashboard with multiple projectors. The active projector, which is the projector that the dashboard will refer to, can be set using `set_active_projector()`. This method requires the id of a registered projector. If no projector is set as active, any callback that requires the backend of the application will not function. 


**Dashboard layout**<br>
A separate class exists that contains the layout of the dashboard, `DashboardLayout`. An instance of this class is created upon initiation of `Dashboard`. The layout references the style sheets contained in `./dashbaord/assets`. Simply adding a new style sheet to that folder allows the Dash framework to apply it to the layout.

**Plot refreshing**<br>
The main component of the dashboard is the `dcc.Graph` object that contains the Plotly figure of the scatter plot. This graph object needs to constantly be refreshed in order to update the figure. This is done by the `refresh_graph_interval()` callback that is triggered by the interval component `refresh-graph-interval`. The callback uses the private function `_refresh_plot()` to request an up-to-date figure from the `ProjectorPlotManager`. 
`refresh-graph-interval` is disabled when switching to interactive mode, seizing the background refreshing of the plot. However, any callback that causes a change to the plot, such as selecting a point, will still call `_refresh_plot()` such that the `dcc.Graph` object matches the backend figure.

**Buttons**<br>
Buttons can be disabled by certain callbacks. To reflect this in their style, the class of the button element is changed from “button” to “button-disabled”. Additionally, due to button text not being retained between page refreshes, there is a separate callback, `set_run_pause_button_text()` that is triggered by the `refresh-run-pause-button-text-interval` element. It ensures that the pause-refresh buttons have the correct text, “pause” or “resume”. The callback references a private variable called `_paused_processes` which is a dictionary tracking which projector processes are paused by the dashboard.

**Toggling Application Mode**<br>
The toggling of the application mode is relatively straightforward. The dashboard calls `ProjectorContinuesShell` to pause or unpause the projection and projector model update processes. Keep in mind this will not interrupt the threads, but stop the threads from starting a new iteration of the processes, meaning the current iteration will continue. Toggling interactive mode will update the internal list of paused processes that all processes are paused. However, not all processes should be unpaused when switching back to projecting mode, the pause state of a process should be retained. For that purpose, there is a similar dictionary called `_paused_processes_retained` which serves as a temporary copy of `_paused_processes` whenever interactive mode is toggled on.


## General Remarks

- Please note that a hybrid mode of fitting the model of a projection method is currently disabled due to it not being functional for any of the implemented projection methods. If this feature is desired, it can be switched on, but should be done so exclusively for the desired projection method. See [Projector -> projector](#projector) for more details.


