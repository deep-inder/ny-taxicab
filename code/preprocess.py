import datetime
import pandas as pd
import numpy as np

def minutes_after_midnight(date_time):
    time = date_time.split(' ')
    if len(time) == 3:
        time_arr = time[1].split(':')
        minutes_after_midnight = 60 * int(time_arr[0]) + int(time_arr[1])
        return 2 * np.pi * minutes_after_midnight / 1440
    else:
        return np.nan

def day_of_week(date_time):
    time = date_time.split(' ')
    if len(time) == 3:
        date_arr = time[0].split('-')
        date = datetime.date(int(date_arr[0]), int(date_arr[1]), int(date_arr[2]))
        return 2 * np.pi * (date.weekday() + 1) / 7
    else:
        return np.nan

def month(date_time):
    time = date_time.split(' ')
    if len(time) == 3:
        return 2 * np.pi * int(time[0].split('-')[1]) / 12
    else:
        return np.nan

def year(date_time):
    time = date_time.split(' ')
    if len(time) == 3:
        return float(time[0].split('-')[0])
    else:
        return np.nan

time_of_day_vec = np.vectorize(minutes_after_midnight)
day_of_week_vec = np.vectorize(day_of_week)
month_vec = np.vectorize(month)
year_vec = np.vectorize(year)

# Function to calculate distance between two points and add it as a feature
from haversine import haversine
def distance(p_lat, p_long, d_lat, d_long):
    pickup = (p_lat, p_long)
    dropoff = (d_lat, d_long)
    dist = haversine(pickup, dropoff)
    return dist

dist_vector = np.vectorize(distance)

# Points in wata are bad..
import matplotlib.pyplot as plt
nyc_bounds = (-74.5, -72.8, 40.5, 41.8)

def select_within_bounds(df, bounds):
    pickup_indices = (df.pickup_longitude >= bounds[0]) & (df.pickup_longitude <= bounds[1]) & \
        (df.pickup_latitude >= bounds[2]) & (df.pickup_latitude <= bounds[3])

    dropoff_indices = (df.dropoff_longitude >= bounds[0]) & (df.dropoff_longitude <= bounds[1]) & \
        (df.dropoff_latitude >= bounds[2]) & (df.dropoff_latitude <= bounds[3])

    return pickup_indices & dropoff_indices

def map_to_nyc_mask(longitude, latitude, points_x, points_y, bounds):
    x = (points_x * (longitude - bounds[0]) / (bounds[1] - bounds[0])).astype('int')
    y = (points_y - points_y * (latitude - bounds[2]) / (bounds[3] - bounds[2])).astype('int')
    return x,y

def remove_points_in_water(df):
    # Create a mask of the New York City with 1 as land and 0 as water
    nyc_mask = plt.imread('img/nyc_water_mask.png')[:,:,0] > 0.9

    # Remove points outside New York
    df = df[select_within_bounds(df, nyc_bounds)]
    print("After Bounds:", df.shape[0])

    # Map the latitudes and longitudes to the points in the map
    pickup_x, pickup_y = map_to_nyc_mask(df.pickup_longitude, df.pickup_latitude, nyc_mask.shape[1],
                                         nyc_mask.shape[0], nyc_bounds)
    dropoff_x, dropoff_y = map_to_nyc_mask(df.dropoff_longitude, df.dropoff_latitude, nyc_mask.shape[1],
                                        nyc_mask.shape[0], nyc_bounds)

    # Compute the indices where pickup and dropoff locations are on land
    indices = nyc_mask[pickup_y, pickup_x] & nyc_mask[dropoff_y, dropoff_x]

    df = df[indices]
    print("Number of trips in water: ", np.sum(~indices))
    return df

def preprocess(df):
    print("Initial number of points: ", df.shape[0])
    # Drop all null values
    df = df.dropna()

    # Cyclise time and remove key column
    time_column = df['pickup_datetime'].to_numpy()
    df = df.drop(columns=['pickup_datetime', 'key'])

    time_of_day = time_of_day_vec(time_column)
    day_of_week = day_of_week_vec(time_column)
    month = month_vec(time_column)
    df['year'] = year_vec(time_column)

    df['sin_time_of_day'] = np.sin(time_of_day)
    df['cos_time_of_day'] = np.cos(time_of_day)
    df['sin_day_of_week'] = np.sin(day_of_week)
    df['cos_day_of_week'] = np.cos(day_of_week)
    df['sin_month'] = np.sin(month)
    df['cos_month'] = np.cos(month)

    df = df.dropna()
    print("Number of points after removing null:", df.shape[0])

    # Make latitude and longitude numeric
    df['pickup_latitude'] = pd.to_numeric(df['pickup_latitude'])
    df['pickup_longitude'] = pd.to_numeric(df['pickup_longitude'])
    df['dropoff_latitude'] = pd.to_numeric(df['dropoff_latitude'])
    df['dropoff_longitude'] = pd.to_numeric(df['dropoff_longitude'])
    df['fare_amount'] = pd.to_numeric(df['fare_amount'])
    df['passenger_count'] = pd.to_numeric(df['passenger_count'])

    # Remove points in water
    df = remove_points_in_water(df)

    # Remove 0 passenger count and negative fare amounts
    df = df[df['passenger_count'] > 0]
    df = df[df['passenger_count'] <= 7]
    df['fare_amount'] = df[df['fare_amount'] > 0]
    print("Number of points after removing semantic:", df.shape[0])

    # Add distance column
    df['distance'] = dist_vector(df['pickup_latitude'].to_numpy(), df['pickup_longitude'].to_numpy(),
                     df['dropoff_latitude'].to_numpy(), df['dropoff_longitude'].to_numpy())
    df = df.reset_index(drop=True)

    return df

def preprocess_test(df):
    print("Initial number of points: ", df.shape[0])
    # Cyclise time
    time_column = df['pickup_datetime'].to_numpy()
    df = df.drop(columns=['pickup_datetime'])

    time_of_day = time_of_day_vec(time_column)
    day_of_week = day_of_week_vec(time_column)
    month = month_vec(time_column)
    df['year'] = year_vec(time_column)

    df['sin_time_of_day'] = np.sin(time_of_day)
    df['cos_time_of_day'] = np.cos(time_of_day)
    df['sin_day_of_week'] = np.sin(day_of_week)
    df['cos_day_of_week'] = np.cos(day_of_week)
    df['sin_month'] = np.sin(month)
    df['cos_month'] = np.cos(month)

    # Make illegal passenger_counts null
    df = df.mask(df['passenger_count'] <= 0)
    df = df.mask(df['passenger_count'] > 7)

    # Add distance column
    df['distance'] = dist_vector(df['pickup_latitude'].to_numpy(), df['pickup_longitude'].to_numpy(),
                     df['dropoff_latitude'].to_numpy(), df['dropoff_longitude'].to_numpy())
    df = df.reset_index(drop=True)

    # Impute the null points with mean
    df = df.fillna(df.mean())

    print("Final number of points:", df.shape[0])
    return df

from sklearn.preprocessing import MinMaxScaler, StandardScaler
def scale(df):
    mm_scaler = MinMaxScaler()
    std_scaler = StandardScaler()

    mm_features = ['passenger_count', 'year']
    std_features = ['pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude',
                    'distance']

    mm_scaler.fit(df[mm_features])
    std_scaler.fit(df[std_features])

    df[mm_features] = pd.DataFrame(mm_scaler.transform(df[mm_features]), columns=mm_features)
    df[std_features] = pd.DataFrame(std_scaler.transform(df[std_features]), columns=std_features)
    return df


def is_valid(p_lat, p_long, d_lat, d_long):
    bounds = (-74.5, -72.8, 40.5, 41.8)
    if ((p_long >= bounds[0]) & (p_long <= bounds[1]) & (p_lat >= bounds[2]) & (p_lat <= bounds[3])):
        if (d_long >= bounds[0]) & (d_long <= bounds[1]) & (d_lat >= bounds[2]) & (d_lat <= bounds[3]):
            return 0
    else:
        return 1

valid_vec = np.vectorize(is_valid)

def make_invalid_water(invalid_col):
    if (invalid_col == 1):
        return 1
    else:
        return 2
inv_vec = np.vectorize(make_invalid_water)

def get_water_invalid(df):
    df2 = remove_points_in_water(df)
    df_diff = pd.concat([df,df2]).drop_duplicates(keep=False)
    df_diff['invalid'] = inv_vec(df.invalid)
    df = pd.concat([df2, df_diff])
    df.reset_index(inplace = True)
    return df

if __name__=="__main__":
    import sys
    flag = sys.argv[1]
    path = sys.argv[2]
    target_path = sys.argv[3]
    if flag == 'train':
        df = pd.read_csv(path, nrows=10000000, low_memory=False)
        preprocessed_df = preprocess(df)
        scaled_df = scale(preprocessed_df)
        print(scaled_df.head())
        scaled_df.to_csv(target_path, index=False)
    elif flag == 'test':
        df = pd.read_csv(path, low_memory=False)
        preprocessed_df = preprocess_test(df)
        scaled_df = scale(preprocessed_df)
        print(scaled_df.head())
        scaled_df.to_csv(target_path, index=False)
