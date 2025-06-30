class SimState:
    header = [
        "time",
        "avg_battery_level",
        "num_bounties",
        "num_task",
        "vehicle_distribution_gini"
    ]
    
    def __init__(self, results):
        self.results = results
        self.time = 0
        self.avg_battery_level = 0
        self.num_bounties = 0
        self.num_task = 0
        self.vehicle_distribution_gini = 0

        # storage for data collection
        self.store = dict.fromkeys(SimState.header, "")

    @staticmethod
    def get_header():
        return ",".join(SimState.header) + "\n"
    
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

    def save_state(self):
        self.set("time", self.time)
        self.set("avg_battery_level", self.avg_battery_level, 2)
        self.set("num_bounties", self.num_bounties, 0)
        self.set("num_task", self.num_task, 0)
        self.set("vehicle_distribution_gini", self.vehicle_distribution_gini, 3)

        self.results.add_state_record(self)

