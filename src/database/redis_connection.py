import json

import numpy as np
import redis
import pandas as pd
import pyarrow as pa
import os


# This works because of the "ports: - 6379:6379" mapping
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

try:
    r.ping()
    print("Successfully connected to Redis running via Docker Compose!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")


# Define a prefix for all our DataFrame keys to keep things organized
REDIS_KEY_PREFIX = "df_cache:"


def delete_dataframe_from_cache(file_path: str):
    """
    Deletes a cached DataFrame from Redis based on its file path.
    """
    # Create the unique key for this file, THE SAME WAY as in the get function.
    # This is the most important step.
    redis_key = f"{REDIS_KEY_PREFIX}{os.path.basename(file_path)}"

    try:
        # The .delete() command returns the number of keys that were deleted.
        # It will be 1 if the key existed and was deleted, 0 otherwise.
        num_deleted = r.delete(redis_key)

        if num_deleted > 0:
            print(f"SUCCESS: Deleted cached DataFrame for '{file_path}' (key: '{redis_key}')")
        else:
            print(f"INFO: No cached DataFrame found for '{file_path}' (key: '{redis_key}'). Nothing to delete.")

    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}. Could not delete key.")

def flush_redis_database():
    """
    Deletes ALL keys in the current Redis database.
    WARNING: This is destructive and will remove data from other applications
    if they share the same Redis database. Use with caution.
    """
    print("WARNING: You are about to delete ALL keys in the current Redis database.")
    # You might want to add a confirmation step in a real application
    # user_input = input("Are you sure? (yes/no): ")
    # if user_input.lower() != 'yes':
    #     print("Operation cancelled.")
    #     return

    try:
        r.flushdb()
        print("SUCCESS: The entire Redis database has been flushed.")
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}. Could not flush the database.")

def get_dataframe_with_cache(file_path: str) -> pd.DataFrame:
    """
    Retrieves a DataFrame, using Redis as a cache to avoid re-reading the Excel file.
    """
    # Create a unique key for this file in Redis
    redis_key = f"{REDIS_KEY_PREFIX}{os.path.basename(file_path)}"

    try:
        # 1. Check for the key in Redis
        cached_df_bytes = r.get(redis_key)

        if cached_df_bytes:
            # 2. CACHE HIT: If it exists, deserialize it and return
            print(f"CACHE HIT for '{file_path}'")
            # PyArrow's deserialize function is perfect for this
            df = pa.deserialize(cached_df_bytes)
            return df
        else:
            # 3. CACHE MISS: If it doesn't exist, read the file
            print(f"CACHE MISS for '{file_path}'. Reading from Excel file...")
            df = pd.read_excel(file_path)

            # 4. Serialize the DataFrame using PyArrow and save to Redis
            print(f"Storing '{file_path}' in Redis cache...")
            df_bytes = pa.serialize(df).to_buffer().to_pybytes()

            # We also set an expiration time (TTL) of 1 day (86400 seconds)
            # This is good practice to prevent stale data. Adjust as needed.
            r.set(redis_key, df_bytes, ex=604800)

            return df

    except redis.exceptions.ConnectionError as e:
        # If Redis is down, fall back to reading the file directly
        print(f"Redis connection error: {e}. Falling back to direct file read.")
        df = pd.read_excel(file_path)
        return df

class CustomEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle special types from pandas and numpy,
    such as Timestamps, numpy numbers, and NaN values.
    """
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            # Convert pandas Timestamp to an ISO 8601 formatted string
            return obj.isoformat()
        if isinstance(obj, np.integer):
            # Convert numpy integer to a standard Python int
            return int(obj)
        if isinstance(obj, np.floating):
            # Convert numpy float to a standard Python float.
            # Crucially, check if it's NaN and convert to None (which becomes null in JSON).
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, np.ndarray):
            # Convert numpy arrays to lists
            return obj.tolist()
        # Let the base class default method raise the TypeError for other types
        return super(CustomEncoder, self).default(obj)


def add_data_to_redis(key: str, value: str):
    """
    Adds a simple key-value pair to Redis.
    """
    try:
        r.set(key, value)
        print(f"Added key '{key}' with value '{value}' to Redis.")
    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}. Could not add key-value pair.")