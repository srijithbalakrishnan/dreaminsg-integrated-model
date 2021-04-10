"""Main module."""
import numpy as np
import pandas as pd
import os
from pathlib import Path

import dreaminsg_integrated_model.network_sim_models.interdependencies as interdependencies
import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo

import dreaminsg_integrated_model.results.figures.plots as plots

def main():
    os.system('cls')

    #get info of current working directory
    cwd = os.getcwd()

    EXAMPLES_DIR = Path('dreaminsg_integrated_model/data/networks/')
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    #load water_network model
    wn = water.load_water_network(EXAMPLES_DIR/'water/Example_water.inp')

    #load power systems network
    pn = power.load_power_network(EXAMPLES_DIR/'power/Example_power.json')

    # #load dynamic traffic assignment model
    transp_folder = EXAMPLES_DIR/'transportation/Example1'
    tn = transpo.Network(
        "{}/example_net.tntp".format(transp_folder), "{}/example_trips.tntp".format(transp_folder))
    tn.userEquilibrium("FW", 400, 1e-4, tn.averageExcessCost)
    stt_1_9 = tn.calculateShortestTravelTime(2,9)
    print("The shortest travel time between 2 and 9 is {} minutes".format(round(stt_1_9),2))
    #Build Interdependencies
    #water to power dependencies
    pw_dep_table = interdependencies.DependencyTable('wp_table')
    pw_dep_table.add_pump_motor_coupling(
        pw_dep_table, name='P2M1', water_id='WP1', power_id='MP1', motor_mw=pn.motor.pn_mech_mw[pn.motor.name == 'MP1'].values[0], pm_efficiency=1.0)

    pw_dep_table.add_gen_reserv_coupling(
        pw_dep_table, name='G2R1', water_id='R1', power_id='G3', gen_mw=1, gr_efficiency=1.0)
    print(pw_dep_table)

    #SIMULATION
    # creating test case dataframe
    disrupt_points = pd.read_csv('dreaminsg_integrated_model/data/disruptive_scenarios/test1/motor_failure.csv')
    test = pd.DataFrame(columns=['time', 'motor_pw_factor'])
    test.time = np.arange(0, 100)
    test.motor_pw_factor = np.interp(
        np.arange(100), disrupt_points.time_stamp, disrupt_points.motor1_break)
    #print(test.motor_pw_factor.values)

    #simulating the netwokwide impacts
    for index, row in test.iterrows():
        #Set motor power level in the power systems model
        pn.motor.pn_mech_mw = test.motor_pw_factor[index]*0.23

        #run power systems model
        power.run_power_simulation(pn)

        #Fix the time until which the wntr model should run in this iteration
        wn.options.time.duration = 864*(index)

        #set the pump power value based on motor power value
        # pump_power = pn.res_bus.iloc[0, 2]*1000
        # wn.get_link('WP1').power = pump_power
        #print(pw_dep_table)

        #run water distribution model and save current status
        wn_results = water.run_water_simulation(wn, 864)
        #print(wn_results.link['flowrate'])
        #print(wn_results.node['pressure'])
        # wn_plot = plots.water_net_plots(wn, wn_results)
        # wn_plot.savefig('disruptive_scenarios/test1/water_plots/time{}.jpg'.format(index))
        # wn_plot.close()

        #transportation.dta_matlab_model(transp_folder)
        #print('Iteration {} completed successfully!'.format(index))


if __name__ == '__main__':
    main()
