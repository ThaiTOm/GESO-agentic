import pandas as pd

# URL of the sample CSV file
csv_url = "data/OPC_data/all_data.csv"

# Read only the first 10 rows of the CSV file
df_first_10 = pd.read_csv(csv_url, nrows=10)

# Print the first 10 rows
print(df_first_10.columns.tolist())