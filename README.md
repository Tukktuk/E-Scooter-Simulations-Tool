# VOI Operations Simulation Tool

This code base is a simulation model built as part of the master thesis of Otto Pagels Fick in the spring of 2024. The goal of the project was to introduce simulation as a tool for operation analysis and to establish a foundation for its use within the organization. The tool was tested on the optimization problem concerning the number of in-field specialists versus scooter availability and demand fulfillment. This problem serves as a perfect example of when simulation is a suitable method, as it depends on system-wide effects that are very difficult to study outside a controlled environment.

## Structure of the Code

### Simulation Model

The model is built of classes representing different entities in the VOI operations environment (such as [Vehicle](core_classes/vehicles_rides/Vehicleclass.py), [Fleet Specialist](core_classes/vehicles_rides/FleetSpecialist.py), and so on) and a [simulation engine](core_classes/vehicles_rides/RideSimulationclass.py) which, after setting up the model, drives the simulation forward. The simulation engine is built with Simpy, a library based on Discrete Event Simulation widely used in scientific studies.

### Other Classes

In the `vehicle_rides` directory, there are classes that support the simulation:

- `Datainterface.py` manages state changes with wider implications. A ride is initiated by the rider, but the data interface ensures changes are made to other parts of the system.
- `FMSimulationEngine.py` is an engine created only to simulate the task management side of operations. It does not involve any rides, just tasks and fleet specialists handling them. NB. This code is currently broken. It does not load the environment correctly. This can be fixed if one wants to study only the task fullfilment part of the operations.
- `plot_results.py` reads output data from a directory and plots the results (more details below).
- `profiler.py` times the execution of different functions.
- `Results.py` creates the output of the simulation and saves it in CSV files in the results directory.

### Data Directory

The data directory holds all the necessary inputs for the simulation model. They include:

- **Areas**: Contains geojson files outlining the operational area for each VOI city. The area is used to download a map of the city, which in turn is used to calculate distances and find the nearest scooter.
  - **Fleet specialist areas**: A subdirectory used if focus areas should be given to the fleet specialists deployed in the simulation.
- **Rides**: Contains historical ride data for each city, used as a proxy for demand in the simulation environment. The demand needs to have three attributes: start time, starting position, and destination position. This means demand can be generated with any pattern as long as these three attributes are provided. Using historical data is a simple way of capturing real-world complexity.
- **Parking spots**: Using a MPZ setup simplifies the simulation significantly. Parking spots are a mandatory part of the simulation input.
- **Tasks**: Used only by `FMSimulationEngine.py`.
- **config.json**: Holds all other inputs for the simulation, including riding speed and swap threshold.

### How to Get the Data in the Required Format

Go to Snowflake and use the queries found in the file `queries.sql`. Download the results as CSV files, rename them, and place them in the appropriate data directory. The file names must match the city name in the config file.

## How to Run a Simulation

By using `RideSimulation.py` as the main script, a simulation can easily be run. Read the comments at the end of the file (after line 236) and ensure all input data is in place.

## How to Run Experiments

`main.py` shows the experiment run in the master thesis. The simulation is run similarly to the simulation described above but with a parameter change for every run (see the for-loop on line 25). Additionally, since the map and parking spots are the same for all simulation runs, they are loaded once for all simulations. This saves a lot of time as setting up these parts can be very time-consuming for large cities.

## How to Treat the Results

### Structure of the Results

All results are saved in the results directory, where you will find one directory for each simulation. The directory contains four files: `config.json`, `task_data.csv`, `vehicle_rides.csv`, and `state_records.csv`.

- **config.json**: Contains the configuration parameters used during the simulation. Note that this file only contains the input stored in the config file. If you change the ride file for a city to reflect a different setting, it may become unclear what demand was used as input for the specific simulation result.
- **task_data.csv**: Shows information regarding each task in the simulation environment, including attributes related to the fleet specialist's resolution of the task, such as time spent and distance traveled. Tasks are saved when they are successfully resolved. All unresolved tasks are "flushed" at the end of the simulation.
- **vehicle_rides.csv**: Contains all completed rides and unfulfilled demand that could not be converted to a ride due to no nearby scooter. Rides are saved after the ride. Rides ongoing when the simulation ends are not saved.
- **state_records.csv**: is an attempt to make the data analysis easier. It has not been used and can be removed.

### Ploting the Results 
**plot_results.py** has a bunch of functions which will take the output of an experiment (several simulations with varying inputs) and plot in different types of graphs. The code asumes the results are gatherd in a directory. See the **Experiments** directory for some examples. 

## Comments

The structure of the code can, in some parts, seem illogical. It is hard to determine where functions responsible for larger state changes (rides, for example) are most logically placed. In some cases, the requirements of the Simpy library have dictated these decisions.

Furthermore, the code can be significantly sped up. Especially the A to B distance calculations in the map class can be sped up by using precomputed shortest paths. See [CityScope/AutonomousMicroMobility](https://github.com/CityScope/AutonomousMicroMobility) for inspiration. The nearest task search can also be optimized.

## Who do I ask when I need help?
Rahman Amandius <rahman.amandius@voiapp.io> is the current owner of the tool at VOI. If you buy me a coffee I would gladly guide you through the code as well.

All the best,
Otto Pagels-Fick
<otto.pagels.fick@gmail.com>
