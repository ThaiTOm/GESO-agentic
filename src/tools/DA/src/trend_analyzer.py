import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')
import pymannkendall as mk


class TrendAnalyzer:
    def __init__(self, min_periods: int = 4, significance_level: float = 0.05):
        self.min_periods = min_periods
        self.significance_level = significance_level
    
    def remove_seasonality(self, time_series: pd.Series, 
                          method: str = 'additive',
                          period: Optional[int] = None) -> Tuple[pd.Series, Dict]:
        if len(time_series) < self.min_periods:
            return time_series, {'method': 'none', 'reason': 'insufficient_data'}
        
        if period is None:
            #period = 4 for quarter, 12 for monthly
            if hasattr(time_series.index, 'freq'):
                if 'Q' in str(time_series.index.freq):
                    period = 4
                elif 'M' in str(time_series.index.freq):
                    period = 12
                else:
                    period = min(4, len(time_series) // 2)
            else:
                period = min(4, len(time_series) // 2)
        
        # need at least 2 full periods for seasonal decomposition
        if len(time_series) < 2 * period:
            return self._simple_detrend(time_series)
        
        try:
            decomposition = seasonal_decompose(
                time_series, 
                model=method, 
                period=period,
                extrapolate_trend='freq'
            )
            deseasonalized = decomposition.trend.dropna()
            decomposition_info = {
                'method': f'seasonal_decompose_{method}',
                'period': period,
                'seasonal_strength': self._calculate_seasonal_strength(decomposition),
                'trend_strength': self._calculate_trend_strength(decomposition)
            }
            
            return deseasonalized, decomposition_info
            
        except Exception as e:
            print(f"seasonal decomposition failed: {str(e)}, falling back to simple detrending")
            return self._simple_detrend(time_series)
    
    def _simple_detrend(self, time_series: pd.Series) -> Tuple[pd.Series, Dict]:
        window = min(3, len(time_series) // 2)
        if window < 2:
            return time_series, {'method': 'none', 'reason': 'too_short'}
        
        # rolling mean
        smoothed = time_series.rolling(window=window, center=True).mean()
        smoothed = smoothed.fillna(method='bfill').fillna(method='ffill')
        
        return smoothed, {'method': 'rolling_mean', 'window': window}
    
    def _calculate_seasonal_strength(self, decomposition) -> float:
        try:
            seasonal_var = np.var(decomposition.seasonal.dropna())
            residual_var = np.var(decomposition.resid.dropna())
            return seasonal_var / (seasonal_var + residual_var) if (seasonal_var + residual_var) > 0 else 0
        except:
            return 0
    
    def _calculate_trend_strength(self, decomposition) -> float:
        try:
            trend_var = np.var(decomposition.trend.dropna())
            residual_var = np.var(decomposition.resid.dropna())
            return trend_var / (trend_var + residual_var) if (trend_var + residual_var) > 0 else 0
        except:
            return 0
    
    def detect_trend_direction(self, time_series: pd.Series) -> Dict:
        if len(time_series) < self.min_periods:
            return {
                'direction': 'insufficient_data',
                'confidence': 0,
                'rate_of_change': 0,
                'method': 'none'
            }
        
        # linear regression slope
        linear_result = self._linear_trend_analysis(time_series)
        
        # mann-kendall trend test
        mk_result = self._mann_kendall_test(time_series)
        
        # Method 3: First vs Last comparison
        comparison_result = self._first_last_comparison(time_series)
        
        # Combine results
        combined_result = self._combine_trend_methods(
            linear_result, mk_result, comparison_result, time_series
        )
        
        return combined_result
    
    def _linear_trend_analysis(self, time_series: pd.Series) -> Dict:
        X = np.arange(len(time_series)).reshape(-1, 1)
        y = time_series.values
        
        ##fit
        model = LinearRegression()
        model.fit(X, y)
        
        slope = model.coef_[0]
        intercept = model.intercept_
        
        y_pred = model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        n = len(time_series)
        if n > 2:
            # standard error of slope
            mse = ss_res / (n - 2)
            x_mean = np.mean(X)
            se_slope = np.sqrt(mse / np.sum((X.flatten() - x_mean) ** 2))
            t_stat = slope / se_slope if se_slope > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        else:
            p_value = 1.0
        
        if p_value <= self.significance_level:
            if slope > 0:
                direction = 'increasing'
            elif slope < 0:
                direction = 'decreasing'
            else:
                direction = 'stable'
        else:
            direction = 'stable'
        
        # rate of change
        mean_value = np.mean(time_series)
        rate_of_change = (slope / mean_value * 100) if mean_value != 0 else 0
        
        return {
            'direction': direction,
            'slope': slope,
            'r_squared': r_squared,
            'p_value': p_value,
            'rate_of_change': rate_of_change,
            'confidence': 1 - p_value,
            'method': 'linear_regression'
        }
    
    def _mann_kendall_test(self, time_series: pd.Series) -> Dict:
        print("====== to _mann_kendall_test:", time_series)
        try:
            result = mk.original_test(time_series.values)
            print("mk.original_test result: =========", result)
            if result.trend == 'increasing':
                direction = 'increasing'
            elif result.trend == 'decreasing':
                direction = 'decreasing'
            else:
                direction = 'stable'
            return {
                'direction': direction,
                'S': result.s,
                'Z': result.z,
                'p_value': result.p,
                'confidence': 1 - result.p,
                'method': 'mann_kendall',
                'tau': result.Tau,
                'slope': result.slope,
                'intercept': result.intercept
            }
        except Exception as e:
            print(f"[ERROR] Exception in _mann_kendall_test: {str(e)}")
            return {
                'direction': 'error',
                'S': None,
                'Z': None,
                'p_value': None,
                'confidence': 0,
                'method': 'mann_kendall',
                'tau': None,
                'slope': None,
                'intercept': None,
                'error': str(e)
            }
    
    def _first_last_comparison(self, time_series: pd.Series) -> Dict:
        n = len(time_series)
        split_size = max(1, n // 4)  # 25% of data for each end
        
        first_portion = time_series.iloc[:split_size].mean()
        last_portion = time_series.iloc[-split_size:].mean()
        
        # rate of change
        if first_portion != 0:
            change_ratio = (last_portion - first_portion) / abs(first_portion)
            rate_of_change = change_ratio * 100 / (n - 1)  # Per period
        else:
            rate_of_change = 0
        
        # threshold-based direction
        threshold = 0.05  # 5% change threshold
        if abs(change_ratio) > threshold:
            direction = 'increasing' if change_ratio > 0 else 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'direction': direction,
            'first_avg': first_portion,
            'last_avg': last_portion,
            'change_ratio': change_ratio,
            'rate_of_change': rate_of_change,
            'method': 'first_last_comparison'
        }
    
    def _combine_trend_methods(self, linear_result: Dict, mk_result: Dict, 
                              comparison_result: Dict, time_series: pd.Series) -> Dict:
        
        # weight the methods based on data characteristics
        n = len(time_series)
        
        # linear regression gets higher weight for longer series
        linear_weight = min(0.5, n / 20)
        mk_weight = 0.3
        comparison_weight = 0.2
        
        # normalize weights
        total_weight = linear_weight + mk_weight + comparison_weight
        linear_weight /= total_weight
        mk_weight /= total_weight
        comparison_weight /= total_weight
        
        # vote on direction
        directions = [linear_result['direction'], mk_result['direction'], comparison_result['direction']]
        weights = [linear_weight, mk_weight, comparison_weight]
        
        # count weighted votes
        direction_votes = {'increasing': 0, 'decreasing': 0, 'stable': 0}
        for direction, weight in zip(directions, weights):
            if direction in direction_votes:
                direction_votes[direction] += weight
        
        # final direction
        final_direction = max(direction_votes, key=direction_votes.get)
        final_confidence = direction_votes[final_direction]
        
        # weighted average rate of change
        rates = [
            linear_result.get('rate_of_change', 0),
            comparison_result.get('rate_of_change', 0)
        ]
        rate_weights = [linear_weight, comparison_weight]
        
        final_rate = sum(rate * weight for rate, weight in zip(rates, rate_weights)) / sum(rate_weights)
        
        return {
            'direction': final_direction,
            'confidence': final_confidence,
            'rate_of_change': final_rate,
            'rate_unit': 'percent_per_period',
            'methods_used': {
                'linear_regression': linear_result,
                'mann_kendall': mk_result,
                'first_last_comparison': comparison_result
            },
            'data_points': len(time_series),
            'analysis_period': f"{time_series.index[0]} to {time_series.index[-1]}"
        }
    
    def analyze_segment(self, time_series: pd.Series, segment_name: str) -> Dict:
        deseasonalized, decomposition_info = self.remove_seasonality(time_series)
        trend_info = self.detect_trend_direction(deseasonalized)
        basic_stats = self._calculate_basic_stats(time_series)
        
        return {
            'segment_name': segment_name,
            'basic_stats': basic_stats,
            'decomposition': decomposition_info,
            'trend_analysis': trend_info,
            'raw_data': time_series,
            'deseasonalized_data': deseasonalized
        }
    
    def _calculate_basic_stats(self, time_series: pd.Series) -> Dict:
        return {
            'mean': time_series.mean(),
            'std': time_series.std(),
            'min': time_series.min(),
            'max': time_series.max(),
            'count': len(time_series),
            'cv': time_series.std() / time_series.mean() if time_series.mean() != 0 else 0,
            'first_value': time_series.iloc[0],
            'last_value': time_series.iloc[-1],
            'total_change': time_series.iloc[-1] - time_series.iloc[0],
            'total_change_pct': ((time_series.iloc[-1] - time_series.iloc[0]) / time_series.iloc[0] * 100) if time_series.iloc[0] != 0 else 0
        }
    
    def analyze_multiple_segments(self, time_series_dict: Dict[str, pd.Series]) -> Dict[str, Dict]:
        results = {}
        
        for segment_name, time_series in time_series_dict.items():
            print(f"analyzing : {segment_name}")
            try:
                results[segment_name] = self.analyze_segment(time_series, segment_name)
            except Exception as e:
                print(f"damnn got error exception in analyze_multiple_segments :: {segment_name}: {str(e)}")
                results[segment_name] = {
                    'segment_name': segment_name,
                    'error': str(e),
                    'trend_analysis': {'direction': 'error', 'confidence': 0, 'rate_of_change': 0}
                }
        
        return results 