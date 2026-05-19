"""
F5: predict the future popularity trend of a target video.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict, Union

try:
    from .utils import DEFAULT_DATA_DIR, load_videos_by_id
except ImportError:
    from utils import DEFAULT_DATA_DIR, load_videos_by_id


class HeatSeriesItem(TypedDict):
    date: str
    heat: float


class FutureSeriesItem(TypedDict):
    date: str
    predicted_heat: float


def build_video_daily_heat(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[Dict[int, Dict[date, float]], date, date]:
    file_path = Path(data_dir) / "watch_logs.csv"
    video_daily_heat: Dict[int, Dict[date, float]] = defaultdict(
        lambda: defaultdict(float)
    ) 
    min_day = None  # type: Optional[date]
    max_day = None  # type: Optional[date]

    with file_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            video_id = int(row["video_id"])
            finish_rate = float(row["finish_rate"])
            liked = int(row["liked"])
            commented = int(row["commented"])
            shared = int(row["shared"])
            watch_day = datetime.fromisoformat(row["watch_time"]).date() #只取日期部分，不要时间部分

            heat_score = 1.0 + finish_rate + liked * 0.8 + commented * 0.6 + shared * 1.0
            video_daily_heat[video_id][watch_day] += heat_score

            if min_day is None or watch_day < min_day:
                min_day = watch_day
            if max_day is None or watch_day > max_day:
                max_day = watch_day

    if min_day is None or max_day is None:
        raise ValueError("No watch logs available for popularity prediction.")

    return video_daily_heat, min_day, max_day


def fill_series( #补齐所需预测热度期间热度
    daily_values: Dict[date, float],
    start_day: date,
    end_day: date,
) -> List[HeatSeriesItem]:
    series: List[HeatSeriesItem] = []
    current_day = start_day

    while current_day <= end_day:
        series.append(
            {
                "date": current_day.isoformat(),
                "heat": round(daily_values.get(current_day, 0.0), 4),
            }
        )
        current_day += timedelta(days=1)

    return series


def moving_average(values: List[float], window_size: int) -> float:
    if not values:
        return 0.0
    window = values[-window_size:]
    return sum(window) / len(window)


def calculate_trend_slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    first_half = values[: len(values) // 2]
    second_half = values[len(values) // 2 :]
    if not first_half or not second_half:
        return 0.0
    return (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half))


def predict_future_heat(
    recent_values: List[float],
    days_ahead: int,
) -> List[float]:
    if not recent_values:
        return [0.0] * days_ahead

    base_heat = moving_average(recent_values, min(7, len(recent_values))) #这里有问题
    trend_slope = calculate_trend_slope(recent_values[-min(14, len(recent_values)) :]) #这里也有问题
    trend_adjustment = trend_slope * 0.35

    predicted: List[float] = []
    current_base = base_heat
    for _ in range(days_ahead):
        current_base = max(0.0, current_base + trend_adjustment)
        predicted.append(round(current_base, 4))

    return predicted


def describe_trend(history_values: List[float], future_values: List[float]) -> str:
    history_avg = moving_average(history_values, min(7, len(history_values)))
    future_avg = moving_average(future_values, len(future_values))
    delta = future_avg - history_avg
    baseline = max(history_avg, 0.1)
    relative_change = delta / baseline

    if delta > 0.3 or relative_change > 0.25:
        return "rising"
    if delta < -0.3 or relative_change < -0.25:
        return "falling"
    return "stable"


def predict_video_popularity(
    video_id: int,
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
    history_days: int = 30,
    predict_days: int = 7,
) -> Dict[str, object]:
    videos = load_videos_by_id(data_dir)
    if video_id not in videos:
        raise ValueError(f"Video {video_id} does not exist.")

    video_daily_heat, min_day, max_day = build_video_daily_heat(data_dir)
    daily_heat = video_daily_heat.get(video_id) #找到对应视频的日热度字典
    if not daily_heat:
        raise ValueError(f"Video {video_id} has no watch history.")

    full_series = fill_series(daily_heat, min_day, max_day)
    recent_series = full_series[-history_days:]
    recent_values = [float(item["heat"]) for item in recent_series]
    predicted_values = predict_future_heat(recent_values, predict_days)
    trend = describe_trend(recent_values, predicted_values)

    future_start = max_day + timedelta(days=1)
    future_series: List[FutureSeriesItem] = []
    for index, heat in enumerate(predicted_values):
        future_day = future_start + timedelta(days=index)
        future_series.append(
            {
                "date": future_day.isoformat(),
                "predicted_heat": heat,
            }
        )

    return {
        "video_id": video_id,
        "title": videos[video_id]["title"],
        "category": videos[video_id]["category"],
        "history_days": len(recent_series),
        "predict_days": predict_days,
        "trend": trend,
        "recent_average_heat": round(moving_average(recent_values, min(7, len(recent_values))), 4),
        "predicted_average_heat": round(moving_average(predicted_values, len(predicted_values)), 4),
        "history_series": recent_series,
        "future_series": future_series,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict future popularity trend for a target video."
    )
    parser.add_argument("video_id", type=int, help="Target video id")
    parser.add_argument("--history-days", type=int, default=30)
    parser.add_argument("--predict-days", type=int, default=7)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = predict_video_popularity(
        video_id=args.video_id,
        data_dir=args.data_dir,
        history_days=args.history_days,
        predict_days=args.predict_days,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
