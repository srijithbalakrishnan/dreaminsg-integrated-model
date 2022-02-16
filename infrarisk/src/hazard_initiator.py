import os
import random
import numpy as np
import pandas as pd
from scipy import interpolate

from bokeh.plotting import figure
from bokeh.transform import factor_cmap
from bokeh.palettes import RdYlGn
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.tile_providers import get_provider, Vendors

import infrarisk.src.network_sim_models.interdependencies as interdependencies

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

from pathlib import Path


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
        self, location=None, folder_extra=None, minimum_data=0
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

            if self.disrupt_file.shape[0] > 30:
                self.disrupt_file = self.disrupt_file.iloc[:30, :]
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


class TrackDisruption:
    """Class of flood disaster where the probability of failure of components reduces with the longitudinal distance from the track of the event."""

    def __init__(
        self,
        hazard_tracks=None,
        buffer_of_impact=25,
        time_of_occurrence=6000,
        intensity="high",
        name="Track disruption",
    ):
        """Initiates the TrackDisruption object.

        :param hazard_tracks: The hazard tracks in shapely LineString object, defaults to None
        :type hazard_tracks: geopandas dataframe, optional
        :param buffer_of_impact: The buffer distance of impact measured from the centerline of the track, defaults to 25
        :type buffer_of_impact: integer/float, optional
        :param time_of_occurrence: The time of occurrence of the event in seconds, defaults to 6000
        :type time_of_occurrence: int, optional
        :param intensity: The intensity of the hazard using which the failure probability will be set. The intensity can be "extreme", "high", "moderate" or "low", defaults to "high"
        :type intensity: string, optional
        :param name: The name of the event, defaults to "Track disruption"
        :type name: string, optional
        """
        self.name = name
        self.intensity = intensity
        self.hazard_tracks = []
        self.set_fail_compon_dict()
        self.set_intensity_failure_probability()
        self.disrupt_file = pd.DataFrame()

        if hazard_tracks is None:
            # print(
            #     "No hazards tracks are provided. User must be manually set the tracks."
            # )
            pass
        else:
            self.set_hazard_tracks_from_shapefile(hazard_tracks)
            # print(f"The hazard tracks are set.")

        self.set_buffer_of_impact(buffer_of_impact)
        # print(
        #     f"The buffer distance of impact of {self.name} is set to {buffer_of_impact}"
        # )

        self.set_time_of_occurrence(time_of_occurrence)
        # print(f"The time of the {self.name} is set to {time_of_occurrence}s.")

    def set_fail_compon_dict(self):
        """Sets the dictionary of components that could be failed due to a radial disaster."""
        self.fail_compon_dict = {
            "power": {"L"},
            "water": {"R", "PMA"},
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
            self.failure_probability = 0.6
        elif self.intensity == "moderate":
            self.failure_probability = 0.3
        elif self.intensity == "low":
            self.failure_probability = 0.1
        elif self.intensity == "random":
            self.failure_probability = 0.7 * random.random()

    def set_hazard_tracks_from_shapefile(self, hazard_tracks):
        """Sets the tracks of the track-based hazard from a shapefile.

        :param hazard_tracks: A shapefile that has tracks of the event as LineString objects.
        :type hazard_tracks: shapefile
        """
        for _, linestring in enumerate(hazard_tracks.geometry):
            if linestring.geom_type == "LineString":
                self.hazard_tracks.append(linestring)
            # else:
            #     print("The entry is not a LineString object and hence ignored.")

    def set_hazard_tracks_from_linestring(self, linestring_track):
        """Sets a hazard track from a LineString object.

        :param linestring_track: A shapely LineString object denoting the track of the hazard.
        :type linestring_track: LineString object
        """
        if linestring_track.geom_type == "LineString":
            self.hazard_tracks.append(linestring_track)
        # else:
        #     print("The entry is not a LineString object and hence ignored.")

    def generate_random_track(self, loc_extents, shape="spline"):
        """Generates a random track using a spline connecting three points on the map.
        :param loc_extents: The [(xmin, ymin), (xmax, ymax)] coordinates from the map denoting the occurrence of the event.
        :type loc_extents: list of tutples
        :param shape: The method of generating the track. If "line", generates a straight line, if "spline", generates a smooth curve.
        :type shape: string
        :return: The disaster track.
        :rtype: shapely LineString object
        """
        (minx, miny), (maxx, maxy) = loc_extents

        sides = {
            1: LineString([(minx, miny), (maxx, miny)]),
            2: LineString([(maxx, miny), (maxx, maxy)]),
            3: LineString([(minx, maxy), (maxx, maxy)]),
            4: LineString([(minx, maxy), (minx, miny)]),
        }

        sides_list = list(sides.keys())
        start_side = random.choice(sides_list)
        sides_list.remove(start_side)
        end_side = random.choice(sides_list)

        start_point = sides[start_side].interpolate(random.random(), True)
        end_point = sides[end_side].interpolate(random.random(), True)
        if shape == "line":
            hazard_track = LineString([start_point, end_point])
        elif shape == "spline":
            midx = sides[1].interpolate(random.random(), True).x
            midy = sides[4].interpolate(random.random(), True).y

            xs = [start_point.x, midx, end_point.x]
            ys = [start_point.y, midy, end_point.y]

            tck, _ = interpolate.splprep([xs, ys], k=2)
            xnew, ynew = interpolate.splev(np.linspace(0, 1, 10), tck, der=0)

            spline_xys = []
            for x, y in zip(xnew, ynew):
                spline_xys.append((x, y))

            hazard_track = LineString(spline_xys)

        return hazard_track

    def set_buffer_of_impact(self, buffer_of_impact):
        """Sets the impact buffer distance in meters.

        :param buffer_of_impact: Impact buffer distance in meters.
        :type buffer_of_impact: interger or float
        """
        if (isinstance(buffer_of_impact, float)) or (isinstance(buffer_of_impact, int)):
            self.buffer_of_impact = buffer_of_impact
        # else:
        #     print(
        #         "Value of buffer distance of impact was not set. The value needs to be an integer in seconds and multiple of 60 (integer)."
        #     )

    def set_time_of_occurrence(self, time_of_occurrence):
        """Sets the time of occurrence of the disruptive event.

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
        # nodes
        affected_nodes = {
            "water": [],
            "power": [],
            "transpo": [],
        }
        for _, track in enumerate(self.hazard_tracks):
            track_buffer = track.buffer(self.buffer_of_impact)

            for _, node in enumerate(G.nodes.keys()):
                point = Point(G.nodes[node]["coord"])
                node_fail_status = self.assign_node_failure(track, point)
                if node_fail_status is True:
                    if (point.intersects(track_buffer)) or (point.within(track_buffer)):
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

        # links
        affected_links = {
            "water": [],
            "power": [],
            "transpo": [],
        }
        for _, track in enumerate(self.hazard_tracks):
            track_buffer = track.buffer(self.buffer_of_impact)

            for _, link in enumerate(G.edges.keys()):
                start_node, end_node = link
                start_coords = G.nodes[start_node]["coord"]
                end_coords = G.nodes[end_node]["coord"]
                link_line = LineString([start_coords, end_coords])
                l = LineString([start_coords, end_coords])

                if (l.intersects(track_buffer)) or (l.within(track_buffer)):
                    link_fail_status = self.assign_link_failure(track, link_line)

                    if link_fail_status == True:
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

            # event area
            for _, track in enumerate(self.hazard_tracks):
                track_buffer = track.buffer(self.buffer_of_impact)

                x, y = [], []
                [
                    (
                        x.append(list(track_buffer.exterior.coords.xy[0])),
                        y.append(list(track_buffer.exterior.coords.xy[1])),
                    )
                ]

                p.patches(
                    "x",
                    "y",
                    source=ColumnDataSource(dict(x=x, y=y)),
                    fill_color="silver",
                    fill_alpha=1,
                    line_color="silver",
                    line_alpha=1,
                    legend_label="Affected area",
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

    def assign_node_failure(self, track, node_point):
        """Assigns node failure status.

        :param track: The track of the disruptive event.
        :type track: shapely LineString object
        :param node_point: The node for which the failure status is to be assigned.
        :type node_point: shapely Point object.
        :return: The failure status of the node.
        :rtype: bool
        """
        nearest_point = nearest_points(track, node_point)[0]

        if self.intensity == "complete":
            exposure_prob = 1
        else:
            exposure_prob = round(
                1 - node_point.distance(nearest_point) / self.buffer_of_impact, 2
            )

        fail_status = (
            True
            if random.random() <= exposure_prob * self.failure_probability
            else False
        )

        return fail_status

    def assign_link_failure(self, track, link_line):
        """Assigns the link failure status.

        :param track: The track of the disruptive event.
        :type track: shapely LineString object
        :param link_line: The link for which the failure status is to be assigned.
        :type link_line: shapely LineString object
        :return: The failure status of the link.
        :rtype: bool
        """
        link_point, track_point = nearest_points(link_line, track)
        if self.intensity == "complete":
            exposure_prob = 1
        else:
            exposure_prob = round(
                1 - link_point.distance(track_point) / self.buffer_of_impact, 2
            )
        fail_status = (
            True
            if random.random() <= exposure_prob * self.failure_probability
            else False
        )

        return fail_status

    def generate_disruption_file(
        self, location=None, folder_extra=None, minimum_data=0
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
            if self.disrupt_file.shape[0] > 30:
                self.disrupt_file = self.disrupt_file.iloc[:30, :]
            # check if the count of components is greater than minimum data to be included in each data point
            if len(self.disrupt_file) > minimum_data:
                flag = 1
                # test_counter = len(os.listdir(location))

                if folder_extra is not None:
                    disruption_folder = f"{location}/{folder_extra}"
                else:
                    disruption_folder = f"{location}"

                if not os.path.exists(disruption_folder):
                    os.makedirs(disruption_folder)
                self.disrupt_file.to_csv(
                    f"{disruption_folder}/disruption_file.csv",
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


class RandomDisruption:
    def __init__(
        self, compon_scope=None, failure_count=[1, 1, 1], name="Random disruption"
    ):
        self.name = name
        self.compon_scope = compon_scope
        self.water_fail_count = failure_count[0]
        self.power_fail_count = failure_count[1]
        self.transpo_fail_count = failure_count[2]
        self.set_fail_compon_dict()
        self.disrupt_file = pd.DataFrame()

    def set_fail_compon_dict(self):
        """Sets the dictionary of components that could be failed due to a radial disaster."""
        self.fail_compon_dict = {
            "power": {"L"},
            "water": {"R", "PMA"},
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
            node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "Power"
        ]
        power_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "Power"
        ]

        allowed_power_compons = [
            "P_" + compon_type for compon_type in self.fail_compon_dict["power"]
        ]

        power_final_list = [
            compon
            for compon in power_node_list + power_link_list
            if any(compon_type in compon for compon_type in allowed_power_compons)
        ]
        if self.compon_scope is not None:
            power_final_list = [
                compon for compon in power_final_list if compon in self.compon_ccope
            ]
        power_fail_list = random.sample(power_final_list, self.power_fail_count)

        self.affected_nodes["power"] = [
            compon for compon in power_fail_list if compon in power_node_list
        ]
        self.affected_links["power"] = [
            compon for compon in power_fail_list if compon in power_link_list
        ]

        # water
        water_node_list = [
            node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "Water"
        ]
        water_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "Water"
        ]

        allowed_water_compons = [
            "W_" + compon_type for compon_type in self.fail_compon_dict["water"]
        ]

        water_final_list = [
            compon
            for compon in water_node_list + water_link_list
            if any(compon_type in compon for compon_type in allowed_water_compons)
        ]
        if self.compon_scope is not None:
            water_final_list = [
                compon for compon in water_final_list if compon in self.compon_ccope
            ]
        water_fail_list = random.sample(water_final_list, self.water_fail_count)

        self.affected_nodes["water"] = [
            compon for compon in water_fail_list if compon in water_node_list
        ]
        self.affected_links["water"] = [
            compon for compon in water_fail_list if compon in water_link_list
        ]

        # transportation
        transpo_node_list = [
            node
            for node in G.nodes.keys()
            if G.nodes[node]["node_type"] == "Transportation"
        ]
        transpo_link_list = [
            G.edges[edge]["id"]
            for edge in G.edges.keys()
            if G.edges[edge]["link_type"] == "Transportation"
        ]

        allowed_transpo_compons = [
            "T_" + compon_type for compon_type in self.fail_compon_dict["transport"]
        ]

        transpo_final_list = [
            compon
            for compon in transpo_node_list + transpo_link_list
            if any(compon_type in compon for compon_type in allowed_transpo_compons)
        ]
        if self.compon_scope is not None:
            transpo_final_list = [
                compon for compon in transpo_final_list if compon in self.compon_ccope
            ]
        transpo_fail_list = random.sample(transpo_final_list, self.transpo_fail_count)

        self.affected_nodes["transpo"] = [
            compon for compon in transpo_fail_list if compon in transpo_node_list
        ]
        self.affected_links["transpo"] = [
            compon for compon in transpo_fail_list if compon in transpo_link_list
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
        self, location=None, folder_extra=None, minimum_data=0
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
            if self.disrupt_file.shape[0] > 30:
                self.disrupt_file = self.disrupt_file.iloc[:30, :]
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
