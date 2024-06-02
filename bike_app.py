import streamlit as st  # Import Streamlit for creating web apps
import requests  # Import requests for making HTTP requests
import pandas as pd  # Import pandas for data manipulation
import datetime as dt  # Import datetime for handling date and time
import urllib  # Import urllib for URL handling
import json  # Import json for handling JSON data
import time  # Import time for time-related functions
import folium  # Import folium for creating interactive maps
from streamlit_folium import folium_static 

st.title('Toronto Bike Share Status')
st.markdown('This dashbord tracks bike availability')


station_url = 'https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status'

with urllib.request.urlopen(station_url) as data_url:
    data = json.loads(data_url.read().decode())
    
def query_station_status(url):
    with urllib.request.urlopen(url) as data_url: #open the url
        data = json.loads(data_url.read().decode()) #read and decode
        
    df = pd.DataFrame(data['data']['stations'])
    df = df[df.is_renting == 1] #filter out st that are not renting
    df = df[df.is_returning == 1] # that are not returning
    df = df.drop_duplicates(['station_id', 'last_reported'])
    df.last_reported = df.last_reported.map(lambda x: dt.datetime.utcfromtimestamp(x))
    df['time'] = data['last_updated']
    df['time'] = df.time.map(lambda x: dt.datetime.utcfromtimestamp(x))
    df = df.set_index('time')
    df.index = df.index.tz_localize('UTC')
    df = pd.concat([df, df['num_bikes_available_types'].apply(pd.Series)])
    
    return df

data = query_station_status(station_url)

def get_station_latlon(url):
    with urllib.request.urlopen(url) as data_url:
        latlon = json.loads(data_url.read().decode())
    latlon = pd.DataFrame(latlon['data']['stations'])
    return latlon

latlon_url = 'https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information'
latlon_df = get_station_latlon(latlon_url)

df = data.merge(latlon_df[['station_id', 'lat', 'lon']],
                   how='left',
                   on='station_id')


data = df
data = data.fillna(0)

center = [43.6548, -79.3883]
m = folium.Map(location = center, zoom_start = 12)

def get_marker_color(num_bikes_available):
    if num_bikes_available > 3:
        return 'green'
    elif 0 < num_bikes_available <=3:
        return 'yellow'
    else:
        return 'red'
    
for _, row in data.iterrows():
    marker_color = get_marker_color(row['num_bikes_available'])
    folium.CircleMarker(
        location = [row['lat'], row['lon']],
        radius = 2,
        color = marker_color,
        fill=True,
        fill_color=marker_color,
        fill_opacity=0.7,
        popup = folium.Popup(f'Station ID: {row['station_id']}<br>'
                             f'Total Bikes Available: {row['num_bikes_available']}<br>'
                             f'Mechanical Bike Available: {row['mechanical']}<br>'
                             f'eBike Available: {row['ebike']}', max_width = 300)
    ).add_to(m)
    
    
    col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label='Bikes Available Now', value = sum(data['num_bikes_available']))
    st.metric(label='E-bikes Available Now', value = sum(data['ebike']))
with col2:
    st.metric(label='Stations w Available Bikes', value = len(data[data[num_bikes_available]]))
    st.metric(label= 'Stations with Available eBikes', value = len(data[data['ebike'] > 0]))
with col3:st.metric(lebel='Stations w Empty Docks', value=len(data[data['num_docks_available']]))            
    

