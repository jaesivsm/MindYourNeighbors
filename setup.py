#!/usr/bin/env python3
from setuptools import setup


setup(name='MindYourNeighbors',
      version='0.0.2',
      description='IP Neighbors table watching script',
      keywords='ip-neigh arp',
      classifiers=[
          "Intended Audience :: System Administrators",
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
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
      data_files=[('/etc/systemd/system', ['mind-your-neighbors.service'])],
      )
