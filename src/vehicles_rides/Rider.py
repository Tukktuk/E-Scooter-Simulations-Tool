import simpy
import logging
from Location import Location
from Ride import Ride

class Rider:
    id_count = 0

    def __init__(self, env, config, data_interface, results, origin_ps, destination_ps, departure_time, target_time=None, ride_distance=None):
        self.next_id()
        self.id = Rider.id_count
        self.env = env
        self.config = config

        self.results = results
        self.user_ride = Ride()
        self.data_interface = data_interface

        # Demand paramenters
        self.origin_parking_spot = origin_ps
        self.destination_parking_spot = destination_ps
        self.departure_time = departure_time
        self.target_time = target_time

        self.status = "unfullfilled"
        self.target_time = None
        self.location = None
        self.vehicle = None

        self.origin_visited_stations = None

        self.time_walk_origin = None
        self.time_ride = None
        self.time_walk_destination = None
        self.ride_distance = ride_distance
        self.battery_in = None
        self.battery_out = None

        self.location = Location(0,0) # TODO: change to origin when rider is activated in simulation


    @classmethod
    def reset(cls):
        Rider.id_count = -1

    def next_id(self):
        Rider.id_count += 1

    
    def __str__(self) -> str:
        return f"Id: {self.id:<7} Status: {self.status:<12} Origin: {self.origin_parking_spot.id:<5} Destination: {self.destination_parking_spot.id:<5}"

    def init_user(self):
        # waits until its the hour to initialize user
        yield self.env.timeout(self.departure_time)
        self.location = self.origin_parking_spot.location
        logging.info("[%.0f] User %d initialized at parking spot %d" % 
                     (self.env.now, self.id, self.origin_parking_spot.id))

    def process(self):
        # 0. Setup initilize at location
        yield self.env.process(self.init_user())

        # 1. Find available vehicle
        self.vehicle = self.origin_parking_spot.pick_available_vehicle()
        if self.vehicle is None:
            # First: Rider check neighboring parking spots within walking distance
            for neighbor in self.origin_parking_spot.neighbor_parking_spots:
                self.vehicle = neighbor.pick_available_vehicle()
                if self.vehicle is not None:
                    self.origin_parking_spot = neighbor
                    break
            # Second: Ride considerd unfullfilled
            if self.vehicle is None:
                logging.info("[%.0f] User %d has no available vehicle at parking spot %d" % (self.env.now, self.id, self.origin_parking_spot.id))
                self.save_user_ride()
                return  # No available vehicle, end the process
        
        # 2. Ride vehicle to destination
        self.vehicle.interrupt_idle_process("Idle interrupted due to RIDE")
        yield self.env.process(self.ride_vehicle())

        # 4. Park vehicle at destination 
        yield self.env.process(self.park_vehicle(self.vehicle))

        # 5. Complete ride 
        self.status = "completed"
        self.save_user_ride()

    def find_nearest_vehicle(self, location):
        pass # return self.data_interface.find_nearest_vehicle(location)
    

    def walk_to(self, location):
        # Simulate walking to the location, takes 50 sek regardless of distance
        logging.info("[%.0f] User %d walking to parking spot %d" % (self.env.now, self.id, self.destination_parking_spot.id))
        yield self.env.timeout(50)  # Simulate time taken to walk
        self.location = location
    
    def ride_vehicle(self):
        logging.info("[%.0f] User %d riding vehicle %d from parking spot %d to %d" % 
                     (self.env.now, self.id, self.vehicle.id, self.origin_parking_spot.id, self.destination_parking_spot.id))
        # data collection
        self.battery_in = self.vehicle.battery.level
        ride_start = self.env.now

        # complete ride
        yield self.env.process(self.data_interface.vehicle_ride(self.vehicle, self.destination_parking_spot, self.ride_distance))

        self.vehicle.resume_idle()  # Resume idle mode in vehicle
        # save data
        self.time_ride = self.env.now - ride_start
        self.battery_out = self.vehicle.battery.level
        self.ride_distance = self.vehicle.ride_distance
        self.location = self.destination_parking_spot.location

    def park_vehicle(self, vehicle):
        # Simulate parking the vehicle
        logging.info("[%.0f] User %d parking vehicle %d at parking spot %d" % (self.env.now, self.id, self.vehicle.id, self.destination_parking_spot.id))
        yield self.env.timeout(30)  # Simulate time taken to park

    def start(self):
        self.env.process(self.process())

    def save_user_ride(self):
        self.user_ride.set("user_id", self.id)
        self.user_ride.set("vehicle_id", None if self.vehicle is None else self.vehicle.id)

        self.user_ride.set("time_departure", self.departure_time, 0)
        self.user_ride.set(("status"), self.status)
        self.user_ride.set("time_target", self.target_time, 0)
        self.user_ride.set("time_ride", self.time_ride, 0)
        self.user_ride.set("origin_parking_spot", self.origin_parking_spot.id, 0)
        self.user_ride.set("destination_parking_spot", self.destination_parking_spot.id, 0)
        self.user_ride.set("origin_lon", self.origin_parking_spot.location.lon, 5)
        self.user_ride.set("origin_lat", self.origin_parking_spot.location.lat, 5)
        self.user_ride.set("destination_lon", self.destination_parking_spot.location.lon, 5)
        self.user_ride.set("destination_lat", self.destination_parking_spot.location.lat, 5)
        self.user_ride.set("ride_distance", self.ride_distance, 0)
        self.user_ride.set("battery_in", self.battery_in, 3)
        self.user_ride.set("battery_out", self.battery_out, 3)

        self.results.add_user_trip(self.user_ride)

