import os
from pathlib import Path
import infrarisk.src.network_recovery as network_recovery
import infrarisk.src.simulation as simulation
import infrarisk.src.physical.integrated_network as int_net
import infrarisk.src.recovery_strategies as strategies
from infrarisk.src.hazards.fragility_based import FragilityBasedDisruption
from infrarisk.src.hazards.random import RandomDisruption
import infrarisk.src.socioeconomic.se_analysis as se_analysis
import infrarisk.src.hazards.random as hazard

import geopandas as gpd
import pandas as pd
import copy
import numpy as np
import random

import gc

import warnings
from IPython.display import clear_output

warnings.filterwarnings("ignore")


class FullSimulation:
    def __init__(
        self,
        network_dir,
        dependency_file,
        se_dir,
        sim_step,
        robust_level,
        resource_levels,
        redundancy_level,
        scenarios_dir=None,
    ):
        self.network_dir = network_dir
        self.dependency_file = dependency_file

        if sim_step % 60 == 0:
            self.sim_step = sim_step
        else:
            self.sim_step = max(60, (sim_step // 60) * 60)
            print(
                f"The simulation step must be a multiple of 60. The simulation step is rounded to the nearest multiple of 60 seconds ({self.sim_step} s)."
            )
        self.sim_step = sim_step
        self.robust_level = robust_level
        self.resource_levels = resource_levels
        self.redundancy_level = redundancy_level
        self.se_dir = se_dir
        self.disrupt_count = 0
        self.repair_order_dict = dict()

        self.set_scenario_dir(scenarios_dir)

        self.unique_repair_orders = None

    def set_scenario_dir(self, scenarios_dir):
        if scenarios_dir is not None:
            self.scenarios_dir = scenarios_dir
            if not os.path.exists(scenarios_dir):
                os.makedirs(scenarios_dir)

    def generate_network(self):
        """This is the main function that contains the whole simulation workflow."""
        os.system("cls")

        shelby_network = int_net.IntegratedNetwork(name="Shelby Network")
        water_folder = self.network_dir / "water"
        power_folder = self.network_dir / "power"
        transp_folder = self.network_dir / "transportation/reduced"

        shelby_network.load_networks(
            water_folder, power_folder, transp_folder, sim_step=self.sim_step
        )

        shelby_network.generate_integrated_graph(basemap=True)
        shelby_network.generate_dependency_table(dependency_file=self.dependency_file)

        self.network = shelby_network

        year, tract, county, state = 2017, "*", 157, 47
        county = 157
        self.shelby_se = se_analysis.SocioEconomicTable(
            name="Shelby",
            year=year,
            tract=tract,
            state=state,
            county=county,
            dir=self.se_dir,
        )

        self.shelby_se.download_se_data(force_download=False)
        self.shelby_se.create_setable()

    def set_source_weights(self, source_weights_file):
        source_weights_df = pd.read_csv(source_weights_file)
        source_weights_df["scenario"] = (
            source_weights_df["source_id"].astype(str)
            + "_"
            + source_weights_df["magnitude"].astype(str)
            + "_gms.csv"
        )
        self.source_weights_df = source_weights_df

    def generate_disruptions(self, fragility_file, gmf_file):
        print("Reading the fragility functions...", end="")
        self.fragility_df = pd.read_csv(fragility_file)
        print("Done!")

        # print("Reading the rupture weights...", end="")
        # weights = self.source_weights_df.weight
        # scenarios = self.source_weights_df.scenario
        # print("Done!")

        # scenario_name = random.choices(scenarios, weights=weights, k=1)
        map_extends = self.network.get_map_extends()

        print("Creating the earthquake event...", end="")
        earthquake_disruption = FragilityBasedDisruption(
            name="earthquake",
            fragility_df=self.fragility_df,
            resilience_level=self.robust_level,
            time_of_occurrence=6000,
        )
        earthquake_disruption.set_fail_compon_dict(
            {
                "power": {"L", "TFEG", "TFLO", "MP"},
                "water": {"PMA", "P", "T"},
                "transport": {"L"},
            }
        )
        earthquake_disruption.set_all_fragility_and_recovery_curves()
        print("Done!")

        self.event = earthquake_disruption

        print("Reading the GMFs...", end="")
        gmf = pd.read_csv(gmf_file)
        self.gmf_gpd = gpd.GeoDataFrame(
            gmf, geometry=gpd.points_from_xy(gmf["lon_UTM"], gmf["lat_UTM"])
        ).set_crs("epsg:3857")
        print("Done!")

        print("Calculating the component-level ground motion parameters...", end="")
        G = self.network.integrated_graph
        self.event.set_gmfs(G, self.gmf_gpd)
        print("Done!")

    def generate_random_disruptions(self, compon_count_dict=None):
        disruption_list = ["random"]

        intensity_list = (
            ["high"] * 2 + ["moderate"] * 5 + ["low"] * 3
        )  # based on probability distribution
        disruptive_event = random.choice(disruption_list)
        intensity = random.choice(intensity_list)

        if  disruptive_event == "random":
            if compon_count_dict is None:
                compon_count_dict = {
                    "water": random.randint(0, 20),
                    "power": random.randint(0, 20),
                    "transpo": random.randint(0, 20),
                }
            micropolis_map_extents = self.network.get_map_extends()
            event = hazard.RandomDisruption(failure_count=compon_count_dict, 
                                       time_of_occurrence=6000,
                                       name="random")
            event.set_affected_components(
                self.network.integrated_graph, plot_components=False
            )
        self.event = event  

        # print(event.affected_links)
        self.disrupt_count = 0

        for infra in event.affected_links.keys():
            self.disrupt_count = self.disrupt_count + len(event.affected_links[infra])
        for infra in event.affected_nodes.keys():
            self.disrupt_count = self.disrupt_count + len(event.affected_nodes[infra])
        # print(self.disrupt_count)

        if self.disrupt_count > 0:
            test_counter = len(os.listdir(self.scenarios_dir))
            self.scenario_path = self.scenarios_dir / f"random{test_counter}"
            if not os.path.exists(self.scenario_path):
                os.makedirs(self.scenario_path)
            scenario_path = event.generate_disruption_file(
                location=self.scenario_path, maximum_data=35
            )
            print(f"Hazard event generated in {self.scenario_path}.")

            self.network.set_disrupted_components(
                disruption_file=self.scenario_path / "disruption_file.dat"
            )
            # self.network.pipe_leak_node_generator()
        else:
            print(
                "Ignoring the generated hazard scenario due to insufficient disruptions."
            )

    def set_disrupted_components_for_event(self):
        path_to_scenario = (
            self.scenarios_dir / f"{self.redundancy_level}/{self.robust_level}"
        )
        if not os.path.exists(path_to_scenario):
            os.makedirs(path_to_scenario)
        print(path_to_scenario)

        self.test_counter = len(os.listdir(path_to_scenario))
        self.scenario_path = path_to_scenario / f"{self.event.name}{self.test_counter}"

        if not os.path.exists(self.scenario_path):
            os.makedirs(self.scenario_path)

        event = copy.deepcopy(self.event)

        print(
            "Performing fragility analysis to determine component damage states...",
            end="",
        )
        event.set_affected_components(
            self.network,
            self.gmf_gpd,
            disruption_time=self.sim_step * 2,
            plot_components=False,
        )
        print("Done!")

        self.disrupt_count = event.fail_probs_df[
            ~event.fail_probs_df["disruption_state"].isin(["None", "Slight"])
        ].shape[0]

        if self.disrupt_count > 0:
            print("Generating the disruption file...", end="")
            self.case_path = event.generate_disruption_file(location=self.scenario_path)

            self.network.set_disrupted_components(
                disruption_file=self.case_path / "disruption_file.dat"
            )
            print("Done!")

        else:
            print(
                "Ignoring the generated hazard scenario due to insufficient disruptions."
            )

    def generate_repair_order_dict(self):
        if self.disrupt_count > 0:
            print("Working on the repair sequences based on predefined strategies...")

            print(
                "Deriving the repair order based on component handling capacity...",
                end="",
            )
            capacity_strategy = strategies.HandlingCapacityStrategy(self.network)
            capacity_strategy.set_repair_order()
            self.repair_order_dict["capacity"] = capacity_strategy.get_repair_order()

            repair_order_pd = pd.DataFrame.from_dict(
                self.repair_order_dict, orient="index"
            ).transpose()
            repair_order_pd.to_csv(
                f"{self.scenario_path}/repair_strategies.csv",
                index=False,
            )

            repair_orders = list(self.repair_order_dict.values())
            self.unique_repair_orders = [
                list(x) for x in set(tuple(x) for x in repair_orders)
            ]
        return self.repair_order_dict

    def perform_shelby_simulation(self):
        if self.disrupt_count > 0:

            for resource_level in self.resource_levels:
                # try:
                base_crew_size = [1,1,1]

                if resource_level == "low":
                    crew_size = [size*1 for size in base_crew_size]
                elif resource_level == "moderate":
                    crew_size = [size*2 for size in base_crew_size]
                elif resource_level == "high":
                    crew_size = [size*3 for size in base_crew_size]
                elif resource_level == "extreme":
                    crew_size = [size*4 for size in base_crew_size]

                self.network.deploy_crews(
                    init_power_crew_locs=["T_J8"] * crew_size[0],
                    init_water_crew_locs=["T_J8"] * crew_size[1],
                    init_transpo_crew_locs=["T_J8"] * crew_size[2],
                )

                shelby_recovery = network_recovery.NetworkRecovery(
                    self.network,
                    sim_step=self.sim_step,
                    pipe_close_policy="repair",
                    pipe_closure_delay=(self.sim_step * 2) / 60,
                    line_close_policy="sensor_based_line_isolation",
                    line_closure_delay=(self.sim_step * 2) / 60,
                )

                # repair_order_dict = self.generate_repair_order_dict(self.network)

                for repair_order in self.unique_repair_orders:
                    print(repair_order)
                    shelby_sim = simulation.NetworkSimulation(shelby_recovery)
                    print(
                        f"Performing simulation for the repair order {repair_order}..."
                    )
                    shelby_sim.network_recovery.schedule_recovery(repair_order)
                    shelby_sim.expand_event_table()

                    clear_output()
                    gc.collect()

                    resilience_metrics = (
                        shelby_sim.simulate_interdependent_effects(
                            shelby_sim.network_recovery
                        )
                    )
                    print("Simulations done")
                    resilience_metrics.calculate_power_resmetric(
                        shelby_sim.network_recovery
                    )
                    resilience_metrics.calculate_water_resmetrics(
                        shelby_sim.network_recovery
                    )
                    print("Resilience metrics calculated")

                    self.shelby_se.combine_infrastructure_se_data(
                        self.network, resilience_metrics
                    )
                    print("Socio-economic data combined")
                    self.shelby_se.calculate_economic_costs()
                    for strategy, values in self.repair_order_dict.items():
                        print(repair_order, values)
                        if repair_order == values:
                            result_dir = (
                                self.scenario_path / f"{resource_level}/{strategy}"
                            )
                            os.makedirs(result_dir, exist_ok=True)
                            shelby_sim.write_results(
                                result_dir, resilience_metrics
                            )

                            # crew size
                            power_size = len(
                                shelby_sim.network_recovery.network.power_crews
                            )
                            water_size = len(
                                shelby_sim.network_recovery.network.water_crews
                            )
                            transpo_size = len(
                                shelby_sim.network_recovery.network.transpo_crews
                            )

                            pd.DataFrame(
                                data=[
                                    ["power", power_size],
                                    ["water", water_size],
                                    ["transpo", transpo_size],
                                ],
                                columns=["infra", "crew_size"],
                            ).to_csv(result_dir / "crew_size.csv", index=False)

                            # event_table
                            shelby_sim.network_recovery.event_table_wide.to_csv(
                                result_dir / "event_table.csv", index=False
                            )

                            # infrastructure and economic disruption
                            self.shelby_se.economic_cost_df.to_csv(
                                result_dir / "economic_cost.csv", index=False
                            )
                # except Exception:
                #     pass

                


# if __name__ == "__main__":
#     NETWORK_DIR = Path("infrarisk/data/networks/micropolis")
#     DEPENDENCY_FILE = NETWORK_DIR / "dependecies.csv"
#     SCENARIOS_DIR = NETWORK_DIR / "scenarios"

#     micropolis_simulation = FullSimulation(NETWORK_DIR, DEPENDENCY_FILE, SCENARIOS_DIR)
#     print(micropolis_simulation.network_dir)
