import os

os.chdir(os.path.split(os.getcwd())[0])

import multiprocessing

import infrarisk.experiments.micropolis_ml_model.micropolis_full_simulation as sim

import copy
from pathlib import Path


NETWORK_DIR = Path("infrarisk/data/networks/micropolis")
DEPENDENCY_FILE = NETWORK_DIR / "dependencies.csv"
SCENARIOS_DIR = NETWORK_DIR / "scenarios"

micropolis_simulation_original = sim.FullSimulation(
    NETWORK_DIR, DEPENDENCY_FILE, SCENARIOS_DIR
)
micropolis_simulation_original.generate_micropolis_network()

SIM_NUMBER = 50


def process_1():
    for i in range(SIM_NUMBER):
        # print(i)
        micropolis_simulation = copy.deepcopy(micropolis_simulation_original)
        try:
            micropolis_simulation.generate_disruptions()

            for mesh_level in micropolis_simulation.networks.keys():
                print(i)
                print(mesh_level)
                micropolis_simulation.set_network(
                    micropolis_simulation.networks[mesh_level]
                )
                micropolis_simulation.set_disrupted_components_for_event(
                    mesh_level=mesh_level
                )
                repair_order_dict = micropolis_simulation.generate_repair_order_dict()
                micropolis_simulation.perform_micropolis_simulation()
                print(micropolis_simulation.network.disruption_time)
                # clear_output(wait=True)
        except StopIteration:
            pass
        except TypeError:
            pass
        except AttributeError:
            pass


def process_2():
    for i in range(SIM_NUMBER):
        # print(i)
        micropolis_simulation = copy.deepcopy(micropolis_simulation_original)
        try:
            micropolis_simulation.generate_disruptions()

            for mesh_level in micropolis_simulation.networks.keys():
                print(i)
                print(mesh_level)
                micropolis_simulation.set_network(
                    micropolis_simulation.networks[mesh_level]
                )
                micropolis_simulation.set_disrupted_components_for_event(
                    mesh_level=mesh_level
                )
                repair_order_dict = micropolis_simulation.generate_repair_order_dict()
                micropolis_simulation.perform_micropolis_simulation()
                print(micropolis_simulation.network.disruption_time)
                # clear_output(wait=True)
        except StopIteration:
            pass
        except TypeError:
            pass
        except AttributeError:
            pass


def process_3():
    for i in range(SIM_NUMBER):
        # print(i)
        micropolis_simulation = copy.deepcopy(micropolis_simulation_original)
        try:
            micropolis_simulation.generate_disruptions()

            for mesh_level in micropolis_simulation.networks.keys():
                print(i)
                print(mesh_level)
                micropolis_simulation.set_network(
                    micropolis_simulation.networks[mesh_level]
                )
                micropolis_simulation.set_disrupted_components_for_event(
                    mesh_level=mesh_level
                )
                repair_order_dict = micropolis_simulation.generate_repair_order_dict()
                micropolis_simulation.perform_micropolis_simulation()
                print(micropolis_simulation.network.disruption_time)
                # clear_output(wait=True)
        except StopIteration:
            pass
        except TypeError:
            pass
        except AttributeError:
            pass


def process_4():
    for i in range(SIM_NUMBER):
        # print(i)
        micropolis_simulation = copy.deepcopy(micropolis_simulation_original)
        try:
            micropolis_simulation.generate_disruptions()

            for mesh_level in micropolis_simulation.networks.keys():
                print(i)
                print(mesh_level)
                micropolis_simulation.set_network(
                    micropolis_simulation.networks[mesh_level]
                )
                micropolis_simulation.set_disrupted_components_for_event(
                    mesh_level=mesh_level
                )
                repair_order_dict = micropolis_simulation.generate_repair_order_dict()
                micropolis_simulation.perform_micropolis_simulation()
                print(micropolis_simulation.network.disruption_time)
                # clear_output(wait=True)
        except StopIteration:
            pass
        except TypeError:
            pass
        except AttributeError:
            pass


def process_5():
    for i in range(SIM_NUMBER):
        # print(i)
        micropolis_simulation = copy.deepcopy(micropolis_simulation_original)
        try:
            micropolis_simulation.generate_disruptions()

            for mesh_level in micropolis_simulation.networks.keys():
                print(i)
                print(mesh_level)
                micropolis_simulation.set_network(
                    micropolis_simulation.networks[mesh_level]
                )
                micropolis_simulation.set_disrupted_components_for_event(
                    mesh_level=mesh_level
                )
                repair_order_dict = micropolis_simulation.generate_repair_order_dict()
                micropolis_simulation.perform_micropolis_simulation()
                print(micropolis_simulation.network.disruption_time)
                # clear_output(wait=True)
        except StopIteration:
            pass
        except TypeError:
            pass
        except AttributeError:
            pass


if __name__ == "__main__":
    proc1 = multiprocessing.Process(target=process_1)
    proc1.start()

    proc2 = multiprocessing.Process(target=process_2)
    proc2.start()

    proc3 = multiprocessing.Process(target=process_3)
    proc3.start()

    proc4 = multiprocessing.Process(target=process_4)
    proc4.start()

    proc5 = multiprocessing.Process(target=process_5)
    proc5.start()

    proc1.join()

    proc2.join()

    proc3.join()

    proc4.join()

    proc5.join()

    # both processes finished
    print("Done!")
