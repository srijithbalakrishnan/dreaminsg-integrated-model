import os
from pathlib import Path

import infrarisk.src.physical.interdependencies as interdependencies
import numpy as np
import pandas as pd
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import RdYlGn
from bokeh.plotting import figure
from bokeh.tile_providers import Vendors, get_provider
from bokeh.transform import factor_cmap


class CustomDisruption:
    def __init__(
        self,
        affected_components,
        name="User defined disruptions",
        time_of_occurrence=6000,
    ):
        """Class of custom disruption. User can define the disruptions based on external vulnerability models.

        :param affected_components: The list of names of the affected components.
        :type affected_components: list
        :param name: The name of the disruption.
        :type name: string
        :param time_of_occurrence: The time of occurrence of the disruption.
        :type time_of_occurrence: integer
        """
        self.name = name
        self.set_time_of_occurrence(time_of_occurrence)
        self.affected_components = affected_components
        self.set_fail_compon_dict()
        self.disrupt_file = pd.DataFrame()

    def set_fail_compon_dict(self):
        """Sets the dictionary of components that could be failed due to a radial disaster."""
        self.fail_compon_dict = {
            "power": {"L"},
            "water": {"R", "PMA", "T"},
            "transport": {"L"},
        }

    def get_fail_compon_dict(self):
        """Returns the dictionary of that could be failed due to a radial disaster.

        :return: dictionary of components that could be failed.
        :rtype: dictionary
        """
        return self.fail_compon_dict

    def set_time_of_occurrence(self, time_of_occurrence):
        """Sets the time of occurrence of the disruptive event.

        :param time_of_occurrence: Time in seconds and multiple of 60.
        :type time_of_occurrence: integer
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence

    def set_affected_components(self, G, plot_components=True):
        self.affected_nodes = {"water": [], "power": [], "transpo": []}
        self.affected_links = {"water": [], "power": [], "transpo": []}

        # power
        power_node_list = [
            node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "power"
        ]
        power_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "power"
        ]

        self.affected_nodes["power"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["power"]
            if (compon.startswith("P_" + compon_type) and compon in power_node_list)
        ]
        self.affected_links["power"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["power"]
            if (compon.startswith("P_" + compon_type) and compon in power_link_list)
        ]

        # water
        water_node_list = [
            node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "water"
        ]
        water_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "water"
        ]

        self.affected_nodes["water"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["water"]
            if (compon.startswith("W_" + compon_type) and compon in water_node_list)
        ]
        self.affected_links["water"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["water"]
            if (compon.startswith("W_" + compon_type) and compon in water_link_list)
        ]

        # transportation
        transpo_node_list = [
            node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "transpo"
        ]
        transpo_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "transpo"
        ]

        self.affected_nodes["transpo"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["transport"]
            if (compon.startswith("T_" + compon_type) and compon in transpo_node_list)
        ]
        self.affected_links["transpo"] = [
            compon
            for compon in self.affected_components
            for compon_type in self.fail_compon_dict["transport"]
            if (compon.startswith("T_" + compon_type) and compon in transpo_link_list)
        ]

        for _, node in enumerate(G.nodes.keys()):
            if (
                node
                in self.affected_nodes["water"]
                + self.affected_nodes["power"]
                + self.affected_nodes["transpo"]
            ):
                G.nodes[node]["fail_status"] = "Disrupted"
            else:
                G.nodes[node]["fail_status"] = "Functional"

        for _, link in enumerate(G.edges.keys()):
            if (
                G.edges[link]["id"]
                in self.affected_links["power"]
                + self.affected_links["water"]
                + self.affected_links["transpo"]
            ):
                G.edges[link]["fail_status"] = "Disrupted"
            else:
                G.edges[link]["fail_status"] = "Functional"

        # bokeh plot
        if plot_components == True:
            palette = [RdYlGn[11][2], RdYlGn[11][9]]

            p = figure(
                background_fill_color="white",
                plot_width=700,
                height=450,
                title=f"{self.name}: Disrupted components",
                x_range=(1000, 8000),
                y_range=(1000, 6600),
            )

            # instatiate the tile source provider
            tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

            # add the back ground basemap
            p.add_tile(tile_provider, alpha=0.1)

            # nodes
            x, y, node_type, node_category, fail_status, id = [], [], [], [], [], []

            for _, node in enumerate(G.nodes.keys()):
                x.append(G.nodes[node]["coord"][0])
                y.append(G.nodes[node]["coord"][1])
                node_type.append(G.nodes[node]["node_type"])
                node_category.append(G.nodes[node]["node_category"])
                fail_status.append(G.nodes[node]["fail_status"])
                id.append(node)

            plot_nodes = p.square(
                "x",
                "y",
                source=ColumnDataSource(
                    dict(
                        x=x,
                        y=y,
                        node_type=node_type,
                        node_category=node_category,
                        fail_status=fail_status,
                        id=id,
                    )
                ),
                color=factor_cmap(
                    "fail_status", palette, np.array(["Functional", "Disrupted"])
                ),
                alpha=0.7,
                size=5,
            )

            # links
            x, y, link_layer, link_category, fail_status, id = [], [], [], [], [], []
            for _, link in enumerate(G.edges.keys()):
                x.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
                y.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
                link_layer.append(G.edges[link]["link_type"])
                link_category.append(G.edges[link]["link_category"])
                fail_status.append(G.edges[link]["fail_status"])
                id.append(G.edges[link]["id"])

            plot_links = p.multi_line(
                "x",
                "y",
                source=ColumnDataSource(
                    dict(
                        x=x,
                        y=y,
                        link_layer=link_layer,
                        link_category=link_category,
                        fail_status=fail_status,
                        id=id,
                    )
                ),
                line_color=factor_cmap(
                    "fail_status", palette, np.array(["Functional", "Disrupted"])
                ),
                line_alpha=1,
                line_width=1.5,
                legend_field="fail_status",
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

            link_hover = HoverTool(renderers=[plot_links])
            link_hover.tooltips = [
                ("Link ID", "@id"),
                ("Infrastructure", "@link_layer"),
                ("Link category", "@link_category"),
                ("Affected", "@fail_status"),
            ]
            p.add_tools(link_hover)

            p.legend.location = "top_left"
            show(p)

    def generate_disruption_file(
        self, location=None, folder_extra=None, minimum_data=0, maximum_data=None
    ):
        """Generates the disruption file consisting of the list of failed components, time of occurrence, and failure percentage (damage extent).

        :param location: The location of the file to be saved.
        :type location: string
        """
        flag = 0
        self.disrupt_file = pd.DataFrame(
            columns=[
                "time_stamp",
                "components",
                "fail_perc",
            ]
        )

        # add failed nodes
        for _, infra in enumerate(self.affected_nodes.keys()):
            for _, node in enumerate(self.affected_nodes[infra]):
                self.disrupt_file = self.disrupt_file.append(
                    {
                        "time_stamp": self.time_of_occurrence,
                        "components": node,
                        "fail_perc": 50,
                    },
                    ignore_index=True,
                )

        # add failed links
        for _, infra in enumerate(self.affected_links):
            for _, link in enumerate(self.affected_links[infra]):
                self.disrupt_file = self.disrupt_file.append(
                    {
                        "time_stamp": self.time_of_occurrence,
                        "components": link,
                        "fail_perc": 50,
                    },
                    ignore_index=True,
                )

        if location is not None:
            # added by geeta
            fail_compon_dict = self.get_fail_compon_dict()
            indices = []

            for index, row in self.disrupt_file.iterrows():
                component_details = interdependencies.get_compon_details(
                    row["components"]
                )

                if component_details[1] in fail_compon_dict["power"]:
                    indices.append(index)
                elif component_details[1] in fail_compon_dict["water"]:
                    indices.append(index)
                elif component_details[1] in fail_compon_dict["transport"]:
                    indices.append(index)

            self.disrupt_file = self.disrupt_file.loc[indices]
            if maximum_data is not None:
                if self.disrupt_file.shape[0] > maximum_data:
                    self.disrupt_file = self.disrupt_file.iloc[:maximum_data, :]
            # check if the count of components is greater than minimum data to be included in each data point
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
