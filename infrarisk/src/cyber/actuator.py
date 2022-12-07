import wntr
from wntr.network.controls import ControlPriority
import infrarisk.src.physical.interdependencies as interdependencies


class Actuator:
    """A class of actuators"""

    def __init__(self, name, status=1):
        """Initiates a actuator object

        :param name: The identifier of the actuator
        :type name: string
        :param status: The operational status of the actuator, defaults to 1
        :type status: integer, optional
        """
        self._name = name
        self._status = status


class WaterPumpActuator(Actuator):
    """A class of actuators for controlling the water pump"""

    def __init__(
        self, pump_id, name, controller_id, type="Water pump actuator", status=1
    ):
        """Initiates a water pump actuator object

        :param name: The identifier of the actuator
        :type name: string
        :param status: The operational status of the actuator, defaults to 1
        :type status: integer, optional
        """
        super().__init__(name, status)
        self._pump_id = pump_id
        self._type = type
        self._controller_id = controller_id
        self._tank_level = None
        self._id = interdependencies.get_compon_details(pump_id)[4]

    def set_pump_initial_status(self, wn, state=1):
        pass

    def turn_on_pump(self, wn, time_stamp):
        """Adds a pump on control action to the wntr object

        :param pump_obj: The water pump object
        :type pump_obj: wntr pump object
        """
        if self._status == 1:
            pump = wn.get_link(self._pump_id)
            act_open = wntr.network.controls.ControlAction(
                pump, "status", wntr.network.LinkStatus.Open
            )
            cond_open = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
            ctrl_open = wntr.network.controls.Control(
                cond_open, act_open, ControlPriority.medium
            )
            if "open pump " + self._pump_id in wn.control_name_list:
                wn.remove_control("open pump " + self._pump_id)
            if "close pump " + self._pump_id in wn.control_name_list:
                wn.remove_control("close pump " + self._pump_id)
            wn.add_control("open pump " + self._pump_id, ctrl_open)
        else:
            print("The pump actuator is not operational")
        # pass

    def turn_off_pump(self, wn, time_stamp):
        """Adds a pump off control action to the wntr object

        :param pump_obj: The water pump object
        :type pump_obj: wntr pump object
        """
        if self._status == 1:
            pump = wn.get_link(self._pump_id)
            act_close = wntr.network.controls.ControlAction(
                pump, "status", wntr.network.LinkStatus.Closed
            )
            cond_close = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
            ctrl_close = wntr.network.controls.Control(
                cond_close, act_close, ControlPriority.medium
            )
            if "open pump " + self._pump_id in wn.control_name_list:
                wn.remove_control("open pump " + self._pump_id)
            if "close pump " + self._pump_id in wn.control_name_list:
                wn.remove_control("close pump " + self._pump_id)
            wn.add_control("close pump " + self._pump_id, ctrl_close)
        else:
            print("The pump actuator is not operational")


class DischargePipeActuator(Actuator):
    """A class of actuators for controlling the discharge from a water tank when tank level breaches the upper threshold level."""

    def __init__(
        self, tank_id, name, controller_id, type="Discharge pipe actuator", status=1
    ):
        """Initiates a discharge pipe actuator object

        :param name: The identifier of the actuator
        :type name: string
        :param status: The operational status of the actuator, defaults to 1
        :type status: integer, optional
        """
        super().__init__(name, status)
        self._tank_id = tank_id
        self._type = type
        self._controller_id = controller_id
        self.tank_level = None
        self._id = interdependencies.get_compon_details(tank_id)[4]

    def set_discharge_initial_status(self, wn, state=1):
        pass

    def turn_on_discharge(self, wn, time_stamp):
        """Adds a discharge on control action to the wntr object

        :param tank_obj: The water tank object
        :type tank_obj: wntr tank object
        """
        if self._status == 1:
            dp_index = self._tank_id.split("W_T")[1]
            discharge_pipe = wn.get_link(f"W_PDP{dp_index}")
            act_open = wntr.network.controls.ControlAction(
                discharge_pipe, "status", wntr.network.LinkStatus.Open
            )
            cond_open = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
            ctrl_open = wntr.network.controls.Control(
                cond_open, act_open, ControlPriority.medium
            )
            if "open discharge " + self._tank_id in wn.control_name_list:
                wn.remove_control("open discharge " + self._tank_id)
            if "close discharge " + self._tank_id in wn.control_name_list:
                wn.remove_control("close discharge " + self._tank_id)
            wn.add_control("open discharge " + self._tank_id, ctrl_open)
        else:
            print("The discharge pipe actuator is not operational")
        # pass

    def turn_off_discharge(self, wn, time_stamp):
        """Adds a discharge off control action to the wntr object

        :param tank_obj: The water tank object
        :type tank_obj: wntr tank object
        """
        if self._status == 1:
            dp_index = self._tank_id.split("W_T")[1]
            discharge_pipe = wn.get_link(f"W_PDP{dp_index}")
            act_close = wntr.network.controls.ControlAction(
                discharge_pipe, "status", wntr.network.LinkStatus.Closed
            )
            cond_close = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
            ctrl_close = wntr.network.controls.Control(
                cond_close, act_close, ControlPriority.medium
            )
            if "open discharge " + self._tank_id in wn.control_name_list:
                wn.remove_control("open discharge " + self._tank_id)
            if "close discharge " + self._tank_id in wn.control_name_list:
                wn.remove_control("close discharge " + self._tank_id)
            wn.add_control("close discharge " + self._tank_id, ctrl_close)
        else:
            print("The discharge pipe actuator is not operational")


class ValveActuator(Actuator):
    def __init__(self, valve_id, name, type="water_plc", status=1):
        super().__init__(name, status)
        self._type = type
        self._id = self._id = interdependencies.get_compon_details(valve_id)[4]

    def get_sensor_reading(self, tank_sensor, wn_results, wn, error_factor=1):
        """Sends a action triggering message to the sensor

        :param sensor: The identifier of the sensor
        :type sensor: string
        :param wn_results: The water network results object
        :type wn_results: wntr results object
        """
        curr_sensor = tank_sensor

        if self._status == 1:
            if curr_sensor._status == 1:
                curr_sensor.update_curr_tank_level(wn_results, wn)
                curr_sensor.update_curr_tank_level(wn_results, wn, error_factor)
                tank_reading = curr_sensor.get_curr_tank_level()
                return tank_reading
            else:
                print("The sensor is not operational")
        else:
            print("The controller is not operational")

    def trigger_discharge_pipe_actuator(
        self, tank_sensor, discharge_pipe_actuator, wn, sim_time
    ):
        """Trigger pump actuator based on the sensor reading

        :param actuator: The identifier of the actuator
        :type actuator: string
        :param wn: The water network object
        :type wn: wntr water network object
        """
        curr_sensor = tank_sensor
        curr_actuator = discharge_pipe_actuator
        print(
            "Current level: ",
            curr_sensor._tank_level,
            " Maximum level: ",
            curr_sensor._max_tank_level,
            " Minimum level: ",
            curr_sensor._min_tank_level,
        )
        if self._status == 1:
            if curr_sensor._tank_level <= curr_sensor._min_tank_level:
                curr_actuator.turn_off_discharge(wn, sim_time)
                print("Added a discharge pipe turn off control action")
            elif curr_sensor._tank_level >= curr_sensor._max_tank_level:
                curr_actuator.turn_on_discharge(wn, sim_time)
                print("Added a discharge pipe turn on control action")
        else:
            print("The controller is not operational")
