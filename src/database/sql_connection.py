import pyodbc
import pandas as pd
import os

class SqlServerDB:
    def __init__(self, server, database, user, password, driver="{ODBC Driver 18 for SQL Server}"):
        self.conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = pyodbc.connect(self.conn_str)
        return self.conn

    def fetchall(self, query, params=None):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        return result

    def execute(self, query, params=None):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        conn.commit()
        cursor.close()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


PARQUET_DIR = "parquet_cache"
os.makedirs(PARQUET_DIR, exist_ok=True)


# lấy dữ liệu df  parquet_cache
def get_cached_df(table_name):
    parquet_path = os.path.join(PARQUET_DIR, f"{table_name}.parquet")
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        return df
    else:
        raise FileNotFoundError(f"No cached parquet file found for table {table_name}")


# trường hợp cần syn thì lấy từ đây

def sync_data_to_df(db, table_name, batch_size=10000):
    conn = db.connect()
    offset = 0
    has_more = True
    all_chunks = []
    while has_more:
        query = (
            f"SELECT * FROM {table_name} WHERE isnull(is_syn_pt,0)=0 "
            f"ORDER BY Id OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY"
        )
        print(f"Executing query: {query}")  # Debug line to print the query

        chunk = pd.read_sql(query, conn)
        if chunk.empty:
            has_more = False
            break
        all_chunks.append(chunk)
        ids = chunk["ID"].astype(str).tolist()
        if ids:
            id_list = ",".join(f"'{id}'" for id in ids)
            update_query = f"UPDATE {table_name} SET is_syn_pt=1 WHERE Id IN ({id_list})"
            conn.execute(update_query)
            conn.commit()
        offset += batch_size
    if all_chunks:
        df = pd.concat(all_chunks, ignore_index=True)
    else:
        df = pd.DataFrame()
    return df

PARQUET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "parquet_cache")
os.makedirs(PARQUET_DIR, exist_ok=True)

TABLE_NAMES = [
    #"FACT_DOANHTHU",
    "DIM_NHANVIEN_KHO",
    "DIM_NHANVIEN_KENH"
]

_dataframes = {}

def load_or_query_parquet(table_name, loader_func):
    parquet_path = os.path.join(PARQUET_DIR, f"{table_name}.parquet")
    if os.path.exists(parquet_path):
        print(f"Loading cached parquet for {table_name} from {parquet_path}")
        df = pd.read_parquet(parquet_path)
    else:
        df = loader_func(table_name)
        df.to_parquet(parquet_path, index=False)
    return df

def loader(table_name):
    db = SqlServerDB(
        server="1.53.252.173,1433",  # Sửa lại dấu phẩy thay cho dấu hai chấm
        database="DWH",
        user="sa",
        password="Dms14Erp28"
    )
    return sync_data_to_df(db, table_name)

def init_dataframes():
    global _dataframes
    _dataframes = {}
    for table in TABLE_NAMES:
        _dataframes[table] = load_or_query_parquet(table, loader)
        print(f"Loaded dataframe for {table}, shape: {_dataframes[table].shape}")
        # count
        print(f"Row count for {table}: {_dataframes[table].shape[0]}")

def get_dataframe(table_name):
    return _dataframes.get(table_name)


loader(TABLE_NAMES[0])