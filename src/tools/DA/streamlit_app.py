import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data_processor import SingleFileDataProcessor
from src.trend_analyzer import TrendAnalyzer

CHUNK_SIZE = 5000000

#sectuin state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'time_series_data' not in st.session_state:
    st.session_state.time_series_data = None

def load_and_process_data(aggregation_level, chunk_size):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing data processor...")
        processor = SingleFileDataProcessor(chunk_size=chunk_size)
        progress_bar.progress(10)
        
        status_text.text("Processing CSV files...")
        processed_data = processor.process_all_files(aggregation_level=aggregation_level)
        print ("processed_data", processed_data)
        progress_bar.progress(70)
        
        # extract time series by segment
        status_text.text("Extracting time series data...")
        time_series_data = processor.get_time_series_by_segment(
            processed_data, 
            segment_column='nhomsanpham',
            value_column='total_revenue'
        )
        progress_bar.progress(90)
        
        status_text.text("Data processing completed!")
        progress_bar.progress(100)
        
        return processed_data, time_series_data
        
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return None, None
    finally:
        status_text.empty()
        progress_bar.empty()

def analyze_trends(time_series_data):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing trend analyzer...")
        analyzer = TrendAnalyzer()
        progress_bar.progress(20)
        
        status_text.text("Analyzing trends for all segments...")
        results = analyzer.analyze_multiple_segments(time_series_data)
        progress_bar.progress(100)
        
        status_text.text("Trend analysis completed!")
        return results
        
    except Exception as e:
        st.error(f"Error analyzing trends: {str(e)}")
        return None
    finally:
        status_text.empty()
        progress_bar.empty()

def create_detailed_segment_chart(segment_name, analysis_result):
    if 'error' in analysis_result:
        st.error(f"Error in analysis: {analysis_result['error']}")
        return None
    
    raw_data = analysis_result['raw_data']
    deseasonalized_data = analysis_result['deseasonalized_data']
    trend_info = analysis_result['trend_analysis']
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            f"{segment_name} - Raw vs Deseasonalized Data",
            "Trend Components"
        ],
        vertical_spacing=0.12,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Raw data
    fig.add_trace(
        go.Scatter(
            x=raw_data.index.astype(str),
            y=raw_data.values,
            mode='lines+markers',
            name='Raw Data',
            line=dict(color='lightblue', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    # Deseasonalized data
    if len(deseasonalized_data) > 0:
        fig.add_trace(
            go.Scatter(
                x=deseasonalized_data.index.astype(str),
                y=deseasonalized_data.values,
                mode='lines+markers',
                name='Deseasonalized (Trend)',
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        
        # Add trend line
        if len(deseasonalized_data) >= 2:
            x_numeric = np.arange(len(deseasonalized_data))
            z = np.polyfit(x_numeric, deseasonalized_data.values, 1)
            trend_line = np.poly1d(z)(x_numeric)
            
            fig.add_trace(
                go.Scatter(
                    x=deseasonalized_data.index.astype(str),
                    y=trend_line,
                    mode='lines',
                    name=f'Trend Line ({trend_info["direction"]})',
                    line=dict(
                        color='green' if trend_info['direction'] == 'increasing' 
                        else 'red' if trend_info['direction'] == 'decreasing' 
                        else 'gray',
                        width=2,
                        dash='dash'
                    )
                ),
                row=1, col=1
            )
    
    # Rate of change visualization
    if 'methods_used' in trend_info:
        methods = trend_info['methods_used']
        filtered_methods = {name: m for name, m in methods.items() if m.get('rate_of_change') not in [None, 0]}
        method_names = list(filtered_methods.keys())
        rates = [filtered_methods[method].get('rate_of_change', 0) for method in method_names]
        confidences = [filtered_methods[method].get('confidence', 0) for method in method_names]
        
        if method_names:  # Only plot if there are valid methods
            fig.add_trace(
                go.Bar(
                    x=method_names,
                    y=rates,
                    name='Rate of Change by Method',
                    marker_color='lightcoral',
                    text=[f"{rate:.2f}%" for rate in rates],
                    textposition='auto'
                ),
                row=2, col=1
            )
    
    fig.update_layout(
        height=700,
        showlegend=True,
        title_text=f"Detailed Analysis: {segment_name}"
    )
    
    fig.update_xaxes(title_text="Time Period", row=1, col=1)
    fig.update_yaxes(title_text="Revenue", row=1, col=1)
    fig.update_xaxes(title_text="Analysis Method", row=2, col=1)
    fig.update_yaxes(title_text="Rate of Change (%)", row=2, col=1)
    
    return fig

def main():
    st.markdown('**Business Performance Trend Analysis**')
    
    st.sidebar.header("config")
    
    st.sidebar.subheader("Data Processing")
    aggregation_level = st.sidebar.selectbox(
        "Aggregation Level",
        ["monthly", "quarterly"],
        index=1,
        help="Choose the time granularity for analysis"
    )
    
    #load data
    if st.sidebar.button("Load & Process Data", type="primary"):
        with st.spinner("Processing data..."):
            processed_data, time_series_data = load_and_process_data(aggregation_level, CHUNK_SIZE)
            
            if processed_data is not None and time_series_data is not None:
                st.session_state.processed_data = processed_data
                st.session_state.time_series_data = time_series_data
                st.session_state.analysis_results = None
                st.success("Data loaded successfully!")
                st.rerun()
    
    # show data summary
    if st.session_state.processed_data is not None:
        data_info = st.sidebar.expander("Data Information")
        with data_info:
            st.write(f"**Records:** {len(st.session_state.processed_data):,}")
            st.write(f"**Time Periods:** {st.session_state.processed_data['time_period'].nunique()}")
            st.write(f"**Segments:** {len(st.session_state.time_series_data)}")
            st.write(f"**Date Range:** {st.session_state.processed_data['time_period'].min()} to {st.session_state.processed_data['time_period'].max()}")
    
    if st.session_state.time_series_data is not None:
        if st.sidebar.button("Analyze Trends", type="secondary"):
            with st.spinner("Analyzing trends..."):
                analysis_results = analyze_trends(st.session_state.time_series_data)
                if analysis_results is not None:
                    st.session_state.analysis_results = analysis_results
                    st.success("Trend analysis completed!")
                    st.rerun()
    
    #main section
    if st.session_state.analysis_results is not None:
        st.header("Detailed Segment Analysis")
        
        available_segments = [name for name, result in st.session_state.analysis_results.items() 
                            if 'error' not in result]
        
        if available_segments:
            selected_segment = st.selectbox(
                "Select a segment for detailed analysis:",
                available_segments,
                key="segment_selector"
            )
            
            if selected_segment:
                analysis_result = st.session_state.analysis_results[selected_segment]
                
                col1, col2, col3 = st.columns(3)
                
                trend_info = analysis_result['trend_analysis']
                basic_stats = analysis_result['basic_stats']
                
                with col1:
                    direction = trend_info['direction']
                    direction_class = f"trend-{direction}"
                    st.markdown(f'<div class="metric-card"><h4>Trend Direction</h4><p class="{direction_class}">{direction.upper()}</p></div>', 
                              unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f'''<div class="metric-card">
                        <h4>Rate of Change</h4>
                        <p><strong>{trend_info["rate_of_change"]:.2f}%</strong> per period</p>
                    </div>''', unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f'''<div class="metric-card">
                        <h4>Confidence</h4>
                        <p><strong>{trend_info["confidence"]:.1%}</strong></p>
                    </div>''', unsafe_allow_html=True)
                
                # Detailed chart
                detailed_chart = create_detailed_segment_chart(selected_segment, analysis_result)
                if detailed_chart:
                    st.plotly_chart(detailed_chart, use_container_width=True)
                
                # Additional statistics
                with st.expander("Statistical Details"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Basic Statistics")
                        st.write(f"**Mean Revenue:** {basic_stats['mean']:,.0f}")
                        st.write(f"**Standard Deviation:** {basic_stats['std']:,.0f}")
                        st.write(f"**Coefficient of Variation:** {basic_stats['cv']:.3f}")
                        st.write(f"**Total Change:** {basic_stats['total_change_pct']:.2f}%")
                    
                    with col2:
                        st.subheader("Method Comparison")
                        if 'methods_used' in trend_info:
                            methods = trend_info['methods_used']
                            for method_name, method_result in methods.items():
                                st.write(f"**{method_name}:**")
                                st.write(f"  - Direction: {method_result.get('direction', 'N/A')}")
                                st.write(f"  - Rate: {method_result.get('rate_of_change', 0):.2f}%")
                                if 'confidence' in method_result:
                                    st.write(f"  - Confidence: {method_result['confidence']:.3f}")
        
        # Data table section
        with st.expander("Full Results Table"):
            summary_data = []
            for segment, results in st.session_state.analysis_results.items():
                if 'error' not in results:
                    trend_info = results['trend_analysis']
                    basic_stats = results['basic_stats']
                    
                    summary_data.append({
                        'Segment': segment,
                        'Trend Direction': trend_info['direction'],
                        'Rate of Change (%)': f"{trend_info['rate_of_change']:.2f}",
                        'Confidence': f"{trend_info['confidence']:.1%}",
                        'Mean Revenue': f"{basic_stats['mean']:,.0f}",
                        'Total Change (%)': f"{basic_stats['total_change_pct']:.2f}",
                        'Data Points': trend_info['data_points']
                    })
            
            if summary_data:
                df_summary = pd.DataFrame(summary_data)
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
if __name__ == "__main__":
    main() 