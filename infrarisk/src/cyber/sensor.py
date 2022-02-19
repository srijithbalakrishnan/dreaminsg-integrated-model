class Sensor:
    """A class of sensors"""

    def __init__(self, name, type, status=1):
        """Initiates a sensor object

        :param name: The identifier of the sensor
        :type name: string
        :param type: The type of the sensor
        :type type: string
        :param status: The operational status of the sensor, defaults to 1
        :type status: integer, optional
        """
        self._name = name
        self._type = type
        self._status = status


# water level sensor - measure water level i nthe tank
