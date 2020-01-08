from setuptools import setup

setup(name='matrixpng',
      version='alpha',
      description='Store 2-D matrices as human-readable PNG files and recover them',
      url='https://github.com/finitemobius/matrixpng-py',
      author='Finite Mobius, LLC',
      author_email='jason@finitemobius.com',
      license='MIT',
      packages=['matrixpng'],
      zip_safe=False,
      install_requires=[
          "pypng >= 0.0.20",
          "numpy >= 1.11"
      ])
