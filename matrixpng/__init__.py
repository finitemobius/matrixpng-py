#!/usr/bin/env python3
"""Store 2-D matrices as human-readable PNG files and recover them

The canonical source for this package is https://github.com/finitemobius/matrixpng-py
See pypng documentation for acceptable modes and bit depths"""

import png
import numpy as np
import io
from ._colormaps import _colormaps
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
                 y_upward=True):
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
        :param y_upward: if y should increase upward (default=True)
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
        # Initialize the internal buffer
        #self._pngbuffer = None
        # Set up the color map
        # Currently fixed at extended-black-body for RGB
        self._setup_colors()
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
        self._y_invert = y_upward  # See _setminmax()
        # For noe, the only non-grayscale color map is extended black body
        self._colormap = "ebb"

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

    def matrix2png(self, matrix, file):
        """Load a numpy 2-D ndarray and build the PNG output"""
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
                    k = int(np.clip([(float(matrix[i][j] - _zmin) /
                                      float(_zmax - _zmin) *
                                      float(self.quantization_levels - 1))],
                                    0, self.quantization_levels - 1)[0])
                    # Save those color values to the array
                    _arr[i][j][:_channels] = self._png["colormap"][k]
        if self._y_invert:
            _arr = np.flipud(_arr)
        _info = {
            "bitdepth": self.bitdepth,
            "compression": 9
        }
        _png = self._make_png(_arr, _info)
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

    def _make_png(self, arr, info):
        """Write png data to a buffer

        :return: io.BytesIO"""
        _mode = self.mode
        # pypng bit depth mode text
        if self.bitdepth == 16:
            _mode += ";16"
        # This returns a png.Image type
        _png_image = png.from_array(arr, mode=_mode, info=info)
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
        _chunklist = []
        #_chunks =
        for c in png.Reader(file=fp).chunks():
            _chunklist.append(c)
        fp.close()
        # Add text chunks
        for k in self._scale.keys():
            _chunklist.append(ChunkITXT(keyword=k, text=str(self._scale[k])).get_chunk())
        if self.mode.startswith('RGB'):
            _chunklist.append(ChunkITXT(keyword='colormap', text=self._colormap).get_chunk())
        # Write the PNG
        png.write_chunks(file, _chunklist)

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
        # If y is increasing bottom to top instead of top to bottom, reverse y_min and y_max
        # (y_min corresponds to the PNG's y=0 row, which is the top right)
        if self._y_invert:
            t = self._scale["y_max"]
            self._scale["y_max"] = self._scale["y_min"]
            self._scale["y_min"] = t

    def png2matrix(self, fp):
        """Read a PNG from a file pointer and build a matrix"""
        # TODO
        pass

    def _get_matrix(self):
        """Return the current matrix

        :return: numpy ndarray"""
        return self._matrix

    def _setup_colors(self):
        """Initialize the color map

        :return: None
        """
        if self.mode is not None and self.bitdepth is not None:
            self._png["colormap"] = _colormaps(self.bitdepth, self.mode)

    @property
    def quantization_levels(self):
        """The number of quantization levels

        :return: int
        """
        return len(self._png["colormap"])


def _main():
    raise (SyntaxError, "Don't call this module directly. Use 'import matrixpng'.")

if __name__ == '__main__':
    _main()
