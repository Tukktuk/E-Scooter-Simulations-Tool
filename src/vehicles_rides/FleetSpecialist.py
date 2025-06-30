import logging
from geopy.distance import geodesic
from shapely.geometry import shape, Point
import json


class FleetSpecialist:
    id_count = -1

    def __init__(self, env, map, config, results, task_manager, start_time, starting_place, data_interface=None, focus_area_path=None):  # env, graph, ui, config, results
        self.next_id()
        self.id = FleetSpecialist.id_count

        self.env = env
        self.map = map
        self.config = config
        self.results = results 
        self.data_interface = data_interface
        self.task_manager = task_manager

        self.start_time = start_time     
        self.location = starting_place

        self.focus_area = None
        if focus_area_path != None:
            with open(focus_area_path, "r") as file:
                area = file.read()
            area_dict = json.loads(area)
            self.focus_area = shape(area_dict)
        
        # Work planing
        self.planed_tasks = []
        self.next_task = None 
        self.busy = False     # on the way, working, planing
        self.optimize = False

        # Parameters
        self.DRIVING_SPEED = self.config["AVG_FLEET_SPECIALIST_TRAVEL_SPEED"] / 3.6  # m/s
        self.TASK_RESOLUTION_TIME_SINGLE = self.config["TIME_PER_SWAP_SINGLE"]
        self.TASK_RESOLUTION_TIME_MULTIPLE = self.config["TIME_PER_SWAP_MULTIPLE"]
        self.REFILL_VAN_BATTERIES_TIME = self.config["REFILL_VAN_BATTERIES_TIME"]
        self.VAN_BATTERY_CAPACITY = self.config["VAN_BATTERY_CAPACITY"]
        
        # Management Parameters
        #self.shift_end = None
        #self.work_area = None
        #self.task_types = Set()

        # Van attributes
        self.num_batteries = self.VAN_BATTERY_CAPACITY

        # Current task attributes
        self.task_start_time = 0
        self.task_time_spent = 0
        self.task_distance_driven = 0
        self.battery_in = 0
        self.battery_out = 1

    
    @classmethod
    def reset(cls):
        FleetSpecialist.id_count = -1

    def next_id(self):
        FleetSpecialist.id_count += 1

    def calculate_distance(self, destination):
        """ Calculates distances to destination
        Method used: Geographic Euclidian distance"""
        distance = geodesic((self.location.lat, self.location.lon), (destination.lat, destination.lon)).meters
        return distance

    def drive_to(self, destination):
        distance = self.map.get_drive_distance(self.location, destination)
        self.task_distance_driven = distance
        travel_time = round(distance / self.DRIVING_SPEED)
        logging.info("[%.0f] Fleet Specialist %d is driving from location [%.4f, %.4f]" % (self.env.now, self.id, self.location.lon, self.location.lat))
        yield self.env.timeout(travel_time)  # Simulate travel time
        logging.info("[%.0f] Fleet Specialist %d arrived at location [%.4f, %.4f]" % (self.env.now, self.id, destination.lon, destination.lat))
        self.location = destination

    def resolve_task(self):
        # Working... (Task resolution time, longer for isolated tasks / first task in a cluster)
        self.next_task.status = "pending"
        if self.task_distance_driven != 0:
            yield self.env.timeout(self.TASK_RESOLUTION_TIME_SINGLE)
        else:
            yield self.env.timeout(self.TASK_RESOLUTION_TIME_MULTIPLE)
            
        self.next_task.battery_out = self.next_task.vehicle.battery.level
        # update state    
        self.num_batteries -= 1
        if self.next_task.vehicle is not None:
            self.battery_in = self.next_task.vehicle.battery.level
        if self.data_interface is not None:
            self.data_interface.resolve_task(self.next_task)
        else:
            self.task_manager.remove_task(self.next_task)
        self.task_time_spent = self.env.now - self.task_start_time
        self.next_task.resolved_time = self.env.now
        self.next_task.status = "resolved"
        self.task_manager.save_task(self.next_task, self, self.env.now)
        self.next_task.vehicle.resume_idle()

        logging.info("[%.0f] Task %d resolved by swapping to a full battery at location [%.4f, %.4f]" % (self.env.now, self.next_task.id, self.next_task.location.lon, self.next_task.location.lat))

    
    def schedule(self):
        self.env.process(self.work_flow())
    
    def init_fleet_specialist(self):
        # waits until its the hour to initialize user
        yield self.env.timeout(self.start_time)
        self.task_manager.add_fleet_specialist(self)
        logging.info("[%.0f] Fleet Specialist %d initialized at location [%.4f, %.4f]" % (self.env.now, self.id, self.location.lon, self.location.lat))

    def work_flow(self):

        # 0. Init at origin
        yield self.env.process(self.init_fleet_specialist())
        
        log_inactivity = True
        # TODO while time still in FS shift
        while True:
            while self.num_batteries > 0:
            # 1. check if there are any tasks 
                if self.task_manager.get_available_tasks():
                    log_inactivity = True
                    # 2. Find the next task
                    self.plan_next_task()
                    self.task_start_time = self.env.now
                    # 3. Drive to next task
                    yield self.env.process(self.drive_to(self.next_task.location))
                    
                    
                    # 4. Check if task is still there
                    # Proceed if:
                    # - task is not already resolved
                    # - task location is the same as current location (has moved)
                    # - and if vehicle is not riding
                    if self.next_task.status == "active" and self.next_task.location == self.location and self.next_task.vehicle.status != "riding":
                        # 5. Reslove task
                        self.next_task.vehicle.interrupt_idle_process("Idle interrupted due to Battery Swap")
                        yield self.env.process(self.resolve_task())
                    else:
                        logging.info("[%.0f] Fleet specilist %d missed task." % (self.env.now, self.id))
                    # 6. Redo: Plan next task 
                else:
                    if log_inactivity:
                        logging.info("[%.0f] Fleet Specialist %d is waiting for tasks" % (self.env.now, self.id))
                        log_inactivity = False
                    yield self.env.timeout(30)  # Wait for 30 seconds if no tasks are available
            # refill batteries at WH
            yield self.env.process(self.refill_batteries())

    def refill_batteries(self):
        """ Simplified process of refilling batteries at warehouse """
        logging.info("[%.0f] Fleet Specialist %d is out of batteries, will go and refill att WH" % (self.env.now, self.id))
        yield self.env.timeout(self.REFILL_VAN_BATTERIES_TIME) # it takes 40 min to drive to WH and refill batteries
        self.num_batteries = self.VAN_BATTERY_CAPACITY
        logging.info("[%.0f] Fleet Specialist %d has now replenished batteries" % (self.env.now, self.id))

    def plan_next_task(self):
        # Get tasks that are not currently planned
        available_tasks = self.task_manager.get_available_tasks()
        # focus on tasks in certain area
        if self.focus_area:
            # Filter tasks based on the focus area polygon
            tasks_in_focus_area = {task for task in available_tasks if self.focus_area.contains(Point(task.location.lon, task.location.lat))}
            # if there are none in focus area, go outside.
            if tasks_in_focus_area:
                available_tasks = tasks_in_focus_area

        if not self.planed_tasks:
            if self.optimize:
                # Find the nearest task based on driving distance and plan it
                nearest_task = self.find_nearest_task_drive(available_tasks)
            else:
                # Find the nearest task based on geographic distance and plan it
                nearest_task = self.find_nearest_task(available_tasks)
            self.planed_tasks.append(nearest_task)

        self.next_task = self.planed_tasks.pop()

    def find_nearest_task(self, tasks):
        # Find the nearest task based on geographic distance
        return min(tasks, key=lambda task: self.calculate_distance(task.location))
    """
    Complexity improvments
    1. Sorted Lists with Binary Search: Using two sorted lists (one sorted by latitude and the other by longitude) could be a practical solution. You can use binary search for efficient querying and insertion. Python's bisect module can help manage these operations efficiently. This approach allows relatively quick updates and reasonably efficient queries, especially if you optimize the search by checking nearby elements after a binary search to refine which task is closest.
    2. Grid Hashing (Spatial Hashing): This method involves dividing the space into a grid and assigning tasks to buckets based on their coordinates. This can significantly reduce the search space for queries, as you only need to check the bucket corresponding to the query location and its adjacent buckets. Insertions and deletions are straightforward as they involve adding or removing tasks from these buckets. This method can be particularly effective if the tasks are somewhat evenly distributed across the area.
    Given the equal frequency of updates and queries, grid hashing might offer the best balance between ease of updates and efficient querying. It simplifies the management of dynamic datasets and can provide fast access to nearby tasks without the overhead of maintaining tree structures or multiple sorted lists. This approach scales well with the number of tasks and can handle frequent changes in the dataset efficiently.
    """
    def find_nearest_task_drive(self, tasks):
        # Find the nearest task based on driving distance
        return min(tasks, key=lambda task: self.map.get_drive_distance(self.location, task.location)) 
