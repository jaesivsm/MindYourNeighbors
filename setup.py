#!/usr/bin/python3
from distutils.core import setup

with open("src/version.txt", "r") as f:
    version = f.read()[:-1]

setup(name="MindYourNeighbors",
      version=version,
      description="Launching command depending on your network neighborhood",
      author="jaesivsm",
      author_email="francois.schmidts@gmail.com",
      url="https://github.com/jaesivsm/MindYourNeighbors",
      license="Apache License",
      packages=["MindYourNeighbors"],
      package_dir={"MindYourNeighbors": "src"},
      package_data={"MindYourNeighbors": ["version.txt"]},
      scripts=['scripts/mind_your_neighbors']
)
