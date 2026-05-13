#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=8.0",
    "numpy>=1.23.0",
    "pandas>=1.5.0",
    "networkx>=2.8",
    "matplotlib>=3.6.0",
    "scipy>=1.6.0",
    "geopandas>=0.9.0",
    "shapely>=1.8.0",
    "folium>=0.12.0",
    "wntr>=0.3.0",
    "pandapower>=2.6.0",
    "pyomo>=6.4.0",
    "scikit-learn>=1.1.0",
    "seaborn>=0.12.0",
    "jupyter>=1.0.0",
    "ipykernel>=6.15.0",
    "contextily>=1.2.0",
    "fiona>=1.8.0",
    "rasterio>=1.2.0",
    "geopy>=2.2.0",
    "requests>=2.28.0",
]

setup_requirements = []

test_requirements = []

setup(
    author="Srijith Balakrishnan",
    author_email="srijith.balakrishnan@sec.ethz.ch",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
    ],
    description="An integrated power-water-transportation model for urban simulations.",
    entry_points={
        "console_scripts": [
            "infrarisk=infrarisk.cli:main",
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="infrarisk",
    name="infrarisk",
    packages=find_packages(include=["infrarisk", "infrarisk.*"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/srijithabalakrishnan/dreaminsg_integrated_model",
    version="0.1.0",
    zip_safe=False,
)
