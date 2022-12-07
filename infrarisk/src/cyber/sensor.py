import infrarisk.src.physical.interdependencies as interdependencies


class Sensor:
    """A class of sensors"""

    def __init__(self, name, status=1):
        """Initiates a sensor object

        :param name: The identifier of the sensor
        :type name: string
        :param status: The operational status of the sensor, defaults to 1
        :type status: integer, optional
        """
        self._name = name
        self._status = status


# water level sensor - measure water level in the tank


class WaterTankLevelSensor(Sensor):
    """A class of sensors for obtaining the level of water in tanks"""

    def __init__(
        self, name, tank_id, controller_id, type="Water tank sensor", status=1
    ):
        """Initiates a water tank level sensor object

        :param name: The identifier of the sensor
        :type name: string
        :param tank_id: The identifier of the tank
        :type tank_id: string
        :param type: The type of the sensor, defaults to "Water tank sensor"
        :type type: string, optional
        :param status: The operational status of the sensor, defaults to 1
        :type status: integer, optional
        """
        super().__init__(name, status)
        self._tank_id = tank_id
        self._type = type
        self._id = self._id = interdependencies.get_compon_details(tank_id)[4]
        self._controller_id = controller_id
        self._tank_level = None
        self._min_tank_level = None
        self._max_tank_level = None

    def set_tank_thresholds(self, min_level, max_level):
        """Sets the minimum and maximum water levels in a tank

        :param min_level: The minimum water level in the tank, defaults to None
        :type min_level: float, optional
        :param max_level: The maximum water level in the tank, defaults to None
        :type max_level: float, optional
        """
        self._min_tank_level = min_level
        self._max_tank_level = max_level

    def update_curr_tank_level(self, wn_results, wn, error_factor=1):
        """Updates the current water level in a tank

        :param wn_results: The results of the water network simulation
        :type wn_results: wntr water network results object
        :param wn: The water network object
        :type wn: wntr water network object
        :param error_factor: The sensor error factor, defaults to 1
        :type error_factor: float, optional
        """
        if self._status == 1:
            self._tank_level = error_factor * (
                wn_results.node["head"][self._tank_id].to_list()[-1]
                - wn.get_node(self._tank_id).elevation
            )
            # print(
            #     f"The current level of water in the tank is {round(self._tank_level, 3)}m"
            # )
        else:
            print("The sensor is not operational")

    def get_curr_tank_level(self):
        """Returns the current water level in a tank"""
        return self._tank_level
