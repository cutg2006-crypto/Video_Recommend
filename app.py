from __future__ import annotations

import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from modules.hot_predictor import predict_video_popularity
from modules.recommender import recommend_videos
from modules.similarity import SimilarUserResult, find_similar_users
from modules.user_cluster import cluster_users
from modules.utils import DEFAULT_DATA_DIR, load_user_profiles, load_videos_by_id
from modules.video_cluster import cluster_videos


app = Flask(__name__)
DATA_DIR = Path(DEFAULT_DATA_DIR)


def parse_positive_int(name: str, default: int, minimum: int = 1, maximum: int = 100) -> int:
    raw_value = request.args.get(name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer.") from exc

    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def count_csv_rows(file_path: Path) -> int:
    with file_path.open("r", encoding="utf-8") as file:
        return max(sum(1 for _ in file) - 1, 0)


@lru_cache(maxsize=1)
def get_dataset_summary() -> Dict[str, Any]:
    videos = load_videos_by_id(DATA_DIR)
    users = load_user_profiles(DATA_DIR)

    return {
        "video_count": len(videos),
        "user_count": len(users),
        "watch_log_count": count_csv_rows(DATA_DIR / "watch_logs.csv"),
        "sample_videos": build_random_video_samples(videos),
        "sample_users": build_random_user_samples(users),
    }


def build_random_video_samples(
    videos: Dict[int, Dict[str, str]],
    sample_size: int = 8,
) -> List[Dict[str, Any]]:
    sample_ids = random.sample(list(videos), min(sample_size, len(videos)))
    return [
        {
            "video_id": video_id,
            "title": videos[video_id]["title"],
            "category": videos[video_id]["category"],
            "tags": videos[video_id]["tags"].split(";"),
        }
        for video_id in sample_ids
    ]


def build_random_user_samples(
    users: Dict[int, Dict[str, str]],
    sample_size: int = 8,
) -> List[Dict[str, Any]]:
    sample_ids = random.sample(list(users), min(sample_size, len(users)))
    return [
        {
            "user_id": user_id,
            "interest_categories": users[user_id]["interest_categories"].split(";"),
            "active_level": users[user_id]["active_level"],
        }
        for user_id in sample_ids
    ]


@lru_cache(maxsize=32)
def cached_similar_users(user_id: int, top_n: int) -> List[SimilarUserResult]:
    return find_similar_users(target_user_id=user_id, top_n=top_n, data_dir=DATA_DIR)


@lru_cache(maxsize=32)
def cached_recommendations(user_id: int, top_n: int, similar_users: int) -> List[Dict[str, Any]]:
    return recommend_videos(
        target_user_id=user_id,
        top_n=top_n,
        similar_user_count=similar_users,
        data_dir=DATA_DIR,
    )


@lru_cache(maxsize=32)
def cached_video_trend(video_id: int, history_days: int, predict_days: int) -> Dict[str, Any]:
    return predict_video_popularity(
        video_id=video_id,
        data_dir=DATA_DIR,
        history_days=history_days,
        predict_days=predict_days,
    )


@lru_cache(maxsize=8)
def cached_video_clusters(cluster_count: int, sample_per_cluster: int) -> List[Dict[str, Any]]:
    return cluster_videos(
        cluster_count=cluster_count,
        sample_per_cluster=sample_per_cluster,
        data_dir=DATA_DIR,
    )


@lru_cache(maxsize=8)
def cached_user_clusters(cluster_count: int, sample_per_cluster: int) -> List[Dict[str, Any]]:
    return cluster_users(
        cluster_count=cluster_count,
        sample_per_cluster=sample_per_cluster,
        data_dir=DATA_DIR,
    )


@app.route("/")
def index() -> str:
    return render_template("index.html", summary=get_dataset_summary())


@app.get("/api/summary")
def api_summary() -> Any:
    return jsonify(get_dataset_summary())


@app.get("/api/sample-videos")
def api_sample_videos() -> Any:
    videos = load_videos_by_id(DATA_DIR)
    return jsonify(build_random_video_samples(videos))


@app.get("/api/sample-users")
def api_sample_users() -> Any:
    users = load_user_profiles(DATA_DIR)
    return jsonify(build_random_user_samples(users))


@app.get("/api/similar-users")
def api_similar_users() -> Any:
    try:
        user_id = parse_positive_int("user_id", default=1, maximum=1_000_000_000)
        top_n = parse_positive_int("top", default=10, maximum=50)
        result = cached_similar_users(user_id, top_n)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.get("/api/recommendations")
def api_recommendations() -> Any:
    try:
        user_id = parse_positive_int("user_id", default=1, maximum=1_000_000_000)
        top_n = parse_positive_int("top", default=10, maximum=30)
        similar_users = parse_positive_int("similar_users", default=20, maximum=100)
        result = cached_recommendations(user_id, top_n, similar_users)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.get("/api/video-trend")
def api_video_trend() -> Any:
    try:
        video_id = parse_positive_int("video_id", default=1, maximum=1_000_000_000)
        history_days = parse_positive_int("history_days", default=30, maximum=180)
        predict_days = parse_positive_int("predict_days", default=7, maximum=30)
        result = cached_video_trend(video_id, history_days, predict_days)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.get("/api/video-clusters")
def api_video_clusters() -> Any:
    try:
        cluster_count = parse_positive_int("clusters", default=5, maximum=20)
        sample_per_cluster = parse_positive_int("sample", default=6, maximum=20)
        result = cached_video_clusters(cluster_count, sample_per_cluster)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.get("/api/user-clusters")
def api_user_clusters() -> Any:
    try:
        cluster_count = parse_positive_int("clusters", default=5, maximum=20)
        sample_per_cluster = parse_positive_int("sample", default=8, maximum=30)
        result = cached_user_clusters(cluster_count, sample_per_cluster)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
