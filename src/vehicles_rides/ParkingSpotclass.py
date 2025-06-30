import math

class ParkingSpot:
    id_count = -1
    def __init__(self, location):
        self.next_id()
        self.id = ParkingSpot.id_count
        self.location = location
        self.vehicles = []  # list to store vehicles parked at this spot
        self.neighbor_parking_spots = []
        self.num_vehicles_cap = math.inf  # Maximum number of vehicles
    
    @classmethod
    def reset(cls):
        ParkingSpot.id_count = -1

    def next_id(self):
        ParkingSpot.id_count += 1
    
    def __str__(self) -> str:
        """Prints ps in one line """
        return f"Parkingspot-id: {self.id:<5} Location : {self.location} "

    def add_vehicle(self, vehicle):
        self.vehicles.append(vehicle)

    def remove_vehicle(self, vehicle):
        self.vehicles.remove(vehicle)

    def pick_available_vehicle(self):
        """Tries to pick a vehicle at the parkingspot. Returns vehicle if possible, else None."""
        for vehicle in self.vehicles:
            if vehicle.available:
                return vehicle
        return None

