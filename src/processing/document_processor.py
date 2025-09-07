import fitz
import os
import logging
from typing import Tuple, Optional
import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import settings
from llm.llm_langchain import cloud_llm_service
from context_engine.rag_prompt import SELECT_EXCEL_FILE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> list[str]:
    """Extracts all text from a PDF file, page by page."""
    pages = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text().lower()
                pages.append(text)
        return pages
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return []


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> tuple[list[str], list[tuple[int, int]]]:
    """
    Splits text into smaller chunks with overlap.
    (This function remains the same as in the original file)
    """
    # ... (The full chunk_text function from the original file goes here) ...
    chunks = []
    chunk_indices = []

    if not text:
        return [], []

    if len(text) <= max_chars:
        return [text], [(0, len(text))]

    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))

        if end < len(text):
            # Find a suitable break point (sentence or space)
            break_point = text.rfind('. ', start, end)
            if break_point != -1 and break_point > start:
                end = break_point + 1
            else:
                break_point = text.rfind(' ', start, end)
                if break_point != -1 and break_point > start:
                    end = break_point + 1

        chunk = text[start:end]
        chunks.append(chunk)
        chunk_indices.append((start, end))

        if end >= len(text):
            break

        start = end - overlap
        if start <= chunk_indices[-1][0]:  # Ensure progress
            start = chunk_indices[-1][0] + 1

    return chunks, chunk_indices


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

def _extract_metadata_from_excel(file_path: str) -> dict | None:
    """
    Extracts metadata from a single Excel file for LLM context.
    Reads only the first few rows for efficiency.

    Args:
        file_path: The path to the Excel file.

    Returns:
        A dictionary containing metadata, or None if the file cannot be processed.
    """
    description = ""
    data_df = None

    # Step 1: Try to get the description from the 'master' sheet
    try:
        master_df = pd.read_excel(file_path, sheet_name="master")
        if not master_df.empty:
            description = " ".join(master_df.iloc[0].astype(str).tolist())
    except ValueError: # This is a more specific error for "sheet not found"
        logger.debug(f"No 'master' sheet in {os.path.basename(file_path)}.")
    except Exception as e:
        logger.warning(f"Could not read master sheet from {os.path.basename(file_path)}: {e}")

    # Step 2: Try to get the data preview from the 'data' sheet or default sheet
    try:
        data_df = pd.read_excel(file_path, sheet_name="data", nrows=5)
    except ValueError:
        logger.debug(f"No 'data' sheet in {os.path.basename(file_path)}, trying default sheet.")
        try:
            data_df = pd.read_excel(file_path, nrows=5)
        except Exception as e:
            logger.warning(f"Could not read default sheet for metadata from {os.path.basename(file_path)}: {e}")
            return None # Critical failure, can't get metadata
    except Exception as e:
        logger.warning(f"Could not read 'data' sheet for metadata from {os.path.basename(file_path)}: {e}")
        return None # Critical failure

    # If we couldn't load any dataframe for metadata, we can't proceed with this file.
    if data_df is None:
        return None

    # Step 3: If successful, create and return the metadata dictionary
    metadata = {
        "file_name": os.path.basename(file_path),
        "description": description,
        "columns": list(data_df.columns),
        "sample_data": data_df.head(2).to_dict(orient="records"),
        "shape": data_df.shape # Note: shape will be (5, num_cols) due to nrows=5
    }
    return metadata


async def select_excel_database(query: str, found_collection: str, cloud: bool =False) -> tuple:
    """
    Selects the appropriate Excel database file based on user query by comparing
    the query with the descriptions in the master sheets of database files.

    Args:
        query: User's query
        found_collection: The collection/folder where Excel files are stored
        cloud
    Returns:
        tuple: (data_df, master_df, database_name, database_description) -
               The data DataFrame, master DataFrame, the name of the database file, and its description
    """
    import os
    import json

    # Path to the collection's folder
    collection_folder = os.path.join(settings.UPLOAD_DIR, found_collection)

    # Check if the folder exists
    if not os.path.exists(collection_folder):
        logger.error(f"Collection folder {collection_folder} does not exist")
        return None, None, "No database available", ""

    # Find all database Excel files (only database_no1.xlsx to database_no5.xlsx format)
    db_files = []
    for temp in os.listdir(collection_folder):
        db_files.append(os.path.join(collection_folder, temp))

    if not db_files:
        logger.error(f"No database files found in {collection_folder}")
        return None, None, "No database available", ""

    # If only one database file exists, return it directly
    if len(db_files) == 1:
        file_path = db_files[0]
        # Use the new helper function
        df, master_df, description, error = _read_excel_file_data(file_path)

        if error:
            # The helper function already logged the error, just return failure state
            return None, None, "Error reading database", ""

        # If no error, return the successfully read data
        return df, master_df, os.path.basename(file_path), description

    db_metadata = [
        metadata for file_path in db_files
        if (metadata := _extract_metadata_from_excel(file_path)) is not None
    ]

    # Handle the case where NO metadata could be extracted from ANY file
    if not db_metadata:
        logger.error("Could not extract metadata from any database files. Falling back to first file.")

        # REUSE the helper function from the previous refactoring!
        df, master_df, description, error = _read_excel_file_data(db_files[0])

        if error:
            # The helper already logged the specific error
            return None, None, "Error reading database", ""

        return df, master_df, os.path.basename(db_files[0]), description

    # Prepare LLM prompt to select the appropriate database
    prompt = SELECT_EXCEL_FILE_PROMPT_TEMPLATE.format({
        "query": query,
        "db_metadata_json": json.dumps(db_metadata, indent=2)
    })
    print(prompt)
    # Call LLM API to select the database
    try:
        cloud_llm = cloud_llm_service
        raw_prompt_template = ChatPromptTemplate.from_template("{prompt}")
        llm_to_use = cloud_llm.bind(max_output_tokens=32)
        simple_chain = raw_prompt_template | llm_to_use | StrOutputParser()
        result = await simple_chain.ainvoke({"input_prompt": prompt})
        print(result)
        raw_text = result.strip()

        # Extract just the filename using regex if the response contains more text
        import re
        filename_match = re.search(r'(database_no\d+\.xlsx)', raw_text)
        if filename_match:
            selected_db = filename_match.group(1)
        else:
            # Check if the response is exactly "NONE"
            if raw_text == "NONE":
                selected_db = "NONE"
            else:
                # LLM didn't follow the format, use first file as fallback
                logger.warning(f"LLM response did not match expected format: ''")
                selected_db = os.path.basename(db_files[0])

        # Validate the selected database
        if selected_db == "NONE":
            logger.info("LLM determined no database can answer the query")
            return None, None, "No suitable database found for this query", ""

        # Find the full path of the selected database and its description
        selected_path = None
        selected_desc = ""
        for file_path in db_files:
            if os.path.basename(file_path) == selected_db:
                selected_path = file_path
                # Try to get description from metadata
                for metadata in db_metadata:
                    if metadata["file_name"] == selected_db:
                        selected_desc = metadata.get("description", "")
                        break
                break

        if selected_path:
            try:
                # Read both data and master sheets from the selected database
                data_df = pd.read_excel(selected_path, sheet_name="data")
                master_df = None
                try:
                    master_df = pd.read_excel(selected_path, sheet_name="master")
                except Exception as e:
                    logger.warning(f"Could not read master sheet from selected database: ")

                logger.info(f"Selected database: ")
                return data_df, master_df, selected_db, selected_desc
            except Exception as e:
                logger.error(f"Error reading data sheet from {selected_path}: ")
                try:
                    # Try with default sheet
                    data_df = pd.read_excel(selected_path)
                    master_df = None
                    try:
                        master_df = pd.read_excel(selected_path, sheet_name="master")
                    except Exception:
                        pass
                    return data_df, master_df, selected_db, selected_desc
                except Exception as e2:
                    logger.error(f"Error reading default sheet from {selected_path}: {e2}")

        # If we couldn't read the selected database, fall back to the first one
        logger.warning(f"Selected database {selected_db} could not be read, falling back to first database")


    except Exception as e:
        logger.error(f"Exception calling LLM API: {e}")

    # Fallback: use the first database file
    file_path = db_files[0]
    description = ""
    master_df = None
    try:
        # Try to read the master sheet to get the description
        master_df = pd.read_excel(file_path, sheet_name="master")
        description = " ".join(master_df.iloc[0].astype(str).tolist())
    except Exception:
        pass

    try:
        # Read the data sheet
        data_df = pd.read_excel(file_path, sheet_name="data")
        return data_df, master_df, os.path.basename(file_path), description
    except Exception:
        try:
            data_df = pd.read_excel(file_path)
            return data_df, master_df, os.path.basename(file_path), description
        except Exception as e:
            logger.error(f"Error reading fallback Excel file {file_path}: {e}")
            return None, None, "Error reading database", ""


def add_new_data(existing_df, new_file_path):
    # Nếu existing_df là None, chỉ đọc file mới và trả về DataFrame đó
    if existing_df is None:
        try:
            print(f"Reading new data file: {new_file_path}")
            # Đọc sheet "data" trong file Excel mới
            new_df = pd.read_excel(new_file_path, sheet_name="data")
            new_df.columns = [col.strip() for col in new_df.columns]
            print(f"==> New data file has {len(new_df)} rows")

            # Đọc sheet "master" để kiểm tra thông tin tóm tắt
            try:
                master_df = pd.read_excel(new_file_path, sheet_name="master")
                print(f"==> Master sheet found with {len(master_df)} rows")
            except Exception as e:
                print(f"Warning: Could not read master sheet: {e}")

            return new_df
        except Exception as e:
            print("Please check your file format! Error:", e)
            raise e

    # Nếu existing_df không None
    existing_columns = [col.strip() for col in existing_df.columns]
    print(f"Existing combined data has {len(existing_df)} rows with columns: {existing_columns}")

    try:
        print(f"Reading new data file: {new_file_path}")
        # Đọc sheet "data" trong file Excel mới
        new_df = pd.read_excel(new_file_path, sheet_name="data")
        new_df.columns = [col.strip() for col in new_df.columns]
        print(f"==> New data file has {len(new_df)} rows with columns: {list(new_df.columns)}")

        # Đọc sheet "master" để kiểm tra thông tin tóm tắt
        try:
            master_df = pd.read_excel(new_file_path, sheet_name="master")
            print(f"==> Master sheet found with {len(master_df)} rows")
        except Exception as e:
            print(f"Warning: Could not read master sheet: {e}")

        # Kiểm tra xem có thể ghép dữ liệu không (có cột chung)
        common_columns = set(existing_columns).intersection(set(new_df.columns))
        if not common_columns:
            raise ValueError("No common columns found between existing data and new data.")

        # Hiển thị thông tin về cột
        missing_in_new = set(existing_columns) - set(new_df.columns)
        extra_in_new = set(new_df.columns) - set(existing_columns)

        if missing_in_new:
            print(f"Info: Columns missing in new file: {missing_in_new}")
        if extra_in_new:
            print(f"Info: Extra columns in new file: {extra_in_new}")

        # Nếu cột không giống hoàn toàn, sử dụng ghép theo cột chung
        if set(existing_columns) != set(new_df.columns):
            print(f"Merging data on common columns: {common_columns}")

            # Chuẩn bị DataFrame để ghép
            # Nếu có cột chung nhiều, chọn tất cả để ghép
            merged_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)

            # Loại bỏ dữ liệu trùng lặp dựa trên tất cả các cột chung
            combined_df_no_dupes = merged_df.drop_duplicates(subset=list(common_columns))
            duplicates_removed = len(merged_df) - len(combined_df_no_dupes)
            print(f"==> Removed {duplicates_removed} duplicate rows based on common columns")
        else:
            # Nếu cột giống nhau hoàn toàn, thực hiện ghép đơn giản
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df_no_dupes = combined_df.drop_duplicates()
            duplicates_removed = len(combined_df) - len(combined_df_no_dupes)
            print(f"==> Removed {duplicates_removed} duplicate rows")

        # Cập nhật sheet "master" với thông tin mới về dữ liệu đã kết hợp
        try:
            # Tạo hoặc cập nhật thông tin tóm tắt cho sheet "master"
            summary_data = {
                'Last_Updated': pd.Timestamp.now(),
                'Total_Rows': len(combined_df_no_dupes),
                'Columns': ', '.join(combined_df_no_dupes.columns),
                'Duplicates_Removed': duplicates_removed
            }

            summary_df = pd.DataFrame([summary_data])

            # Lưu cả hai sheet vào file Excel mới
            output_path = new_file_path.replace('.xlsx', '_combined.xlsx')
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name="master", index=False)
                combined_df_no_dupes.to_excel(writer, sheet_name="data", index=False)

            print(f"Updated combined data saved to {output_path}")
            print(f"Final row count: {len(combined_df_no_dupes)}")
        except Exception as e:
            print(f"Warning: Could not update master sheet: {e}")
            # Vẫn lưu dữ liệu chính nếu không thể cập nhật sheet master
            output_path = new_file_path.replace('.xlsx', '_combined.xlsx')
            combined_df_no_dupes.to_excel(output_path, sheet_name="data", index=False)
            print(f"Only data sheet saved to {output_path}")

        return combined_df_no_dupes

    except Exception as e:
        print("Error during data merge process:", e)
        raise e