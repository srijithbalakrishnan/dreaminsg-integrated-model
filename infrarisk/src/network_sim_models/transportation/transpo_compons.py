class Link:
    """
    Class for network links.  As currently written, assumes costs are calculated as the
    sum of three factors:
       1. Travel time, computed via the BPR function
       2. Toll cost, the product of toll and network.tollFactor
       3. Distance-related costs, the product of length and network.distanceFactor
    """

    def __init__(
        self,
        network,
        tail,
        head,
        capacity=99999,
        length=99999,
        freeFlowTime=99999,
        fft_base=99999,
        alpha=0.15,
        beta=4,
        speedLimit=99999,
        toll=0,
        linkType=0,
    ):
        """
        Initializer for links; note default values for parameters if not specified.
        For the classic traffic assignment problem speedLimit and linkType do  not
        have any impact (and length and toll are only relevant if a distanceFactor
        or tollFactor are specified).
        """
        self.network = network
        self.tail = tail
        self.head = head
        self.capacity = capacity
        self.length = length
        self.freeFlowTime = freeFlowTime
        self.fft_base = fft_base
        self.alpha = alpha
        self.beta = beta
        self.speedLimit = speedLimit
        self.toll = toll
        self.linkType = linkType
        self.sortKey = (
            tail * network.numLinks + head
        )  # makes for easy sorting in forward star order

    def calculateCost(self):
        """
        Calculates the cost of the link using the BPR relation, adding in toll and
        distance-related costs.
        This cost is returned by the method and NOT stored in the cost attribute.
        """
        vcRatio = self.flow / self.capacity
        # Protect against negative flows, 0^0 errors.
        if vcRatio <= 0:
            return (
                self.freeFlowTime
                + self.toll * self.network.tollFactor
                + self.length * self.network.distanceFactor
            )
        travelTime = self.freeFlowTime * (1 + self.alpha * pow(vcRatio, self.beta))
        return (
            travelTime
            + self.toll * self.network.tollFactor
            + self.length * self.network.distanceFactor
        )

    def calculateBeckmannComponent(self):
        """
        Calculates the integral of the BPR function for the link, for its
        contribution to the sum in the Beckmann function.
        """
        vcRatio = self.flow / self.capacity
        # Protect against negative flows, 0^0 errors.
        if vcRatio <= 0:
            return 0
        return self.flow * (
            self.toll * self.network.tollFactor
            + self.length * self.network.distanceFactor
            + self.freeFlowTime
            * (1 + self.alpha / (self.beta + 1) * pow(vcRatio, self.beta))
        )

    def updateCost(self):
        """
        Same as calculateCost, except that the link.cost attribute is updated as well.
        """
        self.cost = self.calculateCost()


class Node:
    def __init__(self, isZone=False):
        self.forwardStar = list()
        self.reverseStar = list()
        self.isZone = isZone
        self.name = None


class OD:
    def __init__(self, origin, destination, demand=0):
        self.origin = origin
        self.destination = destination
        self.demand = demand


class Path:
    """
    A Path is an ordered sequence of adjacent links; these are expressed in the
    attribute 'links', which is a tuple of link IDs.  Other attributes are as
    follows:
       network points to the parent Network class (needed for calculating costs)
       flow is the number of vehicles using this path
       cost is the total cost of the path
    """

    def __init__(self, links, network, flow=0):
        self.links = links
        self.network = network
        self.flow = flow
        self.updateCost()

    def calculateCost(self):
        """
        Calculates the cost of the path by summing the cost of its constituent links.
        This cost is returned by the method and NOT stored in the cost attribute.
        """
        cost = 0
        for ij in self.links:
            cost += self.network.link[ij].cost
        return cost

    def updateCost(self):
        """
        Same as calculateCost, except that the path.cost attribute is updated as well.
        """
        self.cost = self.calculateCost()


def get_transpo_dict():
    transpo_dict = {
        "J": {
            "code": "node",
            "name": "Junction",
            "connect_field": ["name"],
            "repair_time": 24,
        },
        "L": {
            "code": "link",
            "name": "Link",
            "connect_field": ["head", "tail"],
            "repair_time": 24,
        },
    }

    return transpo_dict
