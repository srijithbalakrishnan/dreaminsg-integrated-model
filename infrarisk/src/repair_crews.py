"""Repair crew classes"""


class WaterRepairCrew:
    """Water network repair crew class"""

    def __init__(self, name=None, init_loc=None, crew_size=None):
        """Initiates a water repair crew for the network recovery

        :param name: Name of the repair crew group, defaults to None
        :type name: string, optional
        :param init_loc: Name of the nearest transportation node from the initial location of the crew, defaults to None
        :type init_loc: string, optional
        :param crew_size: Size of the repair crew, defaults to None
        :type crew_size: integer, optional
        """
        self._name = name
        self._init_loc = init_loc
        self._crew_size = crew_size
        self.availability_status = 1
        self.components_repaired = []
        self.next_trip_start = None

        self.crew_loc = init_loc
        self.expertise = None  # undefined but can be used in future

    def reset_locs(self):
        """Resets the current location of the crew."""
        self.curr_loc = self._init_loc

    def set_next_trip_start(self, time):
        """Sets the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        self.next_trip_start = time

    def get_next_trip_start(self):
        """Returns the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        return self.next_trip_start

    def set_crew_loc(self, loc):
        """Sets the current location of the crew.

        :param loc: Name of the current location of the crew
        :type loc: string
        """
        self.crew_loc = loc

    def get_crew_loc(self):
        """Returns the current location of the crew.

        :return: Name of the current location of the crew
        :rtype: string
        """
        return self.crew_loc


class PowerRepairCrew:
    """Power network repair crew class"""

    def __init__(self, name=None, init_loc=None, crew_size=None):
        """Initiates a water repair crew for the network recovery

        :param name: Name of the repair crew group, defaults to None
        :type name: string, optional
        :param init_loc: Name of the nearest transportation node from the initial location of the crew, defaults to None
        :type init_loc: string, optional
        :param crew_size: Size of the repair crew, defaults to None
        :type crew_size: integer, optional
        """
        self._name = name
        self._init_loc = init_loc
        self._crew_size = crew_size
        self.availability_status = 1
        self.components_repaired = []
        self.next_trip_start = None

        self.crew_loc = init_loc
        self.expertise = None  # undefined but can be used in future

    def reset_locs(self):
        """Resets the current location of the crew."""
        self.curr_loc = self._init_loc

    def set_next_trip_start(self, time):
        """Sets the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        self.next_trip_start = time

    def get_next_trip_start(self):
        """Returns the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        return self.next_trip_start

    def set_crew_loc(self, loc):
        """Sets the current location of the crew.

        :param loc: Name of the current location of the crew
        :type loc: string
        """
        self.crew_loc = loc

    def get_crew_loc(self):
        """Returns the current location of the crew.

        :return: Name of the current location of the crew
        :rtype: string
        """
        return self.crew_loc


class TranspoRepairCrew:
    """Traffic network repair crew class"""

    def __init__(self, name=None, init_loc=None, crew_size=None):
        """Initiates a water repair crew for the network recovery

        :param name: Name of the repair crew group, defaults to None
        :type name: string, optional
        :param init_loc: Name of the nearest transportation node from the initial location of the crew, defaults to None
        :type init_loc: string, optional
        :param crew_size: Size of the repair crew, defaults to None
        :type crew_size: integer, optional
        """
        self._name = name
        self._init_loc = init_loc
        self._crew_size = crew_size
        self.availability_status = 1
        self.components_repaired = []
        self.next_trip_start = None

        self.crew_loc = init_loc
        self.expertise = None  # undefined but can be used in future

    def reset_locs(self):
        """Resets the current location of the crew."""
        self.curr_loc = self._init_loc

    def set_next_trip_start(self, time):
        """Sets the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        self.next_trip_start = time

    def get_next_trip_start(self):
        """Returns the next trip start time for the crew.

        :param time: Start time of the next trip start
        :type time: integer
        """
        return self.next_trip_start

    def set_crew_loc(self, loc):
        """Sets the current location of the crew.

        :param loc: Name of the current location of the crew
        :type loc: string
        """
        self.crew_loc = loc

    def get_crew_loc(self):
        """Returns the current location of the crew.

        :return: Name of the current location of the crew
        :rtype: string
        """
        return self.crew_loc
