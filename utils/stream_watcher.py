import pylsl
import xmltodict
import numpy as np
import pandas as pd

from utils.logging import logger


class StreamWatcherNotConnected(ValueError):
    pass


def get_streams_names() -> list[str]:
    """Get a list of all available lsl stream names.

    Returns
    -------
    streams : list[str]
        names of all available LSL streams

    """

    return [s.name() for s in pylsl.resolve_streams()]


def pylsl_xmlelement_to_dict(inf: pylsl.pylsl.StreamInfo) -> dict:
    """
    The pylsl XMLElement is hard to investigate -> cast to a dict for
    simplicity
    """
    return xmltodict.parse(inf.as_xml())


def get_channel_names(inf: pylsl.pylsl.StreamInfo) -> list[str]:
    d = pylsl_xmlelement_to_dict(inf)

    # By adding to the xml meta data structure of LSL, if we only add one
    # channel, the data will be a dict instead of a list of dicts

    try:
        if isinstance(d["info"]["desc"]["channels"]["channel"], dict):
            return [d["info"]["desc"]["channels"]["channel"]["label"]]
        else:
            return [
                ch_inf["label"]
                for ch_inf in d["info"]["desc"]["channels"]["channel"]
            ]
    except TypeError as err:
        return [f"ch_{i + 1}" for i in range(inf.channel_count())]


class StreamWatcher:
    def __init__(
        self,
        name: str = "",
        buffer_size_s: float = 2,
    ):
        """
        Parameters
        ----------
        name : str
            Name tag to identify the manager -> could be same as the LSL stream
            it should be watching
        buffer_size_s : float
            the data buffer size in seconds
        """
        self.name = name
        self.buffer_size_s = buffer_size_s
        self.stream = None
        self.inlet = None

        # Set after connection
        self.n_buffer: int = 0
        self.buffer_t: np.ndarray = np.asarray([])
        self.buffer: np.ndarray = np.asarray([])
        self.last_t: float = float
        self.curr_buffer_position: int = 0
        self.samples: list[list[float]] = []

    def connect_to_stream(self, identifier: [dict, None] = None):
        """
        Either use the self.name or a provided identifier dict to hook up
        with an LSL stream, they should coincide
        """
        if identifier:
            name = identifier["name"]
            self.name = name
        else:
            name = self.name

        self.streams = pylsl.resolve_byprop("name", name)
        if len(self.streams) > 0:
            logger.warn(f"Selecting stream by {name=} was ambigous - taking first")

        self.inlet = pylsl.StreamInlet(self.streams[0])

        self.channel_names = get_channel_names(self.inlet.info())

        self._init_buffer()

        # The first update call will return empty, so do it here already
        self.update()

    def _init_buffer(self):
        if self.streams is None or self.inlet is None:
            raise StreamWatcherNotConnected(
                "StreamWatcher seems not connected, did you call"
                " connect_to_stream() on it?"
            )

        n_samples = int(self.streams[0].nominal_srate() * self.buffer_size_s)
        self.n_buffer = n_samples

        # Using numpy buffers
        self.buffer = np.empty((n_samples, len(self.channel_names)))
        self.buffer_t = np.empty(n_samples)
        self.last_t = 0  # last time stamp
        self.curr_buffer_position = 0

    def read_to_buffers(self, samples: list, times: list):
        if len(samples) > 0 and len(times) > 0:
            if len(samples) > self.n_buffer:
                logger.warning(
                    "Received more data than fitting into the"
                    " buffer. Will only add data to fill buffer"
                    " once with the latest data"
                )

                samples = samples[-self.n_buffer :]
                times = times[-self.n_buffer :]

            # make it a ring buffer with FIFO
            prev_buffer_position = self.curr_buffer_position

            self.curr_buffer_position = (self.curr_buffer_position + len(samples)) % self.n_buffer

            # plain forward fill
            if prev_buffer_position < self.curr_buffer_position:
                self.buffer[prev_buffer_position : self.curr_buffer_position] = samples
                self.buffer_t[prev_buffer_position : self.curr_buffer_position] = times
            # fill buffer up
            elif self.curr_buffer_position == 0:
                self.buffer[prev_buffer_position:] = samples
                self.buffer_t[prev_buffer_position:] = times

            # split needed -> start over at beginning
            else:
                logger.debug("Splitting data to add as buffer is full")
                nfull = self.n_buffer - prev_buffer_position
                self.buffer[prev_buffer_position:] = samples[:nfull]
                self.buffer_t[prev_buffer_position:] = times[:nfull]

                self.buffer[: self.curr_buffer_position] = samples[nfull:]
                self.buffer_t[: self.curr_buffer_position] = times[nfull:]

            self.last_t = times[-1]

    def update(self):
        """Look for new data and update the buffer"""
        samples, times = self.inlet.pull_chunk()
        self.read_to_buffers(samples, times)
        self.samples = samples

    def read_buffer(self) -> pd.DataFrame:
        data = np.vstack(
            [self.buffer[self.curr_buffer_position :], self.buffer[: self.curr_buffer_position]]
        )
        return pd.DataFrame(data, dtype=np.float32)
    
    def read_buffer_t(self) -> pd.DataFrame:
        data = np.vstack(
            [self.buffer_t[self.curr_buffer_position :], self.buffer_t[: self.curr_buffer_position]]
        )
        return pd.DataFrame(data, dtype=np.float32)

    def disconnect(self):
        """TODO to be implemented"""
        pass


if __name__ == "__main__":
    sw = StreamWatcher("mock_EEG_stream")
    sw.connect_to_stream()

    # Updating is quite quick
    # %timeit sw.update()
    # 1.06 µs ± 12.2 ns per loop (mean ± std. dev. of 7 runs, 1,000,000 loops each)
