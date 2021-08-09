import scipy.spatial as spatial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from bokeh.io import show, output_notebook, curdoc
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import *

import networkx as nx
from shapely.geometry import LineString
from shapely.geometry import Point

from pathlib import Path

# from networkx.algorithms.distance_measures import radius


class RadialDisruption:
    """Class of disaster where the probability of failure of components reduces with distance from the point of occurrence"""

    def __init__(
        self, point_of_occurrence=None, radius_of_impact=None, time_of_occurrence=6000
    ):
        """Initiates a RadialDisruption object.

        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float, optional
        """
        if point_of_occurrence == None:
            self.point_of_occurrence = None
        else:
            self.set_point_of_occurrence(point_of_occurrence)
            print(f"The point of occurrence is set to {point_of_occurrence}.")

        if radius_of_impact == None:
            self.radius_of_impact = None
        else:
            self.set_radius_of_impact(radius_of_impact)
            print(f"The radius of impact is set to {radius_of_impact}.")

        self.set_time_of_occurrence(time_of_occurrence)
        print(f"The time of the disruptive event is set to {time_of_occurrence}.")

    def set_point_of_occurrence(self, point_of_occurrence):
        """Sets the point of occurrence of the radial disruption.

        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        """
        if isinstance(point_of_occurrence, tuple):
            self.point_of_occurrence = point_of_occurrence
        else:
            print(
                "Point of occurrence was not set. Point of occurrence needs to be a tuple."
            )

    def set_radius_of_impact(self, radius_of_impact):
        """Sets the radius of the radial disruption.

        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float or integer, optional
        """
        if (isinstance(radius_of_impact, float)) or (isinstance(radius_of_impact, int)):
            self.radius_of_impact = radius_of_impact
        else:
            print(
                "Radius of impact was not set. Radius of impact needs to be a float or integer."
            )

    def set_time_of_occurrence(self, time_of_occurrence):
        """Stes the time of occurrence of the disruptive event.

        :param time_of_occurrence: Time in seconds and multiple of 60.
        :type time_of_occurrence: integers
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence
        else:
            print(
                "Time of diruptive event wasnot set. Time of occurrence needs to be an integer in seconds and multiple of 60 (integer)."
            )

    def set_affected_components(self, G, plot_components=True):
        """Set the affected components (nodes and link)

        :param G: The infrastructure network as a networkx graph.
        :type G: Networkx object
        :param plot_components: plots affected components, defaults to True
        :type plot_components: bool, optional
        """

        # affected nodes
        points = np.array([list(G.nodes[node]["coord"]) for node in G.nodes.keys()])

        point_tree = spatial.cKDTree(points)

        node_indexes = point_tree.query_ball_point(
            list(self.point_of_occurrence), self.radius_of_impact
        )

        affected_nodes = [list(G.nodes.keys())[index] for index in node_indexes]
        print(f"There are {len(affected_nodes)} affected infrastructure nodes.")

        for node in G.nodes.keys():
            G.nodes[node]["fail_status"] = (
                "Disrupted" if node in affected_nodes else "Functional"
            )

        # affected links
        x_po, y_po = self.point_of_occurrence
        p = Point(x_po, y_po)
        c = p.buffer(self.radius_of_impact)

        affected_links = []
        for link in G.edges.keys():
            start_node, end_node = link
            start_coords = G.nodes[start_node]["coord"]
            end_coords = G.nodes[end_node]["coord"]

            l = LineString([start_coords, end_coords])

            if c.intersection(l).is_empty == False or l.within(c):
                G.edges[link]["fail_status"] = "Disrupted"
                affected_links.append(G.edges[link]["id"])
            else:
                G.edges[link]["fail_status"] = "Functional"

        print(f"There are {len(affected_links)} affected infrastructure links.")

        self.affected_nodes = affected_nodes
        self.affected_links = affected_links

        # bokeh plot
        palette = [RdYlGn[11][9], RdYlGn[11][2]]

        p = figure(
            background_fill_color="white",
            plot_width=700,
            height=400,
            title="Disrupted components",
            x_range=(1000, 8000),
            y_range=(1000, 6600),
        )

        # event area
        plot_explosion_area = p.circle(
            x=self.point_of_occurrence[0],
            y=self.point_of_occurrence[1],
            radius=self.radius_of_impact,
            color="red",
            alpha=0.3,
        )
        plot_explosion_point = p.scatter(
            x=self.point_of_occurrence[0],
            y=self.point_of_occurrence[1],
            # radius=self.radius_of_impact,
            marker="cross",
            color="black",
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
            color=factor_cmap("fail_status", palette, np.unique(np.array(fail_status))),
            alpha=1,
            muted_color=factor_cmap(
                "fail_status", palette, np.unique(np.array(fail_status))
            ),
            muted_alpha=0.2,
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
                "fail_status", palette, np.unique(np.array(fail_status))
            ),
            line_alpha=1,
            line_width=1.5,
            muted_color=factor_cmap(
                "fail_status", palette, np.unique(np.array(fail_status))
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
        p.legend.click_policy = "mute"
        show(p)

        # if plot_components == True:
        #     pos = {node: G.nodes[node]["coord"] for node in G.nodes.keys()}

        #     node_color = []
        #     for node in G.nodes.keys():
        #         if G.nodes[node]["fail_status"] == 1:
        #             node_color.append("tab:red")
        #         else:
        #             node_color.append("tab:green")

        #     link_color = []
        #     for link in G.edges.keys():
        #         if G.edges[link]["fail_status"] == 1:
        #             link_color.append("tab:red")
        #         else:
        #             link_color.append("tab:green")

        #     plt.figure(figsize=(10, 7))
        #     nx.draw(
        #         G,
        #         pos,
        #         node_size=1,
        #         node_color=node_color,
        #         edge_color=link_color,
        #     )

    def generate_disruption_file(self, location):
        """Generates the disruption file consisting of the list of failed components, time of occurrence, and failure percentage (damage extent).

        :param location: The location of the file to be saved.
        :type location: string
        """
        disrupt_file = pd.DataFrame(
            columns=[
                "time_stamp",
                "components",
                "fail_perc",
            ]
        )

        # add failed nodes
        for _, node in enumerate(self.affected_nodes):
            disrupt_file = disrupt_file.append(
                {
                    "time_stamp": self.time_of_occurrence,
                    "components": node,
                    "fail_perc": 50,
                },
                ignore_index=True,
            )

        # add failed links
        for _, link in enumerate(self.affected_links):
            disrupt_file = disrupt_file.append(
                {
                    "time_stamp": self.time_of_occurrence,
                    "components": link,
                    "fail_perc": 50,
                },
                ignore_index=True,
            )

        disrupt_file.to_csv(Path(location) / "disrupt_file.csv", index=False, sep=",")
        print(f"Successfully saved the disruption file to {location}")
