class PLController:
    """A class of controllers"""

    def __init__(self, name, type, status=1):
        """Initiates a controller object

        :param name: The identifier of the controller
        :type name: string
        :param type: The type of the controller
        :type type: string
        :param status: The operational status of the controller, defaults to 1
        :type status: integer, optional
        """
        self._name = name
        self._type = type
        self._status = status
        self._sensors = {}
        self._actuators = {}

    def turn_off(self):
        """Turns off the controller"""
        self._status = 0

    def turn_on(self):
        """Turns on the controller"""
        self._status = 1

    def add_sensor(self, sensor, sensor_type):
        """Adds a sensor to the controller'sensor list

        :param sensor: The identifier of the sensor to be added
        :type sensor: string
        :param sensor_type: The type of the sensor
        :type sensor_type: string
        """

        self._sensors[sensor_type].append(sensor)

    def add_actuator(self, actuator, actuator_type):
        """Adds a actuator to the controller's actuator list

        :param actuator: The identifier of the actuator to be added
        :type actuator: string
        :param actuator_type: The type of the actuator
        :type actuator_type: string
        """
        self.actuators[actuator_type].append(actuator)

    def get_sensor_reading(self, sensor):
        """Sends a action triggering message to the sensor

        :param sensor: The identifier of the sensor
        :type sensor: string
        :param msg: The message to be sent
        :type msg: string
        """
        curr_sensor = self.sensors[sensor]
        curr_sensor.get_reading()

    # 1. trigger some action on the actuator


class WaterController(PLController):
    pass


class PowerController(PLController):
    pass


class TransportController(PLController):
    pass


# methods for the controller class
