import logging
import os
import random

import simpy
import json
import pandas as pd
import time
import numpy as np

#from Datainterface import DataInterface
from ParkingSpotclass import ParkingSpot
from Rider import Rider
from Vehicleclass import Vehicle
from Location import Location
from Results import Results
from Datainterface import DataInterface
from TaskManager import TaskManager
from FleetSpecialist import FleetSpecialist
from Map import Map
from SimState import SimState


class RideSimulationEngine:
    def __init__(self, config, parking_spots_or_data_path, map_or_area_ploygon_path, demand_data_path=None, verbose=1, fleet_maintenance=1, seed=None):
        # simulation environment and configuration parameters
        print(f"Setting up simulation environment for {config['CITY']}")
        self.env = simpy.Environment()
        self.config = config
        self.results = Results(self.config, verbose=verbose)

        # Set the random seed for reproducibility
        self.seed = seed
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)

        # data paths
        self.parking_spots_or_data_path = parking_spots_or_data_path 
        self.demand_data_path = demand_data_path

        self.num_of_fleet_specialists = fleet_maintenance

        # support classes
        #self.map = Map() # all distance and location function calls
        self.map = self.init_map(map_or_area_ploygon_path)
        self.data_interface = DataInterface(self.env, self.config) # all function calls which demand diving into data
        self.task_manager = TaskManager(self.results)

        # storage for city state TODO skip put all in data_interface??
        self.parking_spots = []
        self.vehicles = []
        self.riders = []

        self.num_of_parking_spots = 0
        self.num_of_vehicles = config["NUM_OF_VEHICLES"]

        self.start()

    def init_map(self, map_or_area_ploygon_path):
        if isinstance(map_or_area_ploygon_path, str):
            print("Loading map")
            return Map(map_or_area_ploygon_path)
        elif isinstance(map_or_area_ploygon_path, Map):
            return map_or_area_ploygon_path
        else:
            raise ValueError("Invalid map or area polygon path")

    def start(self):
        # set up city from data
        self.init_parking_spots()
        self.init_vehicles()
        if self.num_of_fleet_specialists > 0:
            self.init_fleet_specialists()
        if self.demand_data_path == None:
            if not self.config["TVD"] == 0:
                self.generate_uniform_demand()
        else:
            self.load_demand(self.demand_data_path) 
        self.data_interface.set_data(self.parking_spots, self.vehicles, self.task_manager)


    def init_parking_spots(self):
        """ Checks if parking spots are loaded from a csv or given by constructor arguments"""
        if isinstance(self.parking_spots_or_data_path, str):
            self.parking_spots, self.map = self.load_parking_spots(self.parking_spots_or_data_path, self.map)
            self.parking_spots = self.find_parking_spot_neighbors(self.config, self.parking_spots, self.map)
        else:
            self.parking_spots = self.parking_spots_or_data_path
        self.num_of_parking_spots = len(self.parking_spots)
        logging.info("[%.0f] Number of parking spots placed: %d. Number of vehicles: %d. Number of vehicles per parking spot: %.2f" % (self.env.now, self.num_of_parking_spots, self.config["NUM_OF_VEHICLES"], self.config["NUM_OF_VEHICLES"]/self.num_of_parking_spots))


    @staticmethod
    def load_parking_spots(parking_spot_data_path, map_instance):
        print("Loading parking spots")
        ParkingSpot.reset()
        parking_spots_data = pd.read_csv(parking_spot_data_path)
        parking_spots = []
        for index, row in parking_spots_data.iterrows():
            #if index % 4 != 0:  # Skip every 4th parking spot
            parking_spots.append(ParkingSpot(Location(row['LONGITUDE'], row['LATITUDE'], map=map_instance)))
        print("making kdtree")
        map_instance.create_kdtree(parking_spots)
        return parking_spots, map_instance
    
    @staticmethod
    def find_parking_spot_neighbors(config, parking_spots, map):
        print("Finding neighbors for each parking spot")
        for parking_spot in parking_spots:
            # Query the KDTree for indices of neighbors within walk_radius
            nearby_parking_spots_indices = map.find_nearby_parking_spot_indices(parking_spot.location, config["WALK_RADIUS"])
            # Filter out the parking spot's own index
            parking_spot.neighbor_parking_spots = [parking_spots[i] for i in nearby_parking_spots_indices if i != parking_spot.id]
        print("total number of neighbors: " + str(sum(len(parking_spot.neighbor_parking_spots) for parking_spot in parking_spots)))
        return parking_spots

    def init_vehicles(self):
        print("Placing vehicles")
        Vehicle.reset()
        # Places vehicles in random parking spots until the number of vehicles is reached
        vehicles_placed = 0
        while not vehicles_placed == self.config["NUM_OF_VEHICLES"]:
            random_spot = random.choice(self.parking_spots)
            battery_level = self.data_interface.get_truncated_normal().rvs()
            vehicle = Vehicle(self.env, self.map, self.config, self.data_interface, self.task_manager, random_spot, battery_level=battery_level)
            random_spot.vehicles.append(vehicle)
            self.vehicles.append(vehicle) #TODO: check if this is the right way to do it, double store?
            vehicles_placed += 1

    # Fleet specialist initialization
    def init_fleet_specialists(self):
        print("Initializing fleet specialists")
        FleetSpecialist.reset()
        start_time = 0 # start after 0 day  
        starting_location = self.parking_spots[0].location  # Starting location for the fleet specialist
        focus_area = False
        for i in range(self.num_of_fleet_specialists):
            focus_area_path = os.path.join("data","area","fleet_spec","fs"+str(i)+".geojson") if focus_area else None
            fleet_specialist = FleetSpecialist(self.env, self.map, self.config, self.results, self.task_manager, start_time, starting_location, self.data_interface, focus_area_path)
            fleet_specialist.schedule()
        logging.info("[%.0f] Number of fleet specialists initilised: %d" % (self.env.now, self.num_of_fleet_specialists))


    def load_demand(self, demand_data_path):
        print("Loading demand")
        demand_data = pd.read_csv(demand_data_path)
        for index, row in demand_data.iterrows():
            origin_parking_id = self.map.find_nearest_parking_spot(Location(row["start_lon"], row["start_lat"]))
            destination_parking_id = self.map.find_nearest_parking_spot(Location(row["target_lon"], row["target_lat"]))

            user = Rider(
                            self.env,
                            self.config,
                            self.data_interface,
                            self.results,
                            self.parking_spots[origin_parking_id],
                            self.parking_spots[destination_parking_id],
                            row["start_time"],
                            row["target_time"],
                            row["distance"])
            self.riders.append(user)
            user.start()
            # no need to load more than simulation length
            if row["start_time"] > 3600 * 24 * self.config["NUM_SIMULATED_DAYS"]:
                break

        logging.info("[%.0f] Number of trips planned is %d under %d day(s). TVD: %d" % 
                     (self.env.now, len(self.riders), self.config["NUM_SIMULATED_DAYS"], len(self.riders)/self.config["NUM_SIMULATED_DAYS"]/self.num_of_vehicles))

    def generate_uniform_demand(self, random_time=False):
        """This method generates a uniformly distributed ride-demand over time and parking spots"""
        print("Generating demand")
        Rider.reset()
        trips_per_day = self.config["TVD"] * self.config["NUM_OF_VEHICLES"]
        num_of_trips = round(trips_per_day * self.config["NUM_SIMULATED_DAYS"])
        possible_start_times = self.config["NUM_SIMULATED_DAYS"] * 24 * 3600
        interval = possible_start_times // num_of_trips

        for i in range(num_of_trips):
            # get random origin and destination ps which are not the same
            origin_id = 0
            destination_id = 0
            while origin_id == destination_id:
                origin_id = random.randint(0, self.num_of_parking_spots-1)
                destination_id = random.randint(0, self.num_of_parking_spots-1)
            # get random start time, or constantly spaced start time
            if random_time:
                start_time = random.randint(0, possible_start_times)
            else:
                start_time = round(i * interval)
            
            user = Rider(
                self.env,
                self.config,
                self.data_interface,
                self.results,
                self.parking_spots[origin_id],
                self.parking_spots[destination_id],
                start_time)
            self.riders.append(user)
            user.start()

        logging.info("[%.0f] Number of trips planned is %d under %d day(s). TVD: %d" % 
                     (self.env.now, num_of_trips, self.config["NUM_SIMULATED_DAYS"], self.config["TVD"]))

    def run(self, until):
        print("Running simulation")
        self.env.process(self.periodic_save_state(60*15))  # Schedule the periodic save state
        self.env.run(until)
        print("remaining tasks: " + str(len(self.task_manager.tasks)))
        self.task_manager.log_remaining_tasks()
        self.results.close()
    
    def periodic_save_state(self, period):
        self.state = SimState(self.results)
        while True:
            self.state.time = self.env.now
            self.state.avg_battery_level = sum([vehicle.battery.level for vehicle in self.vehicles]) / self.num_of_vehicles
            self.state.num_bounties = len([task for task in self.task_manager.tasks if task.bounty])
            self.state.num_task = len(self.task_manager.tasks)
            
            # Calculate the Gini coefficient for the number of vehicles per parking spot
            vehicles_per_spot = [len(parking_spot.vehicles) for parking_spot in self.parking_spots]
            sorted_vehicles = sorted(vehicles_per_spot)
            cumulative_vehicles = np.cumsum(sorted_vehicles)
            sum_of_cumulative = cumulative_vehicles.sum()
            gini_numerator = sum_of_cumulative - (cumulative_vehicles[-1] / 2.0)
            gini_denominator = self.num_of_vehicles * len(vehicles_per_spot) / 2.0
            self.state.vehicle_distribution_gini = (gini_denominator - gini_numerator) / gini_denominator
            
            self.state.save_state()
            yield self.env.timeout(period)


if __name__ == "__main__":
    config_path = os.path.join("data", "config_testtown.json")
    with open(config_path) as f:
        config = json.load(f)
    
    config["NUM_OF_FLEET_SPECIALISTS"] = 2
        
    area_ploygon_path = os.path.join("data", "area", config["CITY"] + ".geojson")
    parking_spot_data_path = os.path.join("data", "parking_spots", config["CITY"] + ".csv")
    demand_data_path = os.path.join("data", "demand", "southampton" + ".csv")

    engine = RideSimulationEngine(config, parking_spot_data_path, area_ploygon_path, demand_data_path, verbose=1, fleet_maintenance=config["NUM_OF_FLEET_SPECIALISTS"], seed=42)
    
    start_time = time.time()  # Start timing
    engine.run(config["NUM_SIMULATED_DAYS"] * 3600 * 24)  # Run simulation for specified days
    end_time = time.time()  # End timing
    
    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"Time taken to run the simulation: {int(minutes)} minutes and {seconds:.2f} seconds")
