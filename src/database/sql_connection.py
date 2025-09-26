import pickle
import time

import pandas as pd
import os
from sqlalchemy import create_engine, text

from config import settings
from context_engine.master_db_description import FACT_DOANH_THU_DESCRIPTION
from database.redis_connection import r


DB_ENGINE = create_engine(
    settings.OPC_DATABASE_URL,
    connect_args={"fast_executemany": False}

)
PARQUET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parquet_cache")
os.makedirs(PARQUET_DIR, exist_ok=True)


# --- Revised Core Logic ---

def sync_data_to_df(engine, table_name, id_column, batch_size=10000):
    offset = 0
    has_more = True
    all_chunks = []

    with engine.connect() as conn:
        while has_more:
            # === FIX: Use a 'with' block to manage the transaction for each batch ===
            # This block will automatically begin, commit, or roll back.
            try:
                with conn.begin() as trans:
                    # 1. READ OPERATION (within the transaction)
                    query = (
                        f"SELECT * FROM {table_name} WHERE isnull(is_syn_pt,0)=0 "
                        f"ORDER BY {id_column} OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY"
                    )
                    print(f"Executing query: {query}")

                    # This pd.read_sql now runs inside our explicit transaction
                    chunk = pd.read_sql(query, conn)

                    if chunk.empty:
                        has_more = False
                        # We break here; the transaction will commit successfully (doing nothing)
                        break

                    all_chunks.append(chunk)

                    # 2. WRITE OPERATION (within the same transaction)
                    if id_column in chunk.columns:
                        ids = chunk[id_column].astype(str).tolist()

                        if ids:
                            id_placeholders = ','.join(['?' for _ in ids])
                            update_query = text(
                                f"UPDATE {table_name} SET is_syn_pt=1 WHERE {id_column} IN ({id_placeholders})")

                            # Execute the update
                            conn.execute(update_query, ids)
                            print(f"Updated {len(ids)} rows in {table_name}")
                    else:
                        print(
                            f"Error: '{id_column}' column not found in data from {table_name}. Cannot update sync status.")
                        # Raising an error will cause the 'with' block to automatically roll back
                        raise KeyError(f"Mandatory id_column '{id_column}' not found in {table_name}")

                # The 'with conn.begin()' block commits here if no errors were raised
                offset += len(chunk)

            except Exception as e:
                print(
                    f"An error occurred during the transaction for table {table_name}. The batch will be rolled back. Error: {e}")
                # Stop processing this table on error to prevent infinite loops
                has_more = False

    if all_chunks:
        return pd.concat(all_chunks, ignore_index=True)
    else:
        return pd.DataFrame()


def stream_synced_data(engine, table_name, id_column, batch_size=100000, update_chunk_size=1000):
    """
    Final robust version using direct SQL string formatting for the UPDATE statement.
    This is a last resort to bypass driver/dialect parameter interpretation issues.
    """
    has_more = True
    print(f"Starting data stream for SQL Server table '{table_name}' with batch size {batch_size}.")

    with engine.connect() as conn:
        while has_more:
            try:
                with conn.begin() as trans:
                    # 1. READ OPERATION: Select the NEXT available batch of unsynced rows.
                    query = (
                        f"SELECT TOP ({batch_size}) * FROM {table_name} "
                        f"WHERE is_syn_pt = 0 OR isnull(is_syn_pt, 0) = 0 "
                        f"ORDER BY {id_column}"
                    )

                    print(f"Executing query: {query}")
                    chunk = pd.read_sql(query, conn)

                    if chunk.empty:
                        print("No more unsynced data found. Stream complete.")
                        has_more = False
                        break

                    print(f"Fetched a chunk of size {len(chunk)}.")
                    yield chunk

                    # 2. WRITE OPERATION (within the same transaction)
                    ids = chunk[id_column].tolist()
                    if ids:
                        print(f"Updating {len(ids)} rows in smaller chunks of {update_chunk_size}...")

                        for i in range(0, len(ids), update_chunk_size):
                            ids_subset = ids[i:i + update_chunk_size]
                            if not ids_subset:
                                continue

                            # === FINAL FIX: Direct String Formatting ===
                            # Convert all IDs to strings to handle any potential data type issues
                            # and join them into a comma-separated list.
                            ids_as_strings = [str(item) for item in ids_subset]
                            in_clause_values = ",".join(ids_as_strings)

                            # Construct the SQL query by directly embedding the IDs.
                            # This is safe here because we know the IDs are just numbers from our own query.
                            update_query_text = (
                                f"UPDATE {table_name} SET is_syn_pt=1 "
                                f"WHERE {id_column} IN ({in_clause_values})"
                            )

                            # Execute the raw SQL string without any parameters.
                            conn.execute(text(update_query_text))

                            print(f"  - Updated {len(ids_subset)} rows.")

                        print("All update chunks for this batch completed.")

            except Exception as e:
                print(f"An error occurred during the transaction. Rolling back. Error: {e}")
                import traceback
                traceback.print_exc()  # This will print the full error traceback
                has_more = False  # Stop processing on error

    print("Data stream has finished.")


def loader(table_name):
    config = settings.TABLE_CONFIG.get(table_name)
    if not config:
        raise ValueError(f"No configuration found for table: {table_name}")
    return sync_data_to_df(DB_ENGINE, table_name, config['id_column'])


def load_or_query_parquet(table_name, loader_func):
    parquet_path = os.path.join(PARQUET_DIR, f"{table_name}.parquet")
    if os.path.exists(parquet_path):
        print(f"Loading cached parquet for {table_name} from {parquet_path}")
        df = pd.read_parquet(parquet_path)
    else:
        print(f"No cache found. Syncing data for {table_name} from database...")
        df = loader_func(table_name)
        if not df.empty:
            df.to_parquet(parquet_path, index=False)
            print(f"Saved synced data for {table_name} to {parquet_path}")
        else:
            print(f"No new data to sync for {table_name}, or sync failed.")
    return df


def sql_query_builder(collection_name, table_name, data, save_master=True):
    redis_key = settings.DATAFRAME_CACHE_DEFINE.format(
        collection=collection_name,
        full_path=table_name,
        type="db"
    )
    cached_result_bytes = r.get(redis_key)
    if not cached_result_bytes:
        r.set(redis_key, pickle.dumps(data), ex=settings.REDIS_EXPIRE_TIME)

    if save_master:
        master_description = settings.MASTER_DESCRIPTION_DEFINE.format(
            type="db",
            collection=collection_name,
            full_path=table_name,
            description=FACT_DOANH_THU_DESCRIPTION
        )
        r.rpush(settings.LIST_MASTER_DATA_DESCRIPTION, master_description)

    return

def load_and_cache_database_server(collection_name, table_name, save_master) -> str:
    redis_key = settings.DATAFRAME_CACHE_DEFINE.format(
        collection=collection_name,
        full_path=table_name,
        type="db"
    )
    print("We go to redis key: ", redis_key)
    cached_result_bytes = r.get(redis_key)

    if cached_result_bytes:
        result = pickle.loads(cached_result_bytes)
        print(f"Cache hit for key: {redis_key}. Loading data from Redis cache.")
        result[:1000].to_excel('dimnhanvien.xlsx', index=False, sheet_name='Synced Data')
        # master_description = settings.MASTER_DESCRIPTION_DEFINE.format(
        #     type="db",
        #     collection=collection_name,
        #     full_path=table_name,
        #     description=FACT_DOANH_THU_DESCRIPTION
        # )
        # r.rpush(settings.LIST_MASTER_DATA_DESCRIPTION, master_description)

        return "YES"


    print("Starting data sync and stream...")
    start_time = time.time()

    all_dfs = list(stream_synced_data(
        DB_ENGINE,
        settings.TABLE_CONFIG[table_name]['table_name'],
        settings.TABLE_CONFIG[table_name]['id_column'],
        batch_size=10000,  # Start with a larger batch size
        update_chunk_size=10000
    ))

    db_time = time.time()
    print(f"--- Database streaming took: {db_time - start_time:.2f} seconds ---")

    if all_dfs:
        print("Concatenating all chunks...")
        final_df = pd.concat(all_dfs, ignore_index=True)
        print(f"Saving DataFrame with {len(final_df)} rows to Excel file...")
        excel_start_time = time.time()
        output_filename = 'dimnhanvien.xlsx'
        final_df[:50].to_excel(output_filename, sheet_name='Synced Data', index=False)
        excel_end_time = time.time()

        print(f"--- Excel writing took: {excel_end_time - excel_start_time:.2f} seconds ---")
        print("File saved successfully!")
    else:
        print("No data was synced.")

    end_time = time.time()
    print(f"--- Total script runtime: {end_time - start_time:.2f} seconds ---")
    sql_query_builder(collection_name, table_name, final_df, save_master)
    return "NO"

if __name__ == "__main__":
    # Example usage
    load_and_cache_database_server("duythaitest", "FACTDOANHTHU", save_master=True)
