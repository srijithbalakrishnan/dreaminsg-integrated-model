import os
import copy
import gc
from pysinewave import SineWave
import time
import random

from IPython.display import clear_output


def run_simulations(arguments):
    (
        scenario,
        shelby_simulation_original,
        NETWORK_DIR,
        FRAGILITY_FILE,
        GMF_FOLDER,
        NUM_SIM,
    ) = arguments
    print(scenario)
    # time.sleep(random.randint(0, 50))

    if not os.path.exists(NETWORK_DIR / f"scenarios/shelby_experiments/{scenario}"):
        os.makedirs(NETWORK_DIR / f"scenarios/shelby_experiments/{scenario}")
    SCENARIOS_DIR = NETWORK_DIR / f"scenarios/shelby_experiments/{scenario}"

    try:
        shelby_simulation = copy.deepcopy(shelby_simulation_original)
        shelby_simulation.scenarios_dir = SCENARIOS_DIR
        shelby_simulation.generate_disruptions(
            fragility_file=FRAGILITY_FILE,
            gmf_file=GMF_FOLDER / f"{scenario}/{scenario}_gms.csv",
        )

        for _ in range(NUM_SIM):
            shelby_simulation_for_event = copy.deepcopy(shelby_simulation)

            shelby_simulation_for_event.set_disrupted_components_for_event()

            repair_order_dict = shelby_simulation_for_event.generate_repair_order_dict()
            shelby_simulation_for_event.perform_shelby_simulation()
            gc.collect()
            del shelby_simulation
            del shelby_simulation_for_event
            play_sound("completed")

    except RuntimeError:
        gc.collect()
        clear_output()
        print(
            "Runtime Error occurred - possibly the water network simulation did not converge."
        )
        play_sound("error")
    except Exception:
        gc.collect()


def play_sound(type_of_sound):

    if type_of_sound == "completed":
        sinewave = SineWave(pitch=5)
    elif type_of_sound == "error":
        sinewave = SineWave(pitch=30)

    sinewave.play()
    time.sleep(1)
    sinewave.stop()
    time.sleep(0.5)
    sinewave.play()
    time.sleep(1)
    sinewave.stop()
