import os
import pandas as pd
import matplotlib.pyplot as plt
import json
import matplotlib.dates as mdates
import numpy as np
import folium
from folium.plugins import PolyLineTextPath
from folium.map import LayerControl
from datetime import timedelta

def get_result_dirs(base_path="results"):
    dirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    # Sort directories by the number of fleet specialists
    dirs.sort(key=lambda x: json.load(open(os.path.join(x, 'config.json'), 'r'))['NUM_OF_FLEET_SPECIALISTS'])
    return dirs

def read_data(directory, file):
    data_path = os.path.join(directory, file)
    return pd.read_csv(data_path)

def aggregate_data(data, attribute, interval):
    # Convert the attribute to float first to clear any existing format issues
    data[attribute] = pd.to_datetime(data[attribute], unit='s', origin=pd.Timestamp('2024-05-06'))
    # Drop rows where the datetime conversion resulted in NaT (not a time)
    data.dropna(subset=[attribute])
    data.set_index(attribute, inplace=True)
    return data.resample(interval).count() 

def read_and_aggregate_data(directory, file, attribute, interval):
    data = read_data(directory, file)
    # Convert seconds to datetime, setting origin to a specific date
    data[attribute] = pd.to_datetime(data[attribute], unit='s', origin=pd.Timestamp('2024-05-06'))
    # Drop rows where the datetime conversion resulted in NaT (not a time)
    data.dropna(subset=[attribute])
    return data.resample(interval).count() 

def plot_task_completion_over_time(directories, interval='1h'):
    plt.figure(figsize=(12, 6))

    for directory in directories[1:]:  # Skip the first directory as no tasks are completed there
        
        # Read data
        data = read_data(directory, 'task_data.csv')
        
        # Aggregate completed tasks data
        data_tasks = data
        aggregated_task_data = aggregate_data(data_tasks, 'resolved_time', interval)
        aggregated_task_data = aggregated_task_data[:-1]  # Exclude the last interval if it's not complete
        
        # Read the number of fleet specialists from the config JSON file in the directory
        config_path = os.path.join(directory, 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        num_of_fleet_specialists = config['NUM_OF_FLEET_SPECIALISTS']
        
        # Plot completed tasks
        plt.plot(aggregated_task_data.index, aggregated_task_data['task_id'], label=f'FS: {num_of_fleet_specialists}')  # Adjusted label to include fleet specialists

    plt.xlabel('Date')
    plt.ylabel(f'Number of Tasks Completed (over {interval} intervals)')
    plt.title(f'Task Completions Over Time \n {config["CITY"]}, simulation time: {config["NUM_SIMULATED_DAYS"]} days')
    plt.legend(title='Task Status')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def process_task_data(cur_dir, origin_date, window_size):
    df = pd.read_csv(os.path.join(cur_dir, "task_data.csv"))
    events = []
    for _, row in df.iterrows():
        events.append((row['created_time'], 1))  # Task creation increases open tasks
        if pd.notna(row['resolved_time']):
            events.append((row['resolved_time'], -1))  # Task resolution decreases open tasks

    events_df = pd.DataFrame(events, columns=['time', 'change'])
    events_df = events_df.sort_values('time')
    # Convert time from seconds to datetime
    events_df['time'] = pd.to_datetime(events_df['time'], unit='s', origin=origin_date)
    events_df.set_index('time', inplace=True)

    # Calculate the rolling average of open tasks
    events_df['open_tasks'] = events_df['change'].cumsum()
    events_df['rolling_avg'] = events_df['open_tasks'].rolling(window=window_size).mean()

    return events_df

def plot_open_tasks_over_time(directories, window_size=100):
    plt.figure(figsize=(10, 5))
    origin_date = pd.Timestamp('2024-05-06')  # Define the origin date

    for cur_dir in directories:
        events_df = process_task_data(cur_dir, origin_date, window_size)

        # Read the number of fleet specialists from the config JSON file in the directory
        config_path = os.path.join(cur_dir, 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        num_of_fleet_specialists = config['NUM_OF_FLEET_SPECIALISTS']
        plt.plot(events_df.index, events_df['rolling_avg']) # , label=f'FS: {num_of_fleet_specialists}'

    plt.gca().xaxis.set_major_locator(mdates.DayLocator())  # Set major ticks to daily
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Format date
    plt.xlabel('Date')
    plt.ylabel('Open Tasks')
    plt.title(f'Open Tasks Over Time (rolling average, window size: {window_size} ) \n {config["CITY"]}, simulation time: {config["NUM_SIMULATED_DAYS"]} days')
    #plt.legend(title='Number of Fleet Specialists')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def plot_rides_over_time(directories, interval='1h', include_unfullfiled_demand=False):
    plt.figure(figsize=(12, 6))

    # plot reference All demand
    data = read_data(directories[0], 'vehicle_rides.csv')
    aggregated_demand_data = aggregate_data(data, 'time_departure', interval)
    aggregated_demand_data = aggregated_demand_data[:-1]  # Exclude the last interval if it's not complete
    plt.plot(aggregated_demand_data.index, aggregated_demand_data['user_id'], label='Total Demand')  # Adjusted label to include fleet specialists

    for directory in directories:
        
        # Read data
        data = read_data(directory, 'vehicle_rides.csv')
        
        # Aggregate completed rides data
        data_rides = data[data['status'] == 'completed']
        aggregated_ride_data = aggregate_data(data_rides, 'time_departure', interval)
        aggregated_ride_data = aggregated_ride_data[:-1]  # Exclude the last interval if it's not complete
        

        if include_unfullfiled_demand:
            # Aggregate unfulfilled rides data
            data_unfulfilled = data[data['status'] == 'unfullfilled']
            aggregated_unfulfilled_data = aggregate_data(data_unfulfilled, 'time_departure', interval)
            aggregated_unfulfilled_data = aggregated_unfulfilled_data[:-1]  # Exclude the last interval if it's not complete
            # Plot unfulfilled rides
            plt.plot(aggregated_unfulfilled_data.index, aggregated_unfulfilled_data['user_id'], label='Unfulfilled Rides')

        # Read the number of fleet specialists from the config JSON file in the directory
        config_path = os.path.join(directory, 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        num_of_fleet_specialists = config['NUM_OF_FLEET_SPECIALISTS']
        
        # Plot completed rides
        plt.plot(aggregated_ride_data.index, aggregated_ride_data['vehicle_id'], label=f'FS: {num_of_fleet_specialists}')  # Adjusted label to include fleet specialists

    plt.xlabel('Date')
    plt.ylabel(f'Number of Rides (over {interval} intervals)')
    plt.title(f'Number of Rides Over Time \n {config["CITY"]}, simulation time: {config["NUM_SIMULATED_DAYS"]} days')
    plt.legend(title='Ride Status')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def plot_vehicle_state_over_time(directory):
    # Read the number of vehicles from the config JSON file in the directory
    config_path = os.path.join(directory, 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    NUM_OF_VEHICLES = config['NUM_OF_VEHICLES']

    # Load data
    vehicle_rides = pd.read_csv(f"{directory}/vehicle_rides.csv")
    task_data = pd.read_csv(f"{directory}/task_data.csv")
    

    # Convert times to datetime
    origin_date = pd.Timestamp('2024-05-06')
    vehicle_rides['time_departure'] = pd.to_datetime(vehicle_rides['time_departure'], unit='s', origin=origin_date)
    vehicle_rides['time_ride'] = pd.to_timedelta(vehicle_rides['time_ride'], unit='s')
    task_data['bounty_time'] = pd.to_datetime(task_data['bounty_time'], unit='s', origin=origin_date)
    task_data['resolved_time'] = pd.to_datetime(task_data['resolved_time'], unit='s', origin=origin_date)

    # Filter completed rides
    completed_rides = vehicle_rides[vehicle_rides['status'] == 'completed']

    # Filter tasks where bounty_time is not None
    tasks_with_bounty = task_data.dropna(subset=['bounty_time'])

    # Prepare time series data
    time_series = pd.DataFrame()

    # Ride starts
    ride_starts = completed_rides['time_departure'].value_counts().sort_index()
    ride_ends = (completed_rides['time_departure'] + completed_rides['time_ride']).value_counts().sort_index()

    # Vehicle becomes unavailable and available again
    bounty_starts = tasks_with_bounty['bounty_time'].value_counts().sort_index()
    resolved_times = tasks_with_bounty['resolved_time'].value_counts().sort_index()

    # Combine all events into a single DataFrame
    time_series = pd.concat([ride_starts.rename('ride_start'), ride_ends.rename('ride_end'),
                             bounty_starts.rename('bounty_start'), resolved_times.rename('resolved_time')], axis=1).fillna(0)

    # Calculate net changes for each state
    time_series['net_riding'] = time_series['ride_start'] - time_series['ride_end']
    time_series['net_available'] = -time_series['ride_start'] + time_series['ride_end'] + time_series['resolved_time'] - time_series['bounty_start']
    time_series['net_unavailable'] = time_series['bounty_start'] - time_series['resolved_time']

    # Cumulative sum to track the number of vehicles in each state
    time_series['riding'] = time_series['net_riding'].cumsum()
    time_series['available'] = NUM_OF_VEHICLES + time_series['net_available'].cumsum()
    time_series['unavailable'] = time_series['net_unavailable'].cumsum()

    # Plotting
    plt.figure(figsize=(12, 6))
    plt.stackplot(time_series.index, time_series['riding'], time_series['available'], time_series['unavailable'], 
                  labels=['Riding', 'Available', 'Unavailable'], colors=['#567af0', '#b9ffab', '#ff9991'])
    plt.legend(loc='upper left')
    plt.title(f'Vehicle State Over Time \n {config["CITY"]}, number of Fleet Specialists: {config["NUM_OF_FLEET_SPECIALISTS"]}')
    plt.xlabel('Time')
    plt.ylabel('Number of Vehicles')
    plt.show()

def get_table_of_key_performance_indicators(directories, start_from_time=0):
    kpi_results = []
    for directory in directories:
        task_data_path = os.path.join(directory, 'task_data.csv')
        vehicle_rides_path = os.path.join(directory, 'vehicle_rides.csv')
        state_data_path = os.path.join(directory, "state_records.csv")

        # Read data
        task_data = pd.read_csv(task_data_path)
        vehicle_rides = pd.read_csv(vehicle_rides_path)
        state_data = pd.read_csv(state_data_path)
        # Read config data
        config_path = os.path.join(directory, 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        num_of_fleet_specialists = config['NUM_OF_FLEET_SPECIALISTS']
        # Convert times to datetime
        task_data['created_time'] = pd.to_datetime(task_data['created_time'], unit='s', origin=pd.Timestamp('2024-05-26'))
        task_data['resolved_time'] = pd.to_datetime(task_data['resolved_time'], unit='s', origin=pd.Timestamp('2024-05-26'))
        state_data['time'] = pd.to_datetime(state_data['time'], unit='s', origin=pd.Timestamp('2024-05-26'))

        # Filter data based on start_from_time
        task_data = task_data[task_data['created_time'] >= pd.Timestamp('2024-05-26') + pd.to_timedelta(start_from_time, unit='s')]
        vehicle_rides = vehicle_rides[vehicle_rides['time_departure'] >= start_from_time]
        filtered_state_data = state_data[state_data['time'] >= pd.Timestamp('2024-05-26') + pd.to_timedelta(start_from_time, unit='s')]

        # Calculate KPIs for tasks
        resolved_tasks = task_data[task_data['status'] == 'resolved']
        active_tasks = task_data[task_data['status'] == 'active']
        number_of_tasks_completed = len(resolved_tasks)
        number_of_tasks_in_backlog = len(active_tasks)
        average_time_open = (resolved_tasks['time_open']).mean()
        average_time_to_resolve_task = resolved_tasks['time_spent'].mean()
        average_battery_in = resolved_tasks['battery_in'].mean()
        average_number_of_tasks_completed_per_hour = number_of_tasks_completed / ((task_data['created_time'].max() - task_data['created_time'].min()).total_seconds() / 3600)

        # Calculate KPIs for rides
        rides = vehicle_rides[vehicle_rides['status'] == 'completed']
        number_of_rides = len(rides)
        average_number_of_rides_per_hour = number_of_rides / ((vehicle_rides['time_departure'].max() - vehicle_rides['time_departure'].min()) / 3600)
        average_battery_in = rides['battery_in'].mean()
        
        # Vehicle KPIs

        # Calculate the percentage of downtime
        filtered_state_data['percentage_downtime'] = (filtered_state_data['num_bounties'] / config["NUM_OF_VEHICLES"])
        # Calculate the average percentage of downtime
        average_downtime = filtered_state_data['percentage_downtime'].mean()

        # Append results
        kpi_results.append({
            'folder_name': directory,
            'number_of_fleet_specialists': num_of_fleet_specialists,
            'number_of_tasks_completed': number_of_tasks_completed,
            'number_of_tasks_in_backlog': number_of_tasks_in_backlog,
            'average_downtime': average_downtime,
            'average_time_open': average_time_open,
            'average_time_to_resolve_task': average_time_to_resolve_task,
            'average_battery_in': average_battery_in,
            'average_number_of_tasks_completed_per_hour': average_number_of_tasks_completed_per_hour,
            'average_number_of_tasks_completed_per_hour_per_fleet': np.nan if num_of_fleet_specialists == 0 else average_number_of_tasks_completed_per_hour / num_of_fleet_specialists,
            'number_of_rides_per_swap': np.nan if num_of_fleet_specialists == 0 else number_of_rides / number_of_tasks_completed,
            'number_of_rides': number_of_rides,
            'average_number_of_rides_per_hour': average_number_of_rides_per_hour,
        })

    return pd.DataFrame(kpi_results)

def plot_fleet_route(m, directory, fleet_specialist_id, start_day=3, duration_hours=3, color='purple'):
    file_path = os.path.join(directory, "task_data.csv")
    data = pd.read_csv(file_path)
    config_path = os.path.join(directory, 'config.json')
    
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    num_of_fleet_specialists = config['NUM_OF_FLEET_SPECIALISTS']
    
    start_time = 3600 * 24 * start_day
    end_time = start_time + 3600 * duration_hours
    
    specialist_data = data[(data['resolved_by'] == fleet_specialist_id) &
                           (data['resolved_time'] >= start_time) &
                           (data['resolved_time'] <= end_time)]
    
    specialist_data = specialist_data.sort_values('resolved_time')
    
    # Create a feature group for this route
    route = folium.FeatureGroup(name=f'FS: {num_of_fleet_specialists} - {color}', show=True)
    
    # Add task locations to the map
    for _, row in specialist_data.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"Task ID: {row['task_id']}\nResolved Time: {row['resolved_time']}",
            icon=folium.Icon(color=color)
        ).add_to(route)
    
    # Add lines between the task locations with arrows
    locations = specialist_data[['lat', 'lon']].values.tolist()
    polyline = folium.PolyLine(locations, color=color, weight=2.5, opacity=1)
    route.add_child(polyline)
    
    # Add arrows to the polyline
    arrows = PolyLineTextPath(
        polyline,
        '→',  # Unicode character for arrow
        repeat=True,
        offset=7,
        attributes={'fill': color, 'font-weight': 'bold', 'font-size': '16'}
    )
    route.add_child(arrows)
    
    # Add the route to the map
    m.add_child(route)

def main():
    dir = "experiments/stock_7d"
    result_dirs = get_result_dirs(dir)
    #result_dirs = result_dirs[0:2]
    #
    # plot_open_tasks_over_time(result_dirs, window_size=5)
    #plot_rides_over_time(result_dirs, interval='15min', include_unfullfiled_demand=False)
    #plot_task_completion_over_time(result_dirs, interval='4h')
    kpi_table = get_table_of_key_performance_indicators(result_dirs)
    kpi_table.to_csv('data/validation/kpi_7d.csv', index=False)
    
    #plot_vehicle_state_over_time(result_dirs[0])
    #plot_vehicle_state_over_time(result_dirs[1])
    # plot_vehicle_state_over_time(result_dirs[2])
    # plot_vehicle_state_over_time(result_dirs[3])
    # plot_vehicle_state_over_time(result_dirs[4])
    # plot_vehicle_state_over_time(result_dirs[5])
    # plot_vehicle_state_over_time(result_dirs[6])
    # plot_vehicle_state_over_time(result_dirs[7])

  



    
    # #Create a map centered around a general location
    # m = folium.Map()
    
    # #Plot multiple routes on the same map with different colors
    # plot_fleet_route(m, result_dirs[0], 0, 3, 3, color='blue')
    # plot_fleet_route(m, result_dirs[0], 1, 3, 3, color='green')
    # plot_fleet_route(m, result_dirs[1], 0, 3, 3, color='red')
    # plot_fleet_route(m, result_dirs[1], 1, 3, 3, color='orange')
    # # plot_fleet_route(m, result_dirs[5], 0, 3, 3, color='pink')
    # # plot_fleet_route(m, result_dirs[6], 0, 3, 3, color='brown')
    # # plot_fleet_route(m, result_dirs[7], 0, 3, 3, color='purple')
    
    # #Add a layer control to toggle routes
    # m.add_child(LayerControl())

    # #Save the map to an HTML file
    # map_path = os.path.join(dir, "fleet_routes.html")
    # m.save(map_path)
    # #print(f"Map saved to {map_path}")

if __name__ == "__main__":
    main()
