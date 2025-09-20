import math
import re
from typing import Any

import pandas as pd
from unidecode import unidecode


def standardize_text_upgraded(
        text: Any,
        to_lowercase: bool = True,
        remove_accents: bool = True,
        remove_punctuation: bool = True,
        remove_all_space: bool = True
) -> str:
    """
    Chuẩn hóa một chuỗi văn bản với nhiều tùy chọn linh hoạt.

    Quy trình mặc định:
    1. Xử lý giá trị đầu vào không phải chuỗi (None, NaN, int,...) -> trả về chuỗi rỗng.
    2. Bỏ dấu tiếng Việt (nếu remove_accents=True).
    3. Chuyển thành chữ thường (nếu to_lowercase=True).
    4. Xóa các ký tự đặc biệt, dấu câu (nếu remove_punctuation=True).
    5. Xử lý khoảng trắng:
        - Xóa tất cả khoảng trắng (nếu remove_all_space=True).
        - Chuẩn hóa về một khoảng trắng duy nhất và xóa khoảng trắng thừa ở đầu/cuối (nếu remove_all_space=False).

    Args:
        text (Any): Dữ liệu đầu vào cần chuẩn hóa.
        to_lowercase (bool): True nếu muốn chuyển thành chữ thường.
        remove_accents (bool): True nếu muốn bỏ dấu tiếng Việt.
        remove_punctuation (bool): True nếu muốn xóa dấu câu và ký tự đặc biệt.
        remove_all_space (bool):
            - True: Xóa tất cả khoảng trắng (e.g., "a b c" -> "abc").
            - False: Chuẩn hóa về một khoảng trắng duy nhất (e.g., "a   b  c" -> "a b c").

    Returns:
        str: Chuỗi văn bản đã được chuẩn hóa.
    """
    # 1. Handle non-string, None, or NaN inputs robustly
    if text is None:
        return ""
    # Check for NaN values (e.g., from numpy or pandas)
    if isinstance(text, float) and math.isnan(text):
        return ""

    processed_text = str(text)

    # 2. Remove Vietnamese accents (e.g., "Sữa Mẹ" -> "Sua Me")
    if remove_accents:
        processed_text = unidecode(processed_text)

    # 3. Convert to lowercase (e.g., "Sua Me" -> "sua me")
    if to_lowercase:
        processed_text = processed_text.lower()

    # 4. Remove punctuation and special characters (e.g., "sua-me 100%" -> "sua me 100")
    # This regex keeps letters, numbers, and whitespace.
    if remove_punctuation:
        processed_text = re.sub(r'[^a-z0-9\s]', '', processed_text)

    # 5. Handle whitespace based on the flag
    if remove_all_space:
        # Remove all whitespace characters (e.g., "sua me 100" -> "suame100")
        processed_text = re.sub(r'\s+', '', processed_text)
    else:
        # Normalize multiple whitespace to a single space and trim
        # (e.g., "  sua   me   100  " -> "sua me 100")
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

    return processed_text


def parse_master_sheet(master_df: pd.DataFrame, data_columns: list) -> dict:
    """
    Phân tích DataFrame của sheet 'master' thành một dictionary.
    Key là tên cột, Value là chuỗi miêu tả đầy đủ.
    """
    if master_df.empty or len(master_df.columns) == 0:
        return {}

    master_col_name = master_df.columns[0]
    descriptions = {}
    current_col = None
    current_desc_lines = []

    for line in master_df[master_col_name].dropna().astype(str):
        # Kiểm tra xem dòng này có phải là tên một cột trong sheet data không
        if line.split(":")[0].strip() in data_columns:
            descriptions[line.split(":")[0].strip()] = line.split(":", 1)[1].strip() if ":" in line else ""
        else:
            descriptions[line] = line


    return descriptions