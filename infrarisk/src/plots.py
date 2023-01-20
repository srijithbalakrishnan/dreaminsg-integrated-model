"""Functions to generate infrastructure network plots and result plots."""

# import pandapower.plotting as pandaplot
import contextily as ctx
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from bokeh.io import curdoc, output_notebook, show
from bokeh.models import ColorBar, ColumnDataSource, HoverTool, Range1d
from bokeh.palettes import RdYlGn, Turbo256, Viridis3
from bokeh.plotting import figure

from bokeh.tile_providers import CARTODBPOSITRON_RETINA, get_provider, ESRI_IMAGERY
from bokeh.transform import factor_cmap, linear_cmap
from mpl_toolkits.axes_grid1 import make_axes_locatable

# -----------------------------------------------------------#
#                      NETWORK PLOTS                        #
# -----------------------------------------------------------#

cmap = colors.LinearSegmentedColormap.from_list(
    "", ["green", "yellow", "orange", "red"]
)


def plot_transpo_net(transpo_folder):
    """Generates the transportation network plot.

    :param transpo_folder: Location of the transport model (.tntp files).
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
    :type net: pandapowerNet
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
    :type wn: wntr.network.WaterNetworkModel
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


def plot_bokeh_from_integrated_graph(
    G, title, extent=[(1000, 1000), (8000, 6600)], basemap=False
):
    """Converts the integrated network into a Bokeh interactive plot.

    :param G: Integrated network on which the simulation is to be performed.
    :type G: networkx.Graph
    :param title: Title of the plot.
    :type title: string
    :param extent: Extent of the plot as a list of tuple in the format [(xmin, xmax), (ymin, ymax)], defaults to [(1000, 8000), (1000, 6600)]
    :type extent: list, optional
    """
    output_notebook()
    tile_provider = get_provider(ESRI_IMAGERY)

    p = figure(
        background_fill_color="white",
        plot_width=800,
        height=500,
        title=title,
        x_range=(extent[0][0], extent[1][0]),
        y_range=(extent[0][1], extent[1][1]),
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
        color="grey",
        alpha=0.2,
        muted_color="gainsboro",
        muted_alpha=0.2,
        size=5,
    )

    # links
    x_w, y_w, link_layer_w, link_cat_w, id_w = [], [], [], [], []
    x_p, y_p, link_layer_p, link_cat_p, id_p = [], [], [], [], []
    x_t, y_t, link_layer_t, link_cat_t, id_t = [], [], [], [], []

    for _, link in enumerate(G.edges.keys()):
        link_id = G.edges[link]["id"]
        if link_id.startswith("W_"):
            x_w.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
            y_w.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
            link_layer_w.append(G.edges[link]["link_type"])
            link_cat_w.append(G.edges[link]["link_category"])
            id_w.append(G.edges[link]["id"])
        elif link_id.startswith("P_"):
            x_p.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
            y_p.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
            link_layer_p.append(G.edges[link]["link_type"])
            link_cat_p.append(G.edges[link]["link_category"])
            id_p.append(G.edges[link]["id"])
        elif link_id.startswith("T_"):
            x_t.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
            y_t.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
            link_layer_t.append(G.edges[link]["link_type"])
            link_cat_t.append(G.edges[link]["link_category"])
            id_t.append(G.edges[link]["id"])

    plot_transpolinks = plot_bokeh_lines(
        p=p,
        x=x_t,
        y=y_t,
        link_layer=link_layer_t,
        link_category=link_cat_t,
        ids=id_t,
        infra="Transportation",
        alpha=1,
        line_dash="solid",
        color="limegreen",  # Category10[5][4],
    )
    plot_waterlinks = plot_bokeh_lines(
        p=p,
        x=x_w,
        y=y_w,
        link_layer=link_layer_w,
        link_category=link_cat_w,
        ids=id_w,
        infra="Water",
        alpha=1,
        line_dash="solid",
        color="yellow",  # Category10[5][1],
    )
    plot_powerlinks = plot_bokeh_lines(
        p=p,
        x=x_p,
        y=y_p,
        link_layer=link_layer_p,
        link_category=link_cat_p,
        ids=id_p,
        infra="Power",
        alpha=1,
        line_dash="solid",
        color="lightskyblue",  # Category10[5][3],
    )

    if basemap:
        p.add_tile(tile_provider)
    else:
        p.background_fill_color = "black"

    # hover tools
    node_hover = HoverTool(renderers=[plot_nodes])
    node_hover.tooltips = [
        ("Node ID", "@id"),
        ("Infrastructure", "@node_type"),
        ("Node category", "@node_category"),
    ]
    p.add_tools(node_hover)

    waterlink_hover = HoverTool(renderers=[plot_waterlinks])
    waterlink_hover.tooltips = [
        ("Link ID", "@id"),
        # ("Infrastructure", "@link_layer"),
        ("Link category", "@link_category"),
    ]
    p.add_tools(waterlink_hover)

    powerlink_hover = HoverTool(renderers=[plot_powerlinks])
    powerlink_hover.tooltips = [
        ("Link ID", "@id"),
        # ("Infrastructure", "@link_layer"),
        ("Link category", "@link_category"),
    ]
    p.add_tools(powerlink_hover)

    transpolink_hover = HoverTool(renderers=[plot_transpolinks])
    transpolink_hover.tooltips = [
        ("Link ID", "@id"),
        # ("Infrastructure", "@link_layer"),
        ("Link category", "@link_category"),
    ]
    p.add_tools(transpolink_hover)

    p.legend.location = "top_left"
    p.legend.click_policy = "mute"
    p.legend.background_fill_alpha = 0.3
    p.legend.background_fill_color = "black"
    p.legend.label_text_color = "white"
    p.grid.visible = False
    p.axis.visible = False
    show(p)


def plot_bokeh_lines(
    p,
    x,
    y,
    infra,
    link_layer,
    link_category,
    ids,
    line_dash="-",
    color="black",
    alpha=1,
):
    """Plots the links on the map.

    :param p: The bokeh figure object.
    :type p: bokeh.plotting.figure.Figure
    :param x: The x coordinates of the links.
    :type x: list
    :param y: The y coordinates of the links.
    :type y: list
    :param infra: The infrastructure type of the links.
    :type infra: string
    :param link_layer: The link layer of the links.
    :type link_layer: string
    :param link_category: The link category of the links.
    :type link_category: string
    :param ids: The link ids.
    :type ids: list
    :param line_dash: The line dash style of the links.
    :type line_dash: string
    :param color: The color of the links.
    :type color: string
    :param alpha: The alpha value of the links.
    :type alpha: float
    :return: The bokeh figure object.
    :rtype: bokeh.plotting.figure.Figure

    """
    plot_links = p.multi_line(
        "x",
        "y",
        source=ColumnDataSource(
            dict(x=x, y=y, link_layer=link_layer, link_category=link_category, id=ids)
        ),
        line_color=color,
        line_alpha=alpha,
        line_width=2,
        muted_color=color,
        muted_alpha=0.2,
        line_dash=line_dash,
        legend_label=infra,
    )
    return plot_links


#############################################################
#                      RESULT PLOTS                        #
#############################################################


def plot_repair_curves(network_recovery, scatter=False):
    """Generates the direct impact and repair level plots for the failed components.

    :param network_recovery: The disrupt_generator.DisruptionAndRecovery object.
    :type network_recovery: infrarisk.src.network_recovery.NetworkRecovery
    :param scatter: scatter plot, defaults to False
    :type scatter: bool, optional
    """
    colors = list(Turbo256)
    interval = len(colors) // len(network_recovery.network.get_disrupted_components())

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

    for index, name in enumerate(network_recovery.network.get_disrupted_components()):
        time_tracker = (
            network_recovery.event_table[
                network_recovery.event_table.components == name
            ].time_stamp
            / 60
        )

        damage_tracker = network_recovery.event_table[
            network_recovery.event_table.components == name
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


def plot_interdependent_effects(resilience_metrics, metric, title=True):
    """Plots the interdependent effects of the water and power systems.

    :param resilience_metrics: The object in which simulation results are stored.
    :type resilience_metrics: infrarisk.src.resilience_metrics.WeightedResilienceMetric
    :param metric: The metric to be plotted.
    :type metric: string
    :param title: Whether to show the title, defaults to True
    :type title: bool, optional
    """
    water_metric_list = getattr(resilience_metrics, f"water_{metric}_list")
    power_metric_list = getattr(resilience_metrics, f"power_{metric}_list")

    if metric == "ecs":
        title = "Equivalent Consumer Serviceability"
    elif metric == "pcs":
        title = "Prioritized Consumer Serviceability"

    sns.set_style(style="ticks")
    sns.set_context("paper", font_scale=1.75)
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(7, 5))
    fig.tight_layout()
    sns.lineplot(
        ax=ax,
        x=[x / 60 for x in resilience_metrics.water_time_list],
        y=water_metric_list,
        drawstyle="steps-post",
        label="Water",
        linewidth=2,
        linestyle=(0, (5, 1)),
        alpha=0.95,
        color="tab:red",
    )
    sns.lineplot(
        ax=ax,
        x=[x / 60 for x in resilience_metrics.power_time_list],
        y=power_metric_list,
        drawstyle="steps-post",
        label="Power",
        linewidth=2,
        linestyle=(0, (3, 1, 1, 1)),
        alpha=0.95,
        color="tab:blue",
    )

    plt.legend(loc="lower right")

    ax.set(xlabel="Time (hours)", ylabel="Average satisfied demand (%)", ylim=(0, 1.01))
    if title is True:
        ax.set_title("Network-wide performance", fontsize=12)

    fig.subplots_adjust(hspace=0.35)
    # plt.savefig(f"{metric}_plot.pdf", bbox_inches="tight")


def plot_network_impact_map(
    resilience_metrics,
    integrated_network,
    strategy,
    node_prefix,
    infra="power",
    time_index=None,
):
    """Plots the impact of the disruption on the network.

    :param resilience_metrics: The object in which simulation results are stored.
    :type resilience_metrics: infrarisk.src.resilience_metrics.WeightedResilienceMetric
    :param integrated_network: The integrated network.
    :type integrated_network: infrarisk.src.integrated_network.IntegratedNetwork
    :param strategy: The strategy used to restore the network.
    :type strategy: string
    :param node_prefix: The prefix of the nodes to be considered.
    :type node_prefix: string
    :param infra: The infrastructure to be considered, defaults to "power"
    :type infra: string, optional
    :param time_index: The time index to be considered, defaults to None
    :type time_index: int, optional
    """
    output_notebook()

    if infra == "water":
        avg_water_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}
        water_demands_ratio = resilience_metrics.water_demands_ratio
        water_time_list = resilience_metrics.water_time_list
        for column in water_demands_ratio.columns:
            if column.startswith(node_prefix):
                if column in avg_water_demand_ratio[strategy].keys():
                    if time_index is None:
                        avg_water_demand_ratio[strategy][column].append(
                            integrate(water_time_list, 1 - water_demands_ratio[column])
                        )
                    else:
                        avg_water_demand_ratio[strategy][column].append(
                            1 - water_demands_ratio[column][time_index]
                        )
                else:
                    if time_index is None:
                        avg_water_demand_ratio[strategy][column] = [
                            integrate(water_time_list, 1 - water_demands_ratio[column])
                        ]
                    else:
                        avg_water_demand_ratio[strategy][column] = (
                            1 - water_demands_ratio[column][time_index]
                        )
        water_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}

        for node in avg_water_demand_ratio[strategy].keys():
            if time_index is None:
                water_compon_auc[strategy][node] = (
                    np.mean(avg_water_demand_ratio[strategy][node]) / 60
                )
            else:
                water_compon_auc[strategy][node] = avg_water_demand_ratio[strategy][
                    node
                ]

        water_compon_auc_df = pd.DataFrame(water_compon_auc)
        water_compon_auc_df["component"] = water_compon_auc_df.index

    elif infra == "power":
        avg_power_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}
        power_demands_ratio = resilience_metrics.power_demand_ratio
        power_time_list = resilience_metrics.power_time_list

        for column in power_demands_ratio.columns:
            if column.startswith(node_prefix):
                if column in avg_power_demand_ratio[strategy].keys():
                    if time_index is None:
                        avg_power_demand_ratio[strategy][column].append(
                            integrate(power_time_list, 1 - power_demands_ratio[column])
                        )
                    else:
                        avg_power_demand_ratio[strategy][column].append(
                            1 - power_demands_ratio[column][time_index]
                        )
                else:
                    if time_index is None:
                        avg_power_demand_ratio[strategy][column] = [
                            integrate(power_time_list, 1 - power_demands_ratio[column])
                        ]
                    else:
                        avg_power_demand_ratio[strategy][column] = (
                            1 - power_demands_ratio[column][time_index]
                        )

        power_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}
        for node in avg_power_demand_ratio[strategy].keys():
            if time_index is None:
                power_compon_auc[strategy][node] = (
                    np.mean(avg_power_demand_ratio[strategy][node]) / 60
                )
            else:
                power_compon_auc[strategy][node] = avg_power_demand_ratio[strategy][
                    node
                ]

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
    x, y = [], []
    for _, link in enumerate(G.edges.keys()):
        x.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
        y.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
        # avg_perf.append(G.edges[link]["avg_perf"])

    _ = p.multi_line(
        "x",
        "y",
        source=ColumnDataSource(
            dict(
                x=x,
                y=y,
                # avg_perf=avg_perf,
            )
        ),
        line_color="grey",
        line_alpha=0.6,
        line_width=0.75,
        legend_label="Infrastructure links",
    )

    # nodes
    x, y, avg_perf = [], [], []
    if infra == "water":
        for _, node in enumerate(auc_type[strategy].keys()):
            x.append(G.nodes[node]["coord"][0])
            y.append(G.nodes[node]["coord"][1])
            avg_perf.append(G.nodes[node]["avg_perf"])
    elif infra == "power":
        for index, node in enumerate(integrated_network.pn.load.name):
            if node in auc_type[strategy].keys():
                x.append(integrated_network.pn.loads_geodata.x[index])
                y.append(integrated_network.pn.loads_geodata.y[index])
                avg_perf.append(auc_type[strategy][node])

    if time_index is None:
        title = f"{infra.title()} outage (equivalent outage hours)"
        high = max(avg_perf)
    else:
        title = f"Proportion of satisfied {infra} demand"
        high = 1

    color_mapper = linear_cmap(
        field_name="avg_perf",
        palette=palette,
        low=0,
        high=high,
        nan_color="snow",
    )

    _ = p.square(
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
        title=title,
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


def plot_region_impact_map(resilience_metrics, sa_dict, strategy, extends):
    """Plot the impact map of the region.

    :param resilience_metrics: The object in which simulation results are stored
    :type resilience_metrics: : infrarisk.src.resilience_metrics.WeightedResilienceMetric
    :param sa_dict: The power and water socioeconomic impact dictionary
    :type sa_dict: dictionary of geopandas.GeoDataFrame
    :param strategy: The name of the recovery strategy
    :type strategy: string
    :param extends: The extends of the region
    :type extends: tuple
    """

    avg_water_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}
    avg_power_demand_ratio = {"capacity": {}, "centrality": {}, "zone": {}}

    water_demands_ratio = resilience_metrics.water_demands_ratio
    power_demands_ratio = resilience_metrics.power_demand_ratio
    water_time_list = resilience_metrics.water_time_list
    power_time_list = resilience_metrics.power_time_list

    for water_node in water_demands_ratio.columns:
        if water_node.startswith("W_J"):
            if water_node in avg_water_demand_ratio[strategy].keys():
                avg_water_demand_ratio[strategy][water_node].append(
                    integrate(water_time_list, 1 - water_demands_ratio[water_node])
                )
            else:
                avg_water_demand_ratio[strategy][water_node] = [
                    integrate(water_time_list, 1 - water_demands_ratio[water_node])
                ]

    for power_node in power_demands_ratio.columns:
        if power_node in avg_power_demand_ratio[strategy].keys():
            avg_power_demand_ratio[strategy][power_node].append(
                integrate(power_time_list, 1 - power_demands_ratio[power_node])
            )
        else:
            avg_power_demand_ratio[strategy][power_node] = [
                integrate(power_time_list, 1 - power_demands_ratio[power_node])
            ]

    water_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}
    power_compon_auc = {"capacity": {}, "centrality": {}, "zone": {}}

    for node in avg_water_demand_ratio[strategy].keys():
        water_compon_auc[strategy][node] = (
            np.mean(avg_water_demand_ratio[strategy][node]) / 60
        )
    water_compon_auc_df = pd.DataFrame(water_compon_auc)
    water_compon_auc_df["component"] = water_compon_auc_df.index

    merged_water = pd.merge(
        sa_dict["Water"],
        water_compon_auc_df,
        left_on="Water_Node",
        right_on="component",
        how="left",
    )

    for node in avg_power_demand_ratio[strategy].keys():
        power_compon_auc[strategy][node] = (
            np.mean(avg_power_demand_ratio[strategy][node]) / 60
        )
    power_compon_auc_df = pd.DataFrame(power_compon_auc)
    power_compon_auc_df["component"] = power_compon_auc_df.index

    merged_power = pd.merge(
        sa_dict["Power"],
        power_compon_auc_df,
        left_on="Power_Node",
        right_on="component",
        how="left",
    )

    merged = [merged_water, merged_power]
    vmax = max(merged_power[strategy].max(), merged_water[strategy].max())

    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    sns.set_style("whitegrid")
    sns.set_context("notebook", font_scale=1.75, rc={"lines.linewidth": 2.5})
    fig.suptitle("Networkwide effects of infrastructure disruptions")
    for index, ax in enumerate(axes):
        ax.set_title(f"{list(sa_dict.keys())[index].title()} supply")
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("bottom", size="5%", pad=0.2)
        merged[index].plot(
            column=strategy,
            cmap=cmap,
            ax=ax,
            edgecolor="black",
            linewidth=0,
            legend=True,
            cax=cax,
            alpha=0.65,
            legend_kwds={
                "shrink": 0.25,
                "label": "Equivalent Outage Hours",
                "orientation": "horizontal",
            },
            aspect=1,
            vmin=0,
            vmax=vmax,
        )
        ax.set_xlim(extends[0], extends[1])
        ax.set_ylim(extends[2], extends[3])
        # ctx.add_basemap(ax=ax, source=ctx.providers.Stamen.Terrain)
        # ctx.add_basemap(ax=ax, source=ctx.providers.CartoDB.Positron)
        ctx.add_basemap(ax=ax, source=ctx.providers.Esri.WorldStreetMap)
        ax.set_axis_off()
    fig.tight_layout()


def plot_disruptions_and_crews(integrated_network, basemap=False):
    """Generate a plot of the number of disruptions and crews for each strategy.

    :param integrated_network: The integrated network object
    :type integrated_network: infrarisk.src.physical.integrated_network.IntegratedNetwork
    :param basemap: Whether to include a basemap, defaults to False
    :type basemap: bool, optional
    """
    extent = integrated_network.map_extends
    p = figure(
        background_fill_color="white",
        plot_width=800,
        height=450,
        # x_range=(extent[0][0] - 100, extent[1][0] + 100),
        # y_range=(extent[0][1] - 100, extent[1][1] + 100),
    )
    p.axis.visible = False

    tile_provider = get_provider(CARTODBPOSITRON_RETINA)
    if basemap:
        p.add_tile(tile_provider)

    failed_components_list = integrated_network.disrupted_components.to_list()
    affected_nodes = {}
    affected_links = {}
    fail_compon_dict = {
        "power": {"L", "MP"},
        "water": {"R", "PMA", "P", "WP"},
        "transpo": {"L"},
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
        node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "power"
    ]
    power_link_list = [
        G.edges[edge]["id"]
        for edge in G.edges.keys()
        if G.edges[edge]["link_type"] == "power"
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
        node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "water"
    ]
    water_link_list = [
        G.edges[edge]["id"]
        for edge in G.edges.keys()
        if G.edges[edge]["link_type"] == "water"
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
        node for node in G.nodes.keys() if G.nodes[node]["node_type"] == "transpo"
    ]
    transpo_link_list = [
        G.edges[edge]["id"]
        for edge in G.edges.keys()
        if G.edges[edge]["link_type"] == "transpo"
    ]

    affected_nodes["transpo"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["transpo"]
        if (compon.startswith("T_" + compon_type) and compon in transpo_node_list)
    ]
    affected_links["transpo"] = [
        compon
        for compon in failed_components_list
        for compon_type in fail_compon_dict["transpo"]
        if (compon.startswith("T_" + compon_type) and compon in transpo_link_list)
    ]

    for infra in ["water", "power", "transpo"]:
        affected_links[infra] = list(set(affected_links[infra]))
        affected_nodes[infra] = list(set(affected_nodes[infra]))

    print(affected_links)

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

    output_notebook()

    palette = [RdYlGn[11][2], RdYlGn[11][9]]

    # # instatiate the tile source provider
    # tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    # # add the back ground basemap
    # p.add_tile(tile_provider, alpha=0.1)

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
        size=3,
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
        x.append(G.nodes[node]["coord"][0] - 20)
        y.append(G.nodes[node]["coord"][1] - 20)
        crew_type.append("Power crew")
    for node in crew_locs["water"]:
        x.append(G.nodes[node]["coord"][0] + 20)
        y.append(G.nodes[node]["coord"][1] + 20)
        crew_type.append("Water crew")
    for node in crew_locs["transpo"]:
        x.append(G.nodes[node]["coord"][0] + 40)
        y.append(G.nodes[node]["coord"][1] + 40)
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

    if basemap:
        p.add_tile(tile_provider)
    else:
        p.background_fill_color = "black"

    p.legend.location = "top_left"
    p.legend.click_policy = "mute"
    p.legend.background_fill_alpha = 0.3
    p.legend.background_fill_color = "black"
    p.legend.label_text_color = "white"
    p.grid.visible = False
    p.axis.visible = False
    show(p)


def integrate(x, y):
    """Calculates the area under a curve

    :param x: An array of the x values of the curve
    :type x: list
    :param y: An array of the y values of the curve
    :type y: list
    :return: The area under the curve
    :rtype: float

    """
    sm = 0
    for i in range(1, len(x)):
        h = x[i] - x[i - 1]
        sm += h * (y[i - 1] + y[i]) / 2

    return sm
