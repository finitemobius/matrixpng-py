#!/usr/bin/env python3
"""A test file for matrixpng

The canonical source for this package is https://github.com/finitemobius/matrixpng-py"""

import matrixpng
import numpy as np

__author__ = "Finite Mobius, LLC"
__credits__ = ["Jason R. Miller"]
__license__ = "MIT"
__version__ = "alpha"
__maintainer__ = "Finite Mobius, LLC"
__email__ = "jason@finitemobius.com"
__status__ = "Development"


def _main():
    p = matrixpng.MatrixPNG()
    print(p.mode)
    print(p.bitdepth)
    print(p.quantization_levels)
    # Create a diagonal gradient
    a = np.empty([700, 700])
    for i in range(len(a)):
        for j in range(len(a[i])):
            a[i][j] = i + j
    # Write to a PNG
    with open("test.png", mode='wb') as fp:
        p.matrix2png(a, fp)

if __name__ == '__main__':
    _main()
