import osmnx as ox
import matplotlib.pyplot as plt
import json
from shapely.geometry import shape
from geopy.distance import geodesic, distance
from functools import lru_cache
from scipy.spatial import KDTree
import numpy as np
import pandas as pd
from pyproj import Proj

from Location import Location
from ParkingSpotclass import ParkingSpot

class Map:
    """
    This class is used to calculate distances between locations.
    It uses the osmnx library to calculate distances.
    """
    def __init__(self, area_ploygon_path):
        # init graphs, get geojson from file, 
        with open(area_ploygon_path, "r") as file:
            area = file.read()
        area_dict = json.loads(area)
        polygon = shape(area_dict)
        # download graph from polygon
        self.graph_drive = ox.graph_from_polygon(polygon, network_type='drive')
        self.graph_bike = ox.graph_from_polygon(polygon, network_type='bike')
        
        # Handling parking spots
        self.parking_spots = None
        self.kdtree = None
        self.proj = None  # Projection is not initialized until create_kdtree is called

    def create_kdtree(self, parking_spots):
        """
        Create a KDTree for parking spots using UTM coordinates, initializing the projection based on the first parking spot.

        Args:
            parking_spots (list of ParkingSpot): The list of parking spots to use for creating the KDTree.
        """
        if not parking_spots:
            raise ValueError("Parking spots list is empty, cannot initialize KDTree or projection.")

        # Initialize the projection using the longitude of the first parking spot
        first_lon = parking_spots[0].location.lon
        self.proj = self.get_utm_proj_from_lon(first_lon)

        # Convert parking spots to UTM coordinates using the newly set projection
        utm_locations = [self.latlon_to_utm(ps.location.lat, ps.location.lon) for ps in parking_spots]
        self.kdtree = KDTree(utm_locations)

    def latlon_to_utm(self, lat, lon):
        """Convert latitude and longitude to UTM coordinates."""
        if not self.proj:
            raise Exception("Projection not initialized. Please call create_kdtree first.")
        return self.proj(lon, lat)

    @staticmethod
    def get_utm_proj_from_lon(lon):
        """
        Determine the UTM projection based on longitude.

        Args:
            lon (float): Longitude based on which to determine the UTM zone.

        Returns:
            Proj: A Proj object configured for the appropriate UTM zone.
        """
        zone = int((lon + 180) / 6) + 1
        return Proj(proj='utm', zone=zone, ellps='WGS84', preserve_units=False)

    def find_nearby_parking_spot_indices(self, position, walk_radius):
        """ Finds indices of parking spots within the walk_radius for a given position using the KDTree.

        Args:
            position (Location): The location to evaluate.
            walk_radius (float): The radius within which to find neighboring parking spots in meters.

        Returns:
            list: A list of indices of parking spots within the walk radius.
        """
        # Convert the position to UTM coordinates
        utm_position = self.latlon_to_utm(position.lat, position.lon)
        # Query the KDTree for indices of neighbors within walk_radius
        indices = self.kdtree.query_ball_point(utm_position, walk_radius)
        return indices

    def find_nearest_parking_spot(self, location):
        location_utm = self.latlon_to_utm(location.lat, location.lon)
        _, index_list = self.kdtree.query([location_utm])  # Use underscore to ignore the distance
        return index_list[0]

    def calculate_distance(self, origin, destination):
        """ Calculates distances to destination
        Method used: Geographic Euclidian distance"""
        return geodesic((origin.lat, origin.lon), (destination.lat, destination.lon)).meters
         

    @lru_cache(maxsize=4096*2*2)  # Adjust maxsize as needed
    def get_bike_ride_distance(self, origin_location, destination_location):
        # get nodes
        origin_node = self.get_node_from_location("bike", origin_location)
        destination_node = self.get_node_from_location("bike", destination_location)
        # get route
        route = ox.routing.shortest_path(self.graph_bike, origin_node, destination_node, weight='length')

        if route is None:
            return self.calculate_distance(origin_location, destination_location) * 1.2
        # get route length
        route_length = self.get_route_length(route, "bike")
        return route_length
    
    def get_route_length(self, route, route_type=None):
        # Convert the route to a GeoDataFrame
        # if route is empty, return 0
        if len(route) <= 1:
            return 0

        if route_type == "bike":
            route_gdf = ox.routing.route_to_gdf(self.graph_bike, route)
        else:
            route_gdf = ox.routing.route_to_gdf(self.graph_drive, route)
        # Calculate the total length of the route, 
        # makes a gdf of the route and sums the length TODO is this efficient??
        route_length = route_gdf['length'].sum()    
        return route_length
    
    # def get_route_length(self, route, route_type=None):
    #     if len(route) <= 1:
    #         return 0

    #     total_length = 0
    #     graph = self.graph_bike if route_type == "bike" else self.graph_drive

    #     for i in range(len(route) - 1):
    #         edge_data = graph.get_edge_data(route[i], route[i+1])
    #         if edge_data:
    #             # Summing up the lengths of all edges in the route
    #             total_length += edge_data[0].get('length', 0)  # Using the first edge if multiple edges exist between nodes

    #     return total_length
    
    @lru_cache(maxsize=4096*2*2)  # Adjust maxsize as needed
    def get_drive_distance(self, origin_location, destination_location):
        # get nodes
        origin_node = self.get_node_from_location("drive", origin_location)
        destination_node = self.get_node_from_location("drive", destination_location)
        
        # Check if nodes are in the graph
        if origin_node not in self.graph_drive or destination_node not in self.graph_drive:
            raise Exception(f"One of the nodes is not in the graph: Origin {origin_node}, Destination {destination_node}")

        # get route
        try:
            route = ox.routing.shortest_path(self.graph_drive, origin_node, destination_node, weight='length')
        except Exception as e:
            raise Exception(f"Failed to find route: {e}")
        
        if route is None:
            return self.calculate_distance(origin_location, destination_location) * 1.4
        # get route length
        try:
            route_length = self.get_route_length(route)
        except Exception as e:
            print("origin location: ", origin_location,"destination location: ", destination_location)
            print("origin: ", origin_node, "destination: ", destination_node)
            raise Exception(f"Failed to calculate route length: {e}")

        return route_length

    def get_node_from_location(self, graph, location):
        """
        Retrieve the nearest node in the specified graph for a given location.

        Args:
        graph (networkx.Graph): The graph from which to find the nearest node.
        location (Location): The location object containing longitude and latitude.

        Returns:
        int: The nearest node identifier.
        """
        if graph == "drive":
            if location.drive_node is not None:
                return location.drive_node
            return ox.distance.nearest_nodes(self.graph_drive, location.lon, location.lat)
        elif graph == "bike":
            if location.ride_node is not None:
                return location.ride_node
            return ox.distance.nearest_nodes(self.graph_bike, location.lon, location.lat)
    

if __name__ == "__main__":
    area_file_path = "data/area/test.geojson"
    map = Map(area_file_path)

    parking_spots = [ParkingSpot(Location(18.00002, 59.33405)),
                     ParkingSpot(Location(18.00020, 59.33406)),
                     ParkingSpot(Location(17.59999, 59.33403)),
                     ParkingSpot(Location(17.59998, 59.33402)),
                     ParkingSpot(Location(18.01044, 59.33436))]

    map.create_kdtree(parking_spots)

    index = map.find_nearest_parking_spot(Location(18.0656561744064, 59.34141938775965))
    print(index)

    # Get the node for the parking spot
    node_id = map.get_node_from_location("drive", parking_spots[4].location)
    print("Node ID:", node_id)

    # Plot the graph
    fig, ax = ox.plot_graph(map.graph_drive, show=False, close=False)
    # Highlight the node
    node_x, node_y = map.graph_drive.nodes[node_id]['x'], map.graph_drive.nodes[node_id]['y']
    ax.scatter(node_x, node_y, c='red', s=100, label='Parking Spot Node')
    plt.legend()
    plt.show()
