"""Functions to generate infrastructure network plots and result plots."""

# import pandapower.plotting as pandaplot
import pandas as pd

import matplotlib.pyplot as plt
import networkx as nx

from bokeh.io import show, output_notebook, curdoc
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Range1d, ColorBar
from bokeh.transform import factor_cmap
from bokeh.palettes import Category10, Turbo256, Viridis3, RdYlGn
from bokeh.tile_providers import get_provider, Vendors

from bokeh.transform import factor_cmap, linear_cmap
from sklearn import metrics

import seaborn as sns

import numpy as np

# -----------------------------------------------------------#
#                      NETWORK PLOTS                        #
# -----------------------------------------------------------#


def plot_transpo_net(transpo_folder):
    """Generates the transportation network plot.

    :param transpo_folder: Location of the .tntp files.
    :type transpo_folder: string
    """
    links = pd.DataFrame(
        columns=[
            "Init node",
            "Term node",
            "Capacity",
            "Length",
            "Free Flow Time",
            "B",
            "Power",
            "Speed limit",
            "Toll",
            "Type",
        ]
    )
    with open("{}/example_net.tntp".format(transpo_folder), "r") as f:
        for line in f:
            if "~" in line:
                for line in f:
                    link_data = line.split("\t")[1:11]
                    links = links.append(
                        {
                            "Init node": link_data[0],
                            "Term node": link_data[1],
                            "Capacity": link_data[2],
                            "Length": link_data[3],
                            "Free Flow Time": link_data[4],
                            "B": link_data[5],
                            "Power": link_data[6],
                            "Speed limit": link_data[7],
                            "Toll": link_data[8],
                            "Type": link_data[9],
                        },
                        ignore_index=True,
                    )

    nodes = pd.read_csv("{}/example_node.tntp".format(transpo_folder), sep="\t")

    G = nx.Graph()
    edge_list = list(
        map(list, zip(links["Init node"].values, links["Term node"].values))
    )
    G.add_edges_from(edge_list)
    pos = {str(i + 1): (row[1], row[2]) for i, row in nodes.iterrows()}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)


def plot_power_net(net):
    """Generates the power systems plot.

    :param net: The power systems network.
    :type net: pandapower network object
    """
    options = {
        "bus_size": 1.5,
        "plot_loads": True,
        "library": "networkx",
        "bus_color": "lightsteelblue",
        "show_plot": True,
        "scale_size": True,
    }
    plt.figure(1, figsize=(10, 7))
    pandaplot.simple_plot(net, **options)


def plot_water_net(wn):
    """Generates the water network plot.

    :param wn: The water network.
    :type wn: wntr network object
    """
    # wn = wntr.network.WaterNetworkModel(water_net)

    coord_list = list(wn.query_node_attribute("coordinates"))
    node_coords = [list(ele) for ele in coord_list]
    node_list = wn.node_name_list
    G = wn.get_graph()
    pos = {node_list[i]: element for i, element in enumerate(node_coords)}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)
    # nodes, edges = wntr.graphics.plot_network(water_net, node_cmap='lightsteelblue', **options)


def plot_bokeh_from_integrated_graph(G, title, extent=[(1000, 8000), (1000, 6600)]):
    """Converts the integrated network into a Bokeh interactive plot.

    :param G: Integrated network on which the simulation is to be performed.
    :type G: networkx object
    :param title: Title of the plot.
    :type title: string
    :param extent: Extent of the plot as a list of tuple in the format [(xmin, xmax), (ymin, ymax)], defaults to [(1000, 8000), (1000, 6600)]
    :type extent: list, optional
    """
    output_notebook()

    p = figure(
        background_fill_color="white",
        plot_width=700,
        height=400,
        title=title,
        x_range=extent[0],
        y_range=extent[1],
    )

    # nodes
    x, y, node_type, node_category, id = [], [], [], [], []

    for _, node in enumerate(G.nodes.keys()):
        x.append(G.nodes[node]["coord"][0])
        y.append(G.nodes[node]["coord"][1])
        node_type.append(G.nodes[node]["node_type"])
        node_category.append(G.nodes[node]["node_category"])
        id.append(node)

    plot_nodes = p.square(
        "x",
        "y",
        source=ColumnDataSource(
            dict(x=x, y=y, node_type=node_type, node_category=node_category, id=id)
        ),
        color="gainsboro",
        alpha=0.6,
        muted_color="gainsboro",
        muted_alpha=0.2,
        size=5,
    )

    # links
    x, y, link_layer, link_category, id = [], [], [], [], []
    for _, link in enumerate(G.edges.keys()):
        x.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
        y.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
        link_layer.append(G.edges[link]["link_type"])
        link_category.append(G.edges[link]["link_category"])
        id.append(G.edges[link]["id"])

    plot_links = p.multi_line(
        "x",
        "y",
        source=ColumnDataSource(
            dict(x=x, y=y, link_layer=link_layer, link_category=link_category, id=id)
        ),
        line_color=factor_cmap(
            "link_layer", "Category10_3", np.unique(np.array(link_layer))
        ),
        line_alpha=1,
        line_width=1.5,
        muted_color=factor_cmap(
            "link_layer", "Category10_3", np.unique(np.array(link_layer))
        ),
        muted_alpha=0.2,
        legend_field="link_layer",
    )

    # hover tools
    node_hover = HoverTool(renderers=[plot_nodes])
    node_hover.tooltips = [
        ("Node ID", "@id"),
        ("Infrastructure", "@node_type"),
        ("Node category", "@node_category"),
    ]
    p.add_tools(node_hover)

    link_hover = HoverTool(renderers=[plot_links])
    link_hover.tooltips = [
        ("Link ID", "@id"),
        ("Infrastructure", "@link_layer"),
        ("Link category", "@link_category"),
    ]
    p.add_tools(link_hover)

    p.legend.location = "top_left"
    p.legend.click_policy = "mute"
    p.grid.visible = False
    # p.axis.visible = False
    show(p)


#############################################################
#                      RESULT PLOTS                        #
#############################################################


def plot_repair_curves(disrupt_recovery_object, scatter=False):
    """Generates the direct impact and repair level plots for the failed components.

    :param disrupt_recovery_object: The disrupt_generator.DisruptionAndRecovery object.
    :type disrupt_recovery_object: DisasterAndRecovery object
    :param scatter: scatter plot, defaults to False
    :type scatter: bool, optional
    """
    colors = list(Turbo256)
    interval = len(colors) // len(
        disrupt_recovery_object.network.get_disrupted_components()
    )

    palette = [colors[i] for i in range(0, len(colors), interval)]

    line_width = 2.5
    mode = "after"

    curdoc().theme = "light_minimal"
    p = figure(
        plot_width=750,
        plot_height=450,
        title="Disrupted components and their restoration",
        x_axis_label="Time (min)",
        y_axis_label="Damage level (%)",
        toolbar_location="above",
    )
    p.y_range = Range1d(0, 100)

    for index, name in enumerate(
        disrupt_recovery_object.network.get_disrupted_components()
    ):
        time_tracker = (
            disrupt_recovery_object.event_table[
                disrupt_recovery_object.event_table.components == name
            ].time_stamp
            / 60
        )

        damage_tracker = disrupt_recovery_object.event_table[
            disrupt_recovery_object.event_table.components == name
        ].perf_level

        if scatter == True:
            p.scatter(
                x=time_tracker,
                y=damage_tracker,
                size=5,
                color=palette[index],
                alpha=0.2,
            )
        p.step(
            x=time_tracker,
            y=damage_tracker,
            alpha=1,
            line_width=line_width,
            color=palette[index],
            muted_alpha=0.1,
            mode=mode,
            legend_label=name,
        )
    # p.legend.location = (0, 0)  # "bottom_right"
    p.add_layout(p.legend[0], "right")
    p.legend.background_fill_color = "gainsboro"
    p.legend.background_fill_alpha = 0.1
    p.legend.click_policy = "mute"
    show(p)


def plot_interdependent_effects(resilience_metrics):
    sns.set_context("paper", font_scale=1.25)
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(7, 4))
    fig.tight_layout()
    sns.lineplot(
        ax=ax,
        x=[x / 60 for x in resilience_metrics.water_time_list],
        y=resilience_metrics.water_ecs_list,
        label="Water",
        linewidth=2,
        alpha=0.9,
    )
    sns.lineplot(
        ax=ax,
        x=[x / 60 for x in resilience_metrics.power_time_list],
        y=resilience_metrics.power_ecs_list,
        drawstyle="steps-post",
        label="Power",
        linewidth=2,
        alpha=0.9,
    )

    ax.set(
        xlabel="Time (hours)", ylabel="Equivalent Consumer Serviceability", ylim=(0, 1)
    )
    ax.set_title("Network-wide performance", fontsize=12)

    fig.subplots_adjust(hspace=0.35)


def plot_network_impact_map(
    resilience_metrics, integrated_network, strategy, infra="power"
):
    output_notebook()
    avg_water_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}
    avg_power_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}

    water_demands_ratio = resilience_metrics.water_demands_ratio
    power_demands_ratio = resilience_metrics.power_demand_ratio
    water_time_list = resilience_metrics.water_time_list
    power_time_list = resilience_metrics.power_time_list
    for column in water_demands_ratio.columns:
        if column.startswith("W_JTN"):
            if column in avg_water_demand_ratio[strategy].keys():
                avg_water_demand_ratio[strategy][column].append(
                    metrics.auc(water_time_list, 1 - water_demands_ratio[column])
                )
            else:
                avg_water_demand_ratio[strategy][column] = [
                    metrics.auc(water_time_list, 1 - water_demands_ratio[column])
                ]
    for column in power_demands_ratio.columns:
        if column in avg_power_demand_ratio[strategy].keys():
            avg_power_demand_ratio[strategy][column].append(
                metrics.auc(power_time_list, 1 - power_demands_ratio[column])
            )
        else:
            avg_power_demand_ratio[strategy][column] = [
                metrics.auc(power_time_list, 1 - power_demands_ratio[column])
            ]

    water_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}
    power_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}

    for node in avg_water_demand_ratio[strategy].keys():
        water_compon_auc[strategy][node] = (
            np.mean(avg_water_demand_ratio[strategy][node]) / 60
        )
    for node in avg_power_demand_ratio[strategy].keys():
        power_compon_auc[strategy][node] = (
            np.mean(avg_power_demand_ratio[strategy][node]) / 60
        )

    water_compon_auc_df = pd.DataFrame(water_compon_auc)
    water_compon_auc_df["component"] = water_compon_auc_df.index

    power_compon_auc_df = pd.DataFrame(power_compon_auc)
    power_compon_auc_df["component"] = power_compon_auc_df.index

    G = integrated_network.integrated_graph
    if infra == "water":
        auc_type = water_compon_auc
    elif infra == "power":
        auc_type = power_compon_auc

    for node in G.nodes.keys():
        if node in auc_type[strategy].keys():
            G.nodes[node]["avg_perf"] = auc_type[strategy][node]
        else:
            G.nodes[node]["avg_perf"] = np.nan

    for link in G.edges.keys():
        link_id = G.edges[link]["id"]
        if link_id in auc_type[strategy].keys():
            G.edges[link]["avg_perf"] = auc_type[strategy][link_id]
        else:
            G.edges[link]["avg_perf"] = np.nan

    palette = tuple(
        [
            "#32CD32",
            "#5FCF26",
            "#8DD11B",
            "#BAD310",
            "#E8D505",
            "#FFBF00",
            "#FF8F00",
            "#FF5F00",
            "#FF2F00",
            "#FF0000",
        ]
    )

    p = figure(
        background_fill_color="white",
        plot_width=785,
        height=500,
        # title=f"Mean consumer-level outage during floods: {strategy}-based recovery strategy",
        x_range=(1400, 7400),
        y_range=(2000, 6000),
    )

    # links
    x, y, link_layer, link_category, avg_perf, id = [], [], [], [], [], []
    for _, link in enumerate(G.edges.keys()):
        x.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
        y.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
        avg_perf.append(G.edges[link]["avg_perf"])

    plot_links = p.multi_line(
        "x",
        "y",
        source=ColumnDataSource(
            dict(
                x=x,
                y=y,
                avg_perf=avg_perf,
            )
        ),
        line_color="grey",
        line_alpha=0.6,
        line_width=0.75,
        legend_label="Infrastructure links",
        # legend_field="fail_prob",
    )

    x, y, node_type, node_category, avg_perf, id = [], [], [], [], [], []

    if infra == "water":
        for _, node in enumerate(G.nodes.keys()):
            if G.nodes[node]["avg_perf"] is not np.nan:
                x.append(G.nodes[node]["coord"][0])
                y.append(G.nodes[node]["coord"][1])
                avg_perf.append(G.nodes[node]["avg_perf"])
    elif infra == "power":
        for index, node in enumerate(integrated_network.pn.load.name):
            if node in auc_type[strategy].keys():
                x.append(integrated_network.pn.loads_geodata.x[index])
                y.append(integrated_network.pn.loads_geodata.y[index])
                avg_perf.append(auc_type[strategy][node])
    color_mapper = linear_cmap(
        field_name="avg_perf",
        palette=palette,
        low=0,
        high=max(avg_perf),
        nan_color="snow",
    )

    plot_nodes = p.square(
        "x",
        "y",
        source=ColumnDataSource(
            dict(
                x=x,
                y=y,
                avg_perf=avg_perf,
            )
        ),
        color=color_mapper,
        fill_alpha=1,
        alpha=1,
        size=6,
    )

    p.legend.location = "bottom_left"
    p.legend.label_text_font_size = "14pt"

    # infra = [word[0].upper() + word[1:] for word in s.split()]
    color_bar = ColorBar(
        color_mapper=color_mapper["transform"],
        width=15,
        location=(0, 0),
        title=f"{infra.title()} outage (equivalent outage hours)",
        title_text_font="helvetica",
        title_text_font_style="normal",
        title_text_font_size="14pt",
        major_label_text_font_size="14pt",
    )
    p.add_layout(color_bar, "right")

    p.axis.visible = False
    p.grid.visible = False
    p.outline_line_color = None

    show(p)


def plot_disruptions_and_crews(integrated_network):
    failed_components_list = list(integrated_network.disrupted_components)
    affected_nodes = {}
    affected_links = {}
    fail_compon_dict = {
        "power": {"L"},
        "water": {"R", "PMA"},
        "transport": {"L"},
    }

    G = integrated_network.integrated_graph

    crew_locs = {"power": [], "water": [], "transpo": []}
    for key in integrated_network.power_crews.keys():
        crew_locs["power"].append(integrated_network.power_crews[key]._init_loc)
    for key in integrated_network.water_crews.keys():
        crew_locs["water"].append(integrated_network.water_crews[key]._init_loc)
    for key in integrated_network.water_crews.keys():
        crew_locs["transpo"].append(integrated_network.transpo_crews[key]._init_loc)

    power_node_list = [
        node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "Power"
    ]
    power_link_list = [
        G.edges[edge]["id"]
        for edge in G.edges.keys()
        if G.edges[edge]["link_type"] == "Power"
    ]

    affected_nodes["power"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["power"]
        if (compon.startswith("P_" + compon_type) and compon in power_node_list)
    ]
    affected_links["power"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["power"]
        if (compon.startswith("P_" + compon_type) and compon in power_link_list)
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

    affected_nodes["water"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["water"]
        if (compon.startswith("W_" + compon_type) and compon in water_node_list)
    ]
    affected_links["water"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["water"]
        if (compon.startswith("W_" + compon_type) and compon in water_link_list)
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

    affected_nodes["transpo"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["transport"]
        if (compon.startswith("T_" + compon_type) and compon in transpo_node_list)
    ]
    affected_links["transpo"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["transport"]
        if (compon.startswith("T_" + compon_type) and compon in transpo_link_list)
    ]

    for _, node in enumerate(G.nodes.keys()):
        if (
            node
            in affected_nodes["water"]
            + affected_nodes["power"]
            + affected_nodes["transpo"]
        ):
            G.nodes[node]["fail_status"] = "Disrupted"
        else:
            G.nodes[node]["fail_status"] = "Functional"

    for _, link in enumerate(G.edges.keys()):
        if (
            G.edges[link]["id"]
            in affected_links["power"]
            + affected_links["water"]
            + affected_links["transpo"]
        ):
            G.edges[link]["fail_status"] = "Disrupted"
        else:
            G.edges[link]["fail_status"] = "Functional"

    # for _, node in enumerate(crew_locs["power"]):
    #     G.nodes[node]["crew_type"] = "Power crew"
    # for _, node in enumerate(crew_locs["water"]):
    #     G.nodes[node]["crew_type"] = "Water crew"
    # for _, node in enumerate(crew_locs["transpo"]):
    #     G.nodes[node]["crew_type"] = "Transportation crew"

    output_notebook()

    palette = [RdYlGn[11][2], RdYlGn[11][9]]

    p = figure(
        background_fill_color="white",
        plot_width=700,
        height=450,
        x_range=(1000, 8000),
        y_range=(1000, 6600),
    )

    # instatiate the tile source provider
    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    # add the back ground basemap
    p.add_tile(tile_provider, alpha=0.1)

    # nodes
    x, y, node_type, node_category, fail_status, id = (
        [],
        [],
        [],
        [],
        [],
        [],
    )

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
        size=1,
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
        line_width=2,
        legend_field="fail_status",
    )

    # crews
    x, y, crew_type = (
        [],
        [],
        [],
    )

    for node in crew_locs["power"]:
        x.append(G.nodes[node]["coord"][0])
        y.append(G.nodes[node]["coord"][1])
        crew_type.append("Power crew")
    for node in crew_locs["water"]:
        x.append(G.nodes[node]["coord"][0])
        y.append(G.nodes[node]["coord"][1])
        crew_type.append("Water crew")
    for node in crew_locs["transpo"]:
        x.append(G.nodes[node]["coord"][0])
        y.append(G.nodes[node]["coord"][1])
        crew_type.append("Transportation crew")

    index_cmap = factor_cmap(
        "crew_type",
        palette=Viridis3,
        factors=sorted(set(crew_type)),
    )

    plot_crews = p.square(
        "x",
        "y",
        source=ColumnDataSource(
            dict(
                x=x,
                y=y,
                crew_type=crew_type,
            )
        ),
        color=index_cmap,
        size=10,
        legend_field="crew_type",
    )

    p.legend.location = "top_left"
    p.axis.visible = False
    p.grid.visible = False
    show(p)
