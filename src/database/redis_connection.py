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