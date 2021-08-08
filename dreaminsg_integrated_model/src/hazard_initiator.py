import scipy.spatial as spatial
import numpy as np
import matplotlib.pyplot as plt

import networkx as nx
from shapely.geometry import LineString
from shapely.geometry import Point

# from networkx.algorithms.distance_measures import radius


class RadialDisruption:
    """Class of disaster where the probability of failure of components reduces with distance from the point of occurrence"""

    def __init__(self, point_of_occurrence=None, radius_of_impact=None):
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

    def get_affected_components(self, integrated_network, plot_components=True):

        G = integrated_network.integrated_graph

        # affected nodes
        points = np.array([list(G.nodes[node]["coord"]) for node in G.nodes.keys()])

        point_tree = spatial.cKDTree(points)

        node_indexes = point_tree.query_ball_point(
            list(self.point_of_occurrence), self.radius_of_impact
        )

        affected_nodes = [list(G.nodes.keys())[index] for index in node_indexes]
        print(f"There are {len(affected_nodes)} affected infrastructure nodes.")

        for node in G.nodes.keys():
            G.nodes[node]["fail_status"] = 1 if node in affected_nodes else 0

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
                G.edges[link]["fail_status"] = 1
                affected_links.append(G.edges[link]["id"])
            else:
                G.edges[link]["fail_status"] = 0

        print(f"There are {len(affected_links)} affected infrastructure links.")

        if plot_components == True:
            pos = {node: G.nodes[node]["coord"] for node in G.nodes.keys()}

            node_color = []
            for node in G.nodes.keys():
                if G.nodes[node]["fail_status"] == 1:
                    node_color.append("tab:red")
                else:
                    node_color.append("tab:green")

            link_color = []
            for link in G.edges.keys():
                if G.edges[link]["fail_status"] == 1:
                    link_color.append("tab:red")
                else:
                    link_color.append("tab:green")

            plt.figure(figsize=(10, 7))
            nx.draw(
                G,
                pos,
                node_size=1,
                node_color=node_color,
                edge_color=link_color,
            )

        return affected_nodes, affected_links
