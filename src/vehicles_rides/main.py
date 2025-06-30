import json
import os
import time
from Map import Map
from core_classes.vehicles_rides.Simulationclass import RideSimulationEngine
import copy  # Import the copy module

config_path = os.path.join("data", "config.json")
with open(config_path) as f:
    config = json.load(f)


area_ploygon_path = os.path.join("data", "area", config["CITY"] + ".geojson")
parking_spot_data_path = os.path.join("data", "parking_spots", config["CITY"] +".csv")
demand_data_path = os.path.join("data", "demand", config["CITY"] + ".csv")

print("Setting up map")
map = Map(area_ploygon_path)
print("Initilizing parking spots")
parking_spots, map = RideSimulationEngine.load_parking_spots(parking_spot_data_path, map)
parking_spots = RideSimulationEngine.find_parking_spot_neighbors(config, parking_spots, map)


# Run simulations with different numbers of fleet specialists   
for num_specialists in range(0, 8):
    print("Running simulation with", num_specialists, "fleet specialists")
    config["NUM_OF_FLEET_SPECIALISTS"] = num_specialists  # Set number of fleet specialists in config

    # Create a deep copy of parking_spots for use in this iteration
    parking_spots_copy = copy.deepcopy(parking_spots)

    engine = RideSimulationEngine(config, parking_spots_copy, map, demand_data_path, verbose=1, fleet_maintenance=config["NUM_OF_FLEET_SPECIALISTS"], seed=42)

    start_time = time.time()  # Start timing
    engine.run(config["NUM_SIMULATED_DAYS"] * 3600 * 24)  # Run simulation for specified days
    end_time = time.time()  # End timing

    elapsed_time = end_time - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    print(f"Time taken to run the simulation: {int(minutes)} minutes and {seconds:.2f} seconds")
