# Xử lý bài toán

1. đọc và gộp dữ liệu theo chunk
2. làm sạch lại dữ liệu (Date, None...)
3. aggregate data theo tháng/quý, và theo segment ví dụ đang làm trường "nhomsanpham"
4. Tổng hợp doanh thu cho từng phân khúc (tháng/quý)
5. deseasonalized sử dụng statsmodels
6. phân tích xu hướng sử dụng : 
    Linear Regression: xác định độ dốc (slope) của chuỗi thời gian.
    Mann-Kendall Test: phát hiện xu hướng tăng/giảm.
    So sánh đầu-cuối: So sánh giá trị đầu và cuối, xác định thay đổi tổng thể.
7. tổng hợp và đánh giá

Ngoài ra tại cuối cùng, có propose cách kết hợp các phương pháp để tăng độ tin cậy :
    Linear regression: trọng số cao hơn nếu chuỗi dài.
    Mann-Kendall: trọng số cố định.
    So sánh đầu-cuối: trọng số nhỏ nhất.

8. visualize dữ liệu và các thông số statistic


# HOW TO RUN

unzip all data into folder data/data_sample/
data with format quy_*.csv

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

#run main app
streamlit run streamlit_app.py
```