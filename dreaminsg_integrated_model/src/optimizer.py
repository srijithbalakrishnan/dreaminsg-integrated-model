from abc import ABC, abstractmethod
from itertools import permutations
from sklearn import metrics
import pandas as pd
import timeit

import dreaminsg_integrated_model.src.plots as model_plots


class Optimizer(ABC):
    "The Optimizer class defines an interface to a discrete optimizer or can be implemented as such. This optimizer takes a network object and a prediction horizon and should compute the best steps of the length of the prediction_horizon"
    # TODO: This class might need to take another object defining its optimization objection

    @abstractmethod
    def __init__(self, prediction_horizon=None):
        pass


class BruteForceOptimizer(Optimizer):
    """A Brute Force Optimizer class

    :param Optimizer: An optimizer class.
    :type Optimizer: Optimizer abstract class.
    """

    def __init__(self, prediction_horizon=None):
        """Initiates a BruteForceOptimizer object

        :param prediction_horizon: The size of the prediction horizon, defaults to None
        :type prediction_horizon: non-negative integer, optional
        """
        if prediction_horizon is None:
            self.prediction_horizon = 0
        else:
            self.prediction_horizon = prediction_horizon

        self.best_repair_strategy = None

        self.auc = None
        self.auc_log = pd.DataFrame(
            columns=["repair_order", "water_auc", "power_auc", "auc"]
        )

        # self.set_auc_temp_log()

    def get_repair_permutations(self, simulation):
        """Returns all possible permutations of the repair order.

        :param simulation: An integrated infrastructure network simulation object.
        :type simulation: Simulation object
        :return: A nested list of all possible repair permutations for the given list of components.
        :rtype: list of lists of strings.
        """
        comps_to_repair = simulation.get_components_to_repair()
        if len(comps_to_repair) >= self.prediction_horizon:
            repair_permuts = permutations(comps_to_repair, self.prediction_horizon)
        else:
            repair_permuts = permutations(comps_to_repair, len(comps_to_repair))
        return [list(x) for x in list(repair_permuts)]

    def find_optimal_recovery(self, simulation):
        """Identifies the optimal recovery strategy using the Model Predictive Control principle.

        :param simulation: The infrastructure network simulation object.
        :type simulation: Simulation object.
        """
        start = timeit.default_timer()
        counter = 1

        while len(simulation.get_components_to_repair()) > 0:
            print("PREDICTION HORIZON {}".format(counter))
            print("*" * 50)
            print(
                "Components to repair: ", 
                simulation.get_components_to_repair(),
                "Components repaired: ",
                simulation.get_components_repaired(),
            )

            repair_orders = self.get_repair_permutations(simulation)
            print(
                "Repair orders under consideration in the current prediction horizon: ",
                repair_orders,
            )

            print("-" * 50)
            for index, repair_order in enumerate(repair_orders):
                cum_repair_order = simulation.get_components_repaired() + repair_order
                print(
                    "Simulating the current cumulative repair order",
                    cum_repair_order,
                    "...",
                )

                simulation.network_recovery.schedule_recovery(cum_repair_order)
                # print(simulation.network_recovery.get_event_table())
                simulation.expand_event_table(30)
                # print(simulation.network_recovery.get_event_table())

                (
                    time_tracker,
                    power_consump_tracker,
                    water_consump_tracker,
                ) = simulation.simulate_interdependent_effects(
                    simulation.network_recovery
                )

                ilos_dict = {
                    "water": water_consump_tracker, 
                    "power": power_consump_tracker,
                    "time": time_tracker,
                }

                model_plots.plot_interdependent_effects(
                    power_consump_tracker,
                    water_consump_tracker,
                    time_tracker,
                    scatter=True,
                )
                # plt.savefig("{}.csv".format(cum_repair_order))

                # pd.DataFrame(ilos_dict).to_csv("{}.csv".format(cum_repair_order))

                water_auc = metrics.auc(time_tracker, water_consump_tracker) / max(
                    time_tracker
                )
                power_auc = metrics.auc(time_tracker, power_consump_tracker) / max(
                    time_tracker
                )
                auc = 0.5 * water_auc + 0.5 * power_auc
                print(
                    "Water AUC: ",
                    round(water_auc, 3),
                    "\t",
                    "Power AUC: ", 
                    round(power_auc, 3),
                    "\t",
                    "Weighted AUC: ",
                    round(auc, 3),
                )
                self.auc_log = self.auc_log.append(
                    {
                        "repair_order": cum_repair_order, 
                        "water_auc": round(water_auc, 3),
                        "power_auc": round(power_auc, 3),
                        "auc": round(auc, 3),
                    },
                    ignore_index=True,
                )
                if (self.auc == None) or (auc >= self.auc):
                    self.auc = auc
                    self.best_repair_strategy = cum_repair_order

                simulation.network_recovery.reset_networks()

            best_repair_component = [
                i
                for i in self.best_repair_strategy
                if i not in simulation.get_components_repaired()
            ][0]

            print(
                "\n{} is identified as the next best repair action in the current prediction horizon. The repair order {} produced the highest AUC of {}".format(
                    best_repair_component, self.best_repair_strategy, self.auc
                )
            )
            print("-" * 50)

            simulation.update_repaired_components(best_repair_component)

            self.auc = None
            counter += 1

        print("-" * 50)
        print(
            "Optimization completed. The MPC optimal repair order to restore the network is {}.".format(
                self.best_repair_strategy
            )
        )

        stop = timeit.default_timer()
        print("Process completed in ", round(stop - start, 0), " seconds")

    def get_optimization_log(self):
        """Returns the optimization log.

        :return: A table consisting of the AUC values from the network simulations.
        :rtype: pandas dataframe.
        """
        return self.auc_log
