#!/usr/bin/env python3
from setuptools import setup
import os

__version__ = "0.0.2"
reqs = open(os.path.join(os.path.dirname(__file__), "requirements.txt")).read().split()


setup(name='shipper',
      version=__version__,
      description='Modular API server',
      url='http://git.davepedu.com/dave/shipper',
      author='dpedu',
      author_email='dave@davepedu.com',
      packages=['shipper'],
      install_requires=reqs,
      entry_points={
          "console_scripts": [
              "shipperd = shipper:main",
          ]
      },
      zip_safe=False)
