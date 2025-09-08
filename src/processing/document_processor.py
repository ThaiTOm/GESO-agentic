import fitz
import logging
import pandas as pd

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

def add_new_data(existing_df, new_file_path):
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