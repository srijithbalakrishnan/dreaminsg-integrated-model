# InfraRisk: A simulation tool for interdependent infrastructure simulation

A Python -based model to simulate the interdependent failures in interdependent water-power-transport networks.

## Getting Started

### Prerequisites

- Operating System: Windows 10
- Python 3.7+
- Anaconda

### Installation

Please follow the steps below to setup the InfraRisk Integrated Simulation Platform.

 1. Clone the InfraRisk integrated simulation platfom repository from [Github](https://github.com/srijithbalakrishnan/dreaminsg-integrated-model.git).

```
git clone https://github.com/srijithbalakrishnan/dreaminsg-integrated-model.git folder-name
```

 2. Create a new python virtual environment with all required packages needed to run the simulation platform

 ```
 conda env create --name ENV_NAME --file=environment.ym
 ```

 3. Install the InfraRisk package in the created environment. Go to the project folder and run the following command:

 ```
 conda activate redcar
 pip install –-editable .
 ```

## Help

For instructions to run sample simulation on the simple network testbed, please refer to ```notebooks/event_based_simulations/simple_network.ipynb``` (faster).

For instructions to run sample simulation on the Micropolis testbed, please refer to ```notebooks/event_based_simulations/micropolis_network.ipynb``` (slower).

For instructions to run sample simulation on the Shelby County testbed, please refer to ```notebooks/event_based_simulations/shelby_county.ipynb``` (slower).

For instructions to run MPC optimization on the simple network testbed, please refer to ```notebooks/recovery_optimization/demo_optimization_incomplete.ipynb``` (faster). The notebook works for the current disruptive event (``test1``). However, please note that there could be an issue of infinite loops when performing MPC optimization of repair sequence for disruptions involving inaccessible components. The bug will be rectified soon.

For generating various hazards, see tutorials in ```notebooks/hazard_generation/```

Full documentation is available at ```dreaminsg_documentation.pdf``` or HTML version is available in [Read the Docs website](https://dreaminsg-integrated-model.readthedocs.io/en/latest/index.html). Please do note some sections need to be updated and the process is going on.

## Publications

1. Balakrishnan, S., B. Cassottana. InfraRisk: A Python-based Simulation Platform for Risk and Resilience Analysis in Interdependent Infrastructure Networks. Accepted for publication in *Sustainable Cities and Society* [(link)](https://doi.org/10.1016/j.scs.2022.103963).

## Authors

Contributors' names and contact info:

1. Srijith Balakrishnan, Ph.D. (Email: sbalakrishna@ethz.ch)
2. Beatrice Cassottana, Ph.D.
3. Geetanjali C

## Version History

- 0.1
  - Initial Release

## License

This project is licensed under the MIT License

## SEC Disclaimer

This research is carried out by Singapore ETH Centre through its Future Resilient Systems module
funded by the National Research Foundation (NRF) Singapore. It is subject to Agency's review and hence is for internal use only.
Not the contents necessarily reflect the views of the Agency. Mention of trade names, products, or services does not convey official 
NRF approval, endorsement, or recommendation. 


## Acknowledgments

The platform is developed as part of the DREAMIN'SG project funded by the National Research Foundation Singapore (NRF) through the Intra-CREATE program.
