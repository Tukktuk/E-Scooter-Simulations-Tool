class Ride:
    id_count = -1
    header = [
        "vehicle_id",
        "user_id",
        "time_departure",
        "time_target",
        "status",
        "time_ride",
        "origin_parking_spot",
        "destination_parking_spot",
        "origin_lon",
        "origin_lat",
        "destination_lon",
        "destination_lat",
        "ride_distance",
        "battery_in",
        "battery_out"
    ]

    def __init__(self):
        self.next_id()
        self.id = Ride.id_count

        self.store = dict.fromkeys(Ride.header, "")

    @classmethod
    def reset(cls):
        Ride.id_count = -1

    def next_id(self):
        Ride.id_count += 1

    @staticmethod
    def get_header():
        return ",".join(Ride.header) + "\n"

    def get_data(self):
        return ",".join(map(str, self.store.values())) + "\n"

    def set(self, key, value, digits=2):
        if key in self.store.keys():
            if isinstance(value, bool):
                value = int(value)
                value = str(value)
            elif isinstance(value, int):
                value = str(value)
            elif isinstance(value, float):
                if digits == 0:
                    value = int(value)
                else:
                    value = round(value, digits)
                value = str(value)
            self.store[key] = value
        else:
            raise BaseException
