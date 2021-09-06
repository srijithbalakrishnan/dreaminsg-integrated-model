import networkx as nx
from pathlib import Path
from infrarisk.src.network_recovery import *
from infrarisk.src.network_sim_models.integrated_network import *
import infrarisk.src.hazard_initiator as hazard
from infrarisk.src.network_sim_models.interdependencies import *
from infrarisk.src.optimizer import *
from shapely.geometry import Point, LineString
import os
class Event:
    """Class of different hazard types where the probability of failure of components reduces with distance from the point of occurrence of the event."""
    def __init__(
        self,
        name="Event",
        datapoints=100,
        explosion_datapoints=4,
        flood_datapoints=2,
        tornado_datapoints=2,
        hurricane_datapoints=2,
        radius_of_impact=[100,200],
        intensity=["moderate","high"], 
        buffer_impact=[100,200],
        point_of_occurrence_x=[5000,7000],
        point_of_occurrence_y=[4500,5500],
        minimum_data=5
    ): 
        """Initiates an Event object.
            :param name:  defaults to "Event"
            :type name: str, optional
            :param datapoints: No of datapoints to be generated
            :type datapoints: integer
            :type explosion_datapoints: ratio of explosion data to be generated
            :type explosion_datapoints:integer
            :param flood_datapoints: ratio of flood datapoints to be generated
            :type flood_datapoints:integer
            :type hurricane_datapoints: ratio of hurricane datapoints to be generated
            :type hurricane_datapoints:integer
            :param radius_of_impact: radius of impact in meters from the explosion type event 
            :type radius_of_impact: integer
            :param intensity: The intensity of the hazard using which the failure probability will be set. The intensity can be "extreme", "high", "moderate" or "low", defaults to "high"
            :type intensity: string, optional
            :param buffer_impact: buffer of impact in meters from the flood/hurricane type event 
            :type buffer_impact:integer
            :param point_of_occurrence_x;point_of_occurrence_y: events to be generated within x and y coordinates of integrated map
            :type point_of_occurrence_x;point_of_occurrence_y:integer
            :param minimum_data: minimum components needed to generate a csv file
            :type minimum_data:integer
        """
        self.name = name
        self.intensity = intensity
        self.radius_of_impact=radius_of_impact
        self.explosion_datapoints=explosion_datapoints
        self.tornado_datapoints=tornado_datapoints
        self.flood_datapoints=flood_datapoints
        self.hurricane_datapoints=hurricane_datapoints
        self.datapoints=datapoints
        self.buffer_impact=buffer_impact
        self.point_of_occurrence_x=point_of_occurrence_x
        self.point_of_occurrence_y=point_of_occurrence_y
        self.minimum_data=minimum_data
        self.datageneration()

    def datageneration(self):
        micropolis_network = IntegratedNetwork(name = 'Micropolis')
        MAIN_DIR = Path('')
        network_dir= 'infrarisk/data/networks/micropolis'
        water_file = MAIN_DIR/f'{network_dir}/water/water.inp'
        power_file = MAIN_DIR/f'{network_dir}/power/power.json'
        transp_folder = MAIN_DIR/f'{network_dir}/transportation/'
        #load all infrastructure networks
        micropolis_network.load_networks(water_file, power_file, transp_folder, power_sim_type = '3ph')
        micropolis_network.generate_integrated_graph()
        #initialising local variables
        count=0
        file_is_generated=0
        #generating explosion data
        try:
            for x in range (self.point_of_occurrence_x[0],self.point_of_occurrence_x[1],100):
                for y in range (self.point_of_occurrence_y[0],self.point_of_occurrence_y[1],100):
                    for radius_of_imp in (self.radius_of_impact):
                        for inten in (self.intensity):
                        
                            explosion = hazard.RadialDisruption(point_of_occurrence=(x, y), 
                                                                        radius_of_impact= radius_of_imp, 
                                                                        intensity = inten,
                                                                        name = "Micropolis explosion")
                            
                            no_of_datapoints=(self.datapoints/10)*self.explosion_datapoints                          
                            explosion.set_affected_components(micropolis_network.integrated_graph)
                            scenario_location = MAIN_DIR/network_dir/"scenarios"
                            #check if datapoints to be generated has reached or not
                            if(count > no_of_datapoints):
                                no_of_datapoints=0
                                count=0
                                raise StopIteration
                            file_is_generated=explosion.generate_disruption_file(location = scenario_location,minimum_data=self.minimum_data)                              
                            if (file_is_generated==1):
                                count=count+1
                                file_is_generated=0          
        except StopIteration:
            pass          
                    
        #generating flood data 
        try:
            for buff_imp in  range (self.buffer_impact[0],self.buffer_impact[1],5):
                for inten in (self.intensity):
                    flood = hazard.TrackDisruption(hazard_tracks = None, 
                                           buffer_of_impact = buff_imp, 
                                           time_of_occurrence=6000, 
                                           intensity = inten, 
                                           name = "Micropolis flood")
                    micropolis_flood_extents = [(self.point_of_occurrence_x[0], self.point_of_occurrence_y[0]), (self.point_of_occurrence_x[1], self.point_of_occurrence_y[1])    ]
                    flood_track = flood.generate_random_track(micropolis_flood_extents, shape = "line")
                    flood.set_hazard_tracks_from_linestring(flood_track)
                    flood.set_affected_components(micropolis_network.integrated_graph, plot_components=True)
                    scenario_location = MAIN_DIR/network_dir/"scenarios"
                    no_of_datapoints=(self.datapoints/10)*self.flood_datapoints  
                    if(count > no_of_datapoints):
                        no_of_datapoints=0
                        count=0
                        raise StopIteration                     
                    file_is_generated=flood.generate_disruption_file(location = scenario_location,minimum_data=self.minimum_data)
                    if (file_is_generated==1):
                        count=count+1
                        file_is_generated=0     
        except StopIteration:
            pass  
        
        #generating tornado data 
        try:
            for buff_imp in  range (self.buffer_impact[0],self.buffer_impact[1],5):
                for inten in (self.intensity):
                    tornado = hazard.TrackDisruption(hazard_tracks = None, 
                                           buffer_of_impact = buff_imp, 
                                           time_of_occurrence=6000, 
                                           intensity = inten, 
                                           name = "Micropolis tornado")
                    micropolis_tornado_extents = [(self.point_of_occurrence_x[0], self.point_of_occurrence_y[0]), (self.point_of_occurrence_x[1], self.point_of_occurrence_y[1])    ]
                    tornado_track = tornado.generate_random_track(micropolis_tornado_extents, shape = "line")
                    tornado.set_hazard_tracks_from_linestring(tornado_track)
                    tornado.set_affected_components(micropolis_network.integrated_graph, plot_components=True)
                    scenario_location = MAIN_DIR/network_dir/"scenarios"
                    no_of_datapoints=(self.datapoints/10)*self.tornado_datapoints     
                    if(count > no_of_datapoints):
                        no_of_datapoints=0
                        count=0
                        raise StopIteration                      
                    file_is_generated=tornado.generate_disruption_file(location = scenario_location,minimum_data=self.minimum_data)
                    if (file_is_generated==1):
                        count=count+1
                        file_is_generated=0   
        except StopIteration:
            pass  
            
        #generating hurricane data 
        try:        
            for buff_imp in  range (self.buffer_impact[0],self.buffer_impact[1],5):
                for inten in (self.intensity):
                    hurricane = hazard.TrackDisruption(hazard_tracks = None, 
                                           buffer_of_impact = buff_imp, 
                                           time_of_occurrence=6000, 
                                           intensity = inten, 
                                           name = "Micropolis hurricane")
                    micropolis_hurricane_extents = [(self.point_of_occurrence_x[0], self.point_of_occurrence_y[0]), (self.point_of_occurrence_x[1], self.point_of_occurrence_y[1])]
                    hurricane_track = hurricane.generate_random_track(micropolis_hurricane_extents, shape = "line")
                    hurricane.set_hazard_tracks_from_linestring(hurricane_track)                 
                    no_of_datapoints=(self.datapoints/10)*self.hurricane_datapoints                
                    hurricane.set_affected_components(micropolis_network.integrated_graph, plot_components=True)
                    scenario_location = MAIN_DIR/network_dir/"scenarios"
                    if(count > no_of_datapoints):
                        no_of_datapoints=0
                        count=0
                        raise StopIteration
                    file_is_generated=hurricane.generate_disruption_file(location = scenario_location,minimum_data=self.minimum_data)
                    if (file_is_generated==1):
                        count=count+1
                        file_is_generated=0               
        except StopIteration:
            pass 
                              
