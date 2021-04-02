class Path:
   """
   A Path is an ordered sequence of adjacent links; these are expressed in the
   attribute 'links', which is a tuple of link IDs.  Other attributes are as
   follows:
      network points to the parent Network class (needed for calculating costs)
      flow is the number of vehicles using this path
      cost is the total cost of the path
   """

   def __init__(self, links, network, flow = 0):
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
      