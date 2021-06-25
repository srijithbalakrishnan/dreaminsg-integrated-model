.. DREAMIN'SG documentation master file, created by
   sphinx-quickstart on Wed May 26 14:12:31 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

DREAMIN'SG Integrated Simulation Model documentation
=====================================================

DREAMIN'SG Project Summary
--------------------------

Climate change has caused an increase in the intensity and frequency of extreme weather events, 
with severe consequences on the urban infrastructure. Southeast Asia (SEA) is particularly vulnerable 
to these events because of its densely populated urban areas and the lack of resources and clear 
guidelines for dealing with them. Given the local conditions and resources in the region, this 
project aims at developing innovative technologies and services to design resilient urban infrastructure 
systems, comprising the interdependent water, power, and transport subsystems.

A data-driven simulation platform is developed in Python to model the performance of interdependent 
urban infrastructure systems after a disruptive event based on past case studies in the SEA region. 
Therefore, resilience is assessed using the tools developed under the Future Resilient Systems program. 
Simulations are run and resilience is assessed for various scenarios, involving (i) different system 
features, such as topology, system attributes, and recovery policies, and (ii) relaxed constraints, 
such as technological, regulatorily, and topological constraints. Based on the simulation-generated 
dataset, interpretable machine learning algorithms are implemented in order to not only identify the 
correlation between different system features and the resilience output, but also their causal 
relationships. The ultimate goal is to predict resilience based on the features of a system. Therefore, 
based on the identified features and on the simulation results, conclusions on the requirements of 
potential new products and services are derived to accommodate the relaxed constraints using design 
thinking techniques. In order to validate the simulation model, example networks and hypothetical 
scenarios are considered before analyzing past case studies in the SEA region.

.. figure:: images/methodology.PNG
   :scale: 50 %
   :alt: map to buried treasure

   Figure 1. Methodological framework of DREAMIN'SG project

Overall, the contributions of this project are manifold: 

   1. The developed data-driven simulation platform improves in-depth diagnosis about the impacts of extreme weather events in SEA.
   2. This research advances the understanding of strategic approaches for building resilience in complex urban systems.
   3. The application of interpretable machine learning algorithms is a novel methodological contribution in the resilience community.
   4. This research contributes to the development of new products and services to increase the resilience of urban infrastructure systems.


The Integrated Simulation platform
----------------------------------
The DREAMIN'SG project aims at studying how disaster-related characteristics and post-disaster recovery-related decisions influence
the resilience of an urban network. However, the idea behind developing a Python package was to provide a generic tool for researchers to further
conduct studies and experiments on urban infrastructure networks which are out of the scope of the DREAMIN'SG project. 

.. figure:: images/structure.PNG
   :scale: 50 %
   :alt: map to buried treasure

   Figure 2. DREAMIN'SG integrated simulation platform structure


.. toctree::
   :maxdepth: 3
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
