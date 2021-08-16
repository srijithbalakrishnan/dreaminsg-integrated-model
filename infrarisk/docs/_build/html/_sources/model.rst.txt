Integrated Simulation Platform
==================================

The integrated simulation model has been developed as a Python-based package consisting of modules for simulation of system- and network-level 
cascading effects resulting from component failures. The overall structure of the integrated simulation platform is illustrated in Figure 2.

.. figure:: images/structure.PNG
   :scale: 50 %
   :alt: map to buried treasure

   Figure 2. DREAMIN'SG integrated simulation platform structure

The model is capable of initializing disaster scenarios in interdependent power, water and transportation 
networks and evaluating resilience strategies by generating operational performance curves (Figure 3).
The resilience strategies that can be tested include pre-disaster interventions, such as system redundancy 
enhancements and post-disaster recovery optimization. 

.. figure:: images/perf_curves.PNG
   :scale: 60 %
   :alt: map to buried treasure

   Figure 3. Implementation of the simulation platform to generate performance curves

The model is developed by integrating existing flow-based water, power and transportation network models. 
The whole model can be divided into three broad modules, namely, the integrated infrastructure network module, network recovery module, and the 
recovery optimization module.

Integrated infrastructure network
---------------------------------

This module houses the three infrastructure network models which are used to simulate power-, 
water- and transportation networks independently. These are developed using existing Python-based packages and the details are presented in 
Table 2. The module also consists of an interdependency sub-module which serves as an interface between infrastructure network pairs. 
Currently the following dependencies are considered in the interdependent simulation platform.
   a. Power-water dependencies include dependency of water pumps on electric motors and generators on reservoirs.
   b. Dependencies also exist between traffic networks and the other two infrastructure models, as the former provides access to the latter, which is critical during the recovery phase. The module also stores the details of the states of all network components, including their operational status after a disaster. 

Network recovery
----------------

The recovery module consists of functions to develop an event table to schedule disruptive events and restoration actions after a disaster 
is initiated in the model. The simulation platform uses this table as a reference to modify the operational status of network components 
during a simulation, so that the consequences of disaster events and repair actions are reflected while simulating network performance. The 
recovery module also stores the details such as the number of repair crew for every infrastructure network, their initial locations, etc.


Recovery optimization
---------------------

This module determines the order in which the repair actions are carried out. Currently, the approach of the optimization module leverages 
on the methodology of Model Predictive Control (MPC). In this approach, first, out of *N* repair steps, the solution considering only *k* steps, 
called the prediction horizon, is computed. Next, the first step of the obtained solution is applied to the system and then the process is 
being repeated for the remaining *N-1* components until all components have been scheduled for repair. In the context of the integrated infrastructure 
simulation, the optimizer module evaluates repair sequences of the length of the prediction horizon for each infrastructure (assuming that each of 
the infrastructure has a separate recovery crew) based on a resilience metric. In the model, the integral loss of service (ILOS) is used as the 
resilience metric. The ILOS is calculated as follows:	

.. math::
   ILOS = w_{P}\sum_{k}DPower\times dt_{P}(k)+w_{W}\sum_{k}DWater\times dt_{w}(k)+w_{T}\sum_{k}DTransport\times dt_{T}(k)

where, :math:`DPower`, :math:`DWater` and :math:`DTransport` are the respective demands not served, :math:`dt_{P}(k)`, :math:`dt_{W}(k)` and :math:`dt_{T}(k)` 
the repair-time specific time steps between the repair actions and wp,ww,wTthe weights. The optimal repair sequence is found by minimizing the ILOS. At this stage 
the optimal repair action in each prediction horizon is computed using a brute-force approach where the ILOS is evaluated for each of the repair sequences.

Currently, the network data, interdependency data and infrastructure disruption data are to be manually fed into the model to run the network simulations. 
However, efforts are being made to include separate modules for network generation and hazard initiation in the simulation platform, to enhance the scope of the model. 
The following improvements will also be made to the model:
   a. Realistic policies for network recovery.
   b. Additional interdependencies.
