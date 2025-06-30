import logging

class Battery:
    id_count = -1
    capacity = 1
    def __init__(self, discharge_rate_ride, discharge_rate_idle, level=1.0, charge_rate=None):
        self.next_id()
        self.id = Battery.id_count

        self.charge_rate = charge_rate  # energy per time
        self.discharge_rate_ride = discharge_rate_ride / 1000  # energy per m ride
        self.discharge_rate_idle = discharge_rate_idle / 3600  # energy per s idle
        self.level = level
        self.max_level = 1.0

    @classmethod
    def reset(cls):
        Battery.id_count = -1

    def next_id(self):
        Battery.id_count += 1

    def charge(self, duration):
        self.level = min(self.capacity, self.level + self.charge_rate * duration)

    def discharge_ride(self, distance):
        self.level = max(0, self.level - self.discharge_rate_ride * distance)
    
    def discharge_idle(self, time):
        self.level = max(0, self.level - self.discharge_rate_idle * time)

    def total_charge_time(self):
        return (self.capacity - self.level) / self.charge_rate
