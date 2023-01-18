Methodology and Architecture
==================================

The integrated simulation model has been developed as a Python-based package consisting of modules for simulation of system- and network-level 
cascading effects resulting from component failures. The overall methodological framework of the integrated simulation platform is illustrated in Figure 2.

.. figure:: images/Sim_framework.PNG
   :width: 100 %
   :alt: map to buried treasure

   Figure 2. InfraRisk integrated simulation platform structure

The platform is based on the widely accepted risk- and resilience analysis frameworks as 
presented in [Argyroudis2020]_ and [Balakrishnan2020]_. In this framework, the most important component is an interdependent 
infrastructure model that consists of various infrastructure system submodels of interest. 
In addition, the major hazards in the region can also be modeled. Further, the vulnerabilities 
in the network to those hazards are mapped and the direct impacts (physical and functional failures 
in the infrastructure components) are simulated using the hazard model. For scheduling post-disaster 
restoration/repair actions, a recovery model is also developed. The restoration actions are prioritized 
based on specific recovery strategies or optimization methods. The indirect failures in the network are 
simulated using the interdependent infrastructure model based on the initial failure events and the 
subsequent repair actions. The component- and system-level operational performance are quantified and 
tracked using appropriate resilience metrics.

The basic idea behind the InfraRisk simulation package is to integrate existing infrastructure-specific 
simulation models through an object-oriented interface so that interdependent infrastructure simulation 
can be achieved. Interfacing requires identifying and modeling the dependencies among various infrastructure 
components and time-synchronization among infrastructure simulation models. To address the above challenges, 
InfraRisk is built using a sequential simulation framework (Figure 2). The advantage of this approach
is that it simplifies the efforts for data preparation and enables the complete
utilization of component-level modeling features of the domain-specific infrastructure models.

InfraRisk consists of five modules, namely, 

   #. integrated infrastructure network simulation
   #. hazard initiation and vulnerability modeling
   #. recovery modeling
   #. simulation of direct and indirect effects
   #. resilience quantification. 

In the rest of the section, a detailed discussion on each of the above modules is provided.


.. figure:: images/perf_curves.PNG
   :width: 100 %
   :alt: map to buried treasure

   Figure 3. Implementation of the simulation platform to generate performance curves


Integrated infrastructure network
------------------------------------

This module houses the three infrastructure models to simulate power-,
water-, and transport systems. These models are developed using existing
Python-based packages. In order to model the power system, *pandapower* is
employed [Thurner2018]_. The water distribution system is modeled using *wntr* package
[Klise2018]_. The traffic model provides the travel costs for traveling from one point
in the network to another and is modeled using the static traffic assignment
method [Boyles2020]_. All three packages have network-flow optimization models that
identify the steady-state resource flows in the respective systems considering
the operational constraints. The details of the packages are presented in Table 2.

Table 2. Infrastructure packages used in the simulation model

+----------------+-----------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
| Infrastructure | Package                           | Capabilities                                                                                                                              |
+----------------+-----------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
| Power          | *pandapower*                      | - Capable of generating power distribution systems with standard components, such as lines, buses, and transformers based on design data. |
|                |                                   | - Capable of performing power-flow analysis.                                                                                              |
+----------------+-----------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
| Water          | *wntr*                            | - Capable of generating water distribution systems with standard components such as pipes, tanks, and nodes based on design data.         |
|                |                                   | - Capable of performing pressure dependent demand or demand-driven hydraulic                                                              |
+----------------+-----------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
| Transport      | static traffic assignment package | - Capable of implementing static traffic assignment and computing travel times between origin-destination pairs.                          |
+----------------+-----------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+


Power system model
^^^^^^^^^^^^^^^^^^^^

The *pandapower* package can be used to determine the steady-state optimal power flow 
for a given set of system conditions. The optimal power flow
problem, solved by *pandapower*, attempts to minimize the total power distribution 
costs in the system under load flow-, branch-, bus-, and operational
power constraints (Equation 1)

.. math::

   \begin{aligned}
        \text{min} \quad & \sum_{i\in {gen,sgen,load,extgrid}}P_{i}\times f_{i}\left (P_{i}  \right )\\
        \textrm{s.t.} \quad & P_{min, i}\leq P_{i}\leq P_{max,i} & \forall i \in {gen,sgen,extgrid,load}\\
            & Q_{min, i}\leq Q_{i}\leq Q_{max,i} & \forall i \in {gen,sgen,extgrid,load}\\
            & V_{min,j} \leq V_{j}\leq V_{max,j} & \forall j\in {bus}\\
            & L_{k} \leq L_{max,k} & \forall k \in {trafo,line,trafo3w}
    \end{aligned}

where `i`, `j`, and `k` are the power system components, `gen` is the set of generators, 
`sgen` is the set of static generators, `load` is the set of loads, `extgrid` is the set of 
external grid connections, `bus` is the set of bus bars, `trafo` is 
the set of transformers, `line` is the set of lines, and `trafo3w` is the set of three winding 
transformers, :math:`f_{i}(\cdot)` is the cost function, :math:`P_{i}` is the active power in `i`, :math:`Q_{i}` 
is the reactive power in `i`, :math:`V_{j}` is the voltage in `j` and :math:`L_{k}` is the loading percentage 
in `k`.

Water system model
^^^^^^^^^^^^^^^^^^^^

The *wntr* package can simulate water flows in water distribution systems using 
two common approaches, namely, demand-driven analysis (DDA) and pressure-dependent demand analysis (PDA). 
While DDA assigns pipe flows based on the demands irrespective of the pressure at demand nodes, 
PDA assumes that the demand is a function of the pressure at which water is supplied. The PDA 
approach is more suitable for pressure-deficient situations, such as disaster-induced disruptions 
to water infrastructure. In the case of PDA, the actual node demands is computed as a function of 
available the water pressure at the nodes as in Equation.

The *wntr* package can simulate water flows in water distribution systems 
using two common approaches, namely, demand-driven analysis (DDA) and pressure-dependent demand 
analysis (PDA). While DDA assigns pipe flows based on the demands irrespective of the pressure at 
demand nodes, PDA assumes that the demand is a function of the pressure at which water is supplied. 
The PDA approach is more suitable for pressure-deficient situations, such as disaster-induced 
disruptions to water infrastructure. In the case of PDA, the actual node demands is computed as a 
function of available the water pressure at the nodes as in Equation~\ref{eq:PDA} \cite{Klise2020}.

.. math::

   d_{i}(t) = \begin{cases}
   0 & p_{i}(t) \leq P_{0} \\
   D_{i}(t)\left (\frac{p_{i}(t) - P_{0}}{P_{f} - P_{0}}  \right )^{\frac{1}{e}} & P_{0} < p_{i}(t) \leq P_{f}\\
   D_{i} & p_{i}(t) > P_{0}
   \end{cases}

where     is the actual demand at node `i` at time `t`, :math:`D_{i}(t)` is the desired demand at 
a node `i` at `t`, :math:`p_{i}(t)` is the available pressure in node `i` at `t`, :math:`P_f` is the nominal 
pressure, and :math:`P_0` is the lower pressure threshold,  below which no water is consumed. 
In InfraRisk, the hydraulic simulation is performed using the PDA approach.

Transport system model
^^^^^^^^^^^^^^^^^^^^^^^^

The traffic condition in the transport system is modeled using the 
static traffic assignment method based on the principle of user-equilibrium. Under user-equilibrium, 
every user tries to minimize their travel costs. The traffic assignment problem considered in InfraRisk
package is formulated as follows (Equation~\ref{eq:staeqs}) \cite{Boyles2020}.

.. math::

   \begin{aligned}
      \min_{\mathbf{x,h}} \quad & \sum_{(i,j)\in A} \int_{0}^{x_{ij}} t_{ij}(x_{ij})dx\\
      \textrm{s.t.} \quad & x_{ij} = \sum_{\pi \in \Pi} h^{\pi}\delta_{ij}^{\pi} & \forall (i,j) \in A\\
      & \sum_{\pi \in \Pi^{rs}} h^{\pi} = d^{rs} & \forall (r,s) \in Z^{2}\\
      & h^{\pi} \geq 0 & \forall \pi \in \Pi
   \end{aligned}

where `A` is the set of all road links with `i` and `j` as the tail and head nodes, :math:`t_{ij}` is the 
travel cost on link :math:`(i,j)`, :math:`x_{ij}` is the traffic flow on link :math:`(i,j)`, :math:`h^{\pi}` is the flow on 
path :math:`\pi \in \Pi`, :math:`\delta_{ij}^{\pi}` is an indicator variable that denotes whether :math:`(i,j)` is part 
of :math:`\pi`, :math:`d^{rs}` is the total flow between origin-destination pair :math:`(r,s)`.

Modeling interdependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The module also consists of an interdependency layer which serves as an interface between 
infrastructure systems. The interdependency layer stipulates the 
different pieces of information that can be exchanged among individual infrastructure 
systems and their respective formats. The interdependency submodule 
also stores information related to the various component-to-component couplings between 
infrastructure systems. The module facilitates the communication between 
infrastructure systems and enables information transfer triggered by dependencies. 
Currently the following dependencies are considered.

   #. Power-water dependencies, which include dependency of water pumps on electric motors and generators on reservoirs (hydro-power).
   #. Dependencies also exist between road traffic system and the other two infrastructure systems, as the former provides access to the latter. The disruptions to transport infrastructure components and their recovery are key considerations that influence the restoration and recovery of all other infrastructure systems. The module also stores the functional details of all infrastructure components, including their operational status after a disaster.

The interdependency layer communicates with the infrastructure simulators through inbuilt functions 
(wrappers).

Hazard initiation and vulnerability modeling
------------------------------------------------

The hazard module generates disaster scenarios and initiates disaster-induced infrastructure 
failures based on their vulnerability. The hazard initiation and the resulting infrastructure 
component failures is the first step in the interdependent infrastructure simulation.
The probabilistic failure of an infrastructure component is modeled as follows 
(Equation~\ref{eq:failureprob}):

.. math::

      p\left ( \text{failure}_{i} \right ) = p\left (\text{hazard}  \right ) \times p\left ( \text{exposure}_{i}|\text{hazard} \right ) \times p\left ( \text{failure}_{i}| \text{exposure}_{i} \right )

where `i` is the component, :math:`p(\cdot)` is the probability. The probability of failure of a component 
is computed as the product of the probability of the hazard, the probability of the component being 
exposed to the hazard if it occurs, and the probability of failure of the component if it is exposed 
to the event.

In InfraRisk, infrastructure component failures can be induced using five types of hazards.

   #. Point events (e.g., explosions)
   #. Track-based events (e.g., hurricanes and floods)
   #. Random disruption events (e.g., seven random road link failures)
   #. Custom events (e.g., fail five specific pipelines)
   #. Fragility-based events (e.g., earthquakes)

Among these, the first four two of event types are agnostic to infrastructure vulnerability and focus on the proximity of the
components to the location of the event. The random events are generated randomly based on user requirements. Custom events can generate
disruptions based on the user-defined lists. The fragility-based events are generated based on the component fragility curves and considers the
vulnerability characteristics of the components. 

Recovery modeling
-------------------

The third module, which is the recovery module, determines how the repair actions are sequenced and 
implemented. The three major factors that influence recovery are the availability of 
repair crews, repair times of components, and the criteria used for selecting subsequent 
components to restore. In InfraRisk, the user can specify the number of crews deployed for restoration 
of the three infrastructure systems, their initial locations in the 
network, and the repair times of the infrastructure components. 

The repair sequence can be derived using two approaches as follows. 

Heuristics-based repair sequences
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first approach is to adopt pre-defined 
repair strategies based on performance- and network-based heuristics.
Currently, there are three inbuilt strategies based on the following criteria: 

    #. Maximum flow handled: The resource-flow during normal operating conditions could reflect the importance of an infrastructure component to the system. The maximum resource-flow handled by a component, considering the temporal fluctuations, can be used as a performance-based heuristics to prioritize failed components for restoration.
    #. Betweenness centrality: Centrality is a graph-based measure that is used to denote the relative importance of components (nodes and links) in a system. Betweenness centrality is often cited as an effective measure to identify critical infrastructure components \cite{Almoghathawi2019}.
    #. Landuse/zone: Certain regions of a network may have consumers with large demands or critical to the functioning of the whole city. Industrial zones and central business districts are critical from both societal and economic perspectives.

While it is comparatively easier to derive repair sequences based on heuristics, they may not 
guarantee optimal recovery of the system or the network.

Recovery optimization
^^^^^^^^^^^^^^^^^^^^^^

The second approach is an optimization model leveraging on the concept of 
model predictive control (MPC) \cite{Camacho2007}. In this approach, first, out of `n` repair 
steps, the solution considering only `k` steps (called the prediction horizon) is computed. 
Next, the first step of the obtained solution is applied to the system and then the process 
is repeated for the remaining `n-1` components until all components are scheduled for repair. 
In the context of the integrated infrastructure simulation, the optimizer module evaluates 
repair sequences of the length of the prediction horizon for each infrastructure (assuming 
that each infrastructure has a separate recovery crew) based on a chosen 
resilience metric \cite{Kottmann2021}. The optimal repair sequence is found 
by maximizing the resilience metric. At this stage, the optimal repair action in each prediction 
horizon is computed using a brute-force approach where the resilience metric is evaluated for 
each of the possible repair sequences. The major limitation of MPC is that it is suitable only 
for small disruptions involving a few component failures; MPC becomes computationally expensive 
to derive optimal restoration sequences for larger disruptions due to the large number of 
repair permutations it has to simulate.


Simulation of direct and indirect effects
--------------------------------------------

The simulation module implements the integrated infrastructure simulation in two steps, 
namely, event table generation and interdependent infrastructure simulation.The objective of the 
event table is to provide a reference object to schedule all the disruptions and repair actions for 
implementing the interdependent network simulation.

The component failures, repair actions, and the respective time-stamps, are recorded in an event table for later use in the simulation 
module. The simulation platform uses the event table as a reference to modify the operational status 
of system components during the simulation, so that the consequences of disaster 
events and repair actions are reflected in the system performance. The recovery
module also stores details including the number of repair crews for every infrastructure 
system, and their initial locations.

The next step is to simulate the interdependent effects resulting from the component disruptions 
and the subsequent restoration efforts. One of the main challenge in simulating the interdependent 
effects using a platform that integrates multiple infrastructure models is the time synchronization.

In order to synchronize the times, the power- and water- system models are 
run successively for every subsequent time-interval in the event table. The required 
water system metrics are collected for every one minute of simulation time 
from the *wntr* model, whereas power system characteristics at the start 
of every time interval is recorded from the *pandapower* model. The power flow characteristics 
are assumed to remain unchanged unless there is any modification to the power system 
in the subsequent time-steps in the simulation.


Resilience quantification
--------------------------

Currently, the model has two measures of performance (MOP), namely, equitable consumer 
serviceability (ECS) and prioritized consumer serviceability (PCS), to quantify the system- and 
network steady-state performances. The above MOPs are based on the well-known concepts of 
satisfied demand \cite{Didier2017} and productivity \cite{Poulin2021}. Th MOPs are used as the 
basis for defining the resilience metrics.

Consider an interdependent infrastructure network :math:`\mathbb{K}` consisting of a set of 
infrastructure systems denoted by :math:`K: K\in \mathbb{K}`. There are `N` consumers who are 
connected to :math:`\mathbb{K}` and the resource supply from a system `K` to consumer `i\in N`  
at time `t` under normal operating conditions is represented by :math:`S_{i}^{K} (t)`. 

The ECS approach assumes equal importance to all the consumers dependent on the 
system irrespective of the quantity of resources consumed from 
the system. For an infrastructure system, the ECS at time `t` is 
given by Equation~\ref{eq:ecs}.

.. math::

   \text{ECS}_{K}(t) = \left (\sum_{\forall i: S_{i}^{K}(t) > 0}\frac{s_{i}^{K}(t)}{S_{i}^{K}(t)}  \right )/n_{K}(t), \quad\text{where } 0 \leq s_{i}^{K}(t) \leq S_{i}^{K}(t)


where :math:`s_{i}` is the resource supply at time `t` under stressed system conditions 
and :math:`n_{K}(t)` is the number of consumers with a non-zero normal demand at time `t`. 

In the case of PCS, the consumers are weighted by the quantity of resources drawn by them. This 
approach assumes that disruptions to serviceability of large-scale consumers, such as manufacturing 
sector, have larger effect to the whole region compared to small-scale consumers such as residential 
buildings. The PCS metric of an infrastructure system at time `t` is given by the Equation~\ref{eq:pcs}.

.. math::

   \text{PCS}_{K}(t) = \left (\frac{\sum_{\forall i: S_{i}^{K}(t) > 0} s_{i}^{K}(t)}{\sum_{\forall i: S_{i}^{K}(t) > 0}S_{i}^{K}(t)}  \right ), \quad\text{where~} 0\leq s_{i}^{K}(t) \leq S_{i}^{K}(t)

The normal serviceability component (:math:`S_{i}^{K}(t)`) makes both ECS and PCS metrics unaffected 
by the intrinsic design inefficiencies as well as the temporal fluctuations in demand.

For water distribution systems, pressure-driven approach is chosen as it 
is reported to be most ideal for the hydraulic simulation under pressure deficient situations. 
The component resource supply values for water systems are computed as in 
Equations~\ref{eq:water_t_pda}--\ref{eq:water_base_pda}.

.. math::

   s_{i}^{water}(t) = Q_{i}(t)

   S_{i}^{water}(t) = Q_{i}^{0}(t)

where :math:`Q_{i}(t)` and :math:`Q_{i}^{0}(t)` are the water supplied to consumer `i` during stressed and 
normal system conditions, respectively.

For power systems, the power supplied to components under normal and stressed 
system conditions can be calculated using Equations~\ref{eq:power_t}--\ref{eq:power_base}.

.. math::

   s_{i}^{power}(t) = p_{i}(t)

   S_{i}^{power}(t) = p_{i}^{0}(t)

where :math:`p_{i}(t)` and :math:`p_{i}^{0}(t)` are the power supplied to consumer `i` under stressed and 
normal power system conditions.

The ECS and PCS time series can be used to profile the effect of the disruption on any of the 
infrastructure systems. To quantify the system-level cumulative performance loss, a resilience 
metric called Equivalent Outage Hours (EOH), based on the well-known concept of `resilience triangle' 
\cite{Bruneau2003}, is introduced. EOH of an infrastructure system due to disaster event `\gamma^{K}` 
is calculated as in Equation~\ref{eq:system_eoh}.

.. math::

    \gamma^{K} = \frac{1}{3600}\int_{t_{0}}^{t_{max}} \left [ 1 - PCS_{K}(t)\right ]dt \quad \text{or}\quad \gamma^{K} = \frac{1}{3600}\int_{t_{0}}^{t_{max}} \left [ 1 - ECS_{K}(t)\right ]dt

where :math:`t_{0}` is the time of the disaster event in the simulation and :math:`t_{max}` is the maximum 
simulation time (both in seconds). In Equation~\ref{eq:system_eoh}, system performance during 
normal operating conditions is 1 due to the expression of the MOP used (see Equations ~\ref{eq:ecs}-~\ref{eq:pcs}).

EOH of an infrastructure system can be interpreted as the duration (in hours) of a full 
infrastructure service outage that would result in an equivalent quantity of reduced consumption 
of the same service by all consumers during a disaster. The larger the EOH value, the larger 
the impact on the infrastructure system and thereby on the consumers due 
to the disruptive event. The EOH metric can effectively capture the response and resilience 
of the infrastructure system (Equation~\ref{eq:system_eoh}), according to the serviceability 
criteria chosen by the user. 

Similar to EOH of a system, the consumer-level EOH can also be quantified, which indicates 
the equivalent duration of infrastructure service outage experienced by each consumer 
(Equation~\ref{eq:consum_eoh}).

.. math::

    \gamma_{i}^{K} = \int_{T_{0}}^{T} \left [ 1 -\frac{s_{i}^{K}(t)}{S_{i}^{K}(t)}\right ]dt


Finally, in order to compute the resilience of the interdependent infrastructure network, 
a weighted EOH metric is derived (Equation~\ref{eq:wEOH}).

.. math::

   \overline{\gamma} = \sum_{K\in\mathbb{K}}w^{K}\gamma^{K}



By default, equal weights are applied to both water and power systems.


.. [Argyroudis2020] S A. Argyroudis, S. A. Mitoulis, L. Hofer, M. A. Zanini, E. Tubaldi, D. M. Frangopol, Resilience assessment framework for critical infrastructure in a multihazard environment: Case study on transport assets, Science of the Total Environment 714 (2020) 136854. doi:10.1016/j.scitotenv.2020.136854.

.. [Balakrishnan2020] S Balakrishnan, Methods for Risk and Resilience Evaluation in Interdependent Infrastructure Networks, Ph.D. thesis, The University of Texas at Austin, Austin, Texas (aug 2020). doi:http://dx.doi.org/10.26153/tsw/13859.

.. [Thurner2018] L Thurner, A. Scheidler, F. Schafer, J. H. Menke, J. Dollichon, F. Meier, S. Meinecke, M. Braun, Pandapower - an open-source python tool for convenient modeling, analysis, and optimization of electric power systems, IEEE Transactions on Power Systems 33 (6) (2018) 6510–6521. doi:10.1109/TPWRS.2018.2829021.

.. [Klise2018] K Klise, D. Hart, M. Bynum, J. Hogge, T. Haxton, R. Murray, J. Burkhardt, Water network tool for resilience (wntr) user manual., Tech. rep., Sandia National Lab.(SNL-NM), Albuquerque, NM (United States) (2020).

.. [Boyles2020] S D. Boyles, N. E. Lownes, A. Unnikrishnan, Transportation Network Analysis, 0th Edition, Vol. 1, 2020.