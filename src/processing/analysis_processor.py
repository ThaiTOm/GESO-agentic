import pickle

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from config import settings
from llm.llm_langchain import cloud_llm_service
from context_engine.rag_prompt import SELECT_EXCEL_FILE_PROMPT_TEMPLATE
from typing import Tuple, Optional
import os
import json
import pandas as pd
import numpy as np
import logging
from database.redis_connection import r
import redis
import pyarrow.ipc as ipc
import pyarrow as pa

logger = logging.getLogger(__name__)


def _read_excel_file_data(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str, Optional[str]]:
    """
    Reads data and master sheets from an Excel file.

    Args:
        file_path: The full path to the Excel file.

    Returns:
        tuple: (data_df, master_df, description, error_message)
               - data_df: DataFrame from the "data" sheet or default sheet, or None if failed.
               - master_df: DataFrame from the "master" sheet, or None if failed.
               - description: Extracted description from master sheet, or empty string.
               - error_message: String describing the error if reading data_df failed, else None.
    """
    data_df = None
    master_df = None
    description = ""
    error_message = None

    # Try to read the master sheet
    try:
        master_df = pd.read_excel(file_path, sheet_name="master")
        # Ensure there's at least one row before accessing iloc[0]
        if not master_df.empty:
            description = " ".join(master_df.iloc[0].astype(str).tolist())
    except ValueError: # Specific for sheet_name not found
        logger.debug(f"Master sheet not found in {file_path}. Proceeding without master data.")
    except Exception as e:
        logger.warning(f"Could not read master sheet from {file_path}: {e}")

    # Try to read the data sheet
    try:
        data_df = pd.read_excel(file_path, sheet_name="data")
    except ValueError: # Specific for sheet_name 'data' not found, try default
        logger.info(f"Data sheet not found in {file_path}, attempting to read default sheet.")
        try:
            data_df = pd.read_excel(file_path)
        except Exception as e:
            error_message = f"Error reading default sheet from {file_path}: {e}"
            logger.error(error_message)
    except Exception as e: # Catch other potential errors during 'data' sheet read
        error_message = f"Error reading 'data' sheet from {file_path}: {e}"
        logger.error(error_message)

    return data_df, master_df, description, error_message


def get_excel_data_with_cache(file_path: str) -> Tuple[
    Optional[pd.DataFrame], Optional[pd.DataFrame], str, Optional[str]]:
    """
    A caching wrapper around _read_excel_file_data.
    Uses Redis as a cache, with PICKLE for robust serialization of the result tuple.
    """
    if r is None:
        return _read_excel_file_data(file_path)

    redis_key = f"excel_cache:{file_path}"

    try:
        cached_result_bytes = r.get(redis_key)

        if cached_result_bytes:
            logging.info(f"CACHE HIT for '{os.path.basename(file_path)}'")
            # Deserialize the entire tuple from bytes using pickle.loads
            return pickle.loads(cached_result_bytes)
        else:
            logging.info(f"CACHE MISS for '{os.path.basename(file_path)}'. Reading from file.")
            result_tuple = _read_excel_file_data(file_path)
            _, _, _, error_message = result_tuple

            if error_message is None:
                logging.info(f"Storing '{os.path.basename(file_path)}' in Redis cache.")
                # Serialize the entire tuple into bytes using pickle.dumps
                serialized_result = pickle.dumps(result_tuple)

                r.set(redis_key, serialized_result, ex=86400)

            return result_tuple

    except redis.exceptions.ConnectionError as e:
        logging.error(f"Redis connection error: {e}. Falling back to direct file read.")
        return _read_excel_file_data(file_path)


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


def _extract_metadata_from_excel(file_path: str) -> dict | None:
    """
    Extracts metadata from a single Excel file for LLM context.
    Reads only the first few rows for efficiency.
    """
    description = ""
    data_df = None

    try:
        master_df = pd.read_excel(file_path, sheet_name="master")
        if not master_df.empty:
            description = " ".join(master_df.iloc[0].astype(str).tolist())
    except ValueError:
        logger.debug(f"No 'master' sheet in {os.path.basename(file_path)}.")
    except Exception as e:
        logger.warning(f"Could not read master sheet from {os.path.basename(file_path)}: {e}")

    try:
        data_df = pd.read_excel(file_path, sheet_name="data", nrows=5)
    except ValueError:
        logger.debug(f"No 'data' sheet in {os.path.basename(file_path)}, trying default sheet.")
        try:
            data_df = pd.read_excel(file_path, nrows=5)
        except Exception as e:
            logger.warning(f"Could not read default sheet for metadata from {os.path.basename(file_path)}: {e}")
            return None
    except Exception as e:
        logger.warning(f"Could not read 'data' sheet for metadata from {os.path.basename(file_path)}: {e}")
        return None

    if data_df is None:
        return None

    metadata = {
        "file_name": os.path.basename(file_path),
        "description": description,
        "columns": list(data_df.columns),
        "sample_data": data_df.head(2).to_dict(orient="records"),
        "shape": data_df.shape
    }
    # No changes needed here! The data is returned with its original types.
    return metadata


async def select_excel_database(query: str, found_collection: str, cloud: bool = False) -> tuple:
    """
    Selects the appropriate Excel database file based on user query.
    Uses a Redis cache to speed up repeated file reads.
    """
    collection_folder = os.path.join(settings.UPLOAD_DIR, found_collection)

    if not os.path.exists(collection_folder):
        logger.error(f"Collection folder {collection_folder} does not exist")
        return None, None, "No database available", ""

    db_files = [os.path.join(collection_folder, f) for f in os.listdir(collection_folder)]

    if not db_files:
        logger.error(f"No database files found in {collection_folder}")
        return None, None, "No database available", ""

    # If only one database file exists, use it directly
    if len(db_files) == 1:
        file_path = db_files[0]
        # <<< REPLACED with cached call
        df, master_df, description, error = get_excel_data_with_cache(file_path)

        if error:
            return None, None, "Error reading database", ""
        return df, master_df, os.path.basename(file_path), description

    # Extract metadata (this part is fast, no need to cache `nrows=5` reads)
    db_metadata = [
        metadata for file_path in db_files
        if (metadata := _extract_metadata_from_excel(file_path)) is not None
    ]

    if not db_metadata:
        logger.error("Could not extract metadata from any database files. Falling back to first file.")
        file_path = db_files[0]
        df, master_df, description, error = get_excel_data_with_cache(file_path)
        if error:
            return None, None, "Error reading database", ""
        return df, master_df, os.path.basename(file_path), description

    db_metadata_json = json.dumps(
        db_metadata, indent=2, cls=CustomEncoder, ensure_ascii=False
    )
    prompt = SELECT_EXCEL_FILE_PROMPT_TEMPLATE.format(
        query=query, db_metadata_json=db_metadata_json
    )

    selected_db_name = None
    try:
        cloud_llm = cloud_llm_service
        raw_prompt_template = ChatPromptTemplate.from_template("{prompt}")
        llm_to_use = cloud_llm.bind(max_output_tokens=32)
        simple_chain = raw_prompt_template | llm_to_use | StrOutputParser()
        result = await simple_chain.ainvoke({"prompt": prompt})
        print("File choose is ", result)
        selected_db_name = result.strip()
    except Exception as e:
        logger.error(f"Exception calling LLM API: {e}. Falling back to first file.")
        # Fallback to the first file if LLM fails
        selected_db_name = os.path.basename(db_files[0])

    # --- Process LLM Result ---

    if selected_db_name == "NONE":
        logger.info("LLM determined no database can answer the query")
        return None, None, "No suitable database found for this query", ""

    # Find the full path of the selected database
    selected_path = next((path for path in db_files if os.path.basename(path) == selected_db_name), None)

    if not selected_path:
        logger.warning(f"LLM selected '{selected_db_name}' but it was not found. Falling back to first file.")
        selected_path = db_files[0]

    logger.info(f"Attempting to load data for: {os.path.basename(selected_path)}")
    data_df, master_df, description, error = get_excel_data_with_cache(selected_path)

    if error:
        logger.error(f"Failed to read selected/fallback file {selected_path}: {error}")
        return None, None, "Error reading database", ""

    # Get description from metadata if available, otherwise use from file read
    final_description = next(
        (meta.get("description", "") for meta in db_metadata if meta["file_name"] == os.path.basename(selected_path)),
        description)

    return data_df, master_df, os.path.basename(selected_path), final_description