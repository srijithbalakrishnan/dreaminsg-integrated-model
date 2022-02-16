import os
import random
import numpy as np
import pandas as pd
from scipy import interpolate

from bokeh.plotting import figure
from bokeh.transform import factor_cmap
from bokeh.palettes import RdYlGn
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.tile_providers import get_provider, Vendors

import infrarisk.src.network_sim_models.interdependencies as interdependencies

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

from pathlib import Path


class DisruptionInitiator:
    """
    Class for initiating disruptions
    """

    def __init__(self, name="Disruption", time_of_occurrence=6000, intensity="low"):
        self.name = name
        self.intensity = intensity
        self.set_fail_compon_dict()
        self.disrupt_file = pd.DataFrame()
        self.set_intensity_failure_probability()

    def set_fail_compon_dict(self):
        """Sets the dictionary of components that could be failed due to a radial disaster."""
        self.fail_compon_dict = {
            "power": {"L"},
            "water": {
                "PMA",
                "WP",
            },
            "transport": {"L"},
        }

    def get_fail_compon_dict(self):
        """Returns the dictionary of that could be failed due to a radial disaster.

        :return: dictionary of components that could be failed.
        :rtype: dictionary
        """
        return self.fail_compon_dict

    def set_intensity_failure_probability(self):
        """Sets the vulnerability (probability of failure) based on the intensity of the disaster event (currently arbitrary values are used)."""
        if self.intensity == "complete":
            self.failure_probability = 1
        elif self.intensity == "extreme":
            self.failure_probability = 0.8
        elif self.intensity == "high":
            self.failure_probability = 0.5
        elif self.intensity == "moderate":
            self.failure_probability = 0.3
        elif self.intensity == "low":
            self.failure_probability = 0.1
        elif self.intensity == "random":
            self.failure_probability = 0.7 * random.random()

    def set_time_of_occurrence(self, time_of_occurrence):
        """Stes the time of occurrence of the disruptive event.

        :param time_of_occurrence: Time in seconds and multiple of 60.
        :type time_of_occurrence: integer
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence


class RadialDisruption(DisruptionInitiator):
    def __init__(self, name="Radial disruption", point_of_occurrence=None, radius_of_impact=100,
        time_of_occurrence=6000,
        intensity="high",):
        super().__init__(name, time_of_occurrence, intensity)
    