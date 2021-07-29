from abc import ABC, abstractmethod


class Disaster(ABC):
    """The Disaser class defines an interface to a disaster scenario with specific characteristics."""

    @abstractmethod
    def __init__(self, point_of_occurrence=None, radius_of_impact=None):
        pass

    @abstractmethod
    def generate_hazard_map(self):
        pass

    @abstractmethod
    def generate_infra_disruptions(self, probability_dict):
        pass


class RadialDisruption(Disaster):
    """Class of disaster where the probability of failure of components reduces with distance from the point of occurrence"""

    def __init__(self, point_of_occurrence=None, radius_of_impact=None):
        """Initiates a RadialDisruption object

        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float, optional
        """
        if point_of_occurrence == None:
            self.point_of_occurrence = None
        else:
            self.set_point_of_occurrence(point_of_occurrence)

        if radius_of_impact == None:
            self.radius_of_impact = None
        else:
            self.set_radius_of_impact(radius_of_impact)

    def set_point_of_occurrence(self, point_of_occurrence):
        """Sets the point of occurrence of the radial disruption.

        :param point_of_occurrence: The central point (represented by a tuple of longitude and latitude) of the disruptive event, defaults to None
        :type point_of_occurrence: tuple, optional
        """
        if isinstance(point_of_occurrence, tuple):
            self.point_of_occurrence = point_of_occurrence
        else:
            print(
                "Point of occurrence was not set. Point of occurrence needs to be a tuple."
            )

    def set_radius_of_impact(self, radius_of_impact):
        """Sets the radius of the radial disruption.

        :param radius_of_impact: The radius of the impact (he probability of failure at the curcumferance reacher zero) in metres., defaults to None
        :type radius_of_impact: float, optional
        """
        if isinstance(radius_of_impact, float):
            self.radius_of_impact = radius_of_impact
        else:
            print("Radius of impact was not set. Radius of impact needs to be a float.")

    def generate_hazard_map(self):
        pass

    def generate_infra_disruptions(self, probability_dict):
        pass
