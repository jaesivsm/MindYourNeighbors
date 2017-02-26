#!/usr/bin/env python3
from setuptools import setup

with open('README.md') as fd:
    readme = fd.read()


setup(name='MindYourNeighbors',
      version='0.5.0',
      description='IP Neighbors table watching script',
      long_description=readme,
      keywords='ip-neigh arp',
      classifiers=[
          "Intended Audience :: System Administrators",
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: POSIX :: Linux",
          "Development Status :: 4 - Beta",
          "Topic :: System :: Networking :: Monitoring :: Hardware Watchdog",
          "Topic :: System :: Networking"],
      license="GPLv3",
      author="François Schmidts",
      author_email="francois@schmidts.fr",
      maintainer="François Schmidts",
      maintainer_email="francois@schmidts.fr",
      scripts=['src/myn'],
      packages=['mind_your_neighbors'],
      package_dir={'mind_your_neighbors': 'src/mind_your_neighbors'},
      url='https://github.com/jaesivsm/MindYourNeighbors',
      install_requires=['cronex>=0.1.1'],
      )
