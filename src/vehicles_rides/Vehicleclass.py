import simpy
from Task import Task
import logging

from Battery import Battery

class Vehicle:
    # static variables:
    brand: str = "Voi"
    version: str = "V7"
    id_count = -1

    def __init__(self, env, map, config, data_interface, task_manager, parking_spot, battery_level=1.0):
        # instance variables
        self.next_id()
        self.id = Vehicle.id_count

        self.env = env
        self.map = map
        self.config = config
        self.data_interface = data_interface
        self.task_manager = task_manager

        self.riding_speed = self.config["RIDING_SPEED"] / 3.6 # km/h -> m/s conversion

        self.battery = Battery(self.config["DISCHARGE_RATE_RIDE_KM"], self.config["DISCHARGE_RATE_IDLE_HR"], battery_level)
        self.available: bool = True
        self.status = "ready"
        self.task = None
        self.parking_spot = parking_spot # the vehicle's position?
        
        # if battery is initlized below swap threshold a swap should be added
        self.check_maintenance_need()

        # handling the idle drain of battery
        self.idle_start = None
        self.idle_process = self.env.process(self.idle())   

    @classmethod
    def reset(cls):
        Vehicle.id_count = -1
    
    def next_id(self):
        Vehicle.id_count += 1

    def __str__(self) -> str:
        return f"Id: {self.id:<7} Available: {'True' if self.available else 'False':<7}  Battery: {self.battery.level:.2f} Current Parking Spot: {self.parking_spot.id:<5}"
        
    def ride(self, destination_parking_spot, distance):
        # Ride the vehicle
        if distance != None:
            self.ride_distance = distance
        else:
            self.ride_distance = self.map.get_bike_ride_distance(self.parking_spot.location, destination_parking_spot.location)
        
        time = round(self.ride_distance / self.riding_speed)
        yield self.env.timeout(time)
        # Update the battery
        self.battery.discharge_ride(self.ride_distance)

    def check_maintenance_need(self):
        # Check if battery level is below the threshold for battery swap
        if self.battery.level <= self.config["SWAP_THRESHOLD"] and self.task is None:
            self.generate_task("battery_swap")
        # Check if battery level is below the threshold for bounty
        if self.battery.level <= self.config["BOUNTY_THRESHOLD"]:
            self.task.bounty = True
            self.task.bounty_time = self.env.now
            self.status = "bounty"
    
    def update_availability(self):
        """Sets the availability of the vehicle based on the tasks it has.
        If there is a bounty task, the vehicle is not available."""
        if self.task is None:
            self.available = True
        else:
            self.available = not self.task.bounty

    def generate_task(self, task_type):
        # Logic to generate a maintenance task for battery swap, not bounty to begin with
        self.task = Task(task_type, self.env.now, self, battery_in=self.battery.level)
        self.task_manager.add_task(self.task)
        logging.info("[%.0f] Vehicle %d - Task '%s' created. Battery level is %.2f." % (self.env.now, self.id, task_type, self.battery.level))

    def idle(self):
        try:
            if self.battery.level > self.config["SWAP_THRESHOLD"]:
                next_update_level = self.config["SWAP_THRESHOLD"]
            elif self.battery.level > self.config["BOUNTY_THRESHOLD"]:
                next_update_level = self.config["BOUNTY_THRESHOLD"]
            else:
                next_update_level = 0

            # Calculate the time in hours until the battery reaches the swap threshold
            time_until_next_update = round((self.battery.level - next_update_level) / self.battery.discharge_rate_idle)

            self.idle_start = self.env.now
            yield self.env.timeout(time_until_next_update)
            self.battery.level = next_update_level  # Update battery level to swap threshold
            self.check_maintenance_need()
            self.update_availability()
            # Resume idle (if not battery is empty)
            if self.battery.level > 0:
                self.resume_idle()

        except simpy.exceptions.Interrupt as interrupt:
            # time scooter been idle 
            time_idle = self.env.now - self.idle_start
            
            # drain battery
            self.battery.discharge_idle(time_idle)

    def interrupt_idle_process(self, interrupt_message):
        """Interrupts the idle process if it is alive and not already terminated."""
        if self.idle_process is not None and not self.idle_process.triggered:
            self.idle_process.interrupt(interrupt_message)

    def resume_idle(self):
        """Resume idle mode for the vehicle."""
        self.idle_process = self.env.process(self.idle())


