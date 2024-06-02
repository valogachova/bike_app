#from helpers.py
import urllib  # Import module for working with URLs
import json  # Import module for working with JSON data
import pandas as pd  # Import pandas for data manipulation
import folium  # Import folium for creating interactive maps
import datetime as dt  # Import datetime for working with dates and times
from geopy.distance import geodesic  # Import geodesic for calculating distances
from geopy.geocoders import Nominatim  # Import Nominatim for geocoding
import streamlit as st  # Import Streamlit for creating web apps

@st.cache_data  # Cache the function's output to improve performance
# Define the function to query station status from a given URL
def query_station_status(url):
    with urllib.request.urlopen(url) as data_url:  # Open the URL
        data = json.loads(data_url.read().decode())  # Read and decode the JSON data

    df = pd.DataFrame(data['data']['stations'])  # Convert the data to a DataFrame
    df = df[df.is_renting == 1]  # Filter out stations that are not renting
    df = df[df.is_returning == 1]  # Filter out stations that are not returning
    df = df.drop_duplicates(['station_id', 'last_reported'])  # Remove duplicate records
    df.last_reported = df.last_reported.map(lambda x: dt.datetime.utcfromtimestamp(x))  # Convert timestamps to datetime
    df['time'] = data['last_updated']  # Add the last updated time to the DataFrame
    df.time = df.time.map(lambda x: dt.datetime.utcfromtimestamp(x))  # Convert timestamps to datetime
    df = df.set_index('time')  # Set the time as the index
    df.index = df.index.tz_localize('UTC')  # Localize the index to UTC
    df = pd.concat([df, df['num_bikes_available_types'].apply(pd.Series)], axis=1)  # Expand the bike types column

    return df  # Return the DataFrame
# Define the function to get station latitude and longitude from a given URL
def get_station_latlon(url):
    with urllib.request.urlopen(url) as data_url:  # Open the URL
        latlon = json.loads(data_url.read().decode())  # Read and decode the JSON data
    latlon = pd.DataFrame(latlon['data']['stations'])  # Convert the data to a DataFrame
    return latlon  # Return the DataFrame

# Define the function to join two DataFrames on station_id
def join_latlon(df1, df2):
    df = df1.merge(df2[['station_id', 'lat', 'lon']], 
                how='left', 
                on='station_id')  # Merge the DataFrames on station_id
    return df  # Return the merged DataFrame

# Function to determine marker color based on the number of bikes available
def get_marker_color(num_bikes_available):
    if num_bikes_available > 3:
        return 'green'
    elif 0 < num_bikes_available <= 3:
        return 'yellow'
    else:
        return 'red'
# Define the function to geocode an address
def geocode(address):
    geolocator = Nominatim(user_agent="clicked-demo")  # Create a geolocator object
    location = geolocator.geocode(address)  # Geocode the address
    if location is None:
        return ''  # Return an empty string if the address is not found
    else:
        return (location.latitude, location.longitude)  # Return the latitude and longitude
# Define the function to get bike availability near a location
def get_bike_availability(latlon, df, input_bike_modes):
    """Calculate distance from each station to the user and return a single station id, lat, lon"""
    if len(input_bike_modes) == 0 or len(input_bike_modes) == 2:  # If no mode selected, assume both bikes are selected
        i = 0
        df['distance'] = ''
        while i < len(df):
            df.loc[i, 'distance'] = geodesic(latlon, (df['lat'][i], df['lon'][i])).km  # Calculate distance to each station
            i = i + 1
        df = df.loc[(df['ebike'] > 0) | (df['mechanical'] > 0)]  # Remove stations with no available bikes
        chosen_station = []
        chosen_station.append(df[df['distance'] == min(df['distance'])]['station_id'].iloc[0])  # Get closest station
        chosen_station.append(df[df['distance'] == min(df['distance'])]['lat'].iloc[0])
        chosen_station.append(df[df['distance'] == min(df['distance'])]['lon'].iloc[0])
    else:
        i = 0
        df['distance'] = ''
        while i < len(df):
            df.loc[i, 'distance'] = geodesic(latlon, (df['lat'][i], df['lon'][i])).km  # Calculate distance to each station
            i = i + 1
        df = df.loc[df[input_bike_modes[0]] > 0]  # Remove stations without the selected mode available
        chosen_station = []
        chosen_station.append(df[df['distance'] == min(df['distance'])]['station_id'].iloc[0])  # Get closest station
        chosen_station.append(df[df['distance'] == min(df['distance'])]['lat'].iloc[0])
        chosen_station.append(df[df['distance'] == min(df['distance'])]['lon'].iloc[0])
    return chosen_station  # Return the chosen station


# Define the function to get dock availability near a location
def get_dock_availability(latlon, df):
    """Calculate distance from each station to the user and return a single station id, lat, lon"""
    i = 0
    df['distance'] = ''
    while i < len(df):
        df.loc[i, 'distance'] = geodesic(latlon, (df['lat'][i], df['lon'][i])).km  # Calculate distance to each station
        i = i + 1
    df = df.loc[df['num_docks_available'] > 0]  # Remove stations without available docks
    chosen_station = []
    chosen_station.append(df[df['distance'] == min(df['distance'])]['station_id'].iloc[0])  # Get closest station
    chosen_station.append(df[df['distance'] == min(df['distance'])]['lat'].iloc[0])
    chosen_station.append(df[df['distance'] == min(df['distance'])]['lon'].iloc[0])
    return chosen_station  # Return the chosen station

import requests  # Import requests for making HTTP requests

# Define the function to run OSRM and get route coordinates and duration
def run_osrm(chosen_station, iamhere):
    start = "{},{}".format(iamhere[1], iamhere[0])  # Format the start coordinates
    end = "{},{}".format(chosen_station[2], chosen_station[1])  # Format the end coordinates
    url = 'http://router.project-osrm.org/route/v1/driving/{};{}?geometries=geojson'.format(start, end)  # Create the OSRM API URL

    headers = {'Content-type': 'application/json'}
    r = requests.get(url, headers=headers)  # Make the API request
    print("Calling API ...:", r.status_code)  # Print the status code
  
    routejson = r.json()  # Parse the JSON response
    coordinates = []
    i = 0
    lst = routejson['routes'][0]['geometry']['coordinates']
    while i < len(lst):
        coordinates.append([lst[i][1], lst[i][0]])  # Extract coordinates
        i = i + 1
    duration = round(routejson['routes'][0]['duration'] / 60, 1)  # Convert duration to minutes

    return coordinates, duration  # Return the coordinates and duration










#from app.py
import streamlit as st  # Import Streamlit for creating web apps
import requests  # Import requests for making HTTP requests
import pandas as pd  # Import pandas for data manipulation
import datetime as dt  # Import datetime for handling date and time
import urllib  # Import urllib for URL handling
import json  # Import json for handling JSON data
import time  # Import time for time-related functions
import folium  # Import folium for creating interactive maps
from streamlit_folium import folium_static  # Import folium_static to render Folium maps in Streamlit

# Example URL to fetch bike share data (replace with the actual URL from the resource_urls list)
station_url = 'https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status.json'  
latlon_url = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"

# Streamlit app setup
st.title('Toronto Bike Share Station Status')  # Set the title of the app
st.markdown('This dashboard tracks bike availability at each bike share station in Toronto.')  # Add a description

# Fetch data for initial visualization
data_df = query_station_status(station_url)  # Get station status data
latlon_df = get_station_latlon(latlon_url)  # Get station latitude and longitude data
data = join_latlon(data_df, latlon_df)  # Join the status data with the location data

# Display initial metrics
col1, col2, col3 = st.columns(3)  # Create three columns for metrics
with col1:
    st.metric(label="Bikes Available Now", value=sum(data['num_bikes_available']))  # Display total number of bikes available
    st.metric(label="E-Bikes Available Now", value=sum(data["ebike"]))  # Display total number of e-bikes available
with col2:
    st.metric(label="Stations w Available Bikes", value=len(data[data['num_bikes_available'] > 0]))  # Display number of stations with available bikes
    st.metric(label="Stations w Available E-Bikes", value=len(data[data['ebike'] > 0]))  # Display number of stations with available e-bikes
with col3:
    st.metric(label="Stations w Empty Docks", value=len(data[data['num_docks_available'] > 0]))  # Display number of stations with empty docks

# Track metrics for delta calculation
deltas = [
    sum(data['num_bikes_available']),
    sum(data["ebike"]),
    len(data[data['num_bikes_available'] > 0]),
    len(data[data['ebike'] > 0]),
    len(data[data['num_docks_available'] > 0])
]

# Initialize variables for user input and state
iamhere = 0
iamhere_return = 0
findmeabike = False
findmeadock = False
input_bike_modes = []

# Add sidebar selection for user inputs
with st.sidebar:
    bike_method = st.selectbox("Are you looking to rent or return a bike?", ("Rent", "Return"))  # Selection box for rent or return
    if bike_method == "Rent":
        input_bike_modes = st.multiselect("What kind of bikes are you looking to rent?", ["ebike", "mechanical"])  # Multi-select box for bike types
        st.subheader('Where are you located?')
        input_street = st.text_input("Street", "")  # Text input for street
        input_city = st.text_input("City", "Toronto")  # Text input for city
        input_country = st.text_input("Country", "Canada")  # Text input for country
        drive = st.checkbox("I'm driving there.")  # Checkbox for driving option
        findmeabike = st.button("Find me a bike!", type="primary")  # Button to find a bike
        if findmeabike:
            if input_street != "":
                iamhere = geocode(input_street + " " + input_city + " " + input_country)  # Geocode the input address
                if iamhere == '':
                    st.subheader(':red[Input address not valid!]')  # Display error if address is invalid
            else:
                st.subheader(':red[Please input your location.]')  # Prompt user to input location if missing
    elif bike_method == "Return":
        st.subheader('Where are you located?')
        input_street_return = st.text_input("Street", "")  # Text input for street for return
        input_city_return = st.text_input("City", "Toronto")  # Text input for city for return
        input_country_return = st.text_input("Country", "Canada")  # Text input for country for return
        findmeadock = st.button("Find me a dock!", type="primary")  # Button to find a dock
        if findmeadock:
            if input_street_return != "":
                iamhere_return = geocode(input_street_return + " " + input_city_return + " " + input_country_return)  # Geocode the return address
                if iamhere_return == '':
                    st.subheader(':red[Input address not valid!]')  # Display error if address is invalid
            else:
                st.subheader(':red[Please input your location.]')  # Prompt user to input location if missing

# Initial map setup based on user selection
if bike_method == "Return" and findmeadock == False:
    center = [43.65306613746548, -79.38815311015]  # Coordinates for Toronto
    m = folium.Map(location=center, zoom_start=13, tiles='cartodbpositron')  # Create a map with a grey background
    for _, row in data.iterrows():
        marker_color = get_marker_color(row['num_bikes_available'])  # Determine marker color based on bikes available
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                               f"Total Bikes Available: {row['num_bikes_available']}<br>"
                               f"Mechanical Bike Available: {row['mechanical']}<br>"
                               f"eBike Available: {row['ebike']}", max_width=300)
        ).add_to(m)
    folium_static(m)  # Display the map in the Streamlit app

if bike_method == "Rent" and findmeabike == False:
    center = [43.65306613746548, -79.38815311015]  # Coordinates for Toronto
    m = folium.Map(location=center, zoom_start=13, tiles='cartodbpositron')  # Create a map with a grey background
    for _, row in data.iterrows():
        marker_color = get_marker_color(row['num_bikes_available'])  # Determine marker color based on bikes available
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                               f"Total Bikes Available: {row['num_bikes_available']}<br>"
                               f"Mechanical Bike Available: {row['mechanical']}<br>"
                               f"eBike Available: {row['ebike']}", max_width=300)
        ).add_to(m)
    folium_static(m)  # Display the map in the Streamlit app

# Logic for finding a bike
if findmeabike:
    if input_street != "":
        if iamhere != "":
            chosen_station = get_bike_availability(iamhere, data, input_bike_modes)  # Get bike availability (id, lat, lon)
            center = iamhere  # Center the map on user's location
            m1 = folium.Map(location=center, zoom_start=16, tiles='cartodbpositron')  # Create a detailed map
            for _, row in data.iterrows():
                marker_color = get_marker_color(row['num_bikes_available'])  # Determine marker color based on bikes available
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=2,
                    color=marker_color,
                    fill=True,
                    fill_color=marker_color,
                    fill_opacity=0.7,
                    popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                                       f"Total Bikes Available: {row['num_bikes_available']}<br>"
                                       f"Mechanical Bike Available: {row['mechanical']}<br>"
                                       f"eBike Available: {row['ebike']}", max_width=300)
                ).add_to(m1)
            folium.Marker(
                location=iamhere,
                popup="You are here.",
                icon=folium.Icon(color="blue", icon="person", prefix="fa")
            ).add_to(m1)
            folium.Marker(location=(chosen_station[1], chosen_station[2]),
                          popup="Rent your bike here.",
                          icon=folium.Icon(color="red", icon="bicycle", prefix="fa")
                          ).add_to(m1)
            coordinates, duration = run_osrm(chosen_station, iamhere)  # Get route coordinates and duration
            folium.PolyLine(
                locations=coordinates,
                color="blue",
                weight=5,
                tooltip="it'll take you {} to get here.".format(duration),
            ).add_to(m1)
            folium_static(m1)  # Display the map in the Streamlit app
            with col3:
                st.metric(label=":green[Travel Time (min)]", value=duration)  # Display travel time

# Logic for finding a dock
if findmeadock:
    if input_street_return != "":
        if iamhere_return != "":
            chosen_station = get_dock_availability(iamhere_return, data)  # Get dock availability (id, lat, lon)
            center = iamhere_return  # Center the map on user's location
            m1 = folium.Map(location=center, zoom_start=16, tiles='cartodbpositron')  # Create a detailed map
            for _, row in data.iterrows():
                marker_color = get_marker_color(row['num_bikes_available'])  # Determine marker color based on bikes available
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=2,
                    color=marker_color,
                    fill=True,
                    fill_color=marker_color,
                    fill_opacity=0.7,
                    popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                                       f"Total Bikes Available: {row['num_bikes_available']}<br>"
                                       f"Mechanical Bike Available: {row['mechanical']}<br>"
                                       f"eBike Available: {row['ebike']}", max_width=300)
                ).add_to(m1)
            folium.Marker(
                location=iamhere_return,
                popup="You are here.",
                icon=folium.Icon(color="blue", icon="person", prefix="fa")
            ).add_to(m1)
            folium.Marker(location=(chosen_station[1], chosen_station[2]),
                          popup="Return your bike here.",
                          icon=folium.Icon(color="red", icon="bicycle", prefix="fa")
                          ).add_to(m1)
            coordinates, duration = run_osrm(chosen_station, iamhere_return)  # Get route coordinates and duration
            folium.PolyLine(
                locations=coordinates,
                color="blue",
                weight=5,
                tooltip="it'll take you {} to get here.".format(duration),
            ).add_to(m1)
            folium_static(m1)  # Display the map in the Streamlit app
            with col3:
                st.metric(label=":green[Travel Time (min)]", value=duration)  # Display travel time
