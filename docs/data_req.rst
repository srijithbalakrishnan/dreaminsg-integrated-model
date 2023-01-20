Data requirements
=================

Currently, network generation and hazard generation are not automated in the integrated simulation
model. Therefore, in order to use the model, three types of data are to be manually fed into the
model, namely the water, power and transportation networks, interdependency data, and infrastructure
disruption data. There datasets need to be in specific formats which are compatible with the
model. In this chapter, the details such as file formats and information to be included in the input
files are discussed in detail.

Infrastructre Networks
---------------------------

The infrastructure network data must be compatible with the respective infrastructure model packages
enlisted in Table 1. In addition, disruptions to certain components belonging to the infrastructure
systems are not supported as of now. The individual networks must be constructed taking into
the above aspects into consideration.

Water distribution system
^^^^^^^^^^^^^^^^^^^^^^^^^

Since the integrated simulation model handles the water distribution network models using wntr
package, the input file must be in .inp format. Some examples of water network files can be
found in wntr Github repository1. The water network can be either built using EPANET or wntr
package. Currently, the water network simulation is performed using WNTRSimulator in the wntr
package. Therefore, there are certain exceptions which must be considered while generating the
water network file. These exceptions can be found in wntr's software framework and limitations
page.

In addition, the integrated simulation model identifies the component details such as infrastructure
type, component type, etc. using the component names. The name of the components must follow
the nomenclature. The details of nomenclature and whether a component can be failed in the model
is presented in Table 3.1. For example, a water pump can be named as W_WP1. Integers must be
followed by the prefix to name components belonging to same category.

Table 3.1. Nomenclature for water network components

+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+
| Prefix  | Component name           | Disruption supported  | Prefix  | Component name           | Disruption supported  |
+=========+==========================+=======================+=========+==========================+=======================+
| W_WP    | Pump                     | Yes                   | W_PMA   | Main Pipe                | Yes                   |
+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+
| W_R     | Reservoir                | No                    | W_PHC   | Hydrant Connection Pipe  | Yes                   |
+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+
| W_P     | Pipe                     | Yes                   | W_PV    | Valve converted to Pipe  | Yes                   |
+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+
| W_PSC   | Service Connection Pipe  | Yes                   | W_J     | Junction                 | No                    |
+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+
| W_T     | Tank                     | Yes                   |         |                          |                       |
+---------+--------------------------+-----------------------+---------+--------------------------+-----------------------+


Power systems
^^^^^^^^^^^^^^^^^^

The power system is modeled using pandapower package, and therefore the network file must
be in \*.json format. Several tutorials for generating power system networks using pandapower
are available in the package's tutorial page. Similar to water network components, naming of
power system components must also follow the stipulated nomenclature presented in Table 3. Currently,
power networks are modeled as three-phase systems. Therefore, single-phase components
in pandapower are not supported. Integers must be followed by the prefix to name components
belonging to same category.

Table 3.2. Nomenclature for power network components

+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| Prefix  | Component name                             | Disruption supported  | Prefix  | Component name                          | Disruption supported  |
+=========+============================================+=======================+=========+=========================================+=======================+
| P_B     | Bus                                        | Yes                   | P_L     | Line                                    | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_BLO   | Bus connected to load                      | Yes                   | P_TF    | Transformer                             | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_BS    | Bus connected to switch                    | Yes                   | P_TFEG  | Transformer connected to external grid  | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_BEG   | Bus connected to external grid connection  | yes                   | P_S     | Switch                                  | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_LO    | Load                                       | Yes                   | P_SEG   | Switch connected to external grid       | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_MP    | Motor                                      | Yes                   | P_SLI   | Switch connected to Line                | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+
| P_G     | Generator                                  | No                    | P_EG    | External Grid connection                | Yes                   |
+---------+--------------------------------------------+-----------------------+---------+-----------------------------------------+-----------------------+


Transportation system
^^^^^^^^^^^^^^^^^^^^^^^^

The transportation system is simulated using the static traffic assignment model developed by Prof.
Stephen Boyles of Department of Civil, Architectural and Environmental Engineering, The University
of Texas at Austin. The transportation network data must be in the TNTP data format. More
details on the format and example networks can be found in Ben Stabler's Github page4. The naming
of the transportation network components must follow the nomenclature presented in Table 3.3.
Integers must be followed by the prefix to name components belonging to same category.

Table 3.3. Nomenclature for transportation network components

+---------+-----------------+-----------------------+
| Prefix  | Component name  | Disruption supported  |
+=========+=================+=======================+
| T_J     | Junction        | No                    |
+---------+-----------------+-----------------------+
| T_L     | Link            | Yes                   |
+---------+-----------------+-----------------------+


Infrastructure dependencies
--------------------------------

Data related to water-power dependencies between infrastructure components must be provided
separately in a .csv file. The file must contain ``water_id`` and ``power_id`` fields which represent
the water- and power component names (Table 3.4). The model will determine the type of the waterand
power components and construct the dependencies accordingly.


Table 3.4. Format of disruption data 

+-----------+-----------+
| water_id  | power_id  |
+===========+===========+
| W_WP9     | P_MP1     |
+-----------+-----------+
| W_R9      | P_G3      |
+-----------+-----------+

Infrastructure disruption data
----------------------------------

The third data input is related to disrupted components. Similar to the dependency input file, the
disruption data also needs to be provided in \*.dat format. The file should have three fields, namely
``time_stamp`` (time of disruption in seconds), ``components`` (name of the component that is included
in any of the three networks), `fail_perc` (percentage of damage), and ``recovery_time`` (recovery time in hours). An example for the dependency
data is presented in Table 3.5.

table 3.5. Format of disruption data

+------------+------------+-----------+---------------+
| time_stamp | components | fail_perc | recovery_time |
+============+============+===========+===============+
|       7200 |     W_PMA1 |        50 |             7 |
+------------+------------+-----------+---------------+
|       7200 |      W_MP2 |        75 |           138 |
+------------+------------+-----------+---------------+
|       7200 |     T_L438 |        25 |            13 |
+------------+------------+-----------+---------------+

While the percentage of damage of component is not used in the current model, this may be incorporated
in the model to find the repair duration estimate in the future versions.