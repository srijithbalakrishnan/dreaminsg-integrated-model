import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import RdYlGn
from bokeh.plotting import figure
from bokeh.tile_providers import Vendors, get_provider
from bokeh.transform import factor_cmap
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
import infrarisk.src.physical.interdependencies as interdependencies


class RadialDisruption:
    """Class of disaster where the probability of failure of components reduces with distance from the point of occurrence of the event."""

    def __init__(
        self,
        name="Radial disruption",
        point_of_occurrence=None,
        radius_of_impact=100,
        time_of_occurrence=6000,
        intensity="high",
    ):
        """Initiates a RadialDisruption object.

        :param name: name of the event, defaults to "Radial disruption"
        :type name: str, optional
        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float, optional
        :param time_of_occurrence: Time in seconds and multiple of 60, defaults to 6000.
        :type time_of_occurrence: integer
        :param intensity: The intensity of the hazard using which the failure probability will be set. The intensity can be "extreme", "high", "moderate" or "low", defaults to "high"
        :type intensity: string, optional
        """
        self.name = name
        self.intensity = intensity
        self.set_fail_compon_dict()
        self.disrupt_file = pd.DataFrame()
        self.set_intensity_failure_probability()

        if point_of_occurrence is None:
            self.point_of_occurrence = None
        else:
            self.set_point_of_occurrence(point_of_occurrence)
            # print(f"The point of occurrence is set to {point_of_occurrence}.")

        self.set_radius_of_impact(radius_of_impact)
        # print(f"The radius of impact is set to {radius_of_impact}.")

        self.set_time_of_occurrence(time_of_occurrence)
        # print(f"The time of the disruptive event is set to {time_of_occurrence}.")

    def set_fail_compon_dict(self):
        """Sets the dictionary of components that could be failed due to a radial disaster."""
        self.fail_compon_dict = {
            "power": {"L"},
            "water": {
                "PMA",
                "WP",
            },
            "transport": {"L"},
        }

    def get_fail_compon_dict(self):
        """Returns the dictionary of that could be failed due to a radial disaster.

        :return: dictionary of components that could be failed.
        :rtype: dictionary
        """
        return self.fail_compon_dict

    def set_intensity_failure_probability(self):
        """Sets the vulnerability (probability of failure) based on the intensity of the disaster event (currently arbitrary values are used)."""
        if self.intensity == "complete":
            self.failure_probability = 1
        elif self.intensity == "extreme":
            self.failure_probability = 0.8
        elif self.intensity == "high":
            self.failure_probability = 0.5
        elif self.intensity == "moderate":
            self.failure_probability = 0.3
        elif self.intensity == "low":
            self.failure_probability = 0.1
        elif self.intensity == "random":
            self.failure_probability = 0.7 * random.random()

    def set_point_of_occurrence(self, point_of_occurrence):
        """Sets the point of occurrence of the radial disruption.

        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        """
        if isinstance(point_of_occurrence, tuple):
            self.point_of_occurrence = point_of_occurrence
        # else:
        #     print(
        #         "Point of occurrence was not set. Point of occurrence needs to be a tuple."
        #     )

    def set_radius_of_impact(self, radius_of_impact):
        """Sets the radius of the radial disruption.

        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float or integer, optional
        """
        if (isinstance(radius_of_impact, float)) or (isinstance(radius_of_impact, int)):
            self.radius_of_impact = radius_of_impact
        # else:
        #     print(
        #         "Radius of impact was not set. Radius of impact needs to be a float or integer."
        #     )

    def set_time_of_occurrence(self, time_of_occurrence):
        """Stes the time of occurrence of the disruptive event.

        :param time_of_occurrence: Time in seconds and multiple of 60.
        :type time_of_occurrence: integer
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence
        # else:
        #     print(
        #         "Time of diruptive event was not set. Time of occurrence needs to be an integer in seconds and multiple of 60 (integer)."
        #     )

    def set_affected_components(self, G, plot_components=True):
        """Set the affected components (nodes and link)

        :param G: The infrastructure network as a networkx graph.
        :type G: Networkx object
        :param plot_components: plots affected components, defaults to True
        :type plot_components: bool, optional
        """

        x_po, y_po = self.point_of_occurrence
        p_occ = Point(x_po, y_po)
        c = p_occ.buffer(self.radius_of_impact)

        # affected nodes
        affected_nodes = {
            "water": [],
            "power": [],
            "transpo": [],
        }

        for _, node in enumerate(G.nodes.keys()):
            point = Point(G.nodes[node]["coord"])
            if (point.intersects(c)) or (point.within(c)):
                node_fail_status = self.assign_node_failure(p_occ, point)
                if node_fail_status is True:
                    G.nodes[node]["fail_status"] = "Disrupted"

                    if G.nodes[node]["node_type"] == "power_node":
                        if node not in affected_nodes["power"]:
                            affected_nodes["power"].append(node)
                    elif G.nodes[node]["node_type"] == "water_node":
                        if node not in affected_nodes["water"]:
                            affected_nodes["water"].append(node)
                    elif G.nodes[node]["node_type"] == "transpo_node":
                        if node not in affected_nodes["transpo"]:
                            affected_nodes["transpo"].append(node)
                else:
                    G.nodes[node]["fail_status"] = "Functional"
            else:
                if node not in affected_nodes:
                    G.nodes[node]["fail_status"] = "Functional"

        # print(
        #     f"There are {len(affected_nodes['water']) + len(affected_nodes['power']) + len(affected_nodes['transpo'])} affected infrastructure nodes."
        # )

        # affected links
        affected_links = {
            "water": [],
            "power": [],
            "transpo": [],
        }

        for link in G.edges.keys():
            start_node, end_node = link
            start_coords = G.nodes[start_node]["coord"]
            end_coords = G.nodes[end_node]["coord"]

            l = LineString([start_coords, end_coords])

            if c.intersection(l).is_empty == False or l.within(c):
                link_fail_status = self.assign_link_failure(
                    p_occ, start_coords, end_coords
                )

                if link_fail_status is True:
                    G.edges[link]["fail_status"] = "Disrupted"
                    if G.edges[link]["link_type"] == "Power":
                        if G.edges[link]["id"] not in affected_links["power"]:
                            affected_links["power"].append(G.edges[link]["id"])
                    elif G.edges[link]["link_type"] == "Water":
                        if G.edges[link]["id"] not in affected_links["water"]:
                            affected_links["water"].append(G.edges[link]["id"])
                    elif G.edges[link]["link_type"] == "Transportation":
                        if G.edges[link]["id"] not in affected_links["transpo"]:
                            affected_links["transpo"].append(G.edges[link]["id"])
                else:
                    G.edges[link]["fail_status"] = "Functional"
            else:
                if (
                    G.edges[link]["id"] not in affected_links["power"]
                    and G.edges[link]["id"] not in affected_links["water"]
                    and G.edges[link]["id"] not in affected_links["transpo"]
                ):
                    G.edges[link]["fail_status"] = "Functional"

        # print(
        #     f"There are {len(affected_links['water']) + len(affected_links['power']) + len(affected_links['transpo'])} affected infrastructure links."
        # )

        self.affected_nodes = affected_nodes
        self.affected_links = affected_links

        # bokeh plot
        if plot_components is True:
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

            # event area
            p.circle(
                x=self.point_of_occurrence[0],
                y=self.point_of_occurrence[1],
                radius=self.radius_of_impact,
                color="silver",
                alpha=1,
                legend_label="Affected area",
            )
            p.scatter(
                x=self.point_of_occurrence[0],
                y=self.point_of_occurrence[1],
                # radius=self.radius_of_impact,
                marker="plus",
                color="grey",
                alpha=1,
                size=10,
            )

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
                muted_color=factor_cmap(
                    "fail_status", palette, np.array(["Functional", "Disrupted"])
                ),
                muted_alpha=0.2,
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

    def assign_node_failure(self, p_occ, node_point):
        """Assigns node failure status.

        :param p_occ: The point of occurrence of the disruptive event.
        :type p_occ: shapely Point object
        :param node_point: The node for which the failure status is to be assigned.
        :type node_point: shapely Point object
        :return: The failure status of the node.
        :rtype: bool
        """
        if self.intensity == "complete":
            exposure_prob = 1
        else:
            exposure_prob = round(
                1 - p_occ.distance(node_point) / self.radius_of_impact, 2
            )

        fail_status = (
            True
            if random.random() <= exposure_prob * self.failure_probability
            else False
        )

        return fail_status

    def assign_link_failure(self, p_occ, start_coords, end_coords):
        """Assigns the link failure status.

        :param p_occ: The point of occurrence of the disruptive event.
        :type p_occ: shapely Point object
        :param start_coords: The coordinates of the start node of the link.
        :type start_coords: tuple
        :param end_coords: The coordinates of the end node of the link.
        :type end_coords: tuple
        :return: The failure status of the link
        :rtype: bool
        """
        link_line = LineString([start_coords, end_coords])
        nearest_point = nearest_points(link_line, p_occ)[0]

        if self.intensity == "complete":
            exposure_prob = 1
        else:
            exposure_prob = round(
                1 - p_occ.distance(nearest_point) / self.radius_of_impact, 2
            )
        fail_status = (
            True
            if random.random() <= exposure_prob * self.failure_probability
            else False
        )

        return fail_status

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
