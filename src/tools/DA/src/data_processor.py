import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gc
from dateutil.parser import parse
import warnings
warnings.filterwarnings('ignore')


class DataProcessor:
    def __init__(self, data_dir: str = "/data/data_sample", chunk_size: int = 50000):
        self.data_dir = Path(data_dir)
        self.chunk_size = chunk_size
        self.date_columns = ['NgayGio', 'NgayTao', 'ngay', 'ngayhoadon']
        self.sales_columns = ['soluong', 'tongtien', 'dongia', 'tongtienThucdat']
        self.key_columns = [
            'loai', 'vung', 'khuvuc', 'sitecode', 'nhaphanphoi', 'ngayhoadon',
            'masp', 'tensanpham', 'soluong', 'tongtien', 'nhomsanpham'
        ]


        # read header from template_header.csv
        template_header_path = self.data_dir / 'template_header.csv'
        self.header = pd.read_csv(template_header_path, nrows=0).columns.tolist()
    
    def get_available_files(self) -> List[Path]:
        csv_files = list(self.data_dir.glob("quy_*.csv"))
        return sorted(csv_files)
    
    def parse_quarter_year(self, filename: str) -> Tuple[int, int]:

        parts = filename.split('_')
        quarter = int(parts[1])
        year = int(parts[2].split('.')[0])
        return quarter, year
    
    def process_date_column(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # convert to datetime
        if 'ngayhoadon' in df.columns:
            try:
                # handle various date formats
                df['date'] = pd.to_datetime(df['ngayhoadon'], format='%d/%m/%y', errors='coerce')
                # If that fails, try other formats
                if df['date'].isna().sum() > len(df) * 0.5:
                    df['date'] = pd.to_datetime(df['ngayhoadon'], infer_datetime_format=True, errors='coerce')
            except:
                df['date'] = pd.to_datetime(df['ngayhoadon'], errors='coerce')
        
        # Extract time componentsw
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['year_month'] = df['date'].dt.to_period('M')
        
        return df
    
    def clean_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        for col in self.sales_columns:
            if col in df.columns:
                # Convert to numeric, replacing non-numeric values with 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    
    def process_file_chunked(self, file_path: Path, 
                           aggregation_level: str = 'monthly') -> pd.DataFrame:
        
        print(f"Processing {file_path.name}...")
        aggregated_data = []
        total_rows = 0
        
        try:
            # Read file in chunks using the template header
            chunk_iter = pd.read_csv(
                file_path,
                chunksize=self.chunk_size,
                names=self.header,
                header=None,
                low_memory=False
            )
            
            for chunk_num, chunk in enumerate(chunk_iter):
                print(f"  Processing chunk {chunk_num + 1}... ({len(chunk)} rows)")
                
                # Clean and process chunk
                chunk = self.clean_numeric_columns(chunk)
                chunk = self.process_date_column(chunk)
                
                # Remove rows with invalid dates
                chunk = chunk.dropna(subset=['date'])
                
                if len(chunk) == 0:
                    continue
                
                # aggregate
                if aggregation_level == 'monthly':
                    group_cols = ['year', 'month', 'year_month', 'nhomsanpham', 'vung']
                else: 
                    group_cols = ['year', 'quarter', 'nhomsanpham', 'vung']
                
                # Only include columns that exist in the chunk
                existing_group_cols = [col for col in group_cols if col in chunk.columns]
                
                chunk_agg = chunk.groupby(existing_group_cols).agg({
                    'soluong': 'sum',
                    'tongtien': 'sum',
                    'tongtienThucdat': 'sum' if 'tongtienThucdat' in chunk.columns else lambda x: 0,
                    'masp': 'nunique'  # Number of unique products
                }).reset_index()
                
                chunk_agg.columns = existing_group_cols + ['total_quantity', 'total_revenue', 'total_actual_revenue', 'unique_products']
                
                aggregated_data.append(chunk_agg)
                total_rows += len(chunk)
                
                del chunk
                gc.collect()
        
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            return pd.DataFrame()
        
        if not aggregated_data:
            return pd.DataFrame()
        
        result = pd.concat(aggregated_data, ignore_index=True)
        
        # final aggregation
        group_cols = [col for col in result.columns if col not in ['total_quantity', 'total_revenue', 'total_actual_revenue', 'unique_products']]
        
        final_result = result.groupby(group_cols).agg({
            'total_quantity': 'sum',
            'total_revenue': 'sum',
            'total_actual_revenue': 'sum',
            'unique_products': 'sum'
        }).reset_index()
        
        print(f"  Completed. Processed {total_rows} rows -> {len(final_result)} aggregated records")
        
        return final_result
    
    def process_all_files(self, aggregation_level: str = 'monthly') -> pd.DataFrame:
        files = self.get_available_files()
        if not files:
            raise ValueError(f"No CSV files found in {self.data_dir}")
        
        print(f"Found {len(files)} files to process")
        
        all_data = []
        
        for file_path in files:
            try:
                # extract metadata from filename
                quarter, year = self.parse_quarter_year(file_path.name)
                
                # process file
                df = self.process_file_chunked(file_path, aggregation_level)
                
                if len(df) > 0:
                    # Add file metadata
                    df['source_file'] = file_path.name
                    df['file_quarter'] = quarter
                    df['file_year'] = year
                    
                    all_data.append(df)
                
            except Exception as e:
                print(f"Failed to process {file_path.name}: {str(e)}")
                continue
        
        if not all_data:
            raise ValueError("No data could be processed from any files")
        
        # combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # create a proper time index
        if aggregation_level == 'monthly' and 'year_month' in combined_data.columns:
            combined_data['time_period'] = combined_data['year_month']
        else:
            # create quarterly periods
            combined_data['time_period'] = combined_data.apply(
                lambda row: pd.Period(f"{int(row['year'])}Q{int(row['quarter']) if 'quarter' in combined_data.columns else int(row['file_quarter'])}", freq='Q'),
                axis=1
            )
        
        # Sort by time period
        combined_data = combined_data.sort_values('time_period').reset_index(drop=True)
        
        print(f"Combined dataset: {len(combined_data)} records covering {combined_data['time_period'].nunique()} time periods")
        
        return combined_data
    
    def get_time_series_by_segment(self, df: pd.DataFrame, 
                                 segment_column: str = 'nhomsanpham',
                                 value_column: str = 'total_revenue') -> Dict[str, pd.Series]:
        print(df.columns)
        if segment_column not in df.columns or value_column not in df.columns:
            raise ValueError(f"Required columns {segment_column} or {value_column} not found")
        
        time_series = {}
        
        for segment in df[segment_column].unique():
            if pd.isna(segment):
                continue
                
            segment_data = df[df[segment_column] == segment]
            ts = segment_data.groupby('time_period')[value_column].sum().sort_index()
            # need at least 4 periods for trend analysis
            if len(ts) >= 4:  
                time_series[str(segment)] = ts
        
        return time_series


class CustomPreAggregatedDataProcessor(DataProcessor):
    def __init__(self, data_dir: str = "/data/OPC_data", chunk_size: int = 50000):
        # Initialize paths and chunk size, but DO NOT load template_header.csv
        # super().__init__(data_dir, chunk_size)
        self.data_dir = Path(data_dir)
        self.chunk_size = chunk_size

        # Define the mapping from the new file's columns to the standard internal column names
        self.column_mapping = {
            'NGAYDONHANG': 'ngayhoadon',
            'GAMHANG': 'nhomsanpham',  # This is your segment_column
            'Totals - Sum of SOLUONG': 'total_quantity',
            'Totals - Sum of DOANHTHUSAUVAT': 'total_revenue',  # This is your value_column
            'Totals - Sum of DOANHTHUTRUOCVAT': 'total_revenue_pre_vat',
            'Totals - Sum of TIENVAT': 'total_vat',
            'Totals - Sum of DOANHSO': 'total_sales_figure',
            'MASANPHAM': 'masp',
            'TENSANPHAM': 'tensanpham',
            'NGANHHANG': 'nganhhang',
            'NHANHANG': 'nhanhang',
            'DONVI': 'donvi'
        }

        # Define which columns should be treated as numeric for cleaning
        self.sales_columns = [
            'Totals - Sum of DOANHTHUTRUOCVAT',
            'Totals - Sum of TIENVAT',
            'Totals - Sum of DOANHTHUSAUVAT',
            'Totals - Sum of SOLUONG',
            'Totals - Sum of DOANHSO'
        ]

    def get_available_files(self) -> List[Path]:
        """Finds a single CSV file in the directory, excluding common template files."""
        all_csv_files = list(self.data_dir.glob("*.csv"))
        csv_files = [f for f in all_csv_files]
        if not csv_files:
            return []
        return [csv_files[0]]

    def parse_quarter_year(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Overrides parent method; not needed as date info is in the data."""
        return None, None

    def process_file_chunked(self, file_path: Path,
                             aggregation_level: str = 'monthly') -> pd.DataFrame:
        """
        Processes a pre-aggregated file by cleaning, renaming, and adding date features
        without performing any new aggregations.
        """
        print(f"Processing pre-aggregated file {file_path.name}...")
        processed_chunks = []
        total_rows = 0

        try:
            # Read the file with its own header
            chunk_iter = pd.read_csv(
                file_path,
                chunksize=self.chunk_size,
                header=0,  # Use the first row as the header
                low_memory=False
            )

            for chunk_num, chunk in enumerate(chunk_iter):
                print(f"  Processing chunk {chunk_num + 1}... ({len(chunk)} rows)")

                # Clean numeric columns before renaming
                chunk = self.clean_numeric_columns(chunk)

                # Rename columns to standard format
                chunk = chunk.rename(columns=self.column_mapping)

                # Process date column after renaming
                chunk = self.process_date_column(chunk)

                # Remove rows where date could not be parsed
                chunk = chunk.dropna(subset=['date'])

                if chunk.empty:
                    continue

                # --- NO AGGREGATION IS PERFORMED ---

                processed_chunks.append(chunk)
                total_rows += len(chunk)

                del chunk
                gc.collect()

        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            return pd.DataFrame()

        if not processed_chunks:
            return pd.DataFrame()

        final_result = pd.concat(processed_chunks, ignore_index=True)
        print(f"  Completed. Processed {total_rows} rows from pre-aggregated file.")
        return final_result

    def process_all_files(self, aggregation_level: str = 'monthly') -> pd.DataFrame:
        """Orchestrates the processing of the single pre-aggregated file."""
        files = self.get_available_files()
        if not files:
            raise ValueError(f"No data CSV file found in {self.data_dir}")

        file_path = files[0]
        print(f"Found file to process: {file_path.name}")

        try:
            combined_data = self.process_file_chunked(file_path, aggregation_level)
        except Exception as e:
            raise RuntimeError(f"Failed to process {file_path.name}: {str(e)}")

        if combined_data.empty:
            raise ValueError("No data could be processed from the file")

        # Create the 'time_period' index for time series analysis
        if aggregation_level == 'monthly' and 'year_month' in combined_data.columns:
            combined_data['time_period'] = combined_data['year_month']
        else:
            combined_data['time_period'] = combined_data.apply(
                lambda row: pd.Period(f"{int(row['year'])}Q{int(row['quarter'])}", freq='Q'),
                axis=1
            )

        combined_data = combined_data.sort_values('time_period').reset_index(drop=True)

        print(
            f"Final dataset: {len(combined_data)} records covering {combined_data['time_period'].nunique()} time periods")

        return combined_data