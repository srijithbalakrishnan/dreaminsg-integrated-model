"""Functions to generate the infrastructure networks used for simulation."""

import wntr
import pandapower as pp
import os

os.system("cls")


def generate_watern(file_name):
    """Generates a water network using the wntr package and saves it to local directory.

    :param file_name: Name of the inp file to be saved including path
    :type file_name: string
    """
    wn = wntr.network.WaterNetworkModel()

    # Demand patterns
    pd_1 = [
        0.1,
        0.1,
        0.1,
        0.1,
        0.2,
        0.2,
        0.3,
        0.4,
        0.5,
        0.7,
        0.8,
        0.7,
        0.7,
        0.6,
        0.6,
        0.7,
        0.7,
        0.8,
        0.7,
        0.8,
        0.6,
        0.5,
        0.2,
        0.1,
    ]

    # Add reservoir
    wn.add_reservoir("W_R1", base_head=15, head_pattern=None, coordinates=(0, 500))

    # Add tank
    wn.add_tank(
        "W_T1",
        elevation=10,
        init_level=3,
        min_level=0,
        max_level=5,
        diameter=15,
        coordinates=(400, 500),
    )

    # Add juntions
    wn.add_junction(
        "W_J1",
        base_demand=0.005,
        demand_pattern="pd_1",
        elevation=20,
        coordinates=(200, 600),
    )
    wn.add_junction(
        "W_J2",
        base_demand=0.005,
        demand_pattern="pd_1",
        elevation=0,
        coordinates=(300, 450),
    )
    wn.add_junction(
        "W_J3",
        base_demand=0.002,
        demand_pattern="pd_1",
        elevation=0,
        coordinates=(200, 300),
    )
    wn.add_junction(
        "W_J4",
        base_demand=0.008,
        demand_pattern="pd_1",
        elevation=0,
        coordinates=(300, 300),
    )
    wn.add_junction(
        "W_J5",
        base_demand=0.050,
        demand_pattern="pd_1",
        elevation=0,
        coordinates=(500, 300),
    )
    wn.add_junction(
        "W_J6",
        base_demand=0.020,
        demand_pattern="pd_1",
        elevation=1,
        coordinates=(200, 0),
    )
    wn.add_junction(
        "W_J7",
        base_demand=0.030,
        demand_pattern="pd_1",
        elevation=0,
        coordinates=(500, 0),
    )

    # Add pipes
    wn.add_pipe(
        "W_P3",
        "W_J1",
        "W_J2",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P4",
        "W_J2",
        "W_T1",
        length=1000,
        diameter=0.2,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P5",
        "W_J1",
        "W_J3",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P6",
        "W_J2",
        "W_J4",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P7",
        "W_J3",
        "W_J4",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P8",
        "W_J4",
        "W_J5",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P9",
        "W_J3",
        "W_J6",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P10",
        "W_J5",
        "W_J7",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )
    wn.add_pipe(
        "W_P11",
        "W_J6",
        "W_J7",
        length=1000,
        diameter=0.4,
        roughness=100,
        minor_loss=0,
        status="OPEN",
    )

    # Add pump
    wn.add_pump(
        "W_WP1",
        "W_R1",
        "W_J1",
        pump_type="POWER",
        pump_parameter=50,
        speed=1,
        pattern=None,
    )
    # plot
    # nodes, edges = wntr.graphics.plot_network(wn)
    # plt.show()

    # save to directory
    wn.write_inpfile(file_name, version=2.2)
    print("Water network successfully saved to directory!")


def generate_powern(file_name):
    """Generates a power system network using the pandapower package and saves it to local directory.

    :param file_name: Name of the json file to be saved including path.
    :type file_name: string
    """
    pn = pp.create_empty_network(
        name="sample_network", f_hz=50.0, sn_mva=1, add_stdtypes=True
    )

    # Buses
    bus8 = pp.create_bus(
        pn, vn_kv=10, name="P_B8", geodata=(100, 250), type="b", zone="NW"
    )
    bus7 = pp.create_bus(
        pn, vn_kv=110, name="P_B7", geodata=(200, 350), type="b", zone="NE"
    )
    bus5 = pp.create_bus(
        pn, vn_kv=10, name="P_B5", geodata=(100, 0), type="b", zone="SE"
    )
    bus4 = pp.create_bus(
        pn, vn_kv=10, name="P_B4", geodata=(400, 0), type="b", zone="SW"
    )
    bus6 = pp.create_bus(
        pn, vn_kv=110, name="P_B6", geodata=(200, 550), type="b", zone="C"
    )
    bus2 = pp.create_bus(
        pn, vn_kv=110, name="P_B2", geodata=(400, 275), type="b", zone="NE"
    )
    bus3 = pp.create_bus(
        pn, vn_kv=10, name="P_B3", geodata=(400, 225), type="b", zone="NE"
    )
    bus1 = pp.create_bus(
        pn, vn_kv=110, name="P_B1", geodata=(400, 550), type="b", zone="NE"
    )
    bus9 = pp.create_bus(
        pn, vn_kv=110, name="P_B9", geodata=(200, 250), type="b", zone="NE"
    )
    # print(pn.bus)

    # External grid connections
    pp.create_ext_grid(pn, bus1, name="P_EG1", vm_pu=1.02, va_degree=50)
    # print(pn.ext_grid)

    # Transformers
    transf1 = pp.create_transformer(
        pn, bus9, bus8, name="P_TF1", std_type="63 MVA 110/10 kV"
    )
    transf2 = pp.create_transformer(
        pn, bus2, bus3, name="P_TF2", std_type="63 MVA 110/10 kV"
    )
    # print(pn.trafo)

    # Lines
    line1 = pp.create_line(
        pn,
        bus1,
        bus2,
        length_km=5,
        std_type="N2XS(FL)2Y 1x120 RM/35 64/110 kV",
        name="P_L1",
    )
    line2 = pp.create_line(
        pn, bus3, bus4, length_km=2, std_type="NA2XS2Y 1x70 RM/25 6/10 kV", name="P_L2"
    )
    line3 = pp.create_line(
        pn, bus4, bus5, length_km=5, std_type="NA2XS2Y 1x70 RM/25 6/10 kV", name="P_L3"
    )
    line4 = pp.create_line(
        pn,
        bus1,
        bus6,
        length_km=5,
        std_type="N2XS(FL)2Y 1x120 RM/35 64/110 kV",
        name="P_L4",
    )
    line5 = pp.create_line(
        pn,
        bus6,
        bus7,
        length_km=5,
        std_type="N2XS(FL)2Y 1x120 RM/35 64/110 kV",
        name="P_L5",
    )
    # print(pn.line)

    # Swtiches
    switch1 = pp.create_switch(
        pn, bus7, bus9, et="b", type="CB", closed=True, name="P_S1"
    )

    # Loads
    pp.create_load(pn, bus5, p_mw=2, q_mvar=4, scaling=1, name="P_LO1")
    pp.create_load(pn, bus4, p_mw=2, q_mvar=4, scaling=1, name="P_LO2")
    pp.create_load(pn, bus6, p_mw=2, q_mvar=4, scaling=1, name="P_LO3")
    # print(pn.load)

    # Pump
    MP1 = pp.create_motor(pn, bus8, pn_mech_mw=0.23, cos_phi=0.8, name="P_MP1")
    # print(pn.motor)

    # Generator
    # G = pp.create_gen(pn, bus8, p_mw=0.25, vm_pu=1.02, name = "P_G1")
    # save to directory
    pp.to_json(pn, file_name)
    print("Power systems network successfully saved to directory!")

    # pp.diagnostic(pn)


# generate networks one by one
# generate_watern("dreaminsg_integrated_model/data/networks/water/Example_water.inp")
generate_powern("dreaminsg_integrated_model/data/networks/in2/power/power.json")
