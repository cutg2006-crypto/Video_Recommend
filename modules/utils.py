"""
Shared helpers for recommendation modules.
"""

from __future__ import annotations
from functools import lru_cache

import csv
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Mapping, Set, Tuple, Union

#设置项目根目录和默认数据目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
CATEGORY_ORDER = [
    "food",
    "game",
    "tech",
    "music",
    "movie",
    "sports",
    "study",
    "funny",
    "travel",
    "life",
]

@lru_cache(maxsize=1)
def load_videos_by_id(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Dict[int, Dict[str, str]]:
    videos: Dict[int, Dict[str, str]] = {}
    file_path = Path(data_dir) / "videos.csv"

    with file_path.open("r", encoding="utf-8", newline="") as file: #newline=""的意思是意思是：打开文件时，不要让 Python 自己提前处理换行符，把换行原样交给 csv 模块处理。
        reader = csv.DictReader(file) #这里会自动将第一行表头作为字段名
        for row in reader:
            video_id = int(row["video_id"])
            videos[video_id] = row

    return videos

@lru_cache(maxsize=1)
def load_user_profiles(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Dict[int, Dict[str, str]]:
    users: Dict[int, Dict[str, str]] = {}
    file_path = Path(data_dir) / "users.csv"

    with file_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_id = int(row["user_id"])
            users[user_id] = row

    return users

@lru_cache(maxsize=1)
def build_user_video_stats(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[
    Dict[int, Dict[int, float]],
    Dict[int, Set[int]],
    Dict[int, Dict[str, float]],
    Dict[int, Dict[str, float]],
]:
    videos = load_videos_by_id(data_dir)
    file_path = Path(data_dir) / "watch_logs.csv"

    user_video_scores: DefaultDict[int, DefaultDict[int, float]] = defaultdict(
        lambda: defaultdict(float) #defaultdict(x)这个x就是默认创造出的值，x需为一个函数
    )
    user_seen_videos: Dict[int, Set[int]] = defaultdict(set)
    user_category_scores: DefaultDict[int, DefaultDict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    user_engagement: Dict[int, Dict[str, float]] = defaultdict( #defaultdict会在key不存在时，自动创建一个默认值
        lambda: {
            "watch_count": 0.0,
            "like_count": 0.0,
            "comment_count": 0.0,
            "share_count": 0.0,
            "finish_rate_sum": 0.0,
        }
    )

    with file_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_id = int(row["user_id"])
            video_id = int(row["video_id"])
            finish_rate = float(row["finish_rate"])
            liked = int(row["liked"])
            commented = int(row["commented"])
            shared = int(row["shared"])
            category = videos[video_id]["category"]

            score = 1.0 + finish_rate + liked * 0.8 + commented * 0.6 + shared * 1.0
            user_video_scores[user_id][video_id] += score
            user_seen_videos[user_id].add(video_id)
            user_category_scores[user_id][category] += score

            stats = user_engagement[user_id]
            stats["watch_count"] += 1
            stats["like_count"] += liked
            stats["comment_count"] += commented
            stats["share_count"] += shared
            stats["finish_rate_sum"] += finish_rate

    return (
        {
            user_id: dict(video_scores)
            for user_id, video_scores in user_video_scores.items()
        },
        dict(user_seen_videos),
        {
            user_id: dict(category_scores)
            for user_id, category_scores in user_category_scores.items()
        },
        dict(user_engagement),
    )


def normalize_counter(counter: Mapping[str, float], keys: List[str]) -> List[float]:
    total = sum(counter.values())
    if total <= 0:
        return [0.0 for _ in keys]
    return [counter.get(key, 0.0) / total for key in keys]

@lru_cache(maxsize=1)
def build_video_viewer_stats(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[
    Dict[int, Dict[str, float]],
    Dict[int, Dict[str, float]],
]:
    users = load_user_profiles(data_dir)
    file_path = Path(data_dir) / "watch_logs.csv"

    video_viewer_interest_scores: DefaultDict[int, DefaultDict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    video_engagement: Dict[int, Dict[str, float]] = defaultdict(
        lambda: {
            "watch_count": 0.0,
            "like_count": 0.0,
            "comment_count": 0.0,
            "share_count": 0.0,
            "finish_rate_sum": 0.0,
        }
    )

    with file_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_id = int(row["user_id"])
            video_id = int(row["video_id"])
            finish_rate = float(row["finish_rate"])
            liked = int(row["liked"])
            commented = int(row["commented"])
            shared = int(row["shared"])
            weight = 1.0 + finish_rate + liked * 0.8 + commented * 0.6 + shared * 1.0

            interest_categories = users[user_id]["interest_categories"].split(";") #返回一个列表
            for category in interest_categories:
                video_viewer_interest_scores[video_id][category] += weight

            stats = video_engagement[video_id] #深拷贝，相当于引用
            stats["watch_count"] += 1
            stats["like_count"] += liked
            stats["comment_count"] += commented
            stats["share_count"] += shared
            stats["finish_rate_sum"] += finish_rate

    return (
        {
            video_id: dict(interest_scores)
            for video_id, interest_scores in video_viewer_interest_scores.items() #.items()用于同时遍历key和value
        },
        dict(video_engagement),
    )


def get_user_active_level(users:Dict[int, Dict[str, str]], user_id: int) -> str:

    if user_id not in users:
        raise ValueError(f"User {user_id} does not exist.")

    return users[user_id]["active_level"]


def cosine_similarity(vector_a: Dict[str, float], vector_b: Dict[str, float], level_a:str, level_b:str) -> float:
    if not vector_a or not vector_b:
        return 0.0
    level_score={
    "low" : 0,
    "medium" : 1,
    "high" : 2
    }
    distance = abs(level_score[level_a] - level_score[level_b])
    active_score = 1 - distance/2
    shared_keys = set(vector_a) & set(vector_b)
    numerator = sum(vector_a[key] * vector_b[key] for key in shared_keys)
    norm_a = math.sqrt(sum(value * value for value in vector_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vector_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return (numerator / (norm_a * norm_b))*(0.7 + 0.3*active_score)


def euclidean_distance(vector_a: List[float], vector_b: List[float]) -> float:
    return math.sqrt(
        sum((value_a - value_b) ** 2 for value_a, value_b in zip(vector_a, vector_b))
    )


def average_vectors(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        raise ValueError("Cannot average an empty vector list.")

    vector_length = len(vectors[0])
    sums = [0.0] * vector_length
    for vector in vectors:
        for index, value in enumerate(vector):
            sums[index] += value
    return [value / len(vectors) for value in sums]


def run_kmeans(
    item_vectors: Dict[int, List[float]],
    cluster_count: int,
    max_iterations: int = 20,
    seed: int = 20260511,
) -> Tuple[Dict[int, int], List[List[float]]]:
    if not item_vectors:
        raise ValueError("No vectors available for clustering.")

    item_ids = list(item_vectors) #字典转列表默认读取所有key
    if cluster_count <= 0:
        raise ValueError("cluster_count must be positive.")
    if cluster_count > len(item_ids):
        cluster_count = len(item_ids)

    random.seed(seed)
    initial_ids = random.sample(item_ids, cluster_count)
    centroids = [item_vectors[item_id][:] for item_id in initial_ids]
    assignments: Dict[int, int] = {}

    for _ in range(max_iterations):
        new_assignments: Dict[int, int] = {}
        cluster_vectors: Dict[int, List[List[float]]] = defaultdict(list)

        for item_id, vector in item_vectors.items():
            closest_cluster = min(
                range(cluster_count),
                key=lambda index: euclidean_distance(vector, centroids[index]),
            ) #从range（）中选出key最小的那个
            new_assignments[item_id] = closest_cluster
            cluster_vectors[closest_cluster].append(vector)

        if new_assignments == assignments:
            break

        assignments = new_assignments #更新assignments
        for cluster_index in range(cluster_count):
            if cluster_vectors[cluster_index]:
                centroids[cluster_index] = average_vectors(cluster_vectors[cluster_index])

    return assignments, centroids
