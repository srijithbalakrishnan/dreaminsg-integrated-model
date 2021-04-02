# Sioux Falls Network


WARNING: The Sioux-Falls network is not considered as a realistic one.  However, this network was used in many publications. It is good for code debugging.

## Source / History

Via: [http://www.bgu.ac.il/~bargera/tntp/](http://www.bgu.ac.il/~bargera/tntp/)

All network data including the link numbers indicated on the map (but excluding node coordinates), are taken from the following paper: “An efficient approach to solving the road network equilibrium traffic assignment problem” by LeBlanc, L.J., Morlok, E.K., Pierskalla, W.P., Transportation Research Vol. 9, pp. 309-318, 1975. The links in the network file are sorted by their tail node, thus they do not follow the same order as the original publication. OD flows in the original paper (Table 1) are given in thousands of vehicles per day, with integer values up to 44. OD flows here are the values form the table multiplied by 100. They are therefore 0.1 of the original daily flows, and in that sense might be viewed as approximate hourly flows. This conversion was done to enable comparison of objective values with papers published during the 1980's and the 1990's. The units of free flow travel times are 0.01 hours, but they are often viewed as if they were minutes. Link lengths are set arbitrarily equal to free flow travel times. The parameters in the paper are given in the format of `t=a+b*flow^4`. The original parameter a is the free flow travel time given here. The original parameter b is equal to (free flow travel time)*B/(capacity^Power) in the format used here. In the data here the “traditional” BPR value of B=0.15 is assumed, and the given capacities are computed accordingly. Node coordinates were generated artificially to reproduce the diagram shown in the paper.

[Walter Wong](mailto://kiwong@mail.nctu.edu.tw) points out that another version of the Sioux-Falls network appears in a different publication, “An algorithm for the Discrete Network,” LeBlanc, L.J., Transportation Science, Vol 9, pp 183-199, 1975. The difference between the two versions is that the free-flow travel times on links 15-19, 19-15, 15-22 and 22-15 are 4 instead of 3, and the free-flow travel time on links 10-16 and 16-10 are 5 instead of 4.
 
[Andrew Koh](mailto://atmkoh@yahoo.co.uk) reports that a third version of the Sioux-Falls network has appeared in “Equilibrium Decomposed Optimization: A Heuristic for the Continuous Equilibrium Network Design Problem,” Suwansirikul, C., Friesz, T.L., Tobin, R.L.,  Transportation Science, Vol. 21(4), 1987, pp. 254-263. Click here for a list of differences  between the two versions.
 
[Gregor Laemmel](mailto://laemmel@vsp.tu-berlin.de) reports that the first published version of the Sioux-Falls network appears in "Development and Application of a Highway Network Design Model - Volumes 1 and 2," Morlok, E.K., Schofer, J.L., Pierskalla, Marsten, R.E., W.P., Agarwal, S.K., Stoner, J.W., Edwards, J.L., LeBlanc, L.J., and Spacek, D.T., Final Report to the Federal Highway Administration under contract number DOT-FH-11-7862, Department of Civil Engineering, Northwestern University, Evanston, Illinois, July 1973. Link lengths (in miles) are given the following file: Sioux-Falls Network, which is identical to the first version given here in all other attributes.
 
[David Boyce](mailto://d-boyce@northwestern.edu) comments that yet another slightly different version of the Sioux Falls network appears in LeBlanc’s Ph.D. thesis. The main difference from the published paper version is that flows in the published paper are multiplied by 100, rounded in an unclear manner, and presented as integers, while flows in the thesis are in tenths.

See also: [Sioux Falls Variants for Network Design](http://www.bgu.ac.il/~bargera/tntp/SiouxFalls_CNDP/SiouxFallsVariantsForNetworkDesign.html)


## Scenario


## Contents

 - `SiouxFalls_net.tntp` Network  
 - `SiouxFalls_trips.tntp` Demand  
 - `SiouxFalls_node.tntp` Node Coordinates   
 - `SiouxFalls_flow.tntp`  Best known flow solution   
 - `Sioux-Falls-Network.pdf` Picture of Network  
 - `SiouxFallsMap_AAA1998.jpg`  Picture of actual Sioux Falls from 1998

## Dimensions  
Zones: 24  
Nodes: 24  
Links: 76  
Trips: 360,600.0  

## Units
Time:
Distance: 
Speed: 
Cost: 
Coordinates: 

## Generalized Cost Weights
Toll: 0  
Distance: 0  

## Solutions

`SiouxFalls_flow.tntp` contains best known link flows solution with Average Excess Cost (normalized gap) of 3.9E-15.  Optimal objective function value: 42.31335287107440

## Known Issues
FIXME translate to Github Issues
