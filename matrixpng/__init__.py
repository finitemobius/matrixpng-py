#!/usr/bin/env python3
"""Store 2-D matrices as human-readable PNG files and recover them

The canonical source for this package is https://github.com/finitemobius/matrixpng-py
See pypng documentation for acceptable modes and bit depths"""

import png
import numpy as np
import matrixpng._colormaps

__author__ = "Finite Mobius, LLC"
__credits__ = ["Jason R. Miller"]
__license__ = "MIT"
__version__ = "alpha"
__maintainer__ = "Finite Mobius, LLC"
__email__ = "jason@finitemobius.com"
__status__ = "Development"


class MatrixPNG:
    """The PNG-matrix transformation class"""

    def __init__(self, mode="RGB", bitdepth=8, z_min=None, z_max=None):
        """See pypng documentation for acceptable modes and bit depths

        :param mode: PNG mode
        :param bitdepth: bit depth
        """
        # Settings for the PNG output
        self._png = {
            "mode": None,
            "bitdepth": None,
            "colormap": []
        }
        self.mode = mode
        self.bitdepth = bitdepth
        # Initialize the internal matrix for building the PNG
        self._matrix = np.empty([0, 0, 0])
        # Initialize the internal buffer
        self._pngbuffer = None
        # Set up the color map
        # Currently fixed at extended-black-body for RGB
        self._setup_colors()
        # Scaling min and max values
        # Values outside this range will be clipped
        self._z_min = z_min
        self._z_max = z_max

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
        if bd not in [1, 2, 4, 8, 16]:
            raise ValueError('Bit depth ' + str(bd) + ' is unsupported.')
        else:
            self._png["bitdepth"] = bd

    def matrix2png(self, matrix, file):
        """Load a numpy 2-D ndarray and build the PNG output"""
        # TODO: Embed scale data in PNG using iTXt, tEXt, or zTXt
        # Set up the color scaling
        _zmin = self._z_min
        if _zmin is None:
            _zmin = matrix.min()
        _zmax = self._z_max
        if _zmax is None:
            _zmax = matrix.max()
        # Build out the PNG array
        # Use max value for default alpha
        _arr = np.empty([len(matrix), len(matrix[0]), len(self.mode)], dtype=int)
        _arr.fill(2 ** self.bitdepth - 1)
        # The number of non-alpha channels
        _channels = len(self.mode.rstrip('A'))
        # Assign colors element by element
        for i in range(len(_arr)):
            for j in range(len(_arr[i])):
                if matrix[i][j] is not np.nan:
                    # Find the index
                    k = int(np.clip([(float(matrix[i][j] - _zmin) /
                                     float(_zmax - _zmin) *
                                     float(self.quantization_levels - 1))],
                                    0, self.quantization_levels - 1)[0])
                    # Save those color values to the array
                    _arr[i][j][:_channels] = self._png["colormap"][k]
                else:
                    # NaN values get gray when in RGB mode
                    _arr[i][j][:_channels] = 2 ** self.bitdepth / 2 - 1
        _info = {
            "bitdepth": self.bitdepth
        }
        _png = self._make_png(_arr, _info)
        _png.save(file)

    def _make_png(self, arr, info):
        """Write png data to a buffer

        :return: buffer"""
        # TODO: embed info for axes & scales (using iTXt, tEXt, or zTXt)
        _mode = self.mode
        # pypng bit depth mode text
        if self.bitdepth == 16:
            _mode += ";16"
        _pngbuffer = png.from_array(arr, mode=_mode, info=info)
        return _pngbuffer

    def png2matrix(self, fp):
        """Read a PNG from a file pointer and build a matrix"""
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
            self._png["colormap"] = _colormaps._colormaps(self.bitdepth, self.mode)

    @property
    def quantization_levels(self):
        """The number of quantization levels

        :return: int
        """
        return len(self._png["colormap"])


def _main():
    print("Don't call this module directly. Use 'import matrixpng'.")

if __name__ == '__main__':
    _main()
