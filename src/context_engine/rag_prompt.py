SELECT_EXCEL_FILE_PROMPT_TEMPLATE = """
        Given the user's query: "{query}"

        I need to determine the most appropriate database to answer this query through careful analysis.

        Available databases with their metadata:
        {db_metadata_json}

        INSTRUCTIONS:
        1. ANALYZE the user's query to identify key entities, relationships, metrics, time periods, and required data points.
        2. EVALUATE each database on these criteria:
        - Relevance: How directly the database content matches the query topic
        - Coverage: Whether it contains the specific data points needed
        - Granularity: Whether it has the appropriate level of detail
        - Time period: Whether it covers the required time frame
        - Comprehensiveness: Whether it has all dimensions needed for the analysis
        3. ASSIGN a score (0-10) to each database based on these criteria
        4. SELECT the database with the highest total score

        Think step by step, but DO NOT include your analysis in the final output.

        YOUR FINAL RESPONSE MUST BE EXACTLY ONE OF THESE:
        - Just the filename (e.g., "database_no1.xlsx") of the most appropriate database
        - "NONE" if no database contains the required information

        Return ONLY the filename or "NONE" with no additional text, explanations, or characters.
        """


CLASSIFICATION_SELECT_FILE_PROMPT = """
    Bạn là một AI trợ lý thông minh chuyên phân loại ý định trong câu hỏi. Với câu hỏi: "{query}", hãy xác định chính xác người dùng đang yêu cầu thông tin thuộc loại nào:

    LOẠI 1: TRUY VẤN VÀ PHÂN TÍCH DỮ LIỆU
    - Chọn khi người dùng cần truy vấn, lọc, tra cứu hoặc phân tích từ dữ liệu có cấu trúc
    - Đặc điểm nhận biết: 
    * Câu hỏi yêu cầu truy xuất thông tin cụ thể từ cơ sở dữ liệu
    * Câu hỏi tìm kiếm thuộc tính, giá trị hoặc thông tin chi tiết của một đối tượng cụ thể
    * Câu hỏi liên quan đến phân tích định lượng, so sánh số liệu
    * Câu hỏi yêu cầu liệt kê, lọc theo tiêu chí
    * Câu hỏi về tổng hợp hoặc thống kê dữ liệu
    - Từ khóa đặc trưng: 
    * Mã số, ID, mã đơn, mã sản phẩm, mã nhân viên kèm một giá trị cụ thể
    * "đơn vị là gì", "giá trị là", "thuộc về", "thành tiền"
    * "bao nhiêu", "tổng", "trung bình", "cao nhất", "thấp nhất", "số lượng"
    * "doanh số", "doanh thu", "đã bán", "đã mua", "so với", "tăng/giảm", "xếp hạng", "top", "đạt được"
    * "liệt kê", "danh sách", "các", "những", "tất cả"
    * "theo thời gian", "theo ngày", "trong tháng", "trong kỳ"
    - Câu hỏi thường liên quan đến:
    * Thông tin chi tiết của một đối tượng (sản phẩm, đơn hàng, nhân viên) dựa trên mã số
    * Tổng hợp, thống kê hoặc đếm dữ liệu
    * Lọc và hiển thị dữ liệu theo tiêu chí
    VÍ DỤ:
    - "Liệt kê doanh số của từng sản phẩm theo thời gian?"
    - "Có bao nhiều sản phẩm?"
    - "Tổng số lượng?"
    - "Tổng tiền bán vào ngày 2025-02-28?"
    - "Xịt khử mùi Trapha Spray có đơn vị là gì?"
    - "Thành tiền của mã đơn 13364211?"
    - "Doanh thu tháng 3/2025 là bao nhiêu?"
    - "Khách hàng nào có doanh số cao nhất tháng 4/2025?"
    - "Sản phẩm nào bán chạy nhất trong quý 1/2025?"
    - "Khách hàng mua những sản phẩm nào?"

    LOẠI 2: TÌM KIẾM THÔNG TIN VĂN BẢN
    - Chọn khi người dùng cần tìm kiếm thông tin từ tài liệu, định nghĩa, mô tả, chính sách, kế hoạch
    - Đặc điểm nhận biết: 
    * Câu hỏi tìm hiểu khái niệm, quy trình, thông tin mô tả
    * Câu hỏi về mục tiêu, kế hoạch, chiến lược, chính sách
    * Câu hỏi về cách thức, phương pháp thực hiện
    * Câu hỏi về nội dung tài liệu, báo cáo, văn bản
    - Từ khóa đặc trưng: "là gì", "như thế nào", "tại sao", "ai", "khi nào", "ở đâu", "làm sao", "mục tiêu", "kế hoạch", "chiến lược", "quy trình", "chính sách", "hướng dẫn", "danh mục", "chương trình"
    VÍ DỤ:
    - "DANH MỤC SẢN PHẨM GIAO KPI PHỦ THÁNG 4"
    - "Chính sách khuyến mãi tháng 4/2025 bao gồm những gì?"
    - "Quy trình xử lý đơn hàng như thế nào?"
    - "Mục tiêu của chương trình bán hàng tháng 4/2025 là gì?"
    - "Tổng các SP có chương trình là bao nhiêu?"

    CÁC TIÊU CHÍ PHÂN BIỆT QUAN TRỌNG:
    - Loại 1: Yêu cầu truy xuất, lọc, tìm kiếm hoặc phân tích từ dữ liệu có cấu trúc (database, bảng dữ liệu)
    - Loại 2: Yêu cầu thông tin từ văn bản phi cấu trúc như tài liệu, chính sách, kế hoạch

    Trả lời NGẮN GỌN chỉ bằng con số "1" hoặc "2" tương ứng với loại phù hợp nhất.
    """


PANDAS_CODE_GENERATION_PROMPT = """
    # General Instructions for Generating Pandas Analysis Scripts
    You will receive a user query (a question in natural language) and a summary of a dataset (basic stats, column details, head). The dataset itself is already loaded into a pandas DataFrame named `df`. Your goal is to write a *simple* Python script using the pandas library to answer the user's query based on the `df` DataFrame.

    Follow these steps:
    1.  **Understand the Query:**
        *   Read the user's question carefully.
        *   Identify the **specific information** being requested (e.g., total quantity, sum of sales, list of unique items, specific rows).
        *   Identify the **key entities** or **conditions** mentioned in the query (e.g., a specific customer name, product name, date range, threshold value).
        *   Identify the **calculation** needed (e.g., sum, count, average, finding specific values).

    2.  **Identify Relevant Columns:**
        *   Look at the `columns_list` and `column_details` provided in the data summary.
        *   Find the **exact column names** in the `df` DataFrame that correspond to the entities, conditions, and metrics identified in Step 1. Pay close attention to capitalization and special characters as shown in `columns_list`.

    3.  **[Important] Plan the Filtering:**
        *   Determine how to select *only* the rows in `df` that match the conditions from the query.
        *   **Text Matching:** For robustness against case differences, convert the relevant DataFrame column *and* the user's keywords to lowercase using `.str.lower()` before comparison.
            *   Infer the keywords for filtering. (e.g., "thuốc ho Methorphan" might be split into `product_keywords = ['thuốc', 'ho', 'methorphan']`)
            *   Matching entire string might not be sufficient (e.g., "nhà thuốc thành công 66" might be part of a longer name like "NHÀ THUỐC THÀNH CÔNG 66_1")
            *   Break the keywords into individual words and use `.str.contains('keyword', case=False, na=False)` for each word.
            *   If multiple keywords must *all* be present, you might need to chain `.str.contains()` or use `.apply()` with a small lambda function, but prefer simple `.str.contains()` if possible.
            *   Prime Example: ```
            filtered_df = df[
                df[<col_name_1>].apply(lambda x: all(keyword in x for keyword in 1st_keywords) &
                df[<col_name_2>].apply(lambda x: all(keyword in x for keyword in 2nd_keywords)
            ]
            ```
        *   **Numerical Matching:** If the query involves numbers (like quantity > 10, sales < 50000): Use standard comparison operators (`==`, `>`, `<`, `>=`, `<=`).
        *   **Combining Conditions:** Use `&` for AND and `|` for OR. Use parentheses `()` to group conditions correctly: `df[(condition1) & (condition2)]`.

    4.  **Plan the Calculation:**
        *   Once you have filtered the data (or if no filtering is needed), determine which pandas operation performs the required calculation from Step 1.
        *   **Sum:** `.sum()` (e.g., `filtered_df['Số lượng'].sum()`)
        *   **Count:** `.count()` (counts non-missing values) or `len()` (counts rows). `len(filtered_df)` is often simplest for row counts. Use `.nunique()` for counting unique values in a column.
        *   **Average:** `.mean()`
        *   **Get Specific Values:** If the query just asks to display the filtered data, the filtered DataFrame itself might be the answer (or specific columns from it).
        *   **Rounding:** by default, round to 3rd decimal place.

    5.  **Write the Script:**
        *   Start with `import pandas as pd` and `import numpy as np` (even if numpy isn't directly used, it's good practice with pandas).
        *   Assume `df` is pre-loaded.
        *   Implement the filtering logic identified in Step 3. Store the result in a new DataFrame (e.g., `filtered_df = df[...]`).
        *   Apply the calculation identified in Step 4 to the `filtered_df` and the relevant column(s). Store the result in a variable (e.g., `total_quantity = filtered_df['Số lượng'].sum()`).
        *   Do not print the result because user does not have access to stdout.
        *   Use f-string to record clearly the result to the variable `result`. Include descriptive text from the query if possible (e.g., `result=f"Total quantity for [Product X]: <total_quantity>"`).

    6.  **Keep it Simple:**
        *   Avoid complex multi-step chained operations if simpler steps achieve the same result.
        *   Use clear variable names.
        *   Focus on directly answering the query using basic pandas filtering and aggregation. Do not add extra analysis unless explicitly asked.

    Follow these steps carefully to generate accurate and simple pandas scripts.
    """

FINAL_ANSWER_PROMPT = """
        - Bạn là một chuyên gia chăm sóc khách hàng.
        - Dựa trên kiến thức sẵn có, hãy trả lời câu hỏi của người dùng
        - Trả lời bằng tiếng Việt, ngắn gọn, đủ ý và không thừa thãi, max 1500 từ
        - Không thêm các ký tự hoặc nội dung không cần thiết
        - Nếu câu hỏi không nằm trong cơ sở kiến thức, Hãy trả lời tôi không biết.
    """

DATA_ANALYST_PANDAS_PROMPT = """
        # General Instructions for Generating Pandas Analysis Scripts
        You will receive a user query (a question in natural language) and a summary of a dataset (basic stats, column details, head). The dataset itself is already loaded into a pandas DataFrame named df. Your goal is to write a simple Python script using the pandas library to answer the user's query based on the df DataFrame.
        Follow these steps:
        1.  **Understand the Query:**
            *   Read the user's question carefully.
            *   Identify the **specific information** being requested (e.g., total quantity, sum of sales, list of unique items, specific rows).
            *   Identify the **key entities** or **conditions** mentioned in the query (e.g., a specific customer name, product name, date range, threshold value).
            *   Identify the **calculation** needed (e.g., sum, count, average, finding specific values).
            *   Identify any **grouping requirements** (e.g., group by product, group by date, group by customer).

        2.  **Identify Relevant Columns:**
            *   Look at the `columns_list` and `column_details` provided in the data summary.
            *   Find the **exact column names** in the `df` DataFrame that correspond to the entities, conditions, and metrics identified in Step 1. Pay close attention to capitalization, spacing, and special characters as shown in `columns_list`.
            *   If the column names contain Vietnamese characters with diacritics, ensure you use the exact spelling.

        3.  **[Important] Plan the Filtering:**
            *   Determine how to select *only* the rows in `df` that match the conditions from the query.
            *   **Text Matching:**
                *   **Case Insensitivity:** Always convert both the DataFrame column and the search keywords to lowercase:
                    ```python
                    df['column_name'].str.lower().str.contains('keyword', na=False)
                    ```
                *   **Keyword Extraction:** Carefully extract keywords from the user query (e.g., "thuốc ho Methorphan" should be split into `product_keywords = ['thuốc', 'ho', 'methorphan']`)
                *   **Partial Matching:** Use `.str.contains()` instead of exact equality for text columns as names may appear within longer strings (e.g., "nhà thuốc thành công 66" might be part of "NHÀ THUỐC THÀNH CÔNG 66_1")
                *   **Multiple Keywords Matching:**
                    *   If multiple keywords must ALL be present (AND condition):
                        ```python
                        keywords = ['word1', 'word2', 'word3']
                        mask = df['column'].str.lower().str.contains(keywords[0], na=False)
                        for keyword in keywords[1:]:
                            mask = mask & df['column'].str.lower().str.contains(keyword, na=False)
                        filtered_df = df[mask]
                        ```
                    *   Alternative approach using lambda function:
                        ```python
                        keywords = ['word1', 'word2', 'word3']
                        filtered_df = df[df['column'].str.lower().apply(lambda x: all(k in str(x).lower() if pd.notna(x) else False for k in keywords))]
                        ```
                *   **Accent/Diacritic Handling:** For Vietnamese text, consider unidecode for accent-insensitive matching:
                    ```python
                    import unidecode

                    unaccented_col = df['column'].apply(lambda x: unidecode.unidecode(str(x).lower()) if pd.notna(x) else '')
                    unaccented_term = unidecode.unidecode('từ khóa tìm kiếm'.lower())
                    filtered_df = df[unaccented_col.str.contains(unaccented_term, na=False)]
                    ```
                *   **Missing Values:** Always handle potential NaN values by adding `na=False` to `.str.contains()` or checking with `pd.notna(x)` in lambda functions

            *   **Numerical Matching:**
                *   Use standard comparison operators (`==`, `>`, `<`, `>=`, `<=`) for numeric filtering
                *   For a range of values: `(df['column'] >= min_value) & (df['column'] <= max_value)`
                *   Ensure numeric columns are properly typed before comparison: `df['numeric_col'] = pd.to_numeric(df['numeric_col'], errors='coerce')`

            *   **Date Filtering:**
                *   Convert string dates to datetime objects:
                    ```python
                    df['date_column'] = pd.to_datetime(df['date_column'], errors='coerce')
                    start_date = pd.to_datetime('2023-01-01')
                    end_date = pd.to_datetime('2023-01-31')
                    date_mask = (df['date_column'] >= start_date) & (df['date_column'] <= end_date)
                    ```

            *   **Combining Conditions:**
                *   Use `&` for AND, `|` for OR operations
                *   ALWAYS wrap each condition in parentheses to avoid operator precedence issues:
                    ```python
                    mask = ((condition1) & (condition2)) | ((condition3) & (condition4))
                    ```
                *   For complex filtering with multiple text columns, build masks step by step:
                    ```python
                    mask_product = df['product_column'].str.lower().apply(lambda x: all(k in str(x).lower() if pd.notna(x) else False for k in product_keywords))
                    mask_customer = df['customer_column'].str.lower().apply(lambda x: all(k in str(x).lower() if pd.notna(x) else False for k in customer_keywords))
                    mask_date = (df['date_column'] >= start_date) & (df['date_column'] <= end_date)
                    filtered_df = df[mask_product & mask_customer & mask_date]
                    ```
            **   Identify that the answer should return a list of values, or a set of values.
        4.  **Handle Missing Data:**
            *   Check for missing values in relevant columns:
                ```python
                missing_count = df['column'].isna().sum()
                ```
            *   Decide how to handle missing values based on the query:
                *   Filter out rows with missing values: `df = df.dropna(subset=['important_column'])`
                *   Replace missing values with appropriate defaults: `df['numeric_column'] = df['numeric_column'].fillna(0)`

        5.  **Plan the Calculation:**
            *   Once you have filtered the data (or if no filtering is needed), determine which pandas operation performs the required calculation from Step 1.
            *   **Sum:** `.sum()` (e.g., `filtered_df['so_luong'].sum()`)
            *   **Count:** `.count()` (counts non-missing values) or `len()` (counts rows). `len(filtered_df)` is often simplest for row counts. Use `.nunique()` for counting unique values in a column.
            *   **Average:** `.mean()`
            *   **Median:** `.median()` for robust central tendency
            *   **Min/Max:** `.min()`, `.max()` for extreme values
            *   **Grouping:** For grouped calculations:
                ```python
                # Simple groupby with one aggregation
                grouped_df = filtered_df.groupby('category_column')['value_column'].sum().reset_index()

                # Multiple aggregations
                grouped_df = filtered_df.groupby('category_column').agg({
                    'value1': 'sum',
                    'value2': 'mean',
                    'count_column': 'count'
                }).reset_index()
                ```
            *   **Get Specific Values:** If the query just asks to display the filtered data, the filtered DataFrame itself might be the answer (or specific columns from it).
            *   **Rounding:** By default, round numeric results to 3 decimal places for readability.

        6.  **Write the Script:**
            *   Start with `import pandas as pd` and `import numpy as np` (even if numpy isn't directly used, it's good practice with pandas).
            *   Assume `df` is pre-loaded.
            *   Add `import unidecode` if needed for Vietnamese text processing.
            *   Implement the filtering logic identified in Step 3. Store the result in a new DataFrame (e.g., `filtered_df = df[...]`).
            *   Apply the calculation identified in Step 5 to the `filtered_df` and the relevant column(s). Store the result in a variable (e.g., `total_quantity = filtered_df['so_luong'].sum()`).
            *   Format results appropriately (e.g., for currency values: `f"{total_amount:,.2f}"`)
            *   Do not print the result because user does not have access to stdout.
            *   Use f-string to record clearly the result to the variable `result`. Include descriptive text from the query if possible (e.g., `result=f"Total quantity for [Product X]: {total_quantity:,}"`).
            *   For complex results, consider returning a small, well-formatted DataFrame.

        7.  **Keep it Simple:**
            *   Avoid complex multi-step chained operations if simpler steps achieve the same result.
            *   Use clear variable names.
            *   Add brief comments for clarity when needed.
            *   Focus on directly answering the query using basic pandas filtering and aggregation. Do not add extra analysis unless explicitly asked.
            *   Test your filtering logic against edge cases (empty results, all matching, etc.)
            *   Handle potential errors (division by zero, empty DataFrames, etc.)

        Follow these steps carefully to generate accurate and simple pandas scripts.
        """

FOLLOW_UP_QUESTION_PROMPT = (
"# Suggestion/Expansion/Follow-Up Requests \n"
        "You will receive a user query in natural language along with any prior assistant response or context. \n"
        "Your goal is to generate concise, targeted follow-up requests that relieve the user of cognitive loads. \n"
        "Your requests, when chosen, will be sent to the analyst to answer. So, ask good requests, in scope, in context as to be selected by the user. \n"
        "\n"
        "When constructing follow-up requests: \n"
        "1. Identify any areas for expansion based on the user's query. \n"
        "2. Take into account the context of the dataset and the intention of the user. \n"
        "3. Formulate **open-ended but focused** requests that guide the user to provide exactly the needed information. \n"
        "4. [IMPORTANT]Do not make requests that the dataset cannot fulfill; stay within the limitation of the provided data. \n"
        "5. The follow-up question must take the form of the user's question being directed to the analyst. "
        "Start the question with imperative terms such as but not limited to'Hãy tính..', 'Truy vấn..', 'Tìm..'\n"
        "\n"
        "Output must be valid JSON matching the Pydantic model `FollowUpRequestsResult`, e.g.: \n"
        "{ \n"
        '  "requests": ["<question 1>", "<question 2>", ...] \n'
        "} \n"
)

# src/api/routes/prompts.py

# Prompt to reformulate a user's query based on chat history
REFORMULATION_PROMPT = """
Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the context of the chat history.

Chat History:
{chat_history}

Follow-up Question: {query}

Standalone Question:
"""

# Prompt to classify the content type (PDF or EXCEL) based on an AI's response
CLASSIFY_FILE_TYPE_PROMPT = """
Analyze the following response and determine if it relates to data analysis (typically from a spreadsheet like Excel) or textual information (typically from a document like a PDF).

Response:
"{previous_response}"

Respond with only one word: "EXCEL" or "PDF".
"""

# Prompt to generate follow-up questions for PDF context
SUGGEST_PDF_QUESTIONS_PROMPT = """
Based on the AI's answer regarding a document named "{file_name}":

"{previous_response}"

And the relevant context from the document:

"{context}"

TASK: Propose exactly 3 follow-up questions that can be DIRECTLY and CLEARLY answered from the provided context.

GUIDELINES:
- Each question must be a complete sentence, 10-20 words long.
- Questions should encourage deeper understanding of the topic.
- Ensure the answer to each question is explicitly present in the context.

IMPORTANT: Only list the 3 questions, one per line. Do not add numbers, bullet points, or any other text.
"""

# Prompt to enrich a short or simple question
ENRICH_QUESTION_PROMPT = """
Original question: "{question}"

Enrich and detail this question to make it more insightful and academic, while ensuring it can still be answered by the following context. The new question should be a complete, natural-sounding sentence of 15-25 words.

Context:
{context}

New, enriched question:
"""

# Prompt to verify if questions can be answered from the context
VERIFY_QUESTIONS_PROMPT = """
For each question below, evaluate if its answer can be found DIRECTLY within the provided context.

Context:
{context}

Evaluation Method:
1. Read the question carefully.
2. Search the context for keywords and related information.
3. Determine if a specific passage in the context directly answers the question.
4. Respond with YES if the answer is directly present, or NO if it requires significant inference or is not present.

Format your response as: [YES/NO]: <The question>

Questions to verify:
1. {question_1}
2. {question_2}
3. {question_3}
"""

# Prompt to fix a question that cannot be answered from the context
FIX_QUESTION_PROMPT = """
Context:
{context}

Original question (cannot be answered from the context):
{question}

Create a new, detailed, and insightful question on a similar topic that CAN be answered directly from the provided context. The new question should be a complete sentence of 15-25 words.

Respond with ONLY the new question.
"""