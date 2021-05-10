import os
from pathlib import Path
import time
import re
from numpy import random
import random as rand
import matplotlib.pyplot as plt

from dreaminsg_integrated_model.network_sim_models.interdependencies import *
from dreaminsg_integrated_model.data.disruptive_scenarios.disrupt_generator_discrete import *
import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo


def calculate_base_demand_metrics(wn, pn, tn):
    total_base_water_demand = sum(
        [wn.get_node(node).base_demand for node in wn.junction_name_list]
    )

    total_base_power_demand = pn.res_load.p_mw.sum() + pn.res_motor.p_mw.sum()

    total_base_travel_time = 0
    total_base_travel_time = sum(
        total_base_travel_time + tn.link[i].flow * tn.link[i].cost for i in tn.link
    )

    return total_base_water_demand, total_base_power_demand, total_base_travel_time
