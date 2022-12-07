"""Class of disruption based on fragility analysis"""
import os
from pathlib import Path
import numpy as np
import random
import pandas as pd
import seaborn as sns
from scipy.stats import norm
from scipy.interpolate import griddata
from shapely.geometry import Point, LineString

import matplotlib.pyplot as plt
import contextily as ctx

from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.models.widgets import Panel, Tabs
from bokeh.palettes import RdYlGn
from bokeh.plotting import figure
from bokeh.tile_providers import Vendors, get_provider
from bokeh.transform import factor_cmap

import infrarisk.src.physical.interdependencies as interdependencies


class FragilityBasedDisruption:
    def __init__(
        self,
        resilience_level="high",
        name="Fragility based disruption",
        fragility_df=None,
        time_of_occurrence=6000,
    ):
        """Initializes the fragility based disruption class

        :param name: Name of the disruption, defaults to "Fragility based disruption"
        :type name: str, optional
        :param time_of_occurrence: The time of occurrence of the event in the simulation in seconds, defaults to 6000
        :type time_of_occurrence: int, optional
        """
        self.name = name
        self.time_of_occurrence = time_of_occurrence
        self.fragility_df = fragility_df
        self.fragility_curves = dict()
        self.recovery_curves = dict()
        self.resilience_level = resilience_level

    def set_fail_compon_dict(self, fail_compon_dict):
        """Sets the dictionary of the component types that fail

        :param fail_compon_dict: The dictionary of the component types in each infrastructure system that must be considered for disruption.
        :type fail_compon_dict: dict
        """
        self.fail_compon_dict = fail_compon_dict

    def get_fail_compon_dict(self):
        """Returns the dictionary of the component types that fail

        :return: The dictionary of the component types in each infrastructure system that must be considered for disruption
        :rtype: dict
        """
        return self.fail_compon_dict

    def set_all_fragility_and_recovery_curves(self):
        """Creates a dictionary of all fragility curves that will be used in generating the disruptions."""
        for compon_prefix in self.fragility_df["compon_prefix"].unique():
            compon_list = compon_prefix.split(",")
            compon_type_df = self.fragility_df[
                self.fragility_df["compon_prefix"] == compon_prefix
            ]

            imt = compon_type_df["imt"].unique()[0]
            list_of_states = compon_type_df["damage_state"].to_list()
            list_of_ds_median = compon_type_df["ds_median"].to_list()
            list_of_ds_beta = compon_type_df["ds_beta"].to_list()
            list_of_recov_mean = compon_type_df["recov_mean"].to_list()
            list_of_recov_sigma = compon_type_df["recov_sigma"].to_list()

            for compon in compon_list:
                self.set_compon_fragility_curves(
                    compon, imt, list_of_states, list_of_ds_median, list_of_ds_beta
                )
                self.set_compon_recovery_curves(
                    compon, list_of_states, list_of_recov_mean, list_of_recov_sigma
                )

    def set_compon_recovery_curves(
        self, compon_prefix, list_of_states, list_of_recov_mean, list_of_recov_sigma
    ):
        """Sets the recovery curves for a component type

        :param compon_prefix: The prefix of the component type
        :type compon_prefix: str
        :param list_of_states: The list of states
        :type list_of_states: list
        :param list_of_recov_mean: The list of mean values of the recovery curves in the order of states
        :type list_of_recov_mean: list
        :param list_of_recov_sigma: The list of sigma values of the recovery curves in the order of states
        :type list_of_recov_sigma: list
        """
        self.recovery_curves[compon_prefix] = dict()
        for index, state in enumerate(list_of_states):
            self.recovery_curves[compon_prefix][state] = dict()
            self.recovery_curves[compon_prefix][state][
                "recov_mean"
            ] = list_of_recov_mean[index]
            self.recovery_curves[compon_prefix][state][
                "recov_sigma"
            ] = list_of_recov_sigma[index]

    def set_compon_fragility_curves(
        self, compon_prefix, imt, list_of_states, list_of_ds_median, list_of_ds_beta
    ):
        """Sets the fragility curves for a component type

        :param compon_prefix: The prefix of the component type
        :type compon_prefix: str
        :param imt: The intensity measure type
        :type imt: str
        :param list_of_states: The list of states
        :type list_of_states: list
        :param list_of_ds_median: The list of median values of the fragility curves in the order of states
        :type list_of_ds_median: list
        :param list_of_ds_beta: The list of beta values of the fragility curves in the order of states
        :type list_of_ds_beta: list
        """
        self.fragility_curves[compon_prefix] = dict()
        for index, state in enumerate(list_of_states):
            self.fragility_curves[compon_prefix][state] = dict()
            self.fragility_curves[compon_prefix][state]["imt"] = imt
            self.fragility_curves[compon_prefix][state][
                "ds_median"
            ] = list_of_ds_median[index]
            self.fragility_curves[compon_prefix][state]["ds_beta"] = list_of_ds_beta[
                index
            ]
        self.set_imt_dict()

    def set_imt_dict(self):
        """Sets the mapping between infrastructure components and corresponding imt measures used in fragility curves, if available."""
        self.imt_dict = (
            self.fragility_df[["compon_prefix", "imt"]]
            .drop_duplicates()
            .set_index("compon_prefix")
            .to_dict("index")
        )

    def get_imt_dict(self):
        """Returns the mapping between infrastructure components and corresponding imt measures as a dictionary.

        :return: The dictionary with component prefix as the keys and imt measure types as the values.
        :rtype: dictionary
        """
        return self.imt_dict

    def set_node_gmfs(self, G, gmf_gpd):
        """Calculates the ground motion field values of all node components that must be considered for disruptions.

        :param G: The integrated graph object
        :type G: IntegratedNetwork.integrated_graph object
        :param gmf_gpd: The geopandas GeoDataFrame that consists of the ground motion fields at available geographic points.
        :type gmf_gpd: geopandas.GeoDataFrame object
        """
        self.node_gmfs = {}
        self.nodes_with_no_gmf = []
        for _, node in enumerate(G.nodes.keys()):
            node_details = interdependencies.get_compon_details(node)
            node_prefix = node_details["infra_code"] + "_" + node_details["type_code"]
            if node_prefix in self.get_imt_dict().keys():
                imt_type = self.get_imt_dict()[node_prefix]["imt"]
                coords = G.nodes[node]["coord"]
                self.node_gmfs[node] = self.get_imt_at_point(
                    coords, imt_type=imt_type, gmf_gpd=gmf_gpd
                )
            else:
                self.nodes_with_no_gmf.append(node)

    def set_link_gmfs(self, G, gmf_gpd):
        """Calculates the ground motion field values of all link (edge) components that must be considered for disruptions.

        :param G: The integrated graph object
        :type G: IntegratedNetwork.integrated_graph object
        :param gmf_gpd: The geopandas GeoDataFrame that consists of the ground motion fields at available geographic points.
        :type gmf_gpd: geopandas.GeoDataFrame object
        """
        self.link_gmfs = {}
        self.links_with_no_gmfs = []
        for _, link in enumerate(G.edges().keys()):
            link_id = G.edges[link]["id"]
            link_details = interdependencies.get_compon_details(link_id)
            link_prefix = link_details["infra_code"] + "_" + link_details["type_code"]
            if link_prefix in self.get_imt_dict().keys():
                if link_prefix not in ["W_PMA", "W_P", "W_PSC"]:
                    imt_type = self.get_imt_dict()[link_prefix]["imt"]
                else:
                    imt_type = "PGV"

                start_coords = G.nodes[link[0]]["coord"]
                end_coords = G.nodes[link[1]]["coord"]
                self.link_gmfs[link_id] = self.get_imt_at_line(
                    start_coords, end_coords, imt_type=imt_type, gmf_gpd=gmf_gpd
                )
            else:
                self.links_with_no_gmfs.append(link_id)

    def set_gmfs(self, G, gmf_gpd):
        """Calculates the ground motion field values of all components that must be considered for disruptions.

        :param G: The integrated graph object
        :type G: IntegratedNetwork.integrated_graph object
        :param gmf_gpd: The geopandas GeoDataFrame that consists of the ground motion fields at available geographic points.
        :type gmf_gpd: geopandas.GeoDataFrame object
        """
        self.set_node_gmfs(G, gmf_gpd)
        self.set_link_gmfs(G, gmf_gpd)

    def set_affected_components(
        self, integrated_network, gmf_gpd, disruption_time, plot_components=True
    ):
        """Determines the dirupted infrastructure components using the calculated damage state probabilities.

        :param G: The networkx integrated graph object
        :type G: IntegratedNetwork.integrated_graph object
        :param gmf_gpd: The geopandas GeoDataFrame that consists of the ground motion fields at available geographic points.
        :type gmf_gpd: geopandas.GeoDataFrame object
        :param disruption_time: The time of disruption in seconds
        :type disruption_time: integer
        :param plot_components: boolean to determine whether to generate the diruption plots, defaults to True
        :type plot_components: bool, optional
        """

        self.fail_probs_df = pd.DataFrame(
            columns=[
                "component",
                "disruption_time",
                "state_probs",
                "disruption_state",
                "recovery_time",
            ]
        )
        G = integrated_network.integrated_graph

        for node in G.nodes.keys():
            node_details = interdependencies.get_compon_details(node)
            node_prefix = node_details["infra_code"] + "_" + node_details["type_code"]

            if node_prefix in self.get_imt_dict().keys():
                imt_type = self.get_imt_dict()[node_prefix]["imt"]
                imt = self.node_gmfs[node]

                fail_probs = self.ascertain_damage_probabilities(
                    node, imt_type, imt, plotting=False
                )
                states = list(self.fragility_curves[node_prefix].keys())

                if fail_probs is not None:
                    if np.isnan(fail_probs).all() == False:
                        states = states + ["None"]
                        fail_probs = fail_probs + [1 - sum(fail_probs)]
                        failure_state = random.choices(states, weights=fail_probs, k=1)[
                            0
                        ]
                        recovery_time = self.assign_recovery_time(node, failure_state)

                        G.nodes[node]["failure_state"] = failure_state
                        self.fail_probs_df = self.fail_probs_df.append(
                            {
                                "component": node,
                                "disruption_time": disruption_time,
                                "state_probs": fail_probs,
                                "disruption_state": failure_state,
                                "recovery_time": recovery_time,
                            },
                            ignore_index=True,
                        )
                    else:
                        G.nodes[node]["failure_state"] = "None"
                else:
                    G.nodes[node]["failure_state"] = "None"
            else:
                G.nodes[node]["failure_state"] = "None"

        for link in G.edges.keys():
            link_id = G.edges[link]["id"]
            link_details = interdependencies.get_compon_details(link_id)
            link_prefix = link_details["infra_code"] + "_" + link_details["type_code"]

            if link_prefix in self.get_imt_dict().keys():
                imt_type = self.get_imt_dict()[link_prefix]["imt"]
                imt = self.link_gmfs[link_id]

                if link_prefix not in ["W_PMA", "W_P", "W_PSC"]:
                    fail_probs = self.ascertain_damage_probabilities(
                        link_id, imt_type, imt, plotting=False
                    )
                else:
                    fail_probs = self.ascertain_pipe_damage_probabilities(
                        wn=integrated_network.wn,
                        pipe=link_id,
                        gmf_gpd=gmf_gpd,
                        method=1,
                        plotting=False,
                    )

                states = list(self.fragility_curves[link_prefix].keys())

                if fail_probs is not None:
                    if np.isnan(fail_probs).all() == False:
                        states = states + ["None"]
                        fail_probs = fail_probs + [1 - sum(fail_probs)]
                        failure_state = random.choices(states, weights=fail_probs, k=1)[
                            0
                        ]
                        recovery_time = self.assign_recovery_time(
                            link_id, failure_state
                        )

                        G.edges[link]["failure_state"] = failure_state
                        self.fail_probs_df = self.fail_probs_df.append(
                            {
                                "component": link_id,
                                "disruption_time": disruption_time,
                                "state_probs": fail_probs,
                                "disruption_state": failure_state,
                                "recovery_time": recovery_time,
                            },
                            ignore_index=True,
                        )
                    else:
                        G.edges[link]["failure_state"] = "None"
                else:
                    G.edges[link]["failure_state"] = "None"
            else:
                G.edges[link]["failure_state"] = "None"

        self.fail_probs_df["infra"] = self.fail_probs_df["component"].apply(
            lambda x: interdependencies.get_compon_details(x)["infra"].title()
        )

        damage_perc_dict = {
            "None": 0,
            "Slight": 0,
            "Moderate": 25,
            "Extensive": 50,
            "Complete": 100,
        }
        self.fail_probs_df["damage_perc"] = self.fail_probs_df["disruption_state"].map(
            damage_perc_dict
        )

        if plot_components == True:
            self.plot_disruptions(
                integrated_graph=G, map_extends=integrated_network.map_extends
            )

    def assign_recovery_time(self, component, failure_state):
        """Assigns the recovery time of a component based on the failure state.

        :param component: The component identifier
        :type component: str
        :param failure_state: The failure state of the component
        :type failure_state: str
        :return: The recovery time of the component
        :rtype: float
        """
        component_details = interdependencies.get_compon_details(component)
        component_prefix = (
            component_details["infra_code"] + "_" + component_details["type_code"]
        )

        if failure_state == "None":
            recovery_time = 0
        else:
            mean_days = self.recovery_curves[component_prefix][failure_state][
                "recov_mean"
            ]
            std_days = self.recovery_curves[component_prefix][failure_state][
                "recov_sigma"
            ]
            recovery_time = round(
                min(
                    100 * 24,
                    max(
                        0,
                        min(
                            np.random.normal(mean_days, std_days) * 24,
                            (mean_days + 2 * std_days) * 24,
                        ),
                    ),
                )
            )

        return recovery_time

    def get_affected_components(self):
        """Returns the disrupted infrastructure components.

        :return: The disrupted infrastructure components along with their disruption states probabilities.
        :rtype: pandas.DataFrame object
        """
        return self.fail_probs_df

    @staticmethod
    def get_imt_at_point(coords, imt_type, gmf_gpd):
        """Returns the intensity measure (PGA, PGV, or PGD) at a point if corresponding fragility curves are available.

        :param coords: The coordinates of the point (latitude, longitude) in UTM
        :type coords: list
        :param imt_type: The intensity measure type (PGA, PGV, PGD)
        :type imt_type: str
        :param gmf_gpd: The ground motion field data
        :type gmf_gpd: geopandas.GeoDataFrame
        :return: The intensity measure at the point
        :rtype: float
        """
        node_point = Point(coords)
        node_buffer = node_point.buffer(5000)
        intersects = gmf_gpd.intersects(node_buffer)
        gmf_point = gmf_gpd[intersects]

        xs = np.array(gmf_point.geometry.x)
        ys = np.array(gmf_point.geometry.y)

        points = [[x, y] for x, y in zip(xs, ys)]
        values = np.array(gmf_point[imt_type])
        xi = [coords[0], coords[1]]
        result = griddata(points, values, xi, method="cubic")
        return result.item()

    @staticmethod
    def get_imt_at_line(start_coords, end_coords, imt_type, gmf_gpd):
        """Returns the maximum intensity measure (PGA, PGV, or PGD) along a line if corresponding fragility curves are available.

        :param start_coords: The coordinates of the start point (latitude, longitude) in UTM
        :type start_coords: list
        :param end_coords: The coordinates of the end point (latitude, longitude) in UTM
        :type end_coords: list
        :param imt_type: The intensity measure type (PGA, PGV, PGD)
        :type imt_type: str
        :param gmf_gpd: The ground motion field data
        :type gmf_gpd: geopandas.GeoDataFrame
        :return: The maximum intensity measure along the line
        :rtype: float
        """
        link_string = LineString([start_coords, end_coords])
        num_points = max(2, int(np.ceil(link_string.length / 1000)))
        points = [
            link_string.interpolate(i / float(num_points - 1), normalized=True)
            for i in range(num_points)
        ]
        imt_values = np.array([])
        for point in points:
            imt_values = np.append(
                imt_values,
                FragilityBasedDisruption.get_imt_at_point(
                    point.coords[0], imt_type, gmf_gpd
                ),
            )
        mean = imt_values[~np.isnan(imt_values)].mean()
        return mean

    @staticmethod
    def calculate_state_probability(imt, median, beta):
        """Calculates the damage state cumulative probability from the fragility functions.

        :param imt: The intensity measure used in the fragility curves.
        :type imt: string
        :param median: The median parameter of the fragility curve corresponding to the damage state.
        :type median: float
        :param beta: The beta parameter of the fragility curve corresponding to the damage state.
        :type beta: float
        :return: The cumulative probability distribution value corresponding to the damage state.
        :rtype: float
        """
        val = np.log(imt / median) / beta
        return norm.cdf(val)

    def ascertain_damage_probabilities(
        self, component, imt_type, imt_value, plotting=True
    ):
        """Ascertains the damage of a component type

        :param component: The component type
        :type component: str
        :param imt_value: The intensity measure value
        :type imt_value: float
        """
        compon_type = "".join([i for i in component if not i.isdigit()])
        if compon_type in self.fragility_curves.keys():
            state_cdf = []
            for state in self.fragility_curves[compon_type].keys():
                imt = self.fragility_curves[compon_type][state]["imt"]
                if imt == imt_type:
                    median = self.fragility_curves[compon_type][state]["ds_median"]
                    beta = self.fragility_curves[compon_type][state]["ds_beta"]
                    state_cdf.append(
                        self.calculate_state_probability(imt_value, median, beta)
                    )
                else:
                    print(
                        "The available fragility curves are not applicable for the component type"
                    )
            if len(state_cdf) == len(self.fragility_curves[compon_type].keys()):
                state_probabilities = [
                    state_cdf[i] - state_cdf[i + 1] for i in range(len(state_cdf) - 1)
                ] + [state_cdf[-1]]

            if plotting:
                self.plot_state_probabilities(
                    imt_type, imt_value, compon_type, state_cdf
                )
        else:
            state_probabilities = None

        return state_probabilities

    def ascertain_pipe_damage_probabilities(
        self, wn, pipe, gmf_gpd, method=1, plotting=True
    ):
        pipe_obj = wn.get_link(pipe)
        start_coords = pipe_obj.start_node.coordinates
        end_coords = pipe_obj.end_node.coordinates
        pgv_value = self.get_imt_at_line(start_coords, end_coords, "PGV", gmf_gpd)

        if method == 1 or method == 2:
            corr_factor = (
                0.5 * 1.2
                if self.resilience_level == "low"
                else 0.5 * 1
                if self.resilience_level == "moderate"
                else 0.5 * 0.3
            )  # Asbetos cements vs PVC vs Ductile iron
        elif method == "hazus":
            corr_factor = 1 if self.resilience_level == "low" else 0.3

        if method == 1:
            # linear model
            pgv_value = (pgv_value) / 2.54  # in/s
            repair_rate = corr_factor * 0.00187 * pgv_value
            repair_rate = repair_rate * (3.28 / 1000)  # convert 1/1000ft to 1/m
        elif method == 2:
            # Power model
            pgv_value = (pgv_value) / 2.54  # in/s
            repair_rate = corr_factor * 0.00108 * np.power(pgv_value, 1.173)
            repair_rate = repair_rate * (3.28 / 1000)  # convert 1/1000ft to 1/m
        elif method == "hazus":
            repair_rate = corr_factor * 0.0001 * np.power(pgv_value, 2.25) / 1000
        else:
            print("invalid method")

        repair_count = repair_rate * pipe_obj.length

        state_probabilities = self.ascertain_damage_probabilities(
            component=pipe, imt_type="RR", imt_value=repair_count, plotting=plotting
        )
        # print(
        #     f"{pipe}: repair rate of {round(repair_rate, 5)} per meter for PGV of {round(pgv_value,5)} cm/s, repair count of {round(repair_count,5)}"
        # )

        return state_probabilities

    def plot_imt(self, gmf_gpd, imt_column):
        """Plots the fragility curves based on intensity measure type (PGA, PGV, or PGD) on the map.

        :param gmf_gpd: The ground motion field data
        :type gmf_gpd: geopandas.GeoDataFrame
        :param imt_column: The intensity measure type (PGA, PGV, PGD)
        :type imt_column: str
        """
        fig, ax = plt.subplots(figsize=(8, 8))
        gmf_gpd.plot(
            column=imt_column,
            cmap="rainbow",
            marker="s",
            markersize=180,
            legend=True,
            vmin=0,
            ax=ax,
            alpha=0.9,
            legend_kwds={
                "shrink": 0.8,
                "label": imt_column,
                "orientation": "horizontal",
                "aspect": 20,
            },
        )

        ctx.add_basemap(ax, source=ctx.providers.Stamen.Terrain)
        ax.set_title(
            f"{imt_column} map for a 1-in-2475-year seismic event", fontsize=16
        )
        ax.set_axis_off()

    def plot_state_probabilities(self, imt_type, imt_value, compon_type, state_cdf):
        """Plots the probabilities of a component being in different damage states for a given intensity measure value

        :param imt_type: The intensity measure type (PGA, PGV, PGD)
        :type imt_type: str
        :param imt_value: The intensity measure value
        :type imt_value: float
        :param compon_type: The component type
        :type compon_type: str
        :param state_cdf: The cumulative probabilities of the component being in different damage states
        :type state_cdf: list
        """
        imt_list = np.linspace(0.001, imt_value * 2, 100)
        frag_df = pd.DataFrame(columns=["imt", "state", "fragility"])

        for state in self.fragility_curves[compon_type].keys():
            median = self.fragility_curves[compon_type][state]["ds_median"]
            stdev = self.fragility_curves[compon_type][state]["ds_beta"]
            for imt in imt_list:
                frag_df = frag_df.append(
                    {
                        "imt": imt,
                        "state": state,
                        "fragility": self.calculate_state_probability(
                            imt, median, stdev
                        ),
                    },
                    ignore_index=True,
                )
        sns.set_style("ticks")
        sns.set_context("paper", font_scale=1.5)

        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(x="imt", y="fragility", hue="state", data=frag_df)

        ax.hlines(
            y=state_cdf,
            xmin=0,
            xmax=imt_value,
            color="grey",
            linestyle="--",
        )
        ax.vlines(
            x=imt_value,
            ymin=0,
            ymax=max(state_cdf),
            color="grey",
            linestyle="--",
        )
        ax.set_ylabel("Damage state probability (cumulative)")
        ax.set_xlabel(f"{imt_type}")

        ax.set_xlim(0, imt_value * 2)
        ax.set_title("Fragility curves for " + compon_type, fontsize=16)
        ax.set_ylim(0, 1)

    def plot_disruptions(self, integrated_graph, map_extends):

        plots = {"water": None, "power": None, "transpo": None}

        for infra, _ in plots.items():
            plots[infra] = self.generate_bokeh_disruptions(
                integrated_graph, infra, map_extends
            )

        water_tab = Panel(child=plots["water"], title="Water")
        power_tab = Panel(child=plots["power"], title="Power")
        transpo_tab = Panel(child=plots["transpo"], title="Transport")
        tabs = Tabs(tabs=[water_tab, power_tab, transpo_tab])

        show(tabs)

    def generate_bokeh_disruptions(self, integrated_graph, infra, map_extends):
        palette = [
            RdYlGn[11][0],
            RdYlGn[11][2],
            RdYlGn[11][7],
            RdYlGn[11][9],
            RdYlGn[11][10],
        ]

        name = (
            "Water"
            if infra == "water"
            else "Power"
            if infra == "power"
            else "Transport"
        )
        p = figure(
            background_fill_color="white",
            plot_width=700,
            height=450,
            title=f"{self.name}: Disrupted {name} Components",
            x_range=(map_extends[0][0], map_extends[1][0]),
            y_range=(map_extends[0][1], map_extends[1][1]),
        )

        tile_provider = get_provider(Vendors.CARTODBPOSITRON)
        p.add_tile(tile_provider, alpha=0.8)

        # nodes
        n_x, n_y, n_type, n_cat, n_status, n_id = [], [], [], [], [], []

        for _, node in enumerate(integrated_graph.nodes.keys()):
            if integrated_graph.nodes[node]["node_type"] == infra:

                n_x.append(integrated_graph.nodes[node]["coord"][0])
                n_y.append(integrated_graph.nodes[node]["coord"][1])
                n_type.append(integrated_graph.nodes[node]["node_type"])
                n_cat.append(integrated_graph.nodes[node]["node_category"])
                n_status.append(integrated_graph.nodes[node]["failure_state"])
                n_id.append(node)

        # links
        l_x, l_y, l_type, l_cat, l_status, l_id = [], [], [], [], [], []
        for _, link in enumerate(integrated_graph.edges.keys()):
            if integrated_graph.edges[link]["link_type"] == infra:
                l_x.append(
                    [
                        integrated_graph.nodes[link[0]]["coord"][0],
                        integrated_graph.nodes[link[1]]["coord"][0],
                    ]
                )
                l_y.append(
                    [
                        integrated_graph.nodes[link[0]]["coord"][1],
                        integrated_graph.nodes[link[1]]["coord"][1],
                    ]
                )
                l_type.append(integrated_graph.edges[link]["link_type"])
                l_cat.append(integrated_graph.edges[link]["link_category"])
                l_status.append(integrated_graph.edges[link]["failure_state"])
                l_id.append(integrated_graph.edges[link]["id"])

        if infra in ["water", "power"]:
            plot_nodes = p.square(
                "x",
                "y",
                source=ColumnDataSource(
                    dict(
                        x=n_x,
                        y=n_y,
                        node_type=n_type,
                        node_category=n_cat,
                        fail_status=n_status,
                        id=n_id,
                    )
                ),
                color=factor_cmap(
                    "fail_status",
                    palette,
                    np.array(["None", "Slight", "Moderate", "Extensive", "Complete"]),
                ),
                alpha=0.7,
                size=5,
            )
            # hover tools
            node_hover = HoverTool(renderers=[plot_nodes])
            node_hover.tooltips = [
                ("Node ID", "@id"),
                ("Infrastructure", "@node_type"),
                ("Node category", "@node_category"),
                ("Affected", "@fail_status"),
            ]
            p.add_tools(node_hover)

        plot_links = p.multi_line(
            "x",
            "y",
            source=ColumnDataSource(
                dict(
                    x=l_x,
                    y=l_y,
                    link_layer=l_type,
                    link_category=l_cat,
                    fail_status=l_status,
                    id=l_id,
                )
            ),
            color=factor_cmap(
                "fail_status",
                palette,
                np.array(["None", "Slight", "Moderate", "Extensive", "Complete"]),
            ),
            line_alpha=1,
            line_width=2,
            legend_field="fail_status",
        )

        link_hover = HoverTool(renderers=[plot_links])
        link_hover.tooltips = [
            ("Link ID", "@id"),
            ("Infrastructure", "@link_layer"),
            ("Link category", "@link_category"),
            ("Affected", "@fail_status"),
        ]
        p.add_tools(link_hover)

        p.legend.location = "top_left"
        p.legend.title = "Failure state"
        p.legend.title_text_font_size = "12pt"
        p.legend.label_text_font_size = "10pt"
        p.axis.visible = False
        return p

    def plot_failure_distributions(self):
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.set_context("paper", font_scale=1.5)
        sns.set_style("ticks")
        g = sns.histplot(
            data=self.fail_probs_df,
            x="infra",
            hue="disruption_state",
            stat="count",
            multiple="dodge",
            shrink=0.8,
            common_norm=False,
            hue_order=["None", "Slight", "Moderate", "Extensive", "Complete"],
            ax=ax,
        )
        ax.set_xlabel("Infrastructure")
        ax.set_ylabel("Number of components")

    def generate_disruption_file(
        self, location=None, folder_extra=None, minimum_data=0, maximum_data=None
    ):
        """Generates the disruption file consisting of the list of failed components, time of occurrence, and failure percentage (damage extent).

        :param location: The location of the file to be saved.
        :type location: string
        """
        flag = 0
        self.disrupt_file = pd.DataFrame(
            columns=["time_stamp", "components", "fail_perc", "recovery_time"]
        )

        fail_prob_df = self.fail_probs_df[
            (self.fail_probs_df["recovery_time"] > 0)
            & (self.fail_probs_df["damage_perc"] > 0)
        ]

        self.disrupt_file["components"] = fail_prob_df["component"].tolist()
        self.disrupt_file["fail_perc"] = fail_prob_df["damage_perc"].tolist()
        self.disrupt_file["time_stamp"] = fail_prob_df["disruption_time"].tolist()
        self.disrupt_file["recovery_time"] = fail_prob_df["recovery_time"].tolist()

        if location is not None:

            if maximum_data is not None:
                if self.disrupt_file.shape[0] > maximum_data:
                    self.disrupt_file = self.disrupt_file.iloc[:maximum_data, :]

            if len(self.disrupt_file) > minimum_data:
                flag = 1
                # test_counter = len(os.listdir(location))

                if folder_extra is not None:
                    disruption_folder = f"{location}/{folder_extra}"
                else:
                    disruption_folder = f"{location}"

                print(disruption_folder)
                if not os.path.exists(disruption_folder):
                    os.makedirs(disruption_folder)
                self.disrupt_file.to_csv(
                    f"{disruption_folder}/disruption_file.dat",
                    index=False,
                    sep=",",
                )
                print(
                    f"Successfully saved the disruption file (with {self.disrupt_file.shape[0]} disruptions) to {disruption_folder}/"
                )
                scenario_path = Path(f"{disruption_folder}/")
                return scenario_path
        else:
            print("Target location for saving the file not provided.")
            return flag
