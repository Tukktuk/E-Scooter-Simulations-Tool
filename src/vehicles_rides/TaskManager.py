class TaskManager:
    def __init__(self, results):
        self.results = results
        self.fleet_specialists = set()  # Set of fleet specialists
        self.tasks = set()              # Set of Task objects
        
    def add_fleet_specialist(self, fleet_specialist):
        """ Creates a fleet specialist and deploys to city """
        self.fleet_specialists.add(fleet_specialist)

    def add_task(self, task):
        """ Adds a task to the task manager """
        self.tasks.add(task)

    def remove_task(self, task):
        """ Removes a task from the task manager """
        self.tasks.remove(task)

    def get_available_tasks(self):
        """ Returns tasks that are not currently planned and for vehicles that are not riding"""
        return self.tasks - set(task for task in self.tasks if task.vehicle.status == "riding" or task.status == "pending")

    def log_remaining_tasks(self):
        """ logs the remaining task to log file """
        for task in self.tasks:
            self.save_task(task)


    def save_task(self, task, fleet_specialist=None, time_now=None):
        task.set("task_id", task.id)
        task.set("task_type", task.type)
        task.set("bounty", task.bounty)
        task.set("bounty_time", task.bounty_time)
        task.set("vehicle_id", None if task.vehicle is None else task.vehicle.id)
        task.set("priority", task.priority)
        task.set("lon", task.location.lon, 5)
        task.set("lat", task.location.lat, 5)
        task.set("target_time", task.target_time,0)
        task.set("created_time", task.created_time,0)
        task.set("status", task.status)
        task.set("resolved_by", None if fleet_specialist is None else fleet_specialist.id)
        task.set("resolved_time", None if time_now is None else time_now)
        task.set("time_spent", None if time_now is None else time_now - fleet_specialist.task_start_time)
        task.set("distance_driven", None if fleet_specialist is None else fleet_specialist.task_distance_driven,0)
        task.set("time_open",  None if time_now is None else time_now - task.created_time)
        task.set("battery_in", task.battery_in, 3)
        task.set("battery_out", task.battery_out, 3)

        self.results.add_task(task)
    # Additional methods for managing tasks, specialists, etc. can be added here


