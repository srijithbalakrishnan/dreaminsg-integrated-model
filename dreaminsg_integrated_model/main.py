"""This is the main module of the integrated infrastructure model where the simulations are performed."""

import os
from dreaminsg_integrated_model.src.network_recovery import *
import dreaminsg_integrated_model.src.simulation as simulation
from dreaminsg_integrated_model.src.network_sim_models.integrated_network import *
from dreaminsg_integrated_model.src.optimizer import *

import warnings

warnings.filterwarnings("ignore")


def main():
    os.system("cls")

    simple_network = IntegratedNetwork()

    network_dir = "in2"

    water_file = f"dreaminsg_integrated_model/data/networks/{network_dir}/water/Example_water2.inp"
    power_file = f"dreaminsg_integrated_model/data/networks/{network_dir}/power/Example_power.json"
    transp_folder = (
        f"dreaminsg_integrated_model/data/networks/{network_dir}/transportation/"
    )

    # load all infrastructure networks
    simple_network.load_networks(water_file, power_file, transp_folder)

    simple_network.generate_integrated_graph(plotting=False)
    simple_network.integrated_graph

    dependency_file = "dreaminsg_integrated_model/data/networks/in2/dependecies.csv"
    simple_network.generate_dependency_table(dependency_file=dependency_file)

    scenario_file = "dreaminsg_integrated_model/data/disruptive_scenarios/test1/motor_failure_net1.csv"
    simple_network.set_disrupted_components(scenario_file=scenario_file)

    simple_network.set_init_crew_locs(
        init_power_loc=8, init_water_loc=8, init_transpo_loc=8
    )

    network_recovery = NetworkRecovery(simple_network, 60)
    bf_optimizer = BruteForceOptimizer(prediction_horizon=2)

    sim_step = (
        simple_network.wn.options.time.hydraulic_timestep
    )  # initial_sim_step which will be updated during the simulation
    bf_simulation = simulation.NetworkSimulation(network_recovery, sim_step)

    bf_optimizer.find_optimal_recovery(bf_simulation)


if __name__ == "__main__":
    main()
