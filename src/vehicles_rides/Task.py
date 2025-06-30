class Task:
    id_count = -1
    header = [
        "task_id",
        "task_type",
        "bounty",
        "vehicle_id",
        "priority",
        "lon",
        "lat",
        "target_time",
        "created_time",
        "status",
        "bounty_time",
        "resolved_by",
        "resolved_time",
        "time_spent",
        "distance_driven",
        "time_open",
        "battery_in",
        "battery_out"
    ]
    
    def __init__(self, task_type, created_time, vehicle=None, bounty=False, priority=None, target_time=None, battery_in=None):
        self.next_id()
        self.id = Task.id_count
    
        self.type = task_type
        self.status = "active"  # or 'resolved', 'deleted'
        self.bounty = bounty
        self.bounty_time = None
        self.created_time = created_time
        self.resolved_time = None
        self.resolved_by = None
        self.vehicle = vehicle
        self.priority = priority        # Priority level of the task
        self.target_time = target_time
        self.battery_in = battery_in
        self.battery_out = None

        # storage for data collection
        self.store = dict.fromkeys(Task.header, "")

    # dynamic retrival of the task location
    @property
    def location(self):
        return self.vehicle.parking_spot.location
    
    @classmethod
    def reset(cls):
        Task.id_count = -1

    def next_id(cls):
        Task.id_count += 1

    @staticmethod
    def get_header():
        return ",".join(Task.header) + "\n"
    
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

