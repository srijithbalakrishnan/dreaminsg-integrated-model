import os
from pathlib import Path
import infrarisk.src.network_recovery as network_recovery
import infrarisk.src.simulation as simulation
import infrarisk.src.network_sim_models.integrated_network as int_net
import infrarisk.src.recovery_strategies as strategies
import infrarisk.src.hazard_initiator as hazard

import random
import geopandas as gpd
import pandas as pd
import copy

from random import randrange

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

        micropolis_networks = {"low": None, "med": None, "high": None}

        for mesh_level in micropolis_networks.keys():
            micropolis_networks[mesh_level] = int_net.IntegratedNetwork(
                name=f"Micropolis_{mesh_level}"
            )
            water_folder = self.network_dir / f"water/{mesh_level}"
            power_folder = self.network_dir / f"power/{mesh_level}"
            transp_folder = self.network_dir / f"transportation/{mesh_level}"

            micropolis_networks[mesh_level].load_networks(
                water_folder,
                power_folder,
                transp_folder,
                power_sim_type="1ph",
                water_sim_type="PDA",
            )

            micropolis_networks[mesh_level].generate_integrated_graph()

            micropolis_networks[mesh_level].generate_dependency_table(
                dependency_file=self.dependency_file
            )

            # micropolis_networks[mesh_level].set_init_crew_locs(
            #     init_power_loc="T_J8",
            #     init_water_loc="T_J8",
            #     init_transpo_loc="T_J8",
            # )

            self.networks = micropolis_networks

    def set_network(self, network):
        self.network = network

    def generate_disruptions(self):

        disruption_list = ["targetted"] * 1 + ["track"] * 3

        buffer_list = [50] * 1 + [100] * 4 + [150] * 2 + [200]
        intensity_list = [
            "random"
        ]  # (["high"] * 2 + ["moderate"] * 15 + ["low"] * 2)  # based on probability distribution
        disruptive_event = random.choice(disruption_list)
        buffer = random.choice(buffer_list)
        intensity = random.choice(intensity_list)

        if disruptive_event == "targetted":
            map_extends = self.networks["med"].get_map_extends()
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
            # event.set_affected_components(
            #     self.network.integrated_graph, plot_components=False
            # )

        elif disruptive_event == "flood":
            micropolis_streams = gpd.read_file(
                self.network_dir / "gis/streams_v1.shp", encoding="utf-8"
            )
            event = hazard.TrackDisruption(
                hazard_tracks=micropolis_streams,
                buffer_of_impact=buffer,
                time_of_occurrence=6000,
                intensity=intensity,
                name="flood",
            )
            # event.set_affected_components(
            #     self.network.integrated_graph, plot_components=False
            # )
        elif disruptive_event == "track":
            event = hazard.TrackDisruption(
                hazard_tracks=None,
                buffer_of_impact=50,
                time_of_occurrence=6000,
                intensity=intensity,
                name="track",
            )

            micropolis_map_extents = self.networks["med"].get_map_extends()
            event_track = event.generate_random_track(
                micropolis_map_extents, shape="spline"
            )
            event.set_hazard_tracks_from_linestring(event_track)
            # event.set_affected_components(
            #     self.network.integrated_graph, plot_components=False
            # )
        self.event = event

        test_counter = len(os.listdir(self.scenarios_dir))
        self.scenario_path = self.scenarios_dir / f"{event.name}{test_counter}"
        if not os.path.exists(self.scenarios_dir / f"{event.name}{test_counter}"):
            os.makedirs(self.scenarios_dir / f"{event.name}{test_counter}")

    def set_disrupted_components_for_event(self, mesh_level):

        self.event.set_affected_components(
            self.network.integrated_graph, plot_components=False
        )

        # print(event.affected_links)
        self.disrupt_count = 0

        for infra in self.event.affected_links.keys():
            self.disrupt_count = self.disrupt_count + len(
                self.event.affected_links[infra]
            )
        for infra in self.event.affected_nodes.keys():
            self.disrupt_count = self.disrupt_count + len(
                self.event.affected_nodes[infra]
            )
        # print(self.disrupt_count)

        if self.disrupt_count > 0:
            self.case_path = self.event.generate_disruption_file(
                location=self.scenario_path, folder_extra=mesh_level
            )
            print(f"Hazard event generated in {self.case_path}.")

            # print(f"Network distupt time: {self.network.disruption_time}")
            self.network.set_disrupted_components(
                scenario_file=self.case_path / "disruption_file.csv"
            )
            # print(f"Network distupt time: {self.network.disruption_time}")
            self.network.pipe_leak_node_generator()
        else:
            print(
                "Ignoring the generated hazard scenario due to insufficient disruptions."
            )

    def generate_repair_order_dict(self):
        if self.disrupt_count > 0:
            for strategy in ["capacity", "centrality", "zone"]:
                if not os.path.exists(f"{self.case_path}/{strategy}"):
                    os.makedirs(f"{self.case_path}/{strategy}")

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
                f"{self.case_path}/repair_strategies.csv", index=False
            )

            repair_orders = list(self.repair_order_dict.values())
            self.unique_repair_orders = [
                list(x) for x in set(tuple(x) for x in repair_orders)
            ]
            return self.repair_order_dict

    def perform_micropolis_simulation(self):
        if self.disrupt_count > 0:
            power_count = len(self.network.disrupted_infra_dict["power"])
            water_count = len(self.network.disrupted_infra_dict["water"])
            transpo_count = len(self.network.disrupted_infra_dict["transpo"])

            crew_size = [
                randrange(1, min(power_count + 2, 8)),
                randrange(1, min(water_count + 2, 8)),
                randrange(1, min(transpo_count + 2, 8)),
            ]

            self.network.deploy_crews(
                init_power_crew_locs=["T_J8"] * crew_size[0],
                init_water_crew_locs=["T_J8"] * crew_size[1],
                init_transpo_crew_locs=["T_J8"] * crew_size[2],
            )

            micropolis_recovery = network_recovery.NetworkRecovery(
                self.network, sim_step=60
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
                self.micropolis_sim.expand_event_table(1)

                resilience_metrics = (
                    self.micropolis_sim.simulate_interdependent_effects(
                        self.micropolis_sim.network_recovery
                    )
                )

                for strategy in self.repair_order_dict.keys():
                    if repair_order == self.repair_order_dict[strategy]:
                        result_dir = self.case_path / f"{strategy}"
                        self.micropolis_sim.write_results(
                            result_dir,
                            resilience_metrics,
                            plotting=False,
                        )

                        self.micropolis_sim.network_recovery.event_table_wide.to_csv(
                            result_dir / "event_table_wide.csv", index=False
                        )

                        # crew size
                        power_size = len(
                            self.micropolis_sim.network_recovery.network.power_crews
                        )
                        water_size = len(
                            self.micropolis_sim.network_recovery.network.water_crews
                        )
                        transpo_size = len(
                            self.micropolis_sim.network_recovery.network.transpo_crews
                        )

                        pd.DataFrame(
                            data=[
                                ["power", power_size],
                                ["water", water_size],
                                ["transpo", transpo_size],
                            ],
                            columns=["infra", "crew_size"],
                        ).to_csv(result_dir / "crew_size.csv", index=False)

                        # crew travel time
                        pd.DataFrame(
                            data=[
                                [
                                    "power",
                                    self.micropolis_sim.network_recovery.power_crew_total_tt,
                                ],
                                [
                                    "water",
                                    self.micropolis_sim.network_recovery.water_crew_total_tt,
                                ],
                                [
                                    "transpo",
                                    self.micropolis_sim.network_recovery.transpo_crew_total_tt,
                                ],
                            ],
                            columns=["infra", "crew_tt"],
                        ).to_csv(result_dir / "crew_tt.csv", index=False)


# if __name__ == "__main__":
#     NETWORK_DIR = Path("infrarisk/data/networks/micropolis")
#     DEPENDENCY_FILE = NETWORK_DIR / "dependecies.csv"
#     SCENARIOS_DIR = NETWORK_DIR / "scenarios"

#     micropolis_simulation = FullSimulation(NETWORK_DIR, DEPENDENCY_FILE, SCENARIOS_DIR)
#     print(micropolis_simulation.network_dir)
