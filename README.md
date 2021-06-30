# DREAMIN'SG Integrated Infrastructure Simulation Model

A Python -based model to simulate the cascading failures in interdependent urban water-power-transportation networks.

## Project Description

### Disaster REsilience Assessment, Modelling, and INnovation Singapore (DREAMIN'SG)
Climate change has caused an increase in the intensity and frequency of extreme weather events, with severe consequences on the urban infrastructure. Southeast Asia (SEA) is particularly vulnerable to these events because of its densely populated urban areas and the lack of resources and clear guidelines for dealing with them. Given the local conditions and resources in the region, this project aims at developing innovative technologies and services to design resilient urban infrastructure systems, comprising the interdependent water, power, and transport subsystems.

 A data-driven simulation platform is developed in Python to model the performance of interdependent urban infrastructure systems after a disruptive event based on past case studies in the SEA region. Therefore, resilience is assessed using the tools developed under the Future Resilient Systems program. Simulations are run and resilience is assessed for various scenarios, involving (i) different system features, such as topology, system attributes, and recovery policies, and (ii) relaxed constraints, such as technological, regulatorily, and topological constraints. Based on the simulation-generated dataset, interpretable machine learning algorithms are implemented in order to not only identify the correlation between different system features and the resilience output, but also their causal relationships. The ultimate goal is to predict resilience based on the features of a system. Therefore, based on the identified features and on the simulation results, conclusions on the requirements of potential new products and services are derived to accommodate the relaxed constraints using design thinking techniques. In order to validate the simulation model, example networks and hypothetical scenarios are considered before analyzing past case studies in the SEA region.

Overall, the contributions of this project are manifold:

1. The developed data-driven simulation platform improves in-depth diagnosis about the impacts of extreme weather events in SEA.
2. This research advances the understanding of strategic approaches for building resilience in complex urban systems.
3. The application of interpretable machine learning algorithms is a novel methodological contribution in the resilience community.
4. This research contributes to the development of new products and services to increase the resilience of urban infrastructure systems.

### Python-based DREAMIN'SG Integrated Simulation Platform
The DREAMIN'SG project aims at studying how disaster-related characteristics and post-disaster recovery-related decisions influence the resilience of an urban network. However, the idea behind developing a Python package was to provide a generic tool for researchers to further conduct studies and experiments on urban infrastructure networks which are out of the scope of the DREAMIN'SG project.

## Getting Started

### Prerequisites
 - Operating System: Windows 10
 - Python 3.7+
 - Anaconda

### Installing
Please follow the steps below to setup the DREAMIN'SG Integrated Simulation Platform.

 1. Clone the DREAMIN'SG integrated simulation platfom repository from [Github](https://github.com/srijithbalakrishnan/dreaminsg-integrated-model.git).
```
$ git clone https://github.com/srijithbalakrishnan/dreaminsg-integrated-model.git folder-name
```
 2. Create a new python virtual environment with all required packages needed to run the simulation platform
 ```
 conda env create -f environment.yml
 ``` 

## Help
Please refer to ```/notebooks/demo.ipynb``` for instructions to run simulations.

## Authors

Contributors names and contact info

1. Srijith Balakrishnan (Email: sbalakrishna@ethz.ch)

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License

## Acknowledgments
