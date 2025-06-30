class Location:
    def __init__(self, lon=None, lat=None, map=None):
        self.lon = lon
        self.lat = lat
        self.drive_node = None
        self.ride_node = None
        if map is not None: 
            self.drive_node = map.get_node_from_location("drive", self)
            self.ride_node = map.get_node_from_location("bike", self)
            

    def get_loc(self):
        return [self.lon, self.lat]
    
    def __str__(self) -> str:
        return "[%.4f, %.4f]" % (self.lon, self.lat)


