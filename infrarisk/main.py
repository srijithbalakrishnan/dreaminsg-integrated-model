"""This is the main module of the integrated infrastructure model where the simulations are performed."""

from pathlib import Path
from infrarisk.src.network_recovery import *
import infrarisk.src.simulation as simulation
from infrarisk.src.physical.integrated_network import *
import infrarisk.src.recovery_strategies as strategies
import infrarisk.src.socioeconomic.se_analysis as se_analysis
from infrarisk.src.physical.interdependencies import *

import infrarisk.src.plots as model_plots

import configparser
import tempfile
import os

import sys

# hide warnings
import warnings

warnings.filterwarnings("ignore")


def main(ini_file):
    """This is the main function that contains the whole simulation workflow."""
    os.system("cls")

    # VARIABLES
    settings = read_ini_file(ini_file)

    SIM_STEP = int(settings["sim_step"])
    NETWORK_NAME = settings["name"]

    NETWORK_DIR = Path(settings["network_dir"])
    WATER_FOLDER_NAME = settings["water_folder_name"]
    POWER_FOLDER_NAME = settings["power_folder_name"]
    TRANSPORT_FOLDER_NAME = settings["transport_folder_name"]
    INTERDEPENDENCY_TABLE = settings["interdependency_table"]

    SE_ANALYSIS = True if settings["socioeconomic_analysis"] == "True" else False
    SE_FOLDER_NAME = settings["se_data_folder"]
    SE_YEAR = settings["year"]
    SE_TRACT = settings["tract"]
    SE_STATE = settings["state"]
    SE_COUNTY = settings["county"]

    SCENARIO_FOLDER = settings["scenario_folder"]
    DISRUPTION_FILE = settings["disruption_file"]

    INITIAL_POWER_LOC = settings["initial_power_loc"]
    INITIAL_WATER_LOC = settings["initial_water_loc"]
    INITIAL_TRANSPORT_LOC = settings["initial_transport_loc"]
    WATER_CREW_SIZE = int(settings["water_crew_count"])
    POWER_CREW_SIZE = int(settings["power_crew_count"])
    TRANSPORT_CREW_SIZE = int(settings["transport_crew_count"])

    PIPE_CLOSE_POLICY = settings["pipe_close_policy"]
    PIPE_CLOSURE_DELAY = int(settings["pipe_closure_delay"])
    LINE_CLOSE_POLICY = settings["line_close_policy"]
    LINE_CLOSURE_DELAY = int(settings["line_closure_delay"])

    REPAIR_SEQUENCE_STRATEGY = settings["repair_sequence_strategy"]

    BASEMAP = True if settings["basemap"] == "True" else False

    # Create the integrated network object
    integrated_network = IntegratedNetwork(name=NETWORK_NAME)

    MAIN_DIR = Path("")

    water_folder = os.path.join(MAIN_DIR, NETWORK_DIR, WATER_FOLDER_NAME)
    power_folder = os.path.join(MAIN_DIR, NETWORK_DIR, POWER_FOLDER_NAME)
    transp_folder = os.path.join(MAIN_DIR, NETWORK_DIR, TRANSPORT_FOLDER_NAME)

    print(water_folder, power_folder, transp_folder)

    # load all infrastructure networks
    integrated_network.load_networks(
        water_folder=water_folder,
        power_folder=power_folder,
        transp_folder=transp_folder,
        sim_step=SIM_STEP,
    )
    integrated_network.generate_integrated_graph(basemap=BASEMAP)

    dependency_file = os.path.join(MAIN_DIR, NETWORK_DIR, INTERDEPENDENCY_TABLE)
    integrated_network.generate_dependency_table(dependency_file=dependency_file)
    integrated_network.dependency_table.wp_table.head()
    integrated_network.dependency_table.access_table.head()

    # socioeconomic analysis
    print(os.path.join(MAIN_DIR, NETWORK_DIR, SE_FOLDER_NAME))
    if SE_ANALYSIS is True:
        socio_economic_folder = os.path.join(MAIN_DIR, NETWORK_DIR, SE_FOLDER_NAME)
        socioeconomic_analysis = se_analysis.SocioEconomicTable(
            name=NETWORK_NAME,
            year=SE_YEAR,
            tract=SE_TRACT,
            state=SE_STATE,
            county=SE_COUNTY,
            dir=socio_economic_folder,
        )
        socioeconomic_analysis.load_se_data()
        socioeconomic_analysis.create_setable()

    # Scenario definition
    scenario_folder = os.path.join(MAIN_DIR, NETWORK_DIR, "scenarios", SCENARIO_FOLDER)
    disruption_file = os.path.join(scenario_folder, DISRUPTION_FILE)

    integrated_network.set_disrupted_components(disruption_file=disruption_file)
    disrupted_components = integrated_network.get_disrupted_components()
    print(*disrupted_components, sep=", ")

    # Crew settings
    integrated_network.deploy_crews(
        init_power_crew_locs=[INITIAL_POWER_LOC] * POWER_CREW_SIZE,
        init_water_crew_locs=[INITIAL_WATER_LOC] * WATER_CREW_SIZE,
        init_transpo_crew_locs=[INITIAL_TRANSPORT_LOC] * TRANSPORT_CREW_SIZE,
    )

    # Create network recovery object
    network_recovery = NetworkRecovery(
        integrated_network,
        sim_step=SIM_STEP,
        pipe_close_policy=PIPE_CLOSE_POLICY,
        pipe_closure_delay=PIPE_CLOSURE_DELAY,
        line_close_policy=LINE_CLOSE_POLICY,
        line_closure_delay=LINE_CLOSURE_DELAY,
    )

    bf_simulation = simulation.NetworkSimulation(network_recovery)

    if REPAIR_SEQUENCE_STRATEGY == "capacity":
        repair_strategy = strategies.HandlingCapacityStrategy(integrated_network)
        repair_strategy.set_repair_order()
        repair_order = repair_strategy.get_repair_order()
    elif REPAIR_SEQUENCE_STRATEGY == "centrality":
        repair_strategy = strategies.CentralityStrategy(integrated_network)
        repair_strategy.set_repair_order()
        repair_order = repair_strategy.get_repair_order()

    if not os.path.exists(os.path.join(scenario_folder, REPAIR_SEQUENCE_STRATEGY)):
        os.makedirs(os.path.join(scenario_folder, REPAIR_SEQUENCE_STRATEGY))
    print(
        f"Current repair order according to {REPAIR_SEQUENCE_STRATEGY} repair sequence strategy is {repair_order}"
    )

    # schedule recovery
    bf_simulation.network_recovery.schedule_recovery(repair_order)
    bf_simulation.expand_event_table()

    # Run simulations
    resilience_metrics = bf_simulation.simulate_interdependent_effects(
        bf_simulation.network_recovery
    )

    bf_simulation.write_results(
        os.path.join(scenario_folder, REPAIR_SEQUENCE_STRATEGY), resilience_metrics
    )

    # Resilience quantification
    resilience_metrics.calculate_power_resmetric(network_recovery)
    resilience_metrics.calculate_water_resmetrics(network_recovery)
    resilience_metrics.set_weighted_auc_metrics()

    if SE_ANALYSIS is True:
        socioeconomic_analysis.combine_infrastructure_se_data(
            integrated_network, resilience_metrics
        )
        socioeconomic_analysis.calculate_economic_costs()

    socioeconomic_analysis.economic_cost_df.to_csv(
        os.path.join(scenario_folder, REPAIR_SEQUENCE_STRATEGY, "economic_cost.csv"),
        index=False,
    )


def read_ini_file(ini_file):
    """Read the ini file and return the simulation parameters."""
    config = configparser.ConfigParser()
    config.read(ini_file)
    settings = {
        key: value
        for section in config.sections()
        for key, value in config[section].items()
    }
    return settings


def create_init_file():
    os.makedirs(".tempfiles/", exist_ok=True)
    temp_dir = tempfile.TemporaryDirectory(dir=".tempfiles/", prefix="_emp")
    print(temp_dir.name)

    config = configparser.ConfigParser()

    config["SIMULATION_SETTINGS"] = {
        "sim_step": 60,
        "name": "Shelby",
    }

    config["NETWORK DATA"] = {
        "network_dir": "data/networks/shelby",
        "water_folder_name": "water",
        "power_folder_name": "power",
        "transport_folder_name": "transportation/reduced",
        "interdependency_table": "dependencies.csv",
    }

    config["SOCIOECONOMIC DATA"] = {
        "socioeconomic_analysis": True,
        "se_data_folder": "gis/se_data",
        "year": 2017,
        "tract": "*",
        "county": 157,
        "state": 47,
    }

    config["DISASTER SCENARIO"] = {
        "scenario_folder": "scenario1",
        "disruption_file": "disruption_file.dat",
    }

    config["RECOVERY CREW"] = {
        "initial_power_loc": "T_J8",
        "initial_water_loc": "T_J8",
        "initial_transport_loc": "T_J8",
        "water_crew_count": 10,
        "power_crew_count": 10,
        "transport_crew_count": 10,
    }

    config["RECOVERY SETTINGS"] = {
        "pipe_close_policy": "repair",
        "pipe_closure_delay": 12 * 60,
        "line_close_policy": "sensor_based_line_isolation",
        "line_closure_delay": 12 * 60,
        "repair_sequence_strategy": "capacity",
    }

    config["PLOT SETTINGS"] = {
        "basemap": "True",
    }

    with open(os.path.join(temp_dir.name, "example.ini"), "w") as configfile:
        config.write(configfile)

    #


if __name__ == "__main__":
    main(sys.argv[1])
