import pickle
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from config import settings
from llm.llm_langchain import gemini_llm_service, local_llm_service
from context_engine.rag_prompt import SELECT_EXCEL_FILE_PROMPT_TEMPLATE
from typing import Tuple, Optional, Dict, Any, Coroutine
import os
import json
import pandas as pd
import logging
from database.redis_connection import r, delete_dataframe_from_cache, flush_redis_database, CustomEncoder
import redis


logger = logging.getLogger(__name__)


def _read_excel_file_data(file_path: str) -> Tuple[
    Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any], str, Optional[str]]:
    """
    Reads data, master, and permission sheets from an Excel file.

    Args:
        file_path: The full path to the Excel file.

    Returns:
        tuple: (data_df, master_df, permission_data, description, error_message)
               - data_df: DataFrame from the "data" sheet or default sheet, or None if failed.
               - master_df: DataFrame from the "master" sheet, or None if not found.
               - permission_data: Dictionary of permissions from the "permission" sheet, or {} if not found.
               - description: Extracted description from master sheet, or empty string.
               - error_message: String describing the error if reading data_df failed, else None.
    """
    data_df = None
    master_df = None
    permission_data = {}  # Default to an empty dictionary
    description = ""
    error_message = None

    # Try to read the master sheet (Existing code)
    try:
        master_df = pd.read_excel(file_path, sheet_name="master")
        if not master_df.empty:
            description = " ".join(master_df.iloc[0].astype(str).tolist())
    except ValueError:
        logger.debug(f"Master sheet not found in {file_path}. Proceeding without master data.")
    except Exception as e:
        logger.warning(f"Could not read master sheet from {file_path}: {e}")

    try:
        permission_df = pd.read_excel(file_path, sheet_name="permission")
        # Check if the required columns 'Permission' and 'Value' exist
        if 'Permission' in permission_df.columns and 'Value' in permission_df.columns:
            raw_permissions = permission_df.set_index('Permission')['Value'].to_dict()

            for key, value in raw_permissions.items():
                # Check if the value is a string that looks like a JSON object or array
                if isinstance(value, str) and (value.strip().startswith('{') or value.strip().startswith('[')):
                    try:
                        # If it is, parse it with json.loads
                        permission_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # If parsing fails, keep the original string value
                        permission_data[key] = value
                else:
                    # Otherwise, just use the value as is
                    permission_data[key] = value
        else:
            logger.warning(f"'Permission' or 'Value' column not found in the permission sheet of {file_path}.")

    except ValueError:  # Specific for sheet_name not found
        logger.debug(f"Permission sheet not found in {file_path}. Proceeding without permissions.")
    except Exception as e:
        logger.warning(f"Could not read or process permission sheet from {file_path}: {e}")

    try:
        data_df = pd.read_excel(file_path, sheet_name="data", engine='openpyxl')
    except ValueError:
        logger.info(f"Data sheet not found in {file_path}, attempting to read default sheet.")
        try:
            data_df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            error_message = f"Error reading default sheet from {file_path}: {e}"
            logger.error(error_message)
    except Exception as e:
        error_message = f"Error reading 'data' sheet from {file_path}: {e}"
        logger.error(error_message)

    if data_df is not None:
        # convert_dtypes() sẽ chuyển các cột số nguyên/thực về Int64/Float64
        # (có hỗ trợ giá trị rỗng pd.NA), và các kiểu khác nếu có thể.
        data_df = data_df.convert_dtypes()

    print("Permission data ", permission_data)
    # Note the new position of permission_data in the return tuple
    return data_df, master_df, permission_data, description, error_message


def get_excel_data_with_cache(file_path: str, cache_path: str) -> Tuple[
    Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any], str, Optional[str]]:
    """
    A caching wrapper around _read_excel_file_data.
    Uses Redis as a cache, with PICKLE for robust serialization of the result tuple.
    """
    try:
        # flush_redis_database()
        cached_result_bytes = r.get(cache_path)

        if cached_result_bytes:
            print("-" * 100)
            print("We have cached data for", cache_path)
            logging.info(f"CACHE HIT for '{os.path.basename(file_path)}'")
            # Deserialize the entire tuple from bytes using pickle.loads
            return pickle.loads(cached_result_bytes)
        else:
            logging.info(f"CACHE MISS for '{os.path.basename(file_path)}'. Reading from file.")
            result_tuple = _read_excel_file_data(file_path)
            _, _, _, _, error_message = result_tuple

            if error_message is None:
                logging.info(f"Storing '{os.path.basename(cache_path)}' in Redis cache.")
                # Serialize the entire tuple into bytes using pickle.dumps
                serialized_result = pickle.dumps(result_tuple)
                r.set(cache_path, serialized_result, ex=864000)

            return result_tuple

    except redis.exceptions.ConnectionError as e:
        logging.error(f"Redis connection error: {e}. Falling back to direct file read.")
        return _read_excel_file_data(file_path)



async def select_database(query:str, collection: str) -> tuple | None:
    """
    Extracts metadata from a single Excel file for LLM context.
    Reads only the first few rows for efficiency.
    """

    master_descriptions = r.lrange(settings.LIST_MASTER_DATA_DESCRIPTION, 0, -1)
    master_descriptions = [item.decode('utf-8') for item in master_descriptions]
    collection_description = [temp for temp in master_descriptions if temp.split("_")[0] == collection]
    db_metadata = "\n".join([
        "\n----------------\n" + md.split("Các cột chi tiết trong bảng dữ liệu bao gồm")[0]
        for md in collection_description
    ])

    prompt = SELECT_EXCEL_FILE_PROMPT_TEMPLATE.format(
        query=query, db_metadata_json=db_metadata
    )

    print("DB metadata for prompt: ", db_metadata)

    try:
        raw_prompt_template = ChatPromptTemplate.from_template("{prompt}")
        llm_to_use = gemini_llm_service.bind(max_output_tokens=32)
        simple_chain = raw_prompt_template | llm_to_use | StrOutputParser()
        result = await simple_chain.ainvoke({"prompt": prompt})
        print("LLM selected database (raw):", result)
        selected_db_name = [temp for temp in collection_description if result.strip() in temp][0]
        print("LLM selected database:", selected_db_name)
    except Exception as e:
        logger.error(f"Exception calling LLM API: {e}. Falling back to first file.")
        # Fallback to the first file if LLM fails
        selected_db_name = ""

    _collection_name = selected_db_name.split("_")[0] if selected_db_name else ""
    _type = selected_db_name.split("_")[1] if len(selected_db_name.split("_")) > 1 else ""
    _name_data = selected_db_name.split("_")[2] if len(selected_db_name.split("_")) > 2 else ""
    _selected_metadata = "_".join(selected_db_name.split("_")[3:]) if len(selected_db_name.split("_")) > 3 else ""

    if _type == "xlsx":
        return select_excel_database(_name_data, collection, _selected_metadata)
    else:
        key = settings.DATAFRAME_CACHE_DEFINE.format(
            collection=_collection_name,
            type=_type,
            full_path=_name_data
        )
        print("Selecting server database with key:", key)
        print("Selected metadata:", _selected_metadata)
        return select_server_database(key, _selected_metadata, None, selected_db_name, _selected_metadata)


def select_excel_database(selected_db_name: str, collection: str, descriptions: str) -> tuple:
    """
    Selects the appropriate Excel database file based on user query.
    Uses a Redis cache to speed up repeated file reads.
    """
    collection_folder = os.path.join(settings.UPLOAD_DIR, collection)

    if not os.path.exists(collection_folder):
        logger.error(f"Collection folder {collection_folder} does not exist")
        print(f"Collection folder {collection_folder} does not exist")
        return None, None, "No database available", "", ""
    db_files = [os.path.join(collection_folder, f) for f in os.listdir(collection_folder)]

    selected_path = selected_db_name

    if not selected_path:
        logger.warning(f"LLM selected '{selected_db_name}' but it was not found. Falling back to first file.")
        print(f"LLM selected '{selected_db_name}' but it was not found. Falling back to first file.")
        selected_path = db_files[0]

    logger.info(f"Attempting to load data for: {os.path.basename(selected_path)}")
    print(f"Attempting to load data for: {os.path.basename(selected_path)}")
    cache_path = settings.DATAFRAME_CACHE_DEFINE.format(
        collection=collection,
        type="xlsx",
        full_path=os.path.splitext(os.path.basename(selected_path))[0]
    )
    data_df, master_sheet, permission, description, error = get_excel_data_with_cache(file_path=selected_path, cache_path=cache_path)
    print("We have data: ")
    print(data_df.iloc[:5])
    if error:
        logger.error(f"Failed to read selected/fallback file {selected_path}: {error}")
        return None, None, "Error reading database", "", ""

    return data_df, descriptions, permission, os.path.basename(selected_path), descriptions

def select_server_database(key:str, master_description: str, permission: dict, selected_path: str, description: str) -> tuple:
    print("Selecting server database with key:", key)
    result = r.get(key)
    result = pickle.loads(result)
    print(result.iloc[:5])
    return result, master_description, {}, "selected_path", description