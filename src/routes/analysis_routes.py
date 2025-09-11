import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fastapi import APIRouter, HTTPException, Query
import json
from tools.DA.src.data_processor import CustomPreAggregatedDataProcessor
from tools.DA.src.trend_analyzer import TrendAnalyzer
from config import settings  # Import your settings

# Initialize the router
router = APIRouter()


def load_and_process_data(aggregation_level: str, chunk_size: int):
    """
    Loads and processes the data using DataProcessor.
    """
    try:
        processor = CustomPreAggregatedDataProcessor(chunk_size=chunk_size, data_dir="tools/DA/data/OPC_data")
        processed_data = processor.process_all_files(aggregation_level=aggregation_level)
        time_series_data = processor.get_time_series_by_segment(
            processed_data,
            segment_column='nhomsanpham',
            value_column="total_revenue"
        )
        return processed_data, time_series_data
    except Exception as e:
        # Log the error for debugging
        print(f"Error during data processing: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")


def analyze_trends(time_series_data):
    """
    Analyzes trends in the time series data.
    """
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.analyze_multiple_segments(time_series_data)
        return results
    except Exception as e:
        print(f"Error during trend analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing trends: {str(e)}")


def create_detailed_segment_chart_json(segment_name, analysis_result):
    """
    Creates a detailed chart for a segment and returns it as a JSON-serializable dictionary.
    """
    if 'error' in analysis_result:
        return None

    raw_data = analysis_result['raw_data']
    deseasonalized_data = analysis_result['deseasonalized_data']
    trend_info = analysis_result['trend_analysis']

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f"{segment_name} - Raw vs Deseasonalized Data",
            "Trend Components"
        ),
        vertical_spacing=0.15
    )

    # Add traces for raw data, deseasonalized data, and trend line
    fig.add_trace(go.Scatter(x=raw_data.index.astype(str), y=raw_data.values, mode='lines+markers', name='Raw Data'),
                  row=1, col=1)

    if not deseasonalized_data.empty:
        fig.add_trace(go.Scatter(x=deseasonalized_data.index.astype(str), y=deseasonalized_data.values, mode='lines',
                                 name='Deseasonalized (Trend)'), row=1, col=1)
        if len(deseasonalized_data) >= 2:
            x_numeric = np.arange(len(deseasonalized_data))
            z = np.polyfit(x_numeric, deseasonalized_data.values, 1)
            p = np.poly1d(z)
            fig.add_trace(
                go.Scatter(x=deseasonalized_data.index.astype(str), y=p(x_numeric), mode='lines', name='Trend Line',
                           line=dict(dash='dash')), row=1, col=1)

    # Add bar chart for rate of change
    if 'methods_used' in trend_info and trend_info['methods_used']:
        methods = trend_info['methods_used']
        method_names = list(methods.keys())
        rates = [m.get('rate_of_change', 0) for m in methods.values()]
        fig.add_trace(
            go.Bar(x=method_names, y=rates, name='Rate of Change by Method', text=[f"{r:.2f}%" for r in rates],
                   textposition='auto'), row=2, col=1)
        fig.update_yaxes(title_text="Rate of Change (%)", row=2, col=1)

    fig.update_layout(height=700, title_text=f"Detailed Analysis: {segment_name}",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Revenue", row=1, col=1)

    return json.loads(fig.to_json())


def format_text_results_to_markdown(analysis_results):
    """
    Formats the textual analysis results into a single markdown string for the LLM.
    """
    markdown_output = "# Business Performance Trend Analysis Summary\n\n"
    for segment, result in analysis_results.items():
        if 'error' in result:
            markdown_output += f"## Segment: {segment}\n\nCould not be analyzed. Error: {result['error']}\n\n---\n\n"
            continue

        trend_info = result['trend_analysis']
        basic_stats = result['basic_stats']

        markdown_output += f"## Segment: {segment}\n\n"
        markdown_output += f"- **Overall Trend Direction**: {trend_info['direction'].capitalize()}\n"
        markdown_output += f"- **Average Rate of Change**: {trend_info['rate_of_change']:.2f}% per period\n"
        markdown_output += f"- **Confidence in Trend**: {trend_info['confidence']:.1%}\n\n"
        markdown_output += "### Key Statistics\n"
        markdown_output += f"- **Mean Revenue**: {basic_stats['mean']:,.0f}\n"
        markdown_output += f"- **Total Change Over Period**: {basic_stats['total_change_pct']:.2f}%\n"
        markdown_output += f"- **Data Points Analyzed**: {trend_info['data_points']}\n\n---\n\n"
    return markdown_output

_, time_series_data = load_and_process_data("monthly", settings.DA_CHUNK_SIZE)

@router.get("/analysis", summary="Perform Trend Analysis on Business Data")
def get_analysis(aggregation_level: str = Query("quarterly", enum=["monthly", "quarterly"]), query: str = ""):
    """
    Processes sales data, performs a time-series trend analysis, and returns the results.

    - **Text results** are combined into a single markdown string, suitable for feeding to an LLM.
    - **Plot data** is returned as JSON objects, ready to be rendered by a client-side library like Plotly.js.
    """
    analysis_results = analyze_trends(time_series_data)

    if not analysis_results:
        raise HTTPException(status_code=404, detail="Analysis produced no results.")

    # Generate the markdown summary for the LLM
    text_summary_for_llm = format_text_results_to_markdown(analysis_results)

    # Generate the plot JSON for the client
    plots_for_client = {
        segment: create_detailed_segment_chart_json(segment, result)
        for segment, result in analysis_results.items()
        if 'error' not in result
    }

    return {
        "text_summary_for_llm": text_summary_for_llm,
        "plots_for_client": plots_for_client
    }