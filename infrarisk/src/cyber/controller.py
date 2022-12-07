import infrarisk.src.physical.interdependencies as interdependencies


class PLController:
    """A class of controllers"""

    def __init__(self, name, status=1):
        """Initiates a controller object

        :param name: The identifier of the controller
        :type name: string
        :param status: The operational status of the controller, defaults to 1
        :type status: integer, optional
        """
        self._name = name
        self._status = status
        self._tank_level_sensors = {}
        self._pump_actuators = {}
        self._tank_discharge_actuators = {}

    def turn_off(self):
        """Turns off the controller"""
        self._status = 0

    def turn_on(self):
        """Turns on the controller"""
        self._status = 1


class WaterController(PLController):
    def __init__(self, id, name, type="water_plc", status=1):
        super().__init__(name, status)
        self._type = type
        self._id = id

    def get_sensor_reading(self, tank_sensor, wn_results, wn, error_factor=1):
        """Sends a action triggering message to the sensor

        :param sensor: The identifier of the sensor
        :type sensor: string
        :param wn_results: The water network results object
        :type wn_results: wntr results object
        """
        curr_sensor = tank_sensor

        if self._status == 1:
            if curr_sensor._status == 1:
                curr_sensor.update_curr_tank_level(wn_results, wn)
                curr_sensor.update_curr_tank_level(wn_results, wn, error_factor)
                tank_reading = curr_sensor.get_curr_tank_level()
                return tank_reading
            else:
                print("The sensor is not operational")
        else:
            print("The controller is not operational")

    def trigger_pump_actuator(self, tank_sensor, pump_actuator, wn, sim_time):
        """Trigger pump actuator based on the sensor reading

        :param actuator: The identifier of the actuator
        :type actuator: string
        :param wn: The water network object
        :type wn: wntr water network object
        """
        curr_sensor = tank_sensor
        curr_actuator = pump_actuator
        print(
            "Current level: ",
            curr_sensor._tank_level,
            " Maximum level: ",
            curr_sensor._max_tank_level,
            " Minimum level: ",
            curr_sensor._min_tank_level,
        )
        if self._status == 1:
            if curr_sensor._tank_level <= curr_sensor._min_tank_level:
                curr_actuator.turn_on_pump(wn, sim_time)
                print("Added a pump turn on control action")
            elif curr_sensor._tank_level >= curr_sensor._max_tank_level:
                curr_actuator.turn_off_pump(wn, sim_time)
                print("Added a pump turn off control action")
        else:
            print("The controller is not operational")

    def trigger_discharge_pipe_actuator(
        self, tank_sensor, discharge_pipe_actuator, wn, sim_time
    ):
        """Trigger pump actuator based on the sensor reading

        :param actuator: The identifier of the actuator
        :type actuator: string
        :param wn: The water network object
        :type wn: wntr water network object
        """
        curr_sensor = tank_sensor
        curr_actuator = discharge_pipe_actuator
        print(
            "Current level: ",
            curr_sensor._tank_level,
            " Maximum level: ",
            curr_sensor._max_tank_level,
            " Minimum level: ",
            curr_sensor._min_tank_level,
        )
        if self._status == 1:
            if curr_sensor._tank_level <= curr_sensor._max_tank_level:
                curr_actuator.turn_off_discharge(wn, sim_time)
                print("Added a discharge pipe turn off control action")
            elif curr_sensor._tank_level >= curr_sensor._max_tank_level:
                curr_actuator.turn_on_discharge(wn, sim_time)
                print("Added a discharge pipe turn on control action")
        else:
            print("The controller is not operational")

    # SENSORS
    def add_tank_level_sensor(self, sensor_name, sensor):
        """Adds a sensor to the controller'sensor dictionary

        :param sensor: The sensor object
        :type sensor: object
        """
        self._tank_level_sensors[sensor_name] = sensor

    # ACTUATORS
    def add_pump_actuator(self, actuator_name, actuator):
        """Adds a actuator to the controller's actuator dictionaty

        :param actuator: The actuator to be added to the actuator disctionary
        :type actuator: object
        """
        self._pump_actuators[actuator_name] = actuator

    def add_tank_discharge_actuator(self, actuator_name, actuator):
        """Adds a actuator to the controller's actuator dictionaty

        :param actuator: The actuator to be added to the actuator disctionary
        :type actuator: object
        """
        self._tank_discharge_actuators[actuator_name] = actuator


class PowerController(PLController):
    pass


class TransportController(PLController):
    pass


# methods for the controller class
