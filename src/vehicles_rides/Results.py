import os
import datetime
import json
import logging
from Ride import Ride
from Task import Task
from SimState import SimState


class Results:
    def __init__(self, config, verbose=1):

        self.vehicle_rides_name = "vehicle_rides.csv"
        self.task_data_name = "task_data.csv"
        self.state_records_name = "state_records.csv"  # Added for state records

        self.config_name = "config.json"
        self.log_name = "app.log"
        self.verbose = verbose

        self.mkpath()
        self.mkdir()
        self.setup_log()
        self.save_config(config)
        self.open_user_rides()
        self.open_tasks()
        self.open_state_records()  # Added to open state records file


    def mkpath(self):
        cwd = os.getcwd()
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = os.path.join(cwd, "results", now)

    def mkdir(self):
        os.mkdir(self.path)

    def setup_log(self):
        # Clear existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        if self.verbose == 0:
            # Level 0: No logging
            logging.disable(logging.CRITICAL)  # Disable all logging
        elif self.verbose == 1:
            # Level 1: Logging to file only
            logging.basicConfig(
                filename=os.path.join(self.path, self.log_name), 
                filemode="w", 
                format="%(message)s", 
                level=logging.INFO
            )
        elif self.verbose == 2:
            # Level 2: Logging to both file and terminal
            logging.basicConfig(
                filename=os.path.join(self.path, self.log_name), 
                filemode="w", 
                format="%(message)s", 
                level=logging.INFO
            )
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

    def open_user_rides(self):
        self.user_trips = open(os.path.join(self.path, self.vehicle_rides_name), "a")
        self.user_trips.write(Ride.get_header())

    def add_user_trip(self, user_trip):
        self.user_trips.write(user_trip.get_data())

    def close_user_trips(self):
        self.user_trips.close()

    def save_config(self, config):
        with open(os.path.join(self.path, self.config_name), "w") as f:
            json.dump(config, f)

    def open_tasks(self):
        self.task_data_file = open(os.path.join(self.path, self.task_data_name), "a")
        self.task_data_file.write(Task.get_header())  # Changed from Ride.get_header()

    def add_task(self, task):
        self.task_data_file.write(task.get_data())  # Changed to write task data

    def close_tasks(self):
        self.task_data_file.close()

    def open_state_records(self):  # Added to open state records file
        self.state_records_file = open(os.path.join(self.path, self.state_records_name), "a")
        self.state_records_file.write(SimState.get_header())  # Changed from Ride.get_header()

    def add_state_record(self, state_data):  # Added to write state records
        self.state_records_file.write(state_data.get_data())

    def close_state_records(self):  # Added to close state records file
        self.state_records_file.close()

    def close(self):
        self.close_user_trips()
        self.close_tasks()
        self.close_state_records()  # Added to close state records file
