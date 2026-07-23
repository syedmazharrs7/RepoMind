"""
Reusable statistical utility for analyzing metrics distribution.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


def _interpolate_percentile(sorted_values: Tuple[float, ...], percentile: float) -> float:
    """
    Calculate the percentile value using linear interpolation.

    Args:
        sorted_values: Sorted tuple of float values.
        percentile: Target percentile between 0.0 and 1.0.

    Returns:
        float: Interpolated percentile value.
    """
    if not sorted_values:
        return 0.0
    idx = (len(sorted_values) - 1) * percentile
    low = int(idx)
    high = min(low + 1, len(sorted_values) - 1)
    weight = idx - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


@dataclass(frozen=True)
class MetricStatistics:
    """
    Immutable representation of statistics for a metric values collection.
    Provides mathematical summaries without external dependencies (e.g. numpy).
    """
    values: Tuple[float, ...]
    count: int
    sum: float
    mean: float
    median_value: float
    min: float
    max: float
    p25: float
    p75: float
    p90: float
    p95: float
    p99: float
    histogram_bins: Tuple[float, ...]
    histogram_counts: Tuple[int, ...]

    @classmethod
    def from_values(cls, raw_values: Sequence[float], bin_count: int = 10) -> "MetricStatistics":
        """
        Build MetricStatistics from a sequence of raw numeric values.

        Args:
            raw_values: Sequence of numeric values to analyze.
            bin_count: Number of bins for histogram calculation.

        Returns:
            MetricStatistics instance.
        """
        clean_vals = tuple(float(x) for x in raw_values)
        sorted_vals = tuple(sorted(clean_vals))

        count = len(clean_vals)
        if count == 0:
            return cls(
                values=(),
                count=0,
                sum=0.0,
                mean=0.0,
                median_value=0.0,
                min=0.0,
                max=0.0,
                p25=0.0,
                p75=0.0,
                p90=0.0,
                p95=0.0,
                p99=0.0,
                histogram_bins=(),
                histogram_counts=(),
            )

        val_sum = sum(clean_vals)
        mean = val_sum / count
        v_min = sorted_vals[0]
        v_max = sorted_vals[-1]

        median = _interpolate_percentile(sorted_vals, 0.5)
        p25 = _interpolate_percentile(sorted_vals, 0.25)
        p75 = _interpolate_percentile(sorted_vals, 0.75)
        p90 = _interpolate_percentile(sorted_vals, 0.90)
        p95 = _interpolate_percentile(sorted_vals, 0.95)
        p99 = _interpolate_percentile(sorted_vals, 0.99)

        # Histogram calculation
        if v_min == v_max:
            histogram_bins = (v_min, v_min + 1.0)
            histogram_counts = (count,)
        else:
            step = (v_max - v_min) / bin_count
            histogram_bins = tuple(v_min + step * i for i in range(bin_count + 1))
            counts = [0] * bin_count
            for val in clean_vals:
                bin_idx = int((val - v_min) / step)
                if bin_idx >= bin_count:
                    bin_idx = bin_count - 1
                counts[bin_idx] += 1
            histogram_counts = tuple(counts)

        return cls(
            values=sorted_vals,
            count=count,
            sum=val_sum,
            mean=mean,
            median_value=median,
            min=v_min,
            max=v_max,
            p25=p25,
            p75=p75,
            p90=p90,
            p95=p95,
            p99=p99,
            histogram_bins=histogram_bins,
            histogram_counts=histogram_counts,
        )

    def summary(self) -> Dict[str, Any]:
        """Get a summary dictionary of basic metrics."""
        return {
            "count": self.count,
            "sum": self.sum,
            "mean": self.mean,
            "median": self.median_value,
            "min": self.min,
            "max": self.max,
        }

    def largest(self) -> float:
        """Get the maximum value."""
        return self.max

    def smallest(self) -> float:
        """Get the minimum value."""
        return self.min

    def average(self) -> float:
        """Get the mean value."""
        return self.mean

    def median(self) -> float:
        """Get the median value."""
        return self.median_value

    def percentiles(self, p: Optional[float] = None) -> Union[Dict[str, float], float]:
        """
        Get percentile values.
        If p is None, returns a dictionary of precalculated percentiles (25, 50, 75, 90, 95, 99).
        If p is provided (as a float in range [0, 100]), returns that specific percentile.
        """
        if p is None:
            return {
                "25": self.p25,
                "50": self.median_value,
                "75": self.p75,
                "90": self.p90,
                "95": self.p95,
                "99": self.p99,
            }
        
        # Guard rails for p
        if not (0.0 <= p <= 100.0):
            raise ValueError("Percentile p must be between 0.0 and 100.0 inclusive.")
        return _interpolate_percentile(self.values, p / 100.0)

    def distribution(self) -> List[float]:
        """Get the sorted list of all values."""
        return list(self.values)

    def histograms(self) -> Dict[str, Tuple]:
        """Get histogram bins and counts (data only)."""
        return {
            "bins": self.histogram_bins,
            "counts": self.histogram_counts,
        }
