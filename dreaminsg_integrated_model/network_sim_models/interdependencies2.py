import pandas as pd
import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo

water_dict = water.get_water_dict()
power_dict = power.get_power_dict()

#-------------------------------------------------------------------------------------------------#
#                               DEPENDENCY TABLE CLASS AND METHODS                                #
#-------------------------------------------------------------------------------------------------#

class DependencyTable:
    def __init__(self, table_type):
        """Initiates an empty dataframe to store node-to-node dependencies.

        Arguments:
            table_type {string} -- The type of the table (wp_table - water-power interdependencies, pt_table = power-transportation interdependencies, tw_table - transportation-water interdependencies)
        """
        if table_type == 'wp_table':
            self.table = pd.DataFrame(
                columns=['name', 'water_id', 'power_id', 'water_type', 'power_type'])
        elif table_type == 'pt_table':
            self.table = pd.DataFrame(
                columns=['name', 'power_id', 'transp_id', 'power_type', 'transp_type'])
        elif table_type == 'tw_table':
            self.table = pd.DataFrame(
                columns=['name', 'transp_id', 'water_id', 'transp_type', 'water_type'])
        else:
            print("Enter a valid dependency table type (wp_table - water-power interdependencies, pt_table = power-transportation interdependencies, tw_table - transportation-water interdependencies).")

    #Water-Power interdependencies
    def add_pump_motor_coupling(self, name, water_id, power_id, motor_mw, pm_efficiency=1):
        """Creates a pump-on-motor dependency entry in the dependency table.

        Arguments:
            name {string} -- The user-defined name of the dependency. This name will be used to call the dependency objects during simulation.
            water_id {string} -- The name of the pump in the water network model.
            power_id {string} -- The name of the motor in the power systems model.
            motor_mw {float} -- The rated power of the motor in MegaWatts.
            pm_efficiency {float} -- motor-to-pump efficiency.

        Returns:
            pandas dataframe -- The modified power-water dependency table
        """
        water_type = get_water_type(water_id)
        power_type = get_power_type(power_id)
        #PumpOnMotorDep(name, water_id, power_id, motor_mw, pm_efficiency)
        self.table = self.table.append({
            'name'      : name,
            'water_id'  : water_id,
            'power_id'  : power_id,
            'water_type': water_type,
            'power_type': power_type},
            ignore_index=True)

    def add_gen_reserv_coupling(self, name, water_id, power_id, gen_mw, gr_efficiency):
        """Creates a generator-on-reservoir dependency entry in the dependency table.

        Arguments:
            name {string} -- The user-defined name of the dependency. This name will be used to call the dependency objects during simulation.
            water_id {string} -- The name of the reservoir in the water network model.
            power_id {string} -- The name of the generator in the power systems model.
            gen_mw {float} -- The generator capacity in megawatts.
            gr_efficiency {float} -- Generator efficiency in fractions.
        """
        water_type = get_water_type(water_id)
        power_type = get_power_type(power_id)
        #GeneratorOnReservoirDep(name = name, water_id, pump_id, gen_mw, gr_efficiency)
        self.table = self.table.append({
            'name': name,
            'water_id': water_id,
            'power_id': power_id,
            'water_type': water_type,
            'power_type': power_type},
            ignore_index=True)

    #Power-Transportation and  Interdependencies
    def add_access_to_water_node(self, water_compon):
        """Create a mapping to nearest road link from the water network component.

        Arguments:
            water_component {string} -- The name of the water network component.
        """
        pass

#-------------------------------------------------------------------------------------------------#
#                                           DEPENDENCY CLASSES                                    #
#-------------------------------------------------------------------------------------------------#

class Dependency:
    """A class of infrastructure dependencies.
    """

    def __init__(self, name):
        self.name = name

class PumpOnMotorDep(Dependency):
    """A class of pump-on-motor dependencies. Inherited from the Dependency superclass.

    Arguments:
        Dependency {class} -- Dependency class.
    """
    def __init__(self, name, start_id, end_id, motor_mw, pm_efficiency=1):
        self.name = name
        self.pump_id = start_id
        self.motor_id = end_id
        self.pm_efficiency = pm_efficiency

        def modify_pump_power(self, motor_mw):
            self.pump_power = motor_mw*1000*pm_efficiency

class GeneratorOnReservoirDep(Dependency):
    """A class of generator-on-reservoir dependencies. Inherited from the Dependency superclass.

    Arguments:
        Dependency {class} -- Dependency class.
    """
    def __init__(self, name, start_id, end_id, reserv_head, flowrate, gen_efficiency=1):
        self.name = name
        self.generator_id = start_id
        self.reservoir_id = end_id
        self.generator_power = 10*gen_efficiency*reserv_head*flowrate

#-------------------------------------------------------------------------------------------------#
#                                   MISCELLANEOUS FUNCTIONS                                       #
#-------------------------------------------------------------------------------------------------#

def get_water_type(compon_name):
    """Returns type of water network component

    Arguments:
        compon_name {string} -- Name of the infrastructure component in the respective infrastructure network model.

    Returns:
        string -- The type of the water network component.
    """
    water_type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            water_type = "".join([water_type, char])
    return water_dict[water_type]


def get_power_type(compon_name):
    """Returns the type of power systems component

    Arguments:
        compon_name {string} -- [description]

    Returns:
        string -- The type of the power systems component.
    """
    power_type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            power_type = "".join([power_type, char])
    return power_dict[power_type]
