"""This is the main module of the integrated infrastructure model where the simulations are performed."""

import os
import dreaminsg_integrated_model.src.disrupt_generator as disrupt_generator
import dreaminsg_integrated_model.src.simulation as simulation
import dreaminsg_integrated_model.src.plots as model_plots
import warnings

warnings.filterwarnings("ignore")


def main():
    os.system("cls")

    network_dir = "in2"
    results_dir = f"dreaminsg_integrated_model/data/disruptive_scenarios/test1"

    # ------------------------------------------#
    #        LOAD INFRASTRUCTURE MODELS         #
    # ------------------------------------------#

    water_file = f"dreaminsg_integrated_model/data/networks/{network_dir}/water/Example_water2.inp"
    power_file = f"dreaminsg_integrated_model/data/networks/{network_dir}/power/Example_power.json"
    transp_folder = (
        f"dreaminsg_integrated_model/data/networks/{network_dir}/transportation/"
    )

    # load all infrastructure networks
    wn, pn, tn = simulation.load_networks(water_file, power_file, transp_folder)

    # create a networkx object of the integrated network
    integrated_graph = model_plots.plot_integrated_network(pn, wn, tn, plotting=False)

    # -------------------------------------------#
    #          BUILD INTERDEPENDENCIES           #
    # -------------------------------------------#
    dependency_file = "dreaminsg_integrated_model/data/networks/in2/dependecies.csv"
    dependency_table = disrupt_generator.DependencyTable()

    # power-water dependencies
    dependency_table = simulation.build_power_water_dependencies(
        dependency_table, dependency_file
    )
    # transportation access interdependencies
    dependency_table = simulation.build_transportation_access(
        dependency_table, integrated_graph
    )

    # ------------------------------------------#
    #     SCHEDULE DISRUPTIONS AND RECOVERY     #
    # ------------------------------------------#
    # Setting recovery parameters
    curr_loc_crew = 8

    # Setting simulation parameters
    sim_step = (
        wn.options.time.hydraulic_timestep
    )  # initial_sim_step which will be updated during the simulation

    # creating test case dataframe
    scenario_file = "dreaminsg_integrated_model/data/disruptive_scenarios/test1/motor_failure_net1.csv"
    motor_failure = disrupt_generator.DisruptionAndRecovery(
        scenario_file, sim_step, curr_loc_crew
    )

    # Simulating repair curves
    simulation.schedule_component_repair(motor_failure, integrated_graph, pn, wn, tn)
    simulation.expand_event_table(motor_failure, sim_step, 50)

    # ------------------------------------------#
    #   SIMULATION OF INTERDEPENDENT EFFECTS    #
    # ------------------------------------------#
    (
        time_tracker,
        power_consump_tracker,
        water_consump_tracker,
    ) = simulation.simulate_interdependent_effects(
        motor_failure, dependency_table, pn, wn, tn
    )
    simulation.write_results(
        time_tracker,
        power_consump_tracker,
        water_consump_tracker,
        results_dir,
        plotting=False,
    )


if __name__ == "__main__":
    main()
