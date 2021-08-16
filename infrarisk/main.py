"""This is the main module of the integrated infrastructure model where the simulations are performed."""

import os
import infrarisk.src.network_recovery as nr
import infrarisk.src.simulation as simulation
import infrarisk.src.network_sim_models.integrated_network as int_net
import infrarisk.src.optimizer as optim

import warnings

warnings.filterwarnings("ignore")


def main():
    """This is the main function that contains the whole simulation workflow."""
    os.system("cls")

    # -------------------- create an integrated network object ------------------- #
    simple_network = int_net.IntegratedNetwork()

    # ------------- set the locations of infrastructure network files ------------ #
    network_dir = "in2"

    water_file = f"infrarisk/data/networks/{network_dir}/water/Example_water2.inp"
    power_file = f"infrarisk/data/networks/{network_dir}/power/Example_power.json"
    transp_folder = f"infrarisk/data/networks/{network_dir}/transportation/"

    # ---------------------------------------------------------------------------- #
    #                              NETWORK GENERATION                              #
    # ---------------------------------------------------------------------------- #

    # --------------------- load all infrastructure networks --------------------- #
    simple_network.load_networks(
        water_file,
        power_file,
        transp_folder,
    )

    # ------------ generate a networkx integrated infrastructure graph ----------- #
    simple_network.generate_integrated_graph(plotting=False)

    # ------------------------ generate dependency tables ------------------------ #
    dependency_file = "infrarisk/data/networks/in2/dependecies.csv"
    simple_network.generate_dependency_table(dependency_file=dependency_file)

    # ----------- set disrupted components based on the hazard scenario ---------- #
    scenario_file = "infrarisk/data/disruptive_scenarios/test1/motor_failure_net1.csv"
    simple_network.set_disrupted_components(scenario_file=scenario_file)

    # ----- set the initial locations of the infrastructure maintenance crews ---- #
    simple_network.set_init_crew_locs(
        init_power_loc="T_J8",
        init_water_loc="T_J8",
        init_transpo_loc="T_J8",
    )

    # ------- create leak nodes for simulating leaks resuling from pipe failures if any ------- #
    simple_network.pipe_leak_node_generator()

    # ---------------------------------------------------------------------------- #
    #                     NETWORK RECOVERY AND SIMULATION SETUP                    #
    # ---------------------------------------------------------------------------- #

    # --------------------- create a network recovery object --------------------- #
    network_recovery = nr.NetworkRecovery(
        simple_network,
        sim_step=60,
    )

    # ------------------------ create an optimizer object ------------------------ #
    bf_optimizer = optim.BruteForceOptimizer(prediction_horizon=2)

    # ------------------------- set simulation time-step ------------------------- #
    sim_step = simple_network.wn.options.time.hydraulic_timestep

    # ------------------------ create a simulation object ------------------------ #
    bf_simulation = simulation.NetworkSimulation(
        network_recovery,
        sim_step,
    )

    # ---------------------------------------------------------------------------- #
    #              REPAIR/RECOVERY OPTIMIZATION AND OUTPUT GENERATION              #
    # ---------------------------------------------------------------------------- #
    bf_optimizer.find_optimal_recovery(bf_simulation)


if __name__ == "__main__":
    main()
