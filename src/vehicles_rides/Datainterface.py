import logging
from geopy.distance import geodesic
from scipy.stats import truncnorm


class DataInterface:
    def __init__(self, env, config):
        self.env = env
        self.config = config

        self.task_manager = None
        self.parking_spots = []
        self.vehicles = []

        self.WALK_RADIUS = config["WALK_RADIUS"]
        #self.BATTERY_MIN_LEVEL = config["BATTERY_MIN_LEVEL"]

    def find_nearest_vehicle(self, location):
        nearest_vehicle = None
        min_distance = float('inf')

        for parking_spot in self.parking_spots:
            available_vehicle = parking_spot.pick_available_vehicle()
            if available_vehicle:
                distance = self.calculate_distance(parking_spot.location, location)
                if distance < min_distance and distance <= self.config['WALK_RADIUS']:
                    min_distance = distance
                    nearest_vehicle = available_vehicle
        return nearest_vehicle
    
    def find_nearest_parking_spot(self, location):
        """ Use to get nearest parking spot to certain location.
        TODO: does ps have max cap? only return ps with avialable spots"""
        nearest_parking_spot = None
        min_distance = float('inf')

        for parking_spot in self.parking_spots:
            distance = self.calculate_distance(location, parking_spot.location)
            if distance < min_distance:
                nearest_parking_spot = parking_spot
                min_distance = distance
        return nearest_parking_spot
    
    def vehicle_ride(self, vehicle, destination_parking_spot, given_distance=None):
        # Make vehicle unavailable during the ride
        vehicle.available = False  
        vehicle.status = "riding"

        yield self.env.process(vehicle.ride(destination_parking_spot, given_distance))
        
        # Move vehicle from origin to destination parking spot
        vehicle.parking_spot.remove_vehicle(vehicle)
        destination_parking_spot.add_vehicle(vehicle)
        vehicle.parking_spot = destination_parking_spot
        
        # Update vehicle status
        vehicle.status = "ready"
        
        # Check need for tasks and update availability accordingly
        vehicle.check_maintenance_need()
        vehicle.update_availability()

    def resolve_task(self, task):
        """ Resolve task and update vehicle availability"""
        vehicle = task.vehicle
        # change battery
        vehicle.battery.level = vehicle.battery.max_level
        # remove task from task manager 
        self.task_manager.remove_task(task)
        # remove task from vehicle
        task.vehicle.task = None
        # update vehicle availability
        task.vehicle.update_availability()
        task.vehicle.status = "ready"

    
    @staticmethod
    def calculate_distance(a, b):
        """ Calculates distances between a and b in meters.
        Method used: Geographic Euclidian distance"""
        return geodesic((a.lat, a.lon), (b.lat, b.lon)).meters
    

    @staticmethod
    def get_truncated_normal(mean=0.90, sd=0.3, low=0.05, upp=1.0):
        return truncnorm((low - mean) / sd, (upp - mean) / sd, loc=mean, scale=sd)

    
    # set vehicles and parking spots method
    def set_data(self, parking_spots, vehicles, task_manager):
        self.parking_spots = parking_spots
        self.vehicles = vehicles
        self.task_manager = task_manager
        # pre calculate nearest parking_spots?


