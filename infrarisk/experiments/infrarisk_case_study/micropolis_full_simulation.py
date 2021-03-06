import os
from pathlib import Path

from numpy import maximum
import infrarisk.src.network_recovery as network_recovery
import infrarisk.src.simulation as simulation
import infrarisk.src.physical.integrated_network as int_net
import infrarisk.src.recovery_strategies as strategies
import infrarisk.src.hazard_initiator as hazard

import random
import geopandas as gpd
import pandas as pd
import copy

import warnings

warnings.filterwarnings("ignore")


class FullSimulation:
    def __init__(self, network_dir, dependency_file, scenarios_dir):
        self.network_dir = network_dir
        self.dependency_file = dependency_file
        self.scenarios_dir = scenarios_dir

    def generate_micropolis_network(self):
        """This is the main function that contains the whole simulation workflow."""
        os.system("cls")

        micropolis_network = int_net.IntegratedNetwork(name="Micropolis")

        water_folder = self.network_dir / "water/med"
        power_folder = self.network_dir / "power/low"
        transp_folder = self.network_dir / "transportation/high"

        micropolis_network.load_networks(
            water_folder,
            power_folder,
            transp_folder,
            power_sim_type="1ph",
            water_sim_type="PDA",
        )

        micropolis_network.generate_integrated_graph()

        micropolis_network.generate_dependency_table(
            dependency_file=self.dependency_file
        )

        self.network = micropolis_network

    def generate_disruptions(self):

        disruption_list = ["flood"]

        buffer_list = [100]
        intensity_list = (
            ["high"] * 2 + ["moderate"] * 5 + ["low"] * 3
        )  # based on probability distribution
        disruptive_event = random.choice(disruption_list)
        buffer = random.choice(buffer_list)
        intensity = random.choice(intensity_list)

        if disruptive_event == "targetted":
            map_extends = self.network.get_map_extends()
            point_of_occurrence = (
                random.randint(map_extends[0][0], map_extends[1][0]),
                random.randint(map_extends[0][1], map_extends[1][1]),
            )
            event = hazard.RadialDisruption(
                point_of_occurrence=point_of_occurrence,
                radius_of_impact=buffer,
                intensity=intensity,
                name="point",
            )
            event.set_affected_components(
                self.network.integrated_graph, plot_components=False
            )

        elif disruptive_event == "flood":
            micropolis_streams = gpd.read_file(
                self.network_dir / "gis/streams_v1.shp", encoding="utf-8"
            )
            micropolis_streams = micropolis_streams.loc[[1, 2], :]
            event = hazard.TrackDisruption(
                hazard_tracks=micropolis_streams,
                buffer_of_impact=buffer,
                time_of_occurrence=6000,
                intensity=intensity,
                name="flood",
            )
            event.set_affected_components(
                self.network.integrated_graph, plot_components=False
            )
        elif disruptive_event == "track":
            event = hazard.TrackDisruption(
                hazard_tracks=None,
                buffer_of_impact=50,
                time_of_occurrence=6000,
                intensity=intensity,
                name="track",
            )

            micropolis_map_extents = self.network.get_map_extends()
            event_track = event.generate_random_track(
                micropolis_map_extents, shape="spline"
            )
            event.set_hazard_tracks_from_linestring(event_track)
            event.set_affected_components(
                self.network.integrated_graph, plot_components=False
            )

        # print(event.affected_links)
        self.disrupt_count = 0

        for infra in event.affected_links.keys():
            self.disrupt_count = self.disrupt_count + len(event.affected_links[infra])
        for infra in event.affected_nodes.keys():
            self.disrupt_count = self.disrupt_count + len(event.affected_nodes[infra])
        # print(self.disrupt_count)

        if self.disrupt_count > 0:
            test_counter = len(os.listdir(self.scenarios_dir))
            self.scenario_path = self.scenarios_dir / f"flood{test_counter}"
            if not os.path.exists(self.scenario_path):
                os.makedirs(self.scenario_path)
            scenario_path = event.generate_disruption_file(
                location=self.scenario_path, maximum_data=35
            )
            print(f"Hazard event generated in {self.scenario_path}.")

            self.network.set_disrupted_components(
                scenario_file=self.scenario_path / "disruption_file.csv"
            )
            # self.network.pipe_leak_node_generator()
        else:
            print(
                "Ignoring the generated hazard scenario due to insufficient disruptions."
            )

    def generate_repair_order_dict(self):
        if self.disrupt_count > 0:
            for strategy in ["capacity", "centrality", "zone"]:
                if not os.path.exists(f"{self.scenario_path}/{strategy}"):
                    os.makedirs(f"{self.scenario_path}/{strategy}")

            self.repair_order_dict = dict()
            print("Deriving the repair order based on component handling capacity...")
            capacity_strategy = strategies.HandlingCapacityStrategy(self.network)
            capacity_strategy.set_repair_order()
            self.repair_order_dict["capacity"] = capacity_strategy.get_repair_order()

            print(
                "Deriving the repair order based on component betweenness centrality..."
            )
            centrality_strategy = strategies.CentralityStrategy(self.network)
            centrality_strategy.set_repair_order()
            self.repair_order_dict[
                "centrality"
            ] = centrality_strategy.get_repair_order()

            # print(
            #     "Deriving the repair order based on crew distance to the component..."
            # )
            # distance_strategy = strategies.CrewDistanceStrategy(self.network)
            # distance_strategy.set_repair_order()
            # self.repair_order_dict["crewdist"] = distance_strategy.get_repair_order()

            print("Deriving the repair order based on component zone...")
            micropolis_zones_shp = f"{self.network_dir}/gis/micropolis_zones.shp"
            zone_strategy = strategies.ZoneBasedStrategy(
                self.network, micropolis_zones_shp
            )
            zone_strategy.set_repair_order()
            self.repair_order_dict["zone"] = zone_strategy.get_repair_order()

            repair_order_pd = pd.DataFrame.from_dict(
                self.repair_order_dict, orient="index"
            ).transpose()
            repair_order_pd.to_csv(
                f"{self.scenario_path}/repair_strategies.csv", index=False
            )

            repair_orders = list(self.repair_order_dict.values())
            self.unique_repair_orders = [
                list(x) for x in set(tuple(x) for x in repair_orders)
            ]
            return self.repair_order_dict

    def perform_micropolis_simulation(self):

        self.network.deploy_crews(
            init_power_crew_locs=["T_J8"],
            init_water_crew_locs=["T_J8"],
            init_transpo_crew_locs=["T_J8"],
        )

        if self.disrupt_count > 0:
            micropolis_recovery = network_recovery.NetworkRecovery(
                self.network,
                sim_step=60,
                pipe_close_policy="sensor_based_cluster_isolation",
                pipe_closure_delay=10,
                line_close_policy="sensor_based_cluster_isolation",
                line_closure_delay=10,
            )

            sim_step = self.network.wn.options.time.hydraulic_timestep

            # repair_order_dict = self.generate_repair_order_dict(self.network)

            for repair_order in self.unique_repair_orders:
                self.micropolis_sim = simulation.NetworkSimulation(
                    copy.deepcopy(micropolis_recovery),
                    sim_step,
                )
                print(f"Performing simulation for the repair order {repair_order}...")
                self.micropolis_sim.network_recovery.schedule_recovery(repair_order)
                self.micropolis_sim.expand_event_table(5)

                resilience_metrics = (
                    self.micropolis_sim.simulate_interdependent_effects(
                        self.micropolis_sim.network_recovery
                    )
                )

                # resilience_metrics.set_weighted_auc_metrics()

                # time_tracker, power_consump_tracker, water_consump_tracker = (
                #     resilience_metrics.time_tracker,
                #     resilience_metrics.power_consump_tracker,
                #     resilience_metrics.water_consump_tracker,
                # )

                for strategy in self.repair_order_dict.keys():
                    if repair_order == self.repair_order_dict[strategy]:
                        result_dir = self.scenario_path / f"{strategy}"
                        self.micropolis_sim.write_results(
                            result_dir,
                            resilience_metrics,
                            plotting=False,
                        )

                        self.micropolis_sim.network_recovery.event_table_wide.to_csv(
                            result_dir / "event_table_wide.csv", index=False
                        )


# if __name__ == "__main__":
#     NETWORK_DIR = Path("infrarisk/data/networks/micropolis")
#     DEPENDENCY_FILE = NETWORK_DIR / "dependecies.csv"
#     SCENARIOS_DIR = NETWORK_DIR / "scenarios"

#     micropolis_simulation = FullSimulation(NETWORK_DIR, DEPENDENCY_FILE, SCENARIOS_DIR)
#     print(micropolis_simulation.network_dir)
