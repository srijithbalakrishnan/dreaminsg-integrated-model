import pandas as pd
import networkx as nx
import wntr
import math
import os

import infrarisk.src.physical.interdependencies as interdependencies
import infrarisk.src.physical.water.water_network_model as water
import infrarisk.src.physical.power.power_system_model as power
import infrarisk.src.physical.transportation.network as transpo
import infrarisk.src.plots as model_plots

import infrarisk.src.repair_crews as repair_crews
import numpy as np
import geopandas as gpd
from pathlib import Path


class IntegratedNetwork:
    """An integrated infrastructure network class"""

    def __init__(
        self,
        name,
        water_folder=None,
        power_folder=None,
        transp_folder=None,
        power_sim_type=None,
        water_sim_type=None,
    ):
        """Initiates the IntegratedNetwork object.

        :param name: The name of the network.
        :type name: string
        :param water_folder: The directory that consists of required water network files, defaults to None
        :type water_folder: pathlib.Path object, optional
        :param power_folder: The directory that consists of required power network files, defaults to None
        :type power_folder: pathlib.Path object, optional
        :param transp_folder: The directory that consists of required traffic network files, defaults to None
        :type transp_folder: pathlib.Path object, optional
        :param power_sim_type: Power simulation type ("1ph" for single phase networks, "3ph" for three phase networks), defaults to "1ph"
        :type power_sim_type: string, optional
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        """
        self.name = name
        # FIX: initialise attributes that load_networks also sets, so the object
        # is always in a consistent state regardless of which loader is called.
        self.has_cyber_layer = False
        self.time_step = 60

        if water_folder is None:
            self.wn = None
        else:
            self.load_water_network(water_folder, water_sim_type=water_sim_type)

        if power_folder is None:
            self.pn = None
        else:
            self.load_power_network(power_folder, power_sim_type=power_sim_type)

        if transp_folder is None:
            self.tn = None
        else:
            self.load_transpo_network(transp_folder)

    def load_networks(
        self,
        water_folder,
        power_folder,
        transp_folder,
        power_sim_type="1ph",
        water_sim_type="PDA",
        sim_step=60,
        cyber_layer=False,
    ):
        """Loads the water, power and transportation networks.

        :param water_folder: The directory that consists of required water network files, defaults to None
        :type water_folder: pathlib.Path object, optional
        :param power_folder: The directory that consists of required power network files, defaults to None
        :type power_folder: pathlib.Path object, optional
        :param transp_folder: The directory that consists of required traffic network files, defaults to None
        :type transp_folder: pathlib.Path object, optional
        :param power_sim_type: Power simulation type ("1ph" for single phase networks, "3ph" for three phase networks), defaults to "1ph"
        :type power_sim_type: string, optional
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        :param sim_step: Simulation step in seconds, defaults to 60
        :type sim_step: int, optional
        :param cyber_layer: Whether to include cyber layer in the integrated network, defaults to False
        :type cyber_layer: bool, optional
        """
        self.has_cyber_layer = cyber_layer
        self.time_step = sim_step

        if water_folder is not None:
            self.load_water_network(
                water_folder, water_sim_type, sim_step, cyber_layer=cyber_layer
            )

        if power_folder is not None:
            self.load_power_network(
                power_folder, power_sim_type, cyber_layer=cyber_layer
            )

        if transp_folder is not None:
            self.load_transpo_network(transp_folder)

    def load_power_network(self, power_folder, power_sim_type, cyber_layer=False):
        """Loads the power network.

        :param power_folder: The directory that consists of required power network files
        :type power_folder: pathlib.Path object
        :param power_sim_type: Power simulation type ("1ph" for single phase networks, "3ph" for three phase networks), defaults to "1ph"
        :type power_sim_type: string, optional
        :param cyber_layer: If True, the cyber layer will be loaded, defaults to False
        :type cyber_layer: bool, optional
        """
        # FIX: catch Exception instead of UserWarning (UserWarning is never raised
        # as an exception, so the original bare except was effectively dead code).
        try:
            pn = power.load_power_network(
                os.path.join(power_folder, "power.json"), sim_type=power_sim_type
            )
            power.run_power_simulation(pn)
            self.pn = pn
            self.power_sim_type = power_sim_type
            self.base_power_supply = power.generate_base_supply(pn)
        except Exception as exc:
            print(
                "Error: The power systems file could not be loaded. "
                f"{os.path.join(power_folder, 'power.json')} — {exc}"
            )
            return

        line_switch_path = os.path.join(power_folder, "line_to_switch_map.csv")
        if os.path.exists(line_switch_path):
            line_switch_df = pd.read_csv(line_switch_path, sep=",")
            self.line_switch_dict = {
                row["line"]: [x for x in row[1:] if x is not np.nan]
                for _, row in line_switch_df.iterrows()
            }

        service_area_file = os.path.join(power_folder, "service_area/service_area.shp")
        if os.path.exists(service_area_file):
            print("Loading power service area details...")
            pn.service_area = gpd.read_file(service_area_file, crs="epsg:4326")
            pn.service_area = pn.service_area.to_crs("epsg:3857")
            pn.service_area.Power_Node = "P_LO" + pn.service_area.Power_Node.astype(str)
            pn.service_area.Id = pn.service_area.index

    def load_water_network(
        self, water_folder, water_sim_type, initial_sim_step=60, cyber_layer=False
    ):
        """Loads the water network.

        :param water_folder: The directory that consists of required water network files
        :type water_folder: pathlib.Path object
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        :param initial_sim_step: The initial simulation step in seconds, defaults to 60
        :type initial_sim_step: int, optional
        :param cyber_layer: If True, the cyber layer will be loaded, defaults to False
        :type cyber_layer: bool, optional
        """
        self.wn = water.load_water_network(
            f"{water_folder}/water.inp", water_sim_type, initial_sim_step, cyber_layer
        )
        self.water_sim_type = water_sim_type

        if water_sim_type == "DDA":
            base_wns = os.path.join(water_folder, "base_water_node_supply.csv")
            base_wlf = os.path.join(water_folder, "base_water_link_flow.csv")
            if not os.path.exists(base_wns):
                print("Generating base water supply values...")
                water.generate_base_supply(self.wn, water_folder)
            self.base_water_node_supply = pd.read_csv(base_wns)
            self.base_water_link_flow = pd.read_csv(base_wlf)

        elif water_sim_type == "PDA":
            base_wns_pda = os.path.join(water_folder, "base_water_node_supply_pda.csv")
            base_wlf_pda = os.path.join(water_folder, "base_water_link_flow_pda.csv")
            if not os.path.exists(base_wns_pda):
                print("Generating base water supply values...")
                water.generate_base_supply_pda(self.wn, water_folder)
            # FIX: both files are now checked/loaded together so a missing
            # base_water_link_flow_pda.csv no longer causes a silent crash.
            self.base_water_node_supply = pd.read_csv(base_wns_pda)
            self.base_water_link_flow = pd.read_csv(base_wlf_pda)

        pipe_valve_path = os.path.join(water_folder, "pipe_to_valve_map.csv")
        if os.path.exists(pipe_valve_path):
            pipe_valve_df = pd.read_csv(pipe_valve_path, sep=",")
            self.pipe_valve_dict = {
                row["pipe"]: [x for x in row[1:] if x is not np.nan]
                for _, row in pipe_valve_df.iterrows()
            }

        service_area_file = os.path.join(water_folder, "service_area/service_area.shp")
        if os.path.exists(service_area_file):
            print("Loading water service area details...")
            self.wn.service_area = gpd.read_file(service_area_file, crs="epsg:4326")
            self.wn.service_area = self.wn.service_area.to_crs("epsg:3857")
            self.wn.service_area.Water_Node = (
                "W_J" + self.wn.service_area.Water_Node.astype(str)
            )
            self.wn.service_area.Id = self.wn.service_area.index

    def load_transpo_network(self, transp_folder):
        """Loads the transportation network.

        :param transp_folder: The directory that consists of required transportation network files
        :type transp_folder: string
        """
        try:
            tn = transpo.Network(
                f"{transp_folder}/transpo_net.tntp",
                f"{transp_folder}/transpo_trips.tntp",
                f"{transp_folder}/transpo_node.tntp",
            )
            print(
                f"Transportation network successfully loaded from {transp_folder}. "
                "Static traffic assignment method will be used to calculate travel times."
            )
            self.transpo_link_geometry = self._load_transpo_link_geometry(
                transp_folder, tn
            )
            self.tn = tn
        except FileNotFoundError:
            print(
                f"Error: The transportation network folder does not exist. "
                f"No such directory: {transp_folder}."
            )
        except AttributeError:
            print("Error: Some required network files not found.")

    @staticmethod
    def _nearest_node_name(point_xy, node_names, node_xy):
        """Return nearest node and squared distance for a point coordinate pair."""
        px, py = point_xy
        deltas = node_xy - np.array([px, py])
        d2 = np.einsum("ij,ij->i", deltas, deltas)
        idx = int(np.argmin(d2))
        return node_names[idx], float(d2[idx])

    @staticmethod
    def _iter_candidate_transport_shapefiles(transp_folder):
        """Yield likely transport polyline shapefiles near a transport folder."""
        transport_path = Path(transp_folder)
        network_root = transport_path.parent.parent
        roads_dir = network_root / "gis" / "shelby_roads"

        preferred = [
            roads_dir / "shelby_final_small.shp",
            roads_dir / "shelby_final2.shp",
            roads_dir / "shelby_final.shp",
            roads_dir / "Road_Centerlines.shp",
        ]
        for shp in preferred:
            if shp.exists():
                yield shp

    def _build_geometry_lookup_from_shapefile(self, shp_path, tn, snap_tol=400.0):
        """Build directed pair -> polyline coordinates by snapping line endpoints to transport nodes."""
        roads = gpd.read_file(shp_path)
        if roads.empty or "geometry" not in roads.columns:
            return {}

        if roads.crs is None:
            roads = roads.set_crs("epsg:4326")
        roads = roads.to_crs("epsg:3857")

        node_coords_idx = tn.node_coords.set_index("Node")
        node_names = node_coords_idx.index.to_numpy()
        node_xy = node_coords_idx[["X", "Y"]].to_numpy(dtype=float)

        best = {}
        for geom in roads.geometry:
            if geom is None or geom.is_empty:
                continue

            # Support both LineString and MultiLineString records.
            if hasattr(geom, "geoms"):
                parts = [g for g in geom.geoms if hasattr(g, "coords") and len(g.coords) >= 2]
                if not parts:
                    continue
                line = max(parts, key=lambda g: g.length)
            elif hasattr(geom, "coords") and len(geom.coords) >= 2:
                line = geom
            else:
                continue

            coords = [(float(x), float(y)) for x, y in line.coords]
            start = coords[0]
            end = coords[-1]

            u, d2_u = self._nearest_node_name(start, node_names, node_xy)
            v, d2_v = self._nearest_node_name(end, node_names, node_xy)

            if u == v:
                continue

            max_dist = max(np.sqrt(d2_u), np.sqrt(d2_v))
            if max_dist > snap_tol:
                continue

            score = d2_u + d2_v
            for key, geom_coords in (((u, v), coords), ((v, u), list(reversed(coords)))):
                if key not in best or score < best[key]["score"]:
                    best[key] = {"coords": geom_coords, "score": score}

        return {k: v["coords"] for k, v in best.items()}

    def _load_transpo_link_geometry(self, transp_folder, tn):
        """Load road geometry for transportation links if matching shapefiles are available."""
        directed_pairs = {(link.tail, link.head) for link in tn.link.values()}
        if not directed_pairs:
            return {}

        best_lookup = {}
        best_coverage = 0
        for shp in self._iter_candidate_transport_shapefiles(transp_folder):
            try:
                lookup = self._build_geometry_lookup_from_shapefile(shp, tn)
            except Exception:
                continue

            coverage = sum(1 for pair in directed_pairs if pair in lookup)
            if coverage > best_coverage:
                best_lookup = lookup
                best_coverage = coverage

        if best_coverage > 0:
            print(
                f"Loaded geometric road polylines for {best_coverage}/{len(directed_pairs)} "
                "transport links."
            )
        else:
            print(
                "Road polyline geometry not found for transport links; "
                "using straight junction-to-junction segments."
            )
        return best_lookup

    def generate_integrated_graph(self, basemap=False, icon_size = 1250):
        """Generates the integrated network as a Networkx graph.

        :param basemap: If True, the basemap will be added to the integrated graph, defaults to False
        :type basemap: bool, optional
        :param icon_size: The size of the icons in the plot, defaults to 20
        :type icon_size: int, optional
        """
        self.power_graph = self.generate_power_networkx_graph()
        print("Successfully added power network to the integrated graph...")
        self.water_graph = self.generate_water_networkx_graph()
        print("Successfully added water network to the integrated graph...")
        self.transpo_graph = self.generate_transpo_networkx_graph()
        print("Successfully added transportation network to the integrated graph...")

        G = nx.compose_all([self.transpo_graph, self.power_graph, self.water_graph])
        self.integrated_graph = G
        self.set_map_extends()
        print("Integrated graph successfully created.")

        self.generate_betweenness_centrality()
        model_plots.plot_bokeh_from_integrated_graph(
            G,
            title=f"{self.name} integrated network",
            extent=self.map_extends,
            basemap=basemap,
            icon_size=icon_size
        )

    def generate_betweenness_centrality(self):
        """Generates the betweenness centrality of the integrated graph."""
        print("Generating betweenness centrality...")
        for attr, graph in [
            ("pn", self.power_graph),
            ("wn", self.water_graph),
            ("tn", self.transpo_graph),
        ]:
            setattr(self, f"{attr}_nodebc", nx.betweenness_centrality(graph, normalized=True))
            setattr(self, f"{attr}_edgebc", nx.edge_betweenness_centrality(graph, normalized=True))

    def set_map_extends(self):
        """Sets the extents of the map in the format ((xmin, ymin), (xmax, ymax))."""
        x, y = zip(
            *[
                self.integrated_graph.nodes[node]["coord"]
                for node in self.integrated_graph.nodes
            ]
        )
        x_min, x_max = math.floor(min(x)), math.floor(max(x))
        y_min, y_max = math.floor(min(y)), math.floor(max(y))
        tol = 0.02

        self.map_extends = [
            (x_min - tol * (x_max - x_min), y_min - tol * (y_max - y_min)),
            (x_max + tol * (x_max - x_min), y_max + tol * (y_max - y_min)),
        ]

    def get_map_extends(self):
        """Returns the extents of the map in the format ((xmin, ymin), (xmax, ymax)).

        :return: The extent of the integrated graph (coordinates)
        :rtype: list of tuples
        """
        return self.map_extends

    @staticmethod
    def _compute_edge_lengths(graph):
        """Adds a 'length' attribute to every edge in *graph* (Euclidean distance).

        :param graph: A networkx graph whose nodes have a 'coord' attribute.
        :type graph: networkx.Graph or networkx.DiGraph
        """
        for link in graph.edges.keys():
            sx, sy = graph.nodes[link[0]]["coord"]
            ex, ey = graph.nodes[link[1]]["coord"]
            graph.edges[link]["length"] = round(
                math.sqrt((sx - ex) ** 2 + (sy - ey) ** 2), 3
            )

    def generate_power_networkx_graph(self, plot=False):
        """Generates the power network as a networkx object.

        :param plot: To generate the network plot, defaults to False.
        :type plot: bool, optional
        :return: The power network as a networkx object.
        :rtype: networkx.Graph
        """
        # FIX: build lists first, then construct DataFrames in one call —
        # avoids O(n²) copying from the deprecated DataFrame.append pattern.
        node_rows = []
        for index, row in self.pn.bus.iterrows():
            node_rows.append(
                {
                    "id": row["name"],
                    "node_type": "power",
                    "node_category": "Bus",
                    "x": self.pn.bus_geodata.x[index],
                    "y": self.pn.bus_geodata.y[index],
                }
            )
        power_nodes = pd.DataFrame(node_rows)

        link_rows = []
        for _, row in self.pn.line.iterrows():
            link_rows.append(
                {
                    "id": row["name"],
                    "link_type": "power",
                    "link_category": "Power line",
                    "from": self.pn.bus.name.values[row["from_bus"]],
                    "to": self.pn.bus.name.values[row["to_bus"]],
                }
            )
        for _, row in self.pn.trafo.iterrows():
            link_rows.append(
                {
                    "id": row["name"],
                    "link_type": "power",
                    "link_category": "Transformer",
                    "from": self.pn.bus.name.values[row["hv_bus"]],
                    "to": self.pn.bus.name.values[row["lv_bus"]],
                }
            )
        for _, row in self.pn.switch[self.pn.switch.et == "b"].iterrows():
            link_rows.append(
                {
                    "id": row["name"],
                    "link_type": "power",
                    "link_category": "Switch",
                    "from": self.pn.bus.name.values[row["bus"]],
                    "to": self.pn.bus.name.values[row["element"]],
                }
            )
        power_links = pd.DataFrame(link_rows)

        G_power = nx.from_pandas_edgelist(
            power_links,
            source="from",
            target="to",
            edge_attr=["id", "link_type", "link_category"],
        )

        for _, row in power_nodes.iterrows():
            G_power.nodes[row["id"]]["node_type"] = row["node_type"]
            G_power.nodes[row["id"]]["node_category"] = row["node_category"]
            G_power.nodes[row["id"]]["coord"] = (row["x"], row["y"])

        self._compute_edge_lengths(G_power)

        if plot:
            pos = {node: G_power.nodes[node]["coord"] for node in power_nodes.id}
            nx.draw(G_power, pos, node_size=1)

        return G_power

    def generate_water_networkx_graph(self, plot=False):
        """Generates the water network as a networkx object.

        :param plot: To generate the network plot, defaults to False.
        :type plot: bool, optional
        :return: The water network as a networkx object.
        :rtype: networkx.Graph
        """
        # FIX: cache coordinates per node to avoid fetching twice.
        node_rows = []
        node_categories = {
            "Junction": self.wn.junction_name_list,
            "Tank": self.wn.tank_name_list,
            "Reservoir": self.wn.reservoir_name_list,
        }
        for category, name_list in node_categories.items():
            for node_name in name_list:
                coords = self.wn.get_node(node_name).coordinates
                node_rows.append(
                    {
                        "id": node_name,
                        "node_type": "water",
                        "node_category": category,
                        "x": coords[0],
                        "y": coords[1],
                        "coord": coords,
                    }
                )
        water_nodes = pd.DataFrame(node_rows)

        link_rows = []
        link_categories = {
            "Water pipe": self.wn.pipe_name_list,
            "Water pump": self.wn.pump_name_list,
        }
        for category, name_list in link_categories.items():
            for link_name in name_list:
                lnk = self.wn.get_link(link_name)
                link_rows.append(
                    {
                        "id": link_name,
                        "link_type": "water",
                        "link_category": category,
                        "from": lnk.start_node_name,
                        "to": lnk.end_node_name,
                    }
                )
        water_links = pd.DataFrame(link_rows)

        G_water = nx.from_pandas_edgelist(
            water_links,
            source="from",
            target="to",
            edge_attr=["id", "link_type", "link_category"],
        )

        for _, row in water_nodes.iterrows():
            G_water.nodes[row["id"]]["node_type"] = row["node_type"]
            G_water.nodes[row["id"]]["node_category"] = row["node_category"]
            G_water.nodes[row["id"]]["coord"] = row["coord"]

        self._compute_edge_lengths(G_water)

        if plot:
            pos = {node: G_water.nodes[node]["coord"] for node in water_nodes.id}
            nx.draw(G_water, pos, node_size=1)

        return G_water

    def generate_transpo_networkx_graph(self, plot=False):
        """Generates the transportation network as a networkx object.

        :param plot: To generate the network plot, defaults to False.
        :type plot: bool, optional
        :return: The transportation network as a networkx object.
        :rtype: networkx.DiGraph
        """
        # FIX: index node_coords once instead of filtering per node per attribute.
        node_coords_idx = self.tn.node_coords.set_index("Node")

        transpo_node_list = list(self.tn.node.keys())
        node_rows = []
        for node_name in transpo_node_list:
            node_rows.append(
                {
                    "id": node_name,
                    "node_type": "transpo",
                    "node_category": "Junction",
                    "x": node_coords_idx.loc[node_name, "X"],
                    "y": node_coords_idx.loc[node_name, "Y"],
                }
            )
        transpo_nodes = pd.DataFrame(node_rows)

        link_rows = [
            {
                "id": link_name,
                "link_type": "transpo",
                "link_category": "Road link",
                "from": self.tn.link[link_name].tail,
                "to": self.tn.link[link_name].head,
                "geometry": self.transpo_link_geometry.get(
                    (self.tn.link[link_name].tail, self.tn.link[link_name].head)
                ),
            }
            for link_name in self.tn.link.keys()
        ]
        transpo_links = pd.DataFrame(link_rows)

        G_transpo = nx.from_pandas_edgelist(
            transpo_links,
            source="from",
            target="to",
            edge_attr=["id", "link_type", "link_category", "geometry"],
            create_using=nx.DiGraph(),
        )

        for _, row in transpo_nodes.iterrows():
            G_transpo.nodes[row["id"]]["node_type"] = "transpo"
            G_transpo.nodes[row["id"]]["node_category"] = row["node_category"]
            G_transpo.nodes[row["id"]]["coord"] = (row["x"], row["y"])

        self._compute_edge_lengths(G_transpo)

        if plot:
            pos = {node: G_transpo.nodes[node]["coord"] for node in transpo_nodes.id}
            nx.draw(G_transpo, pos, node_size=1)

        return G_transpo

    def generate_dependency_table(self, dependency_file):
        """Generates the dependency table from an input file.

        :param dependency_file: The location of the dependency file in csv format.
        :type dependency_file: string
        """
        dependency_table = interdependencies.DependencyTable()
        dependency_table.build_power_water_dependencies(dependency_file)
        dependency_table.build_transportation_access(self.integrated_graph)
        self.dependency_table = dependency_table

    def set_disrupted_components(self, disruption_file):
        """Sets the disrupted components in the network.

        :param disruption_file: The location of the physical disruption scenario file.
        :type disruption_file: string
        """
        self.disruptive_events = pd.read_csv(disruption_file, sep=",")
        self.disruptive_events.time_stamp = 2 * self.time_step
        self.disrupted_components = self.disruptive_events.components
        self.set_disrupted_infra_dict()

        self.disruption_time_dict = {}
        for infra in ("power", "water", "transpo"):
            comp_list = self.disrupted_infra_dict[infra]
            self.disruption_time_dict[infra] = self.disruptive_events[
                self.disruptive_events["components"].isin(comp_list)
            ]["time_stamp"].min()

    def set_disrupted_cyber_components(self, cyber_disruption_file):
        """Sets the disrupted cyber components in the network.

        :param cyber_disruption_file: The location of the cyber disruption scenario file.
        :type cyber_disruption_file: string
        """
        if self.has_cyber_layer:
            self.cyber_disruptive_events = pd.read_csv(cyber_disruption_file, sep=",")
            self.disrupted_cyber_components = (
                self.cyber_disruptive_events.cyber_component
            )
            self.set_disrupted_cyber_dict()
        else:
            print("The network has no cyber layer. Please construct a cyber layer.")

    def get_disruptive_events(self):
        """Returns the disruptive event data.

        :return: The table of disruptive events.
        :rtype: pandas.DataFrame
        """
        return self.disruptive_events

    def get_disrupted_components(self):
        """Returns the list of disrupted components.

        :return: Current list of disrupted components.
        :rtype: list
        """
        return list(self.disrupted_components)

    # ------------------------------------------------------------------
    # FIX: shared helper removes the duplicated classify-by-infra logic
    # that appeared in both set_disrupted_infra_dict and
    # set_disrupted_cyber_dict.
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_components_by_infra(components):
        """Classifies a list of component names into infrastructure buckets.

        :param components: Iterable of component name strings.
        :return: dict with keys 'power', 'water', 'transpo' and list values.
        :rtype: dict
        """
        result = {"power": [], "water": [], "transpo": []}
        for component in components:
            infra = interdependencies.get_compon_details(component)["infra"]
            if infra in result:
                result[infra].append(component)
        return result

    def set_disrupted_infra_dict(self):
        """Sets the disrupted infrastructure components dictionary."""
        self.disrupted_infra_dict = self._classify_components_by_infra(
            self.disrupted_components
        )

    def set_disrupted_cyber_dict(self):
        """Sets the disrupted cyber components dictionary.

        FIX: was incorrectly iterating over self.disrupted_components instead
        of self.disrupted_cyber_components.
        """
        self.disrupted_cyber_dict = self._classify_components_by_infra(
            self.disrupted_cyber_components
        )

    def get_disrupted_infra_dict(self):
        """Returns the disrupted infrastructure components dictionary.

        :return: The disrupted infrastructure components dictionary.
        :rtype: dictionary
        """
        return self.disrupted_infra_dict

    def deploy_crews(
        self,
        init_power_crew_locs=None,
        power_crews_size=None,
        init_water_crew_locs=None,
        water_crews_size=None,
        init_transpo_crew_locs=None,
        transpo_crews_size=None,
    ):
        """Deploys the infrastructure crews for performing recovery actions.

        :param init_power_crew_locs: Initial locations (nearest transportation nodes) of the power crews.
        :type init_power_crew_locs: list of strings
        :param power_crews_size: Size of the power crews.
        :type power_crews_size: list
        :param init_water_crew_locs: Initial locations of the water crews.
        :type init_water_crew_locs: list
        :param water_crews_size: Size of the water crews.
        :type water_crews_size: list
        :param init_transpo_crew_locs: Initial locations of the transportation crews.
        :type init_transpo_crew_locs: list of strings
        :param transpo_crews_size: Size of the transportation crews.
        :type transpo_crews_size: list
        """
        self.power_crews = {}
        self.water_crews = {}
        self.transpo_crews = {}

        crew_configs = [
            (
                "power",
                init_power_crew_locs,
                power_crews_size,
                repair_crews.PowerRepairCrew,
                self.power_crews,
            ),
            (
                "water",
                init_water_crew_locs,
                water_crews_size,
                repair_crews.WaterRepairCrew,
                self.water_crews,
            ),
            (
                "transpo",
                init_transpo_crew_locs,
                transpo_crews_size,
                repair_crews.TranspoRepairCrew,
                self.transpo_crews,
            ),
        ]

        for infra, locs, sizes, crew_cls, crew_dict in crew_configs:
            try:
                for i, loc in enumerate(locs):
                    crew_size = None if sizes is None else sizes[i]
                    crew = crew_cls(name=i + 1, init_loc=loc, crew_size=crew_size)
                    crew.set_next_trip_start(self.disruption_time_dict[infra])
                    crew_dict[i + 1] = crew
                print(f"{infra.capitalize()} repair crews successfully deployed.")
            except TypeError:
                print(
                    f"TypeError: The initial locations of the {infra} crews "
                    "are not specified or not valid."
                )

    # FIX: extract repeated min-search into a private helper; get_idle_crew
    # now delegates to it for all three crew types.
    @staticmethod
    def _find_idle_crew(crews):
        """Returns the crew with the earliest next_trip_start.

        :param crews: dict of crew objects keyed by crew name.
        :return: The crew with the smallest next_trip_start value.
        """
        return min(crews.values(), key=lambda c: c.next_trip_start)

    def get_idle_crew(self, crew_type, min_time=None):
        """Returns the idle crew of the given type.

        :param crew_type: Type of the crew ('power', 'water', or 'transpo').
        :type crew_type: string
        :param min_time: Earliest time to be considered for the idle crew (currently reserved).
        :type min_time: float, optional
        :return: The idle crew of the given type.
        """
        crew_map = {
            "power": self.power_crews,
            "water": self.water_crews,
            "transpo": self.transpo_crews,
        }
        crews = crew_map.get(crew_type)
        if crews is None:
            raise ValueError(f"Unknown crew_type: {crew_type!r}")
        return self._find_idle_crew(crews)

    def reset_crew_locs(self):
        """Resets the location of infrastructure crews."""
        for crew_type in [self.power_crews, self.water_crews, self.transpo_crews]:
            for crew in crew_type.values():
                crew.reset_locs()

    def set_power_crew_loc(self, power_crew_loc):
        """Sets the location of the power crew.

        :param power_crew_loc: The name of the location (transportation node)
        :type power_crew_loc: string
        """
        self.power_crew_loc = power_crew_loc

    def set_water_crew_loc(self, water_crew_loc):
        """Sets the location of the water crew.

        :param water_crew_loc: The name of the location (transportation node)
        :type water_crew_loc: string
        """
        self.water_crew_loc = water_crew_loc

    def set_transpo_crew_loc(self, transpo_crew_loc):
        """Sets the location of the transportation crew.

        :param transpo_crew_loc: The name of the location (transportation node)
        :type transpo_crew_loc: string
        """
        self.transpo_crew_loc = transpo_crew_loc

    def get_power_crew_loc(self):
        """Returns the current power crew location.

        :return: Power crew location
        :rtype: string
        """
        return self.power_crew_loc

    def get_water_crew_loc(self):
        """Returns the current water crew location.

        :return: Water crew location
        :rtype: string
        """
        return self.water_crew_loc

    def get_transpo_crew_loc(self):
        """Returns the current transportation crew location.

        :return: Transportation crew location
        :rtype: string
        """
        return self.transpo_crew_loc

    def pipe_leak_node_generator(self):
        """Splits the directly affected pipes to induce leak during simulations."""
        pipe_categories = {
            "Pipe",
            "Service Connection Pipe",
            "Main Pipe",
            "Hydrant Connection Pipe",
            "Valve converted to Pipe",
        }
        for component in self.get_disrupted_components():
            compon_details = interdependencies.get_compon_details(component)
            if compon_details["name"] in pipe_categories:
                self.wn = wntr.morph.split_pipe(
                    self.wn,
                    component,
                    f"{component}_B",
                    f"{component}_leak_node",
                )

    def get_node_link_dict(self):
        """Returns the dictionary of nodes and links in the network.

        :return: Nested dict keyed by infrastructure type then 'node'/'link'.
        :rtype: dict
        """
        return {
            "water": {
                "node": ["R", "J", "JIN", "JVN", "JTN", "JHY", "T"],
                "link": ["P", "PSC", "PMA", "PHC", "PV", "WP"],
            },
            "power": {
                "node": ["B", "BL", "BS", "LO", "MP", "AL", "AS", "G"],
                "link": ["S", "L", "LS", "TF", "TH", "I", "DL"],
            },
            "transpo": {"node": ["J"], "link": ["L"]},
        }