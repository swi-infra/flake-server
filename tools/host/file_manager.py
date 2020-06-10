"""Data file creation module to configure data files on server."""
import os
import re
import time
import shutil
import string
import numpy as np
from scipy.io import wavfile
from PIL import Image, ImageDraw
from cv2 import VideoWriter, VideoWriter_fourcc
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/data_files.json"


class DataFile:
    """Data file class for handling data files."""

    def __init__(self, config, server_config, data_path):
        """Initialize data files."""
        self._base_name = config["base_name"]
        self._extension = config["extension"]
        self._size_list = config["size_list"]
        base_folder = server_config["files"]["location"]
        base_folder = os.path.expandvars(base_folder)
        self._data_path = os.path.join(base_folder, data_path)
        # Data conversion units
        self._units = {
            "B": 1,
            "KB": 2 ** 10,
            "MB": 2 ** 20,
            "GB": 2 ** 30,
            "TB": 2 ** 40,
        }

    @staticmethod
    def get_data_handler(data_type, config, server_config):
        """Get data handler for data type."""
        data_class = "%sFile" % data_type.capitalize()
        try:
            data_handler = eval(data_class)
        except NameError as e:
            flog.error(
                "cannot find class %s, %s is not a valid data type."
                % (data_class, data_type)
            )
            raise e
        return data_handler(config, server_config)

    def _clear_data_folder(self):
        """Remove data folder tree."""
        if os.path.exists(self._data_path):
            shutil.rmtree(self._data_path)

    @property
    def _data_folder(self):
        """Data folder."""
        if not os.path.exists(self._data_path):
            os.mkdir(self._data_path)
        return self._data_path

    def _generate_file_path(self, size):
        """Generate file path."""
        file_name = "%s%s%s" % (self._base_name, size, self._extension)
        return os.path.join(self._data_folder, file_name)

    def _parse_size(self, size):
        """Parse data size."""
        size = size.upper()
        if not re.match(r" ", size):
            size = re.sub(r"([KMGT]?B)", r" \1", size)
        number, unit = [tmp_str.strip() for tmp_str in size.split()]
        return int(float(number) * self._units[unit])

    def configure(self, force=False):
        """Create files."""
        if force:
            self._clear_data_folder()
        for size in self._size_list:
            if force or not self.check_file(size):
                self.create_file(size)
        return True

    def check_file(self, size):
        """Check if file exists."""
        file_path = self._generate_file_path(size)
        flog.info("Checking if {} exists".format(file_path))
        if not os.path.exists(file_path):
            flog.warning("{} does not exist".format(file_path))
            return False
        flog.info("{} exists".format(file_path))
        return True


class TextFile(DataFile):
    """Data file class for handling text files."""

    def __init__(self, config, server_config):
        """Initialize text file handler."""
        super().__init__(config, server_config, "text")

    def create_file(self, size):
        """Create data file (text)."""
        file_path = self._generate_file_path(size)
        flog.info("Creating a text file %s of size %s" % (file_path, size))
        byte_size = self._parse_size(size)
        with open(file_path, "w") as f:
            f.write("".join(np.random.choice(list(string.ascii_lowercase), byte_size)))


class BinaryFile(DataFile):
    """Data file class for handling binary files."""

    def __init__(self, config, server_config):
        """Initialize binary file handler."""
        super().__init__(config, server_config, "binary")

    def create_file(self, size):
        """Create data file (binary)."""
        file_path = self._generate_file_path(size)
        flog.info("Creating a binary file %s of size %s" % (file_path, size))
        byte_size = self._parse_size(size)
        with open(file_path, "wb") as f:
            f.write(os.urandom(byte_size))


class ImageFile(DataFile):
    """Data file class for handling photo files."""

    def __init__(self, config, server_config):
        """Initialize image file handler."""
        super().__init__(config, server_config, "image")

    def create_file(self, size):
        """Create data file (image)."""
        file_path = self._generate_file_path(size)
        flog.info("Creating a image file %s of size %s" % (file_path, size))
        byte_size = self._parse_size(size)
        # Need a slow growing series sqrt(x)/2.048 works for this.
        size = int(np.sqrt(byte_size) / 2.048)
        img = Image.new("F", (size, size))
        draw = ImageDraw.Draw(img)
        half_size = int(size / 2)
        colours = ("red", "green", "blue", "yellow")
        index = 0
        for x in (0, half_size):
            for y in (0, half_size):
                c0 = (x, y)
                c1 = (x + half_size, y + half_size)
                draw.rectangle((c0, c1), fill=colours[index])
                index += 1
        del draw
        img.save(file_path)


class VideoFile(DataFile):
    """Data file class for handling video files."""

    def __init__(self, config, server_config):
        """Initialize video file handler."""
        super().__init__(config, server_config, "video")

    def create_file(self, size):
        """Create data file (video)."""
        file_path = self._generate_file_path(size)
        flog.info("Creating a video file %s of size %s" % (file_path, size))
        byte_size = self._parse_size(size)
        width = 500
        height = 500
        FPS = 50
        # Need a series series to match growth of file.
        seconds = float(float(byte_size ** 1.00433) / float(142000))
        fourcc = VideoWriter_fourcc(*"XVID")
        video = VideoWriter(file_path, fourcc, float(FPS), (width, height))

        for i in range(int(FPS * seconds)):
            a = np.zeros((height, width, 3), np.uint8)
            a.fill(i % 256)
            video.write(a)
        video.release()


class AudioFile(DataFile):
    """Data file class for handling audio files."""

    def __init__(self, config, server_config):
        """Initialize audio file handler."""
        super().__init__(config, server_config, "audio")

    def create_file(self, size):
        """Create data file (audio)."""
        file_path = self._generate_file_path(size)
        flog.info("Creating a audio file %s of size %s" % (file_path, size))
        byte_size = self._parse_size(size)
        # Need to take fraction of the size to get correct output size.
        length = byte_size / 370000
        sample_rate = 44100
        frequency = 440.0
        t = np.linspace(0, length, int(sample_rate * length))
        y = np.sin(frequency * 2 * np.pi * t)  # Has frequency of 440Hz
        wavfile.write(file_path, sample_rate, y)


def configure_files(force=False, config_file=CONFIG):
    """Configure server files."""
    config = ConfigHandler(config_file)
    configuration_times = {}
    total_time = time.time()
    for data_type, data_values in config.items():
        start_time = time.time()
        data_handler = DataFile.get_data_handler(
            data_type=data_type, config=data_values, server_config=config.server
        )
        data_handler.configure(force)
        configuration_times[data_type] = "%ss" % format(time.time() - start_time, ".2f")
    configuration_times["Total"] = "%ss" % format(time.time() - total_time, ".2f")
    flog.info("Time to configure files:\n%s" % configuration_times)
    return True
