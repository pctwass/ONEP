# Online Neurodata and Embedding Projector (ONEP)

The Online Neurodata and Embedding Projector (ONEP) module allows a user to feed a stream of data into a dimensionality reduction model, such as UMAP or CEBRA, in order to visualize it in real-time as a 2D image. This process will be referred to as projecting. Projecting data from the input stream *in real-time* means that new data points are displayed in the 2D projection space whenever new data is published to the stream. Additionally, the data from the input stream is used to train the underlying projection model, allowing for improved projections over time. ONEP includes a simple graphical interface and the possibility to easily implement new or custom projection methods/algorithms.


## Startup

1. Copy or clone the project code from the GitHub.
2. Install the dependencies from the `requirement.txt` file.
3. Pull git submodules,
    `git submodule update --recursive --remote`
4. If required, implement the desired projection method.
5. If required, adjust the configuration file.
6. If required, add or adjust the relevant hyperparameter file.
7. Run `api/server.py` to launch the ONEP application.
8. Start the Dareplane Control Room and ensure it has access to the stream containing your data.
9. Run the `LAUNCH` command for the ONEP module from the Dareplane Control Room. As an argument, pass the name of your data stream, or ensure the data stream name is set in the configuration (see Configuration File).
10. Once the ONEP UI is available on your browser, run the `START PROJECTING` command from the Control Room to start the projector. Executing this command will allow the projector to begin reading data from the data stream, using it to train the projection model and create projections to display in the 2D figure.


## Documentation

- For an extensive overview of how to use ONEP, including how to implement a new projection method, see the [user guide](https://github.com/pctwass/Dareplane/blob/main/modules/dp-embedding-projector/documentation/USER%20GUIDE.md) in the documentation section.
- To get an overview and explanation of the implementation of ONEP for development purposes, see the [development guide](https://github.com/pctwass/Dareplane/blob/main/modules/dp-embedding-projector/documentation/DEV%20GUIDE.md) in the documentation section.
