#!/usr/bin/env python3
"""Store 2-D matrices as human-readable PNG files and recover them

The canonical source for this package is https://github.com/finitemobius/matrixpng-py
See pypng documentation for acceptable modes and bit depths"""

import png
import numpy as np
import io
from ._colormaps import ColorMaps
from ._pngTextChunks import ChunkITXT

__author__ = "Finite Mobius, LLC"
__credits__ = ["Jason R. Miller"]
__license__ = "MIT"
__version__ = "alpha"
__maintainer__ = "Finite Mobius, LLC"
__email__ = "jason@finitemobius.com"
__status__ = "Development"


class MatrixPNG:
    """The matrix-PNG transformation class"""

    def __init__(self, mode="RGB", bitdepth=8,
                 z_min=None, z_max=None, z_units=None,
                 x_min=None, x_max=None, x_units=None,
                 y_min=None, y_max=None, y_units=None,
                 y_ascend_up=True):
        """Initialize the matrix-PNG transformer

        :param mode: PNG mode (default = 'RGB')
        :param bitdepth: bit depth (8 or 16, default = 8)
        :param z_min: minimum z value (default = minimum element value)
        :param z_max: maximum z value (default = maximum element value)
        :param z_units: z units (default = None)
        :param x_min: minimum x value (default = 0)
        :param x_max: maximum x value (default = len(matrix))
        :param x_units: x units (default = None)
        :param y_min: minimum y value (default = 0)
        :param y_max: maximum y value (default = len(matrix[0]))
        :param y_units: y units (default = None)
        :param y_ascend_up: if y should increase upward (default=True)
        """
        # Settings for the PNG output
        self._png = {
            "mode": None,
            "bitdepth": None,
            "colormap": []
        }
        # See mode.setter
        self.mode = mode
        # See bitdepth.setter
        self.bitdepth = bitdepth
        # Initialize the internal matrix for building the PNG
        self._matrix = np.empty([0, 0, 0])
        # Data/scale information
        # Values outside z_min and z_max will be clipped
        self._scale = {
            "z_min": z_min,
            "z_max": z_max,
            "z_units": z_units,
            "x_min": x_min,
            "x_max": x_max,
            "x_units": x_units,
            "y_min": y_min,
            "y_max": y_max,
            "y_units": y_units
        }
        # Whether the y axis should be inverted (y ascends upward)
        self._y_invert = y_ascend_up
        # For now, the only non-grayscale color map is extended black body
        self._colormap = "ebb"
        # Set up the color map
        self._setup_colors()

    @property
    def mode(self):
        return self._png["mode"]

    @mode.setter
    def mode(self, m):
        if m not in ['L', 'LA', 'RGB', 'RGBA']:
            raise ValueError('Mode ' + str(m) + ' is unknown.')
        else:
            self._png["mode"] = m
            self._setup_colors()

    @property
    def bitdepth(self):
        return self._png["bitdepth"]

    @bitdepth.setter
    def bitdepth(self, bd):
        # Even though pypng supports smaller bit depths,
        # only 8 or 16 are really useful in our case
        if bd not in [8, 16]:
            raise ValueError('Bit depth ' + str(bd) + ' is unsupported.')
        else:
            self._png["bitdepth"] = bd

    def set_scaling(self, z_min=None, z_max=None, z_units=None,
                    x_min=None, x_max=None, x_units=None,
                    y_min=None, y_max=None, y_units=None,
                    y_ascend_up=None):
        """Set the minimum, maximum, and units for x, y, and z

        Only set the parameters you want to modify with each call

        :param z_min: minimum z value (default = minimum element value)
        :param z_max: maximum z value (default = maximum element value)
        :param z_units: z units (default = None)
        :param x_min: minimum x value (default = 0)
        :param x_max: maximum x value (default = len(matrix))
        :param x_units: x units (default = None)
        :param y_min: minimum y value (default = 0)
        :param y_max: maximum y value (default = len(matrix[0]))
        :param y_units: y units (default = None)
        :param y_ascend_up: if y should increase upward (default=True)
        :return: None
        """
        if z_min is not None:
            self._scale["z_min"] = z_min
        if z_max is not None:
            self._scale["z_max"] = z_max
        if z_units is not None:
            self._scale["z_units"] = z_units
        if x_min is not None:
            self._scale["x_min"] = x_min
        if x_max is not None:
            self._scale["x_max"] = x_max
        if x_units is not None:
            self._scale["x_units"] = x_units
        if y_min is not None:
            self._scale["y_min"] = y_min
        if y_max is not None:
            self._scale["y_max"] = y_max
        if y_units is not None:
            self._scale["y_units"] = y_units
        if y_ascend_up is not None:
            self._y_invert = y_ascend_up

    def matrix2png(self, matrix, file, x_axis_first=True):
        """Load a numpy 2-D ndarray and build the PNG output

        By default, we assume that the first dimension corresponds to x (columns) and the second to y (rows).
        If you have already transposed your matrix (perhaps because you're used to matplotlib),
        then set x_axis_first to False.
        :param matrix: 2-D numpy.ndarray
        :param file: File name (string) to write
        :param x_axis_first: Whether the x axis is the first axis in the 2-D array
        """
        # Set up scale values
        self._setminmax(matrix)
        # Local values to simplify this code section
        _zmin = self._scale["z_min"]
        _zmax = self._scale["z_max"]
        # Initialize the PNG array
        _arr = np.empty([len(matrix), len(matrix[0]), len(self.mode)], dtype=int)
        # Fill array with default alpha value (fully opaque)
        # This simplifies things later
        _arr.fill(2 ** self.bitdepth - 1)
        # The number of non-alpha channels
        _channels = len(self.mode.rstrip('A'))
        # Assign colors element by element
        for i in range(len(_arr)):
            for j in range(len(_arr[i])):
                if matrix[i][j] is np.nan:
                    # NaN values get gray when in RGB mode
                    _arr[i][j][:_channels] = self._nan_value()
                else:
                    # Find the index
                    k = int(np.clip([(float(matrix[i][j] - _zmin) / self.quantization_delta)],
                                    0, self.quantization_levels - 1)[0])
                    # Save those color values to the array
                    _arr[i][j][:_channels] = self._png["colormap"][k]
        # If the array is to be represented as m[x][y] rather than m[y][x] (rows = y, cols = x)
        if x_axis_first:
            _arr = np.transpose(_arr, axes=(1, 0, 2))
        # Make y ascend upward rather than downward
        if self._y_invert:
            _arr = np.flipud(_arr)
        _png = self._make_png(_arr)
        self._save_png(_png, file)

    def _nan_value(self):
        """Determine what gets wirtten in the case of np.nan"""
        # RGB mode = gray
        if len(self.mode.rstrip('A')) > 1:
            return 2 ** self.bitdepth / 2 - 1
        # Grayscale mode = black (minimum)
        else:
            return 0
        # In the future, we can play with alpha or something

    def _make_png(self, arr):
        """Write png data to a buffer

        :return: io.BytesIO"""
        _mode = self.mode
        # pypng bit depth mode text
        if self.bitdepth == 16:
            _mode += ";16"
        # This returns a png.Image type
        _png_image = png.from_array(arr, mode=_mode, info={"bitdepth": self.bitdepth})
        # Save this to a buffer
        f = io.BytesIO()
        _png_image.save(f)
        f2 = io.BytesIO(f.getvalue())
        f.close()
        # Return a readable BytesIO buffer
        return f2

    def _save_png(self, fp, file):
        """Write the PNG file

        :param fp: File pointer containing a "written" png byte stream
        :param file: Name or fp of file to write to
        """
        # Convert the png "image" to a list of chunks
        # (Use a list because we're appending to it)
        chunklist = []
        for c in png.Reader(file=fp).chunks():
            chunklist.append(c)
        fp.close()
        # Add text chunks
        # Scale information
        for k in self._scale.keys():
            chunklist.insert(-1, ChunkITXT(keyword=k, text=str(self._scale[k])).get_chunk())
        # Color map name (only valid for RGB/RGBA)
        if self.mode.startswith('RGB'):
            chunklist.insert(-1, ChunkITXT(keyword='colormap', text=self._colormap).get_chunk())
        # Which way does the y axis ascend?
        if self._y_invert:
            chunklist.insert(-1, ChunkITXT(keyword='y_ascend', text="up").get_chunk())
        else:
            chunklist.insert(-1, ChunkITXT(keyword='y_ascend', text="down").get_chunk())
        # Write the PNG
        png.write_chunks(file, chunklist)

    def _setminmax(self, matrix):
        """Set default values for scales"""
        if self._scale["z_min"] is None:
            self._scale["z_min"] = matrix.min()
        if self._scale["z_max"] is None:
            self._scale["z_max"] = matrix.max()
        if self._scale["x_min"] is None:
            self._scale["x_min"] = 0
        if self._scale["x_max"] is None:
            self._scale["x_max"] = len(matrix)
        if self._scale["y_min"] is None:
            self._scale["y_min"] = 0
        if self._scale["y_max"] is None:
            self._scale["y_max"] = len(matrix[0])
        # Reset the quantization info
        self._setup_quantization()

    def pngfile2matrix(self, filename):
        """Read a PNG from a filename and build a matrix

        :param filename: File name
        :return: dict of matrix information
        """
        with open(filename, 'rb') as fp:
            r = self.png2matrix(fp)
        return r

    def png2matrix(self, fp):
        """Read a PNG from a file pointer and build a matrix

        :param fp: File pointer, opened in binary mode
        :return: dict of matrix information
        """
        # Read in the data
        f = io.BytesIO(fp.read())
        # Close the file pointer
        fp.close()
        # Get the chunks
        for c in png.Reader(f).chunks():
            # Process iTXt chunks
            if c[0].lower() == 'itxt':
                cd = ChunkITXT(c[1]).get_chunkdata()
                # Does the keyword match a known scale key?
                if cd["keyword"] in self._scale.keys():
                    # Try to cast as int or float before saving as text
                    try:
                        t = int(cd["text"])
                    except:
                        try:
                            t = float(cd["text"])
                        except:
                            t = cd["text"]
                    self._scale[cd["keyword"]] = t
                # Other known keywords
                elif cd["keyword"] == "colormap":
                    self._colormap = cd["text"]
                elif cd["keyword"] == "y_ascend":
                    if cd["text"] == "down":
                        self._y_invert = False
                    elif cd["text"] == "up":
                        self._y_invert = True
        # Set up the color map
        self._setup_colors()
        # Set up quantization
        self._setup_quantization()
        # Reset f
        f.seek(0)
        # Get the matrix representing the PNG
        # Read in using 'direct' format
        m = png.Reader(f).asDirect()
        # TODO: Convert to matrix
        print(str(m[0]) + "x" + str(m[1]) + "; " + "planes: " + str(m[3]["planes"]) + ", alpha: " + str(m[3]["alpha"]))
        return None

    def _setup_colors(self):
        """Initialize the color map

        :return: None
        """
        # Load our color map
        if self.mode is not None and self.bitdepth is not None:
            self._png["colormap"] = ColorMaps(mode=self.mode, bd=self.bitdepth, colormap=self._colormap)

    def _setup_quantization(self):
        """Do some preliminary work to save some hassle later

        :return: None
        """
        # Enforce z_min and z_max being floats
        for k in "z_min", "z_max":
            self._scale[k] = float(self._scale[k])
        # Compute the quantization delta
        self._quantization_delta = float(self._scale["z_max"] - self._scale["z_min"]) /\
                                   float(self.quantization_levels - 1)

    def _color_to_z_value(self, color):
        """Convert a color to a z value

        :param color: Color value (list or tuple)
        :return: z value (float)
        """
        # TODO

    @property
    def quantization_levels(self):
        """The number of quantization levels

        :return: int
        """
        return len(self._png["colormap"])

    @property
    def quantization_delta(self):
        """The quantization delta

        :return: float
        """
        return self._quantization_delta

def _main():
    raise (SyntaxError, "Don't call this module directly. Use 'import matrixpng'.")

if __name__ == '__main__':
    _main()
