import re

import pandas as pd
from unidecode import unidecode


def standardize_text(text: str) -> str:
    """
    Chuẩn hóa một chuỗi văn bản:
    1. Chuyển thành chuỗi (để xử lý các giá trị không phải string như NaN).
    2. Bỏ dấu tiếng Việt.
    3. Chuyển thành chữ thường.
    4. Xóa tất cả các khoảng trắng.
    """
    if not isinstance(text, str):
        text = str(text)

    # 1. Bỏ dấu tiếng Việt (e.g., "Sữa" -> "Sua")
    text_no_accent = unidecode(text)

    # 2. Chuyển thành chữ thường (e.g., "Sua" -> "sua")
    text_lower = text_no_accent.lower()

    # 3. Xóa tất cả khoảng trắng (e.g., "colos baby gold for mom" -> "colosbabygoldformom")
    text_no_space = re.sub(r'\s+', '', text_lower)

    return text_no_space


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