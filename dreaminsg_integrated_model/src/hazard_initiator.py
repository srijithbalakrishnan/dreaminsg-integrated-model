from os import mkdir
import scipy.spatial as spatial
import numpy as np
import pandas as pd

from bokeh.plotting import figure
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
from bokeh.palettes import RdYlGn
from bokeh.tile_providers import get_provider, Vendors
import dreaminsg_integrated_model.src.network_sim_models.interdependencies as interdependencies

from shapely.geometry import LineString, Point

from pathlib import Path
import glob
import os

    

    
    
class RadialDisruption:
    """Class of disaster where the probability of failure of components reduces with distance from the point of occurrence of the event."""

    def __init__(
        self,
        name="Radial disruption",
        point_of_occurrence=None,
        radius_of_impact=100,
        time_of_occurrence=6000,
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
        """
        self.name = name

        if point_of_occurrence == None:
            self.point_of_occurrence = None
        else:
            self.set_point_of_occurrence(point_of_occurrence)
            print(f"The point of occurrence is set to {point_of_occurrence}.")

        self.set_radius_of_impact(radius_of_impact)
        print(f"The radius of impact is set to {radius_of_impact}.")

        self.set_time_of_occurrence(time_of_occurrence)
        print(f"The time of the disruptive event is set to {time_of_occurrence}.")
    
    def get_dict(self):
        self.fail_compon_dict = {
        "power": {
            "B",
            "LO",
            "LOA",
            "TF",
            "LS",
            "L",
            "SW"
        },
        "water":{
        "R",
        "P",
        "PSC",
        "PMA",
        "PV",
        "T"},
        "transport":{
        "L"}}
        return self.fail_compon_dict

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
        :type time_of_occurrence: integer
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence
        else:
            print(
                "Time of diruptive event was not set. Time of occurrence needs to be an integer in seconds and multiple of 60 (integer)."
            )

    def set_affected_components(self, G, plot_components=True):
        """Set the affected components (nodes and link)

        :param G: The infrastructure network as a networkx graph.
        :type G: Networkx object
        :param plot_components: plots affected components, defaults to True
        :type plot_components: bool, optional
        """

        x_po, y_po = self.point_of_occurrence
        p = Point(x_po, y_po)
        c = p.buffer(self.radius_of_impact)

        # affected nodes
        affected_nodes = {
            "water": [],
            "power": [],
            "transpo": [],
        }
        for _, node in enumerate(G.nodes.keys()):
            point = Point(G.nodes[node]["coord"])
            if (point.intersects(c)) or (point.within(c)):
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
                if node not in affected_nodes:
                    G.nodes[node]["fail_status"] = "Functional"

        print(
            f"There are {len(affected_nodes['water']) + len(affected_nodes['power']) + len(affected_nodes['transpo'])} affected infrastructure nodes."
        )

        # affected links

        # affected_links = []
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
                if (
                    G.edges[link]["id"] not in affected_links["power"]
                    and G.edges[link]["id"] not in affected_links["water"]
                    and G.edges[link]["id"] not in affected_links["transpo"]
                ):
                    G.edges[link]["fail_status"] = "Functional"

        print(
            f"There are {len(affected_links['water']) + len(affected_links['power']) + len(affected_links['transpo'])} affected infrastructure links."
        )

        self.affected_nodes = affected_nodes
        self.affected_links = affected_links

        # bokeh plot
        if plot_components == True:
            palette = [RdYlGn[11][9], RdYlGn[11][2]]

            p = figure(
                background_fill_color="white",
                plot_width=1000,
                height=700,
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
                    "fail_status", palette, np.unique(np.array(fail_status))
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
            show(p)

    def set_failure_probability(self, G):
        pass

    def generate_disruption_file(self, location=None):
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
        for _, infra in enumerate(self.affected_nodes.keys()):
            for _, node in enumerate(self.affected_nodes[infra]):
                disrupt_file = disrupt_file.append(
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
                disrupt_file = disrupt_file.append(
                    {
                        "time_stamp": self.time_of_occurrence,
                        "components": link,
                        "fail_perc": 50,
                    },
                    ignore_index=True,
                )
        if location is not None:
            test_counter = len(os.listdir(location))

            if not os.path.exists(f"{location}/test{test_counter}"):
                os.makedirs(f"{location}/test{test_counter}_{self.name}")
                
                                            
            #added by geeta

            fail_compon_dict=self.get_dict()
            indices=[]
            
            for index, row in disrupt_file.iterrows():             
                component_details=interdependencies.get_compon_details(row['components'])             
                if (component_details[1] in fail_compon_dict['power']):
                    indices.append(index)
                elif(component_details[1] in fail_compon_dict['water']):
                    indices.append(index)
                elif(component_details[1] in fail_compon_dict['transport']):
                    indices.append(index)
                #disrupt_file=disrupt_file[~disrupt_file['components'].str.contains('W_J|T_J',na=False)]
               
                
            disrupt_file=disrupt_file.loc[indices]
            disrupt_file.to_csv(
                Path(location) / f"test{test_counter}_{self.name}/disruption_file.csv",
                index=False,
                sep=",",
            )
            print(
                f"Successfully saved the disruption file to {location}/test{test_counter}_{self.name}/"
            )
        else:
            print("Target location for saving the file not provided.")


class TrackDisruption:
    """Class of flood disaster where the probability of failure of components reduces with the longitudinal distance from the track of the event."""

    def __init__(
        self,
        hazard_tracks=None,
        buffer_of_impact=25,
        time_of_occurrence=6000,
        name="Track disruption",
    ):
        self.name = name

        self.set_hazard_tracks(hazard_tracks)
        print(f"The hazard tracks are set.")

        self.set_buffer_of_impact(buffer_of_impact)
        print(f"The buffer distance of impact is set to {buffer_of_impact}")

        self.set_time_of_occurrence(time_of_occurrence)
        print(f"The time of the disruptive event is set to {time_of_occurrence}.")
    def get_dict(self):
        self.fail_compon_dict = {
        "power": {
            "B",
            "LO",
            "LOA",
            "TF",
            "LS",
            "L",
            "SW"
        },
        "water":{
        "R",
        "P",
        "PSC",
        "PMA",
        "PV",
        "T"},
        "transport":{
        "L"}}
        return self.fail_compon_dict

    def set_hazard_tracks(self, hazard_tracks):
        """Sets the tracks of the track-based hazard from a shapefile.

        :param hazard_tracks: A shapefile that has tracks of the event as LineString objects.
        :type hazard_tracks: shapefile
        """
        self.hazard_tracks = []
        for _, linestring in enumerate(hazard_tracks.geometry):
            if linestring.geom_type == "LineString":
                self.hazard_tracks.append(linestring)
            else:
                print("The entry is not a LineString object and hence ignored.")

    def set_buffer_of_impact(self, buffer_of_impact):
        """Sets the impact buffer distance in meters.

        :param buffer_of_impact: Impact buffer distance in meters.
        :type buffer_of_impact: interger or float
        """
        if (isinstance(buffer_of_impact, float)) or (isinstance(buffer_of_impact, int)):
            self.buffer_of_impact = buffer_of_impact
        else:
            print(
                "Value of buffer distance of impact was not set. The value needs to be an integer in seconds and multiple of 60 (integer)."
            )

    def set_time_of_occurrence(self, time_of_occurrence):
        """Sets the time of occurrence of the disruptive event.

        :param time_of_occurrence: Time in seconds and multiple of 60.
        :type time_of_occurrence: integer
        """
        if isinstance(time_of_occurrence, int):
            self.time_of_occurrence = time_of_occurrence
        else:
            print(
                "Time of diruptive event was not set. Time of occurrence needs to be an integer in seconds and multiple of 60 (integer)."
            )

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
                    if node not in affected_nodes:
                        G.nodes[node]["fail_status"] = "Functional"

        print(
            f"There are {len(affected_nodes['water']) + len(affected_nodes['power']) + len(affected_nodes['transpo'])} affected infrastructure nodes."
        )

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

                l = LineString([start_coords, end_coords])

                if (l.intersects(track_buffer)) or (l.within(track_buffer)):
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
                    if (
                        G.edges[link]["id"] not in affected_links["power"]
                        and G.edges[link]["id"] not in affected_links["water"]
                        and G.edges[link]["id"] not in affected_links["transpo"]
                    ):
                        G.edges[link]["fail_status"] = "Functional"

        print(
            f"There are {len(affected_links['water']) + len(affected_links['power']) + len(affected_links['transpo'])} affected infrastructure links."
        )

        self.affected_nodes = affected_nodes
        self.affected_links = affected_links

        # bokeh plot
        if plot_components == True:
            palette = [RdYlGn[11][9], RdYlGn[11][2]]

            p = figure(
                background_fill_color="white",
                plot_width=1000,
                height=700,
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
                    "fail_status", palette, np.unique(np.array(fail_status))
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
                    "fail_status", palette, np.unique(np.array(fail_status))
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

    def generate_disruption_file(self, location=None):
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
        for _, infra in enumerate(self.affected_nodes.keys()):
            for _, node in enumerate(self.affected_nodes[infra]):
                disrupt_file = disrupt_file.append(
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
                disrupt_file = disrupt_file.append(
                    {
                        "time_stamp": self.time_of_occurrence,
                        "components": link,
                        "fail_perc": 50,
                    },
                    ignore_index=True,
                )
        if location is not None:
            test_counter = len(os.listdir(location))

            if not os.path.exists(f"{location}/test{test_counter}"):
                os.makedirs(f"{location}/test{test_counter}_{self.name}")
                
            #added by geeta

            fail_compon_dict=self.get_dict()
            indices=[]
            
            for index, row in disrupt_file.iterrows():             
                component_details=interdependencies.get_compon_details(row['components'])             
                if (component_details[1] in fail_compon_dict['power']):
                    indices.append(index)
                elif(component_details[1] in fail_compon_dict['water']):
                    indices.append(index)
                elif(component_details[1] in fail_compon_dict['transport']):
                    indices.append(index)
                #disrupt_file=disrupt_file[~disrupt_file['components'].str.contains('W_J|T_J',na=False)]
               
                
            disrupt_file=disrupt_file.loc[indices]

            disrupt_file.to_csv(
                Path(location) / f"test{test_counter}_{self.name}/disruption_file.csv",
                index=False,
                sep=",",
            )
            print(
                f"Successfully saved the disruption file to {location}/test{test_counter}_{self.name}/"
            )
        else:
            print("Target location for saving the file not provided.")


class RandomDisruption:
    def __init__(self, failure_counts=[2, 2], infra_type="Water"):
        pass
