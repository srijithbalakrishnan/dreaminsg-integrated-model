# import contextily as ctx

import itertools
from operator import itemgetter

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandapower as pp

import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

import pandapower.plotting as pandaplot


class ShelbyPowerNetwork:
    """A class for Shelby County power network"""

    def __init__(self, name="Shelby power network"):
        self._name = name
        self.compon_id_dict = dict()

    def load_network(self, nodes, links):
        """Load network from pandas dataframes of nodes and links

        :param nodes: pandas dataframe of nodes
        :type nodes: pandas.DataFrame
        :param links: pandas dataframe of links
        :type links: pandas.DataFrame
        """
        self._nodes = nodes
        self._links = links

    def generate_empty_network(self):
        """Generate an empty pandapower network object

        :return: pandapower network object
        :rtype: pandapower network object
        """
        pn = pp.create_empty_network(
            name="shelby_network", f_hz=50.0, sn_mva=1, add_stdtypes=True
        )
        return pn

    def plot_networkx(self, plotting=True):
        """Plot the network as networkx graph object

        :param plotting: Generate plot, defaults to True
        :type plotting: bool, optional
        :return: networkx graph object
        :rtype: networkx.Graph
        """
        G = nx.from_pandas_edgelist(self._links, "from", "to")
        pos = {
            row["intPowerID"]: (row["X_UTM"], row["Y_UTM"])
            for _, row in self._nodes.iterrows()
        }

        for node in G.nodes.keys():
            G.nodes[node]["type"] = self._nodes[self._nodes["intPowerID"] == node][
                "type"
            ].values[0]
            G.nodes[node]["x"] = self._nodes[self._nodes["intPowerID"] == node][
                "X_UTM"
            ].values[0]
            G.nodes[node]["y"] = self._nodes[self._nodes["intPowerID"] == node][
                "Y_UTM"
            ].values[0]

        if plotting:
            nx.draw(
                G,
                pos,
                with_labels=True,
            )
        return G, pos

    def convert_latlon_to_coords(self):
        """Convert lat/lon coordinates to UTM coordinates"""
        for index, row in self._nodes.iterrows():
            x1, y1 = row["X_Lon"], row["Y_Lat"]

            transformer = Transformer.from_crs(
                crs_from="epsg:4326", crs_to="epsg:3857", always_xy=True
            )
            x2, y2 = transformer.transform(xx=x1, yy=y1)

            self._nodes.loc[index, "X_UTM"] = x2
            self._nodes.loc[index, "Y_UTM"] = y2

    def construct_nodes(self, pn):
        """Construct pandapower nodes from pandas dataframe of nodes

        :param pn: pandapower network object
        :type pn: pandapower network object
        """
        pn.loads_geodata = pd.DataFrame(columns=["x", "y"])
        pn.ext_grid_geodata = pd.DataFrame(columns=["x", "y"])
        self.buses = dict()
        self.ext_grids = dict()
        self.switches = dict()
        self.trafos = dict()

        for _, row in self._nodes.iterrows():
            x, y = row["X_UTM"], row["Y_UTM"]
            self.buses[f"bus{row.intPowerID}"] = pp.create_bus(
                pn, vn_kv=23, name=f"P_B{row.intPowerID}", geodata=(x, y), type="b"
            )

            if row["type"] == "External grid connection":
                self.buses[f"bus{row.intPowerID}G"] = pp.create_bus(
                    pn,
                    vn_kv=138,
                    name=f"P_B{row.intPowerID}G",
                    geodata=(x, y + 20),
                    type="b",
                )

                self.buses[f"bus{row.intPowerID}EG"] = pp.create_bus(
                    pn,
                    vn_kv=138,
                    name=f"P_B{row.intPowerID}EG",
                    geodata=(x, y + 40),
                    type="b",
                )

                self.ext_grids["ext_grid1"] = pp.create_ext_grid(
                    pn,
                    self.buses[f"bus{row.intPowerID}EG"],
                    name=f"P_EG{row.intPowerID}",
                    s_sc_max_mva=1000,
                    rx_max=0.1,
                    x0x_max=1.0,
                    r0x0_max=0.1,
                )
                pn.ext_grid_geodata = pn.ext_grid_geodata.append(
                    {"x": x, "y": y + 60}, ignore_index=True
                )
                self.compon_id_dict[f"P_EG{row.intPowerID}"] = row["intPowerID"]


                pp.create_transformer_from_parameters(
                    pn,
                    hv_bus=self.buses[f"bus{row.intPowerID}G"],
                    lv_bus=self.buses[f"bus{row.intPowerID}"],
                    sn_mva=row["flow"],
                    vn_hv_kv=138,
                    vn_lv_kv=23,
                    vk_percent=12,
                    vkr_percent=0.41,
                    pfe_kw=14,
                    i0_percent=0,
                    shift_degree=150,
                    tap_side="hv",
                    tap_neutral=0,
                    tap_min=-9,
                    tap_max=9,
                    tap_step_degree=0,
                    tap_step_percent=1.5,
                    tap_phase_shifter=False,
                    index=pp.get_free_id(pn.trafo) + 1,
                    name=f"P_TF{row.intPowerID}EG",
                )

                self.switches[f"switch{row.intPowerID}EG"] = pp.create_switch(
                    pn,
                    self.buses[f"bus{row.intPowerID}EG"],
                    self.buses[f"bus{row.intPowerID}G"],
                    et="b",
                    type="CB",
                    closed=True,
                    name=f"P_S{row.intPowerID}EG",
                )
            elif row["type"] == "Intersection":
                # self.buses[f"bus{row.intPowerID}"] = pp.create_bus(
                #     pn, vn_kv=138, name=f"P_B{row.intPowerID}", geodata=(x, y), type="b"
                # )
                pass
            elif row["type"] in ["Substation"]:
                # self.buses[f"bus{row.intPowerID}"] = pp.create_bus(
                #     pn, vn_kv=23, name=f"P_B{row.intPowerID}", geodata=(x, y), type="b"
                # )
                self.compon_id_dict[f"P_B{row.intPowerID}"] = row["intPowerID"]

                self.buses[f"bus{row.intPowerID}LO1"] = pp.create_bus(
                    pn,
                    vn_kv=0.12,
                    name=f"P_B{row.intPowerID}LO1",
                    geodata=(x, y - 20),
                    type="b",
                )
                self.buses[f"bus{row.intPowerID}LO2"] = pp.create_bus(
                    pn,
                    vn_kv=0.12,
                    name=f"P_B{row.intPowerID}LO2",
                    geodata=(x, y - 40),
                    type="b",
                )
                pp.create_load(
                    pn,
                    self.buses[f"bus{row.intPowerID}LO2"],
                    p_mw=-row["flow"],
                    q_mvar=-0.2 * row["flow"],
                    name=f"P_LO{row.intPowerID}",
                )
                pp.create_transformer_from_parameters(
                    pn,
                    hv_bus=self.buses[f"bus{row.intPowerID}"],
                    lv_bus=self.buses[f"bus{row.intPowerID}LO1"],
                    sn_mva=-1.2 * row["flow"],
                    vn_hv_kv=23,
                    vn_lv_kv=0.12,
                    vk_percent=10.1,
                    vkr_percent=0.266,
                    pfe_kw=0,
                    i0_percent=0.05,
                    shift_degree=150,
                    tap_side="hv",
                    tap_neutral=0,
                    tap_min=-2,
                    tap_max=2,
                    tap_step_degree=0,
                    tap_step_percent=2.5,
                    tap_phase_shifter=False,
                    index=pp.get_free_id(pn.trafo) + 1,
                    name=f"P_TF{row.intPowerID}LO",
                )
                self.switches[f"switch{row.intPowerID}L"] = pp.create_switch(
                    pn,
                    self.buses[f"bus{row.intPowerID}LO1"],
                    self.buses[f"bus{row.intPowerID}LO2"],
                    et="b",
                    type="CB",
                    closed=True,
                    name=f"P_S{row.intPowerID}LI",
                )
                pn.loads_geodata = pn.loads_geodata.append(
                    {"x": x, "y": y - 40}, ignore_index=True
                )

    def construct_links(self, pn):
        pp.create_std_type(
            pn,
            {
                "c_nf_per_km": 10,
                "r_ohm_per_km": 0.01,  # 0.642,
                "x_ohm_per_km": 0.02,
                "max_i_ka": 0.142,
                "type": "ol",
            },
            name="shelby_line",
        )

        shelby_line = "shelby_line"

        line_count_dict = {node: 0 for node in self._nodes.intPowerID.unique()}

        for _, row in self._links.iterrows():

            fromnode = int(row["from"])
            tonode = int(row["to"])
            count_from = line_count_dict[fromnode]
            count_to = line_count_dict[tonode]

            x1, y1 = self.get_buffer_point(fromnode, tonode, 20)
            x2, y2 = self.get_buffer_point(tonode, fromnode, 20)

            self.buses[f"bus{fromnode}L{count_from}"] = pp.create_bus(
                pn,
                vn_kv=23,
                name=f"P_B{fromnode}L{count_from}",
                geodata=(x1, y1),
                type="b",
            )
            self.buses[f"bus{tonode}L{count_to}"] = pp.create_bus(
                pn,
                vn_kv=23,
                name=f"P_B{tonode}L{count_to}",
                geodata=(x2, y2),
                type="b",
            )
            self.switches[f"switch{fromnode}-{tonode}"] = pp.create_switch(
                pn,
                self.buses[f"bus{fromnode}"],
                self.buses[f"bus{fromnode}L{count_from}"],
                et="b",
                type="CB",
                closed=True,
                name=f"P_S{fromnode}-{tonode}",
            )

            self.switches[f"switch{tonode}-{fromnode}"] = pp.create_switch(
                pn,
                self.buses[f"bus{tonode}"],
                self.buses[f"bus{tonode}L{count_to}"],
                et="b",
                type="CB",
                closed=True,
                name=f"P_S{tonode}-{fromnode}",
            )
            pp.create_line(
                pn,
                from_bus=self.buses[f"bus{fromnode}L{count_from}"],
                to_bus=self.buses[f"bus{tonode}L{count_to}"],
                length_km=row["length_km"],
                std_type=shelby_line,
                name=f"P_L{int(row['linknwid'])}",
            )
            self.compon_id_dict[f"P_L{int(row['linknwid'])}"] = row["linknwid"]

            line_count_dict[fromnode] += 1
            line_count_dict[tonode] += 1

    def construct_motors(self, pn):
        wp_mp_dict = {
            81: 26,
            82: 27,
            83: 10,
            84: 25,
            85: 36,
            86: 41,
            87: 37,
            88: 32,
            89: 16,
            90: 16,
            91: 16,
            92: 10,
            93: 10,
            94: 41,
        }

        pn.pumps_geodata = pd.DataFrame(columns=["x", "y"])
        pumps = dict()
        for wp, mp in wp_mp_dict.items():
            pp.create_motor(
                pn,
                self.buses[f"bus{mp}LO2"],
                pn_mech_mw=0.23,
                cos_phi=0.8,
                name=f"P_MP{wp}",
            )

    def get_coordinates(self, node_id):
        x, y = self._nodes.loc[
            self._nodes["intPowerID"] == node_id, ["X_UTM", "Y_UTM"]
        ].values[0]
        return x, y

    def get_type(self, node_id):
        type = self._nodes.loc[self._nodes["intPowerID"] == node_id, "type"].values[0]
        return type

    def get_buffer_point(self, node1_id, node2_id, buffer_m):
        x1, y1 = self.get_coordinates(node1_id)
        x2, y2 = self.get_coordinates(node2_id)

        p = Point(x1, y1)
        c = p.buffer(buffer_m).boundary
        l = LineString(((x1, y1), (x2, y2)))
        i = c.intersection(l)
        return i.x, i.y

    def plot_pandaplot(self, pn):
        options = {
            "bus_size": 0.25,
            "plot_loads": True,
            "library": "networkx",
            "bus_color": "red",
            "switch_color": "green",
            "trafo_color": "royalblue",
            "load_size": 0.5,
            "show_plot": True,
            "scale_size": True,
            "trafo_size": 0.35,
            "ext_grid_size": 0.5,
        }

        plt.figure(1, figsize=(50, 50))
        pandaplot.simple_plot(pn, **options)

    def run_diagnostic(self, pn):
        pp.diagnostic(pn)

    def run_simulation(self, pn):
        pp.runpp(pn)

    def write_json(self, pn, dir):
        pp.to_json(pn, f"{dir}/power.json")


class ShelbyTranspoNetwork:
    def __init__(self, name="Shelby transportation network"):
        self._name = name

    def load_network(self, road_shp, road_nodes, taz_shp):
        road_shp.crs = "epsg:4326"
        road_shp = road_shp.to_crs({"init": "epsg:3857"})

        self._roads = road_shp

        road_nodes.crs = "epsg:4326"
        road_nodes = road_nodes.to_crs("epsg:3857")

        road_nodes.node_id = "T_J" + road_nodes.roadnode_id.astype(str)
        road_nodes["X"] = round(road_nodes.centroid.x, 0)
        road_nodes["X"] = road_nodes["X"].astype(int)
        road_nodes["Y"] = round(road_nodes.centroid.y, 0)
        road_nodes["Y"] = road_nodes["Y"].astype(int)
        self._road_nodes = road_nodes

        # taz_shp["geometry"] = taz_shp["geometry"].to_crs(epsg=3857)
        taz_shp["id"] = taz_shp.index
        taz_shp = taz_shp[["id", "geometry"]]
        self._taz = taz_shp

        taz_centroids = taz_shp.copy()
        taz_centroids["geometry"] = taz_centroids["geometry"].centroid
        self._taz_centroids = taz_centroids

    def ckdnearest(self):
        A = np.concatenate(
            [np.array(geom.coords) for geom in self._taz_centroids.geometry.to_list()]
        )
        B = [np.array(geom.coords) for geom in self._road_nodes.geometry.to_list()]
        B_ix = tuple(
            itertools.chain.from_iterable(
                [itertools.repeat(i, x) for i, x in enumerate(list(map(len, B)))]
            )
        )
        B = np.concatenate(B)
        ckd_tree = cKDTree(B)
        _, idx = ckd_tree.query(A, k=1)
        idx = itemgetter(*idx)(B_ix)
        ids = []
        for index, id in enumerate(idx):
            ids.append(self._road_nodes["roadnode_id"][id])
        self._taz_centroids["road_node"] = ids

        self._taz_centroids["nearest_node"] = None
        for index, row in self._taz_centroids.iterrows():
            self._taz_centroids["nearest_node"][index] = nearest_points(
                self._road_nodes[
                    self._road_nodes["roadnode_id"] == row["road_node"]
                ].geometry.values[0],
                row.geometry,
            )[0]

    def build_taz_connectors(self):
        """Construct connectors from centroid of taz to nearest road node"""
        for _, row in self._taz_centroids.iterrows():
            self._roads = self._roads.append(
                {
                    "ROAD_CLASS": "Connector",
                    "geometry": LineString([row["geometry"], row["nearest_node"]]),
                },
                ignore_index=True,
            )

    def plot_transport(self, plot_taz_connectors=False):
        """Plot the transportation network

        :param plot_taz_connectors: plot taz connectors to main network, defaults to False
        :type plot_taz_connectors: boolean, optional
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        self._taz.plot(
            ax=ax, color="white", edgecolor="black", linewidth=0.5, alpha=0.1, aspect=1
        )
        if plot_taz_connectors:
            self.build_taz_connectors()
            self._taz_centroids.plot(
                ax=ax, color="red", alpha=0.2, markersize=10, marker="o", aspect=1
            )
        self._roads.plot(
            ax=ax,
            column="ROAD_CLASS",
            cmap="tab10",
            linewidth=1.5,
            aspect=1,
            legend=True,
        )
        self._road_nodes.plot(
            ax=ax, color="tab:red", markersize=1, alpha=0.2, aspect=1, legend=False
        )

        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
        fig.axes[0].axis("off")

        minx, miny, maxx, maxy = self._roads.geometry.total_bounds
        tol_x = 0.1 * (maxx - minx)
        tol_y = 0.1 * (maxy - miny)
        ax.set_xlim(minx - tol_x, maxx + tol_x)
        ax.set_ylim(miny - tol_y, maxy + tol_y)


class ShelbyWaterNetwork:
    """A class for Shelby water network"""

    def __init__(self, name="Shelby water network"):
        self._name = name

    def load_network(self, nodes, links):
        """Load network from pandas dataframes of nodes and links

        :param nodes: pandas dataframe of nodes
        :type nodes: pandas.DataFrame
        :param links: pandas dataframe of links
        :type links: pandas.DataFrame
        """
        self._nodes = nodes
        self._links = links

    def convert_latlon_to_coords(self):
        """Convert lat/lon coordinates to UTM coordinates"""
        for index, row in self._nodes.iterrows():
            x1, y1 = row["X_Lon"], row["Y_Lat"]

            transformer = Transformer.from_crs(
                crs_from="epsg:4326", crs_to="epsg:3857", always_xy=True
            )
            x2, y2 = transformer.transform(xx=x1, yy=y1)
            self._nodes.loc[index, "X_UTM"] = x2
            self._nodes.loc[index, "Y_UTM"] = y2
