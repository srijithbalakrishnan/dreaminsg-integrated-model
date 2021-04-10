"""Functions to generate and save disruptive scenaios"""

import pandas as pd
import numpy as np
import random
import dreaminsg_integrated_model.network_sim_models.interdependencies as interdependencies


class DisruptionAndRecovery():
    def __init__(self, scenario_file, sim_time, sim_step, curr_loc_crew):
        self.disruptive_events = pd.read_csv(scenario_file, sep=",")
        #print(self.disruptive_events)

        self.sim_time = sim_time
        self.sim_step = sim_step
        self.next_crew_trip_start = min(self.disruptive_events.time_stamp)
        self.next_recov_scheduled = False #Flag to identify when the cre must stop at a point and schedule next recovery
        self.curr_loc_crew = curr_loc_crew

        self.distrupted_components = self.disruptive_events.components
        
        column_list = ["time_stamp"] + [component for component in self.distrupted_components]
        self.event_table = pd.DataFrame(columns=column_list)
        self.event_table["time_stamp"] = np.arange(
            0, self.sim_time, self.sim_step)
        
        for component in self.distrupted_components:
            self.event_table[component] = 100 #initial performance level

            failure_start = self.disruptive_events[self.disruptive_events["components"] == component].time_stamp.item()
            #print(failure_start)
            failure_start_index = int(failure_start/self.sim_step)
            self.event_table[component][failure_start_index:] = 100 - self.disruptive_events[
                self.disruptive_events["components"] == component].fail_perc.item() #disrupted performance level

    def schedule_recovery(self, component, recovery_start, recovery_rate):
        recovery_start_index = self.event_table.time_stamp[self.event_table.time_stamp == recovery_start].index.to_list()[0]
        start_perf = self.event_table[component].iloc[recovery_start_index]

        for index, row in self.event_table.iloc[recovery_start_index:].iterrows():
            self.event_table.loc[index, component] = min(100, start_perf + recovery_rate*(row["time_stamp"] - recovery_start))
            #print(self.event_table.loc[index, component])
            while (self.event_table.loc[index, component] == 100) & (self.next_recov_scheduled == False):
                self.curr_loc_crew = component
                self.next_crew_trip_start = row["time_stamp"]
                print("The repair action at {} successfuly completed at time {} minutes\n".format(component, row["time_stamp"]/self.sim_step))
                self.next_recov_scheduled = True
        self.next_recov_scheduled = False

    def optimze_recovery_strategy(self):
        repair_order = list(self.distrupted_components)
        random.shuffle(repair_order)
        return repair_order
    
    def update_directly_affected_components(self, pn, wn, time_index):    
        for index, component in enumerate(self.distrupted_components):
            compon_infra = interdependencies.get_infra_type(component)
            if compon_infra == "power":
                compon_code, compon_type, compon_name = interdependencies.get_power_type(component)
                compon_index = pn[compon_type].query(
                    'name == "{}"'.format(component)).index.item()
                if (self.event_table.loc[time_index, component] < 100):
                    pn[compon_type].at[compon_index, 'in_service'] = False
                else:
                    pn[compon_type].at[compon_index, 'in_service'] = True
