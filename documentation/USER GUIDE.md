# Online Neurodata and Embedding Projector (ONEP)

This project is made to function as a module for the [Dareplane](https://github.com/bsdlab/Dareplane) Framework. Familiarity with the Dareplane Control Room module is assumed. The relevant functionality of the Control Room module is limited to registering a module and importing an input stream.

The ONEP module allows a user to feed a stream of data into a dimensionality reduction model, such as UMAP or CEBRA, in order to create and visualize a 2D image. This process will be referred to as projecting. Projecting data from the input stream is executed in real time, allowing for new data points to be displayed in the 2D projection space whenever new data is published to the stream. Additionally, the data from the input stream is used to train the underlying projection model, allowing for improved projections over time. ONEP includes a simple graphical interface and the possibility to implement new or custom projection methods/algorithms.

Note that launching the application may take a few minutes.


## Launch Steps

1. Copy or clone the project code from the GitHub.
2. Install the dependencies from the requirement.txt file.
3. If needed, implement the desired projection method (see [Implementing a Projection Method](#Implementing-a-Projection-Method)).
4. Adjust the configuration file (see [Configuration File](#Configuration-File)).
5. If needed, add or adjust the relevant hyperparameter file (see [Configuration File](#Configuration-File)).
6. Start the program in one of three ways:
    * Launch ONEP through the Dareplane Control Room module
    * Run api/server.py to run ONEP with a server entry point.
    * Run console_interface.py to run ONEP as a console application.
7. Run or send the “Launch”. This will open the user interface in the browser and prepare the program for projecting. Note, that the interface may take a moment to become reachable through the browser.
8. Once the ONEP UI is available on your browser, run the “Start Projecting” command. Executing this command will allow the projector to begin reading data from the data stream, using it to train the projection model and create projections to display in the 2D figure.


## Termanology

- **Data/input stream:** Stream exposed to ONEP. The stream may contain the feature data, label data, and timestamps used by ONEP to create projections and train the underlying model.
- **Sample:** Singular data entry read from the input stream. In the context of reading from the input stream, a sample refers to the complete entry read from the stream. Otherwise, a sample is a combination of the following: a set of features, a time stamp, and optionally a class label.  
- **Projecting:** Transforming data from a higher dimensional space to a 2D space.
- **Projection:** The result of projecting data from the input stream to the 2D space.
- **Projected/Projection Point:** The projection of a data point from the input stream specifically referred to in the context of the 2D space to which it is projected.
- **Projection model:** An instance of a projection algorithm such as UMAP or CEBRA. Projection models can be trained with higher dimensional data in order to learn how to project such data to a lower dimensional (2D) space.
- **Projector:** The component of the application that is responsible for training and maintaining a projection model and producing projections using this model. It also reads data from the input stream and triggers the event to plot projected data.
- **Projector processes:** The two main tasks performed by the projector: training new projection models/model iterations and reading, projecting, and plotting data from the data stream. These processes are performed independently, each running on its own dedicated threat. 
- **Projector (model) iteration:** An instance of a trained projection model, managed by the projector. Not every new iteration will automatically be used by the projector. They are referred to as iterations for two reasons. 1\) A newly trained projection model is identical to the previous model in terms of settings and hyperparameters. 2\) The data used to train previous iterations is a subset of the training data for the new iteration.
- **Updating projector (model):** Setting the projection model iteration used by the projector to the latest iteration that has been trained.
- **Dashboard:** The user interface (UI) of the application as shown in the browser.
- **Plot/figure:** The scatter plot figure onto which the projected points are plotted. This figure is shown on the dashboard. 


### Input Stream
ONEP is able to read feature data and class labels from the datastream(s) available to it. ONEP is designed to extract such features and labels from a wide array of streams, as long as the relevant aspects of the streams have been correctly set in the configurations. ONEP is developed to receive Lab Streaming Layer (LSL) streams.

### Feature and Auxiliary Stream
ONEP can receive up to two streams at once, a feature stream and an auxiliary stream. The feature stream is primarily used to supply the feature data, however, it may also contain label data. The auxiliary stream may be used to supply label data in case this data is sent on a separate stream from the feature data. In the configuration file, the name of the feature and auxiliary stream may be set (see [Configuration File - Stream Settings](#Configuration-File)). 

### Stream Sections
In order to retrieve features and labels from the input stream(s), ONEP uses a concept called stream sections. These sections can be defined in the configurations, requiring a reference name, a starting index, and a length. When reading out a stream, whenever a section is read out, the program will use the start index and length of the section to determine where it exists within a sample. ONEP requires one stream section to be defined for reading out the features. If it is desired to read labels from (one of) the input streams, there should be a separate section defined for the labels. Sections containing neither feature nor label data do not need to be defined, these are ignored by ONEP.


### Label Interpretation
ONEP can currently only function with a singular set of labels, i.e. one label per sample. However, it may be the case that the label should be based of a set of scores or classification results. ONEP can handle such a situation through the implementation of an interpreter. In the config, the method of interpreting the label function may be defined. This interpretation function translates the label section into an integer, float, or string which can be used by ONEP. At the time of writing the following three interpretation functions are defined:
- *as-is*: interprets the stream section identical to how it is provided; may only be used when the label section is of length 1.
- *Index of highest*: Assigns the label to be the index of the highest numerical value in the section. Indices are section-based, i.e. the first index of the section is index 0. Requires the section values to be in the same order as the labels as defined in the general config. Can only be used for numerical values.
- *Index of lowest*: Identical to index of heights, except the index of the lowest numerical value is selected.
It is possible for a user to define a custom interpretation function in the stream_reading/stream_interpreter.py file.


### Stream Matching
When the labels are read from the auxiliary stream, ONEP will need to match the feature samples from the feature stream with the label samples. To do so, ONEP can utilize either the LSL timestamps that are automatically assigned to each stream, or extract a sample match id from each stream sample to match based on those. The sample match id should be given as an integer or float at any position in the sample. Using the config, the position of the sample match id can be defined. 
How exactly the timestamps or sample match ids are matched is determined by the sample matching scheme. This scheme can be set in the configuration. By default, ONEP supports three schemes for both the timestamps and sample match ids:
- *Match-samples*: (timestamps) Matches each label to the feature with the nearest timepoint, or (sample match ids) matches all features to the label with an identical sample match id. Multiple features can be matched to the same label when using the sample match ids. 
- *Until-next*: Matches a label to each feature for which the feature timestamp or match sample id is greater or equal to that of the label, but less than that of the next label. Intended to match multiple features to the same label.
- *From-previous\**: Matches a label to each feature for which the feature timestamp or match sample id is less or equal to that of the label and greater than that of the next label. Intended to match multiple features to the same label.
It is possible for a user to define a custom matching scheme in the stream_reading/stream_matcher.py file.

*not implemented yet at the time of writing.


### Quick Guide to the Stream Configuration
Setting up the config for the input stream may be challenging for a novel user, therefore, this section will provide a brief list of scenarios and which settings to assign. Note, there is a full list explaining all settings in the configuration in the later Configuration File section.

*Features are read from a singular stream, no labels are read:*
- Set “feature-stream-name” to the stream containing the features
- Set “watch-labels” to false
- Add a “feature-stream-layout” section:
    * Set “id-index” to an empty string or leave out unless sample ids are used in the stream 
    * Add a “section” section for features:
        * * Set “name” to the section name (user’s choice)
        * * Set “start-index” to where the features start in a stream sample (likely 0)
        * * Set “length” to the number of features
- Set “feature-section” equal to the name of the feature stream section “name”

*Features and labels read from a singular stream:*
- Copy steps from Features are read from a singular stream, no labels are read
- Set “watch-labels” to true
- Set “labels-from-auxiliary-stream” to false
- Set “label-interpretation-method” to the desired interpretation method
- In the “feature-stream-layout” section:
    * Add “section” section for labels:
        * * Set “name” to the section name (user’s choice)
        * * Set “start-index” to where the labels start in a stream sample
        * * Set “length” to the number of entries in a stream sample used for the labels (1 if the ‘one-to-one’ interpretation method is used)
- Set “label-section” equal to the name of the label stream section “name”

*Features and labels are read from separate streams, match by timestamp:*
- Copy steps from Features are read from a singular stream, no labels are read
- Set “watch-labels” to true
- Set “labels-from-auxiliary-stream” to true
- Set “label-interpretation-method” to the desired interpretation method
- Set “match-by-sample-id” to false
- Set “label-feature-matching-scheme” to the desired scheme
- Add an “auxiliary-stream-layout” section:
    * Set “id-index” to an empty string or leave out unless sample ids are used in 
    * Add “section” section for labels:
        * * Set “name” to the section name (user’s choice)
        * * Set “start-index” to where the labels start in a stream sample (likely 0)
        * * Set “length” to the number of entries in a stream sample used for the labels (1 if the ‘one-to-one’ interpretation method is used)
- Set “label-section” equal to the name of the label stream section “name”

*Features and labels are read from separate streams, match by sample id:*
- Copy steps from Features and labels are read from separate streams, match by timestamp
- Set “match-by-sample-id” to true
- In the “feature-stream-layout” section:
    * Set “id-index” to the location of the match id in a stream sample
- In the “auxiliary-stream-layout” section:
    * Set “id-index” to the location of the match id in a stream sample


## User Interface
<picture>
    <source srcset="./assets/dashboard.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dashboard.png">
</picture>

### Figure
The majority of the interface contains the plot/figure that displays the projected data points. Data points are regularly projected to this figure as long as the projecting process of the projector is running. 

**Labeling**<br>
Points are assigned a color matching their label. The color relates to which label is shown in the figure’s legend and can be set in the “plot settings” section of the configuration file (see [Configuration File](#Configuration-File)).

<br>**Opacity**<br>
As new projections are plotted, previous data points will be reduced in opacity. Changing of opacity is not done gradually, instead, points are assigned an opacity level based on how recently they were plotted. Upon plotting a new point, the oldest points in an opacity level are moved over to the next level, usually of a lower opacity value, i,e, more translucent. This will continue until a point is assigned a minimum, user-defined, opacity value.

The opacity levels and how many data points are assigned to each level can be set in the configuration file (see [Configuration File](#Configuration-File)). By default, there are five configured opacity levels: 1.0, 0.75, 0.5, and 0.25. Here 0.25 is the minimum opacity value.

<br>**Selection and Highlighting**<br>
Using the interface, points may be selected and given a highlight (see Select and Assign Highlight or Label). Selected points will be given a border. The color and width of this border can be set in the configuration settings (see [Configuration File](#Configuration-File)). By default, the color is set to gray. 

Selected points can also be highlighted. Highlights will be retained upon updating the projector model and will always be set to an opacity value of 1, meaning fully opaque. Additionally, highlighted points are increased in size and given a border. The highlight size, border, and border size can each be set in the configuration (see [Configuration File](#Configuration-File)).

<br>**Updating Projector**<br>
Whenever a new iteration of the projector model is selected, all projected data points will be recomputed and the figure will be updated with the new projections. This means that all data points are plotted anew, making it seem as if all points are being shifted in the figure.
 
To make it easier for the user to track the shifting of the points, the Plotly backend utilizes a transition animation. Visually, this will appear to the user as if the points are moving around in the 2D space, moving to their new position in a straight line. The duration of this transition animation can be set in the configuration (see [Configuration File](#Configuration-File)). By default, this transition lasts 500 ms.

<br>**Axis**<br>
The coordinates in the 2D image of the projected data are in an arbitrary unit and their absolute value is not relevant, only the relative position between the projected points should be considered. For this reason, the axes are automatically rescaled and their values are hidden by default. Axes step values can be shown by changing the configuration option `show-axis` to true (see [Configuration File](#Configuration-File)).

Note, for technical reasons, the plotted data is normalized to a 0-1 range, meaning the coordinates of the data points in the figure should not be seen as informative. The shape and the relative distance of the projected points are maintained while normalizing. 

Additionally, the range of the axis is automatically rescaled on a page refresh (including the initial page load) in order to ensure the figure is visualized as a square space. Meaning that the displayed distance between the steps along each axis is of equal size. This scaling is done based on the size of the monitor. As such, **if the window containing the UI is moved to a monitor of a different size, it is recommended refresh the page**.


### <br>Projecting and Interactive Mode
<picture>
    <source srcset="./assets/dashboard-application-mode.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dashboard-application-mode.png">
</picture>

The interface allows a user to switch the application between two modes, projection mode and interactive mode. By default, the application will run in projection mode. 

**Projection Mode**<br>
The application will read data from the input stream, train the projection model, and create projections that are displayed in the figure. When the application is in this mode, available interactions with the figure are limited. For example, zooming in to a specific area or selecting a multitude of points is not possible. It is still possible to select individual points in the figure. 

<br>**Interactive Mode**<br>
This mode enables the user to interface with the figure freely. It is recommended to activate this mode whenever intending to highlight data points or change their labels. Upon activating this mode, the projector processes are paused (see [Pausing Projector Processes](#Pausing-Projector-Processes)). When interactive mode is switched off, projector processes are resumed. If a projector functionality was already paused upon activating interactive mode, it will not be unpaused upon toggling off interactive mode. It is not possible to turn on any of these projector processes while interactive mode is active.


### <br>Pausing Projector Processes
<picture>
    <source srcset="./assets/dashboard-pause-resume-buttons.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dashboard-pause-resume-buttons.png">
</picture>

In the background, two processes are active that are managed by the projector. 1\) projecting and plotting new data points, 2\) training a new iteration of the projector. Either of these processes can be paused at any point. 

Note that pausing either of these processes will not halt their current operation. If a data point is being projected, pausing this process will allow the application to finish projecting this point, however, it will not start projecting any new points until it is unpaused. Similarly, when pausing the projection model updating, the application will continue training a model if this process has already started, but will not start a new training session until this process has been unpaused.

If it is desirable to interrupt the current training or projection process, it is recommended to make use of the `Stop Projector` command in the control room (see [Control Room Commands](#Control-Room-Commands)).

Upon switching to interactive mode, both projector processes will be paused. 


### <br>Activate Latest Model Iteration
<picture>
    <source srcset="./assets/dashboard-model-iteration-update.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dashboard-model-iteration-update.png">
</picture>

As new iterations of the projection model are trained, these iterations will become available. To make it easier to keep track of the projections, the figure is not automatically updated to utilize the latest model iteration. Instead, by clicking the “apply latest iteration” button, the latest model iteration can be applied manually at a time convenient to the user. This may be done in both projection and interaction mode. 

The counter noted “currently used” refers to the iteration of the projector model that is currently being used to project novel data points and display them in the figure. The counter noted “latest available” displays the latest iteration of the projector model that has been trained and may be applied as the active model version.

The “Update Display Model” is disabled by default, becoming interactable the moment there is a newer iteration available compared to the one being used.


### <br>Select and Assign Highlight or Label
<picture>
    <source srcset="./assets/dashboard-selection-highlighting.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dashboard-selection-highlighting.png">
</picture>

When in interactive mode, the standard Plotly box-select and lasso-select functions can be used to select one or multiple points on the figure. Alternatively, a single point may be selected or deselected by being clicked on. Selected points will by default be given a gray border. This visual effect might differ based on the provided configurations (see [Configuration File](#Configuration-File)). 

> **Note.** The application currently displays some odd behavior when it comes to selecting and deselecting points by clicking on them. When selecting a point by clicking on it, the same point cannot be clicked again immediately in order to deselect it. Instead, click on a different point first, then on the previously selected point or use the “Deselect Points” button.

<br>**Assigning a label**<br>
Upon selecting one or multiple points in the figure, it becomes possible to select a label from the dropdown menu. The user may select a desired label and press the “submit” button to apply this label to all of the selected points. 

<br>**Highlighting**<br>
By selecting the “highlight” button, the application will highlight all selected points. By default, these points will increase in size, are applied a gray border, and become opaque. They will retain this highlighting until it is removed by the user. Highlights of selected points can be removed by pressing the “Remove Highlight” button. All highlights may be removed by pressing the “Clear All Highlights” button. Note that this will remove highlights of all points, even those that are not selected.


## Server/Console Interface Commands
<picture>
    <source srcset="./assets/dareplane-control-room.png"  media="(prefers-color-scheme: dark)">
    <img src="./assets/dareplane-control-room.png">
</picture>

In addition to the default `Stop` and `Close` control room commands, ONEP introduces three additional commands: `Launch`, `Start Projector`, and `Stop Projector`.

**Launch**<br>
Launches the ONEP dashboard and initiates the projector. No training of the projector model is done at this point, nor any reading from the data stream.

<br>**Start Projector**<br>
Starts the projector processes to train new iterations of the projector model and to project data points once the first model iteration has been trained.

<br>**Stop Projector**<br>
Stops the above-mentioned projector processes. Note, unlike the pause buttons of the dashboard, this command will interrupt the threads of the projector processes, meaning the current iteration being trained and the projection being created will be lost.

<br>**Exit** (console interface only)<br>
Shut down the application.


> **Note.** After running the `Stop Projector` command, it is possible to resume the projector processes by running `Start Projector`. The internal state of the application will be retained, meaning the figure and projector model iterations are still available. Do note that the application does not read from the data stream whenever the projector is stopped.


## Configuration File

The configuration file can be found at  `./configs/config.toml`.

It is possible to either change the existing configuration file or add a new one. To set the configuration file used by the application, assign the variable `config_file_name` in main.py with the target configuration file. If the file is placed in a different folder than the default configuration file, also update the config_folder variable to reflect this.

Additionally, there is a folder called `./configs/hyperparameters`. This folder contains the configuration for the hyperparameters used by the projection method. Given that each projection method has varying hyperparameters, there is no template for these files. Hyperparameter config files already exist for all implemented projection methods. The general settings contain a mapping between the projector method and its hyperparameter config file location.

### General Settings
- **host** *[string]*: Address used by ONEP to expose itself.
- **host** *[int]*: Port used by ONEP to expose itself.
- **dashboard-host** *[string]*: Address used by ONEP to run the web interface.
- **dashboard-port** *[int]*: Port used by ONEP to run the web interface.
- **data-stream-name** *[string]*: The name of the data/input stream as configured in the Dareplane Control Center. Will be ignored when the data stream name is passed in the `Launch` command.
- **labels** *[list of strings]*: An exhaustive list of labels assigned to the data. If the data contains a label that is not in this list, the application is prone to throw errors or produce undesired behavior.
- **unclassified-label** *[string]*: The label given to any unclassified data points.
- **hyperparameter-config-folder** *[string]*: Path to the folder containing the hyperparameter config files. The path is relative to `main.py`.
- **hyperparameter-config-files** *[dictionary of ProjectionMethodEnum-string]*: Denotes the file name of the hyperparameter config file matchin a specific projection method.


### Projector Settings
- **projection-method** *[string]*: Specifies which projection algorithm to be used by the projector. Will throw an error after running the `Launch` command in the control room when this value refers to an unimplemented projection method.
- **align-projections** *[bool]*: Optional setting used by some projection methods to align projection spaces upon updating the model. Only of use for projection methods that provide alignment as an option and this option is implemented in the related method class.
- **use-mock-data** *[bool]*: Toggles the projector to use mock data instead of reading data read from a stream. When set, the stream watcher is not used (so stream-settings can be left out). Should only be used for testing or debugging purposes.
- **min-training-samples-to-start-projecting** *[int]*: Numbers of data samples required to be read before the first model is trained by the projector. 
- **max-sampling-frequency** *[float]*: The maximum frequency at which data points are projected and plotted. Also determines the frequency at which data is read from the stream (this does not affect the stream buffer size). The true sampling frequency may be lower than the provided value if the application projects and plots data at a slower rate than the provided frequency.
- **max-model-update-frequency** *[float]*: The maximum frequency at which the projector is updated. The true update frequency may be lower than the provided value if the application creates new model iterations at a slower rate than the provided frequency.


### Plot Settings
- **scatter-point-size** *[float]*: Size of the projection points of the figure.
- **point-selection-border-size** *[float]*: Size of the border of a selected point. 
- **point-selection-border-color** *[string]*: Color of the border of a selected point.
- **point-highlight-size** *[float]*: Size of a highlighted point.
- **point-highlight-border-size** *[float]*: Size of the border of a highlighted point.
- **point-highlight-border-color** *[string]*: Color of the border of a highlighted point.
- **unclassified-label-color** *[string]*: Color of the unclassified label.
- **min-opacity** *[float]*: Minimum opacity that can be assigned to a point.
- **show-axis** *[boolean]*: Whether to show the numerical values along the axes.
- **transition-duration** *[float]*: Duration of the transition animation in milliseconds.
- **label-colors** *[dictionary of string-string]*: The colors to be used for the labels of the data. Not all labels need to be assigned a color. Unassigned labels will be given a random color whenever the application is launched.
- **opacity-thresholds** *[dictonary of float-int]*: Each opacity level and the maximum number of points that may belong to that level. The order of the opacity levels used by the application matches the order of the entries of this field.
- **default-x-range** *[float, float]*: The static range of the x-axis of the figure. May be provided a start and end value. This will not change the normalization of the data points, meaning this field primarily sets the empty space surrounding the [0-1] range in which the data points are plotted. Must be empty If automatic scaling of the x-axis is desired (see User [Interface - Figure - Axes](#Axis)).
- **default-y-range**  *[float, float]*: The static range of the y-axis of the figure. May be provided a start and end value. This will not change the normalization of the data points, meaning this field primarily sets the empty space surrounding the [0-1] range in which the data points are plotted. Required If automatic scaling of the x-axis is desired (see User [Interface - Figure - Axes](#Axis)).


### Dashboard Settings
- **graph-refresh-rate-per-ms** *[float]*: Number of times the figure is refreshed on the dashboard. Only when the figure is refreshed, changes, such as new data points, will be displayed in the UI. The refresh rate is only used during projection mode. During interactive mode, the figure is refreshed upon each action taken by the user that leads to a change to the figure. 


### Stream Settings
The stream settings may be complicated for a novel user. For a brief guide on which settings to set see [Input Stream - Quick Guide to the Stream Configuration](#quick-guide-to-the-stream-configuration).  
- **feature-stream-name** *[string]*: The name of the LSL stream that carries the features.
- **auxiliary-stream-name** *[string]*: The name of the LSL stream that carries the labels if these are not in the same stream as the features.
- **stream-buffer-size-s** *[float]*: Size of the buffer used when reading from the data stream, given in seconds. Determines the number of data points that may be read from the stream at once. The true buffer size is based on this field and the sampling frequency of the stream. 
- **feature-section** *[string]*: Name of the stream section that describes how the features are contained in the feature stream.
- **watch-labels** *[bool]*: Whether to read labels from the (feature or auxiliary) stream. If false, all samples are read as unclassified.
- **label-section** *[string]*: Name of the stream section that describes how the labels are contained in the feature or auxiliary stream.
- **labels-from-auxiliary-stream** *[bool]*: True if the labels should be read from the auxiliary stream, false if they should be read from the feature stream.
- **label-interpretation-method** *[string]*: Method used to interpret/resolve the labels from the stream.
- **match-by-sample-id** *[bool]*: If labels are read from the auxiliary stream, determine if matching of the feature and auxiliary streams should be done using sample match ids. If false, match streams using their LSL timestamps.
- **auxiliary-stream-drift-ms** *[float]*: Delay of the auxiliary stream compared to the feature stream. Is only relevant when matching the streams using timestamps.
- **feature-stream-layout** *[StreamLayout]*: Layout of the feature stream.
- **auxiliary-stream-layout** *[StreamLayout]*: Layout of the auxiliary stream.
StreamLayout:
- **id-index** *[int]*: Index of the sample match id. Relevant only when matching by sample id. However, if no such matching is done and the sample id is included in the stream, watch out to reflect that in the start index of the stream sections (e.g. if the sample id is at position 0 of the feature, then the start index of the feature section should not be 0, but at least 1).
- **section** *[StreamSection]*: Sections of the stream.
StreamSection:
- **section-name** *[string]*: User-given name to the stream section, used by “feature-section” and “:label-section” settings.
- **start-index** *[int]*: First position of the section.
- **length** *[int]*: Length of the section.


## Implementing a Projection Method
ONEP allows users to add additional projection algorithms in a relatively simple manner. The most important part of adding an algorithm is creating a method class that contains a number of function definitions that are called by the Projector class. This can be achieved by ensuring that your wrapper class is compatible with the `projection_method_interface.py` interface class, i.e. the method class should implement this interface.

When creating your method class, there are two recommended methods to implement the required functions. Either import the method as a package if this is available or import the Git source code of the method, optionally as a submodule. The latter option requires a bit more work. For an example of either option, see `umap_proj_method.py` and `cebra_proj_method.py` in the `projector/projection_methods` folder. The UMAP method class is implemented using a package reference while the CEBRA method uses a Git submodule.

Below a step-by-step guide is given on how to implement a new projection method.

**When using a package reference in the projection method class**
1. Install the package in your environment 
2. (optionally) add the package reference to the Requirements.txt file

**When using a Git submodule in the projection method class**
1, Import the method source code, optionally as a Git submodule. Recommended: select the following folder as the import/submodule destination:  
`./embedding_projector/projection_method/submodules/[your method]`
2. Add the path to the imported code/submodule in the reference paths of the `depency_resolver.py`. It should look similar to the CEBRA submodule path which is already added.

**General steps**
1. Expand the projection_methods_enum.py class with an enum entry for your class.
2. Create a class in the projector/projection_methods folder.
3. Use the function description as given in the projection_method_interface.py interface to implement all required functions in your wrapper class and have the wrapper class implement the interface. See the umap_proj_method.py and cebra_proj_method.py files for an example.
* Note that in the existing method classes arguments for the methods are obtained from a kwargs dict object. It is strongly recommended to adopt this implementation in a custom method class due to the Projector class passing a set amount of parameters, some maybe not be needed for the custom method class. The kwargs implementation helps avoid errors. Which parameters are contained in the kwargs dict are given in projection_method_interface.py.
* Hyperparameters should be set in the configuration file according to how they are named in the projection model class. This means that the hyperparameters parameter in the __init__() method is a keyword argument dictionary that can be directly passed to the model instance of the projection method.
I4. n the `main_projector.py` class, expand the match statement in the *_resolve_projection_method()* function to include the initiation of the custom method class.