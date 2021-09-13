from abc import ABC, abstractmethod


class Strategy(ABC):
    """This is an abstract class for recovery strategies."""

    @abstractmethod
    def __init__(self, name, repair_compons=None):
        self.name = name
        if repair_compons is None:
            self.repair_compons = None
            print("Repair components need to be set later.")
        else:
            self.repair_compons = self.set_repair_compons(repair_compons)

    @abstractmethod
    def set_repair_compons(self, repair_compons):
        self.repair_compons = repair_compons

    @abstractmethod
    def set_repair_order(self):
        pass


class CentralityStrategy(Strategy):
    """Based on betweenness centrality of the components multiplied by capacity. Break ties randomly."""

    pass


class CrewDistanceStrategy(Strategy):
    """Based on the distance between the component and the crew location. Break ties randomly."""

    pass


class ComponentPriorityStrategy(Strategy):
    """Based on the predetermined priority for different components"""

    pass


class JointStrategy(Strategy):
    """Optimized strategy. Capture interdependencies somehow if exist. Not an immediate priority"""

    pass
