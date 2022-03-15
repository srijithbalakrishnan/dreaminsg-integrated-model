from black import Line
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from pyproj import Proj, transform

import pandapower as pp

from shapely.geometry import LineString
from shapely.geometry import Point

import pandapower.plotting as pandaplot
import matplotlib.pyplot as plt


class ShelbyPowerNetwork:
    def _init_(self, name="Shelby power network"):
        self._name = name

    def load_network(self, nodes, links):
        self._nodes = nodes
        self._links = links

    def generate_empty_network(self):
        pn = pp.create_empty_network(
            name="shelby_network", f_hz=50.0, sn_mva=1, add_stdtypes=True
        )
        return pn

    def plot_network(self):
        G = nx.from_pandas_edgelist(self._links, "fromnode", "tonode")
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

        nx.draw(
            G,
            pos,
            with_labels=True,
        )

    def convert_latlon_to_coords(self):
        for index, row in self._nodes.iterrows():
            outProj = Proj(init="epsg:3857")
            inProj = Proj(init="epsg:4326")
            x1, y1 = row["X_Lon"], row["Y_Lat"]
            x2, y2 = transform(inProj, outProj, x1, y1)

            self._nodes.loc[index, "X_UTM"] = x2
            self._nodes.loc[index, "Y_UTM"] = y2

    def construct_nodes(self, pn):
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

            if row["type"] == "gate_stations":
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
            elif row["type"] == "intersections":
                # self.buses[f"bus{row.intPowerID}"] = pp.create_bus(
                #     pn, vn_kv=138, name=f"P_B{row.intPowerID}", geodata=(x, y), type="b"
                # )
                pass
            elif row["type"] in ["23kv_substations", "12kv_substations"]:
                # self.buses[f"bus{row.intPowerID}"] = pp.create_bus(
                #     pn, vn_kv=23, name=f"P_B{row.intPowerID}", geodata=(x, y), type="b"
                # )
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
                    name=f"P_S{row.intPowerID}L",
                )
                pn.loads_geodata = pn.loads_geodata.append(
                    {"x": x, "y": y - 40}, ignore_index=True
                )

    def construct_links(self, pn):
        pp.create_std_type(
            pn,
            {
                "c_nf_per_km": 210,
                "r_ohm_per_km": 0.1,  # 0.642,
                "x_ohm_per_km": 0.083,
                "max_i_ka": 0.142,
                "type": "ol",
            },
            name="shelby_line",
        )

        shelby_line = "shelby_line"

        line_count_dict = {node: 0 for node in self._nodes.intPowerID.unique()}

        for _, row in self._links.iterrows():

            fromnode = int(row["fromnode"])
            tonode = int(row["tonode"])
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
            self.switches[f"switch{fromnode}_{tonode}"] = pp.create_switch(
                pn,
                self.buses[f"bus{fromnode}"],
                self.buses[f"bus{fromnode}L{count_from}"],
                et="b",
                type="CB",
                closed=True,
                name=f"P_S{fromnode}_{tonode}",
            )

            self.switches[f"switch{tonode}_{fromnode}"] = pp.create_switch(
                pn,
                self.buses[f"bus{tonode}"],
                self.buses[f"bus{tonode}L{count_to}"],
                et="b",
                type="CB",
                closed=True,
                name=f"P_S{tonode}_{fromnode}",
            )
            pp.create_line(
                pn,
                from_bus=self.buses[f"bus{fromnode}L{count_from}"],
                to_bus=self.buses[f"bus{tonode}L{count_to}"],
                length_km=row["length_km"],
                std_type=shelby_line,
                name=f"P_L{fromnode}_{tonode}",
            )
            line_count_dict[fromnode] += 1
            line_count_dict[tonode] += 1

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
