"""
F6: cluster videos watched by similar groups of users.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Union

try:
    from .utils import (
        CATEGORY_ORDER,
        DEFAULT_DATA_DIR,
        build_video_viewer_stats,
        load_videos_by_id,
        normalize_counter,
        run_kmeans,
    )
except ImportError:
    from utils import (
        CATEGORY_ORDER,
        DEFAULT_DATA_DIR,
        build_video_viewer_stats,
        load_videos_by_id,
        normalize_counter,
        run_kmeans,
    )


class VideoClusterMetadata(TypedDict):
    title: str
    category: str
    watch_count: int
    avg_finish_rate: float


def build_video_feature_vectors(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[Dict[int, List[float]], Dict[int, VideoClusterMetadata]]:
    videos = load_videos_by_id(data_dir)
    video_viewer_interest_scores, video_engagement = build_video_viewer_stats(data_dir)

    feature_vectors: Dict[int, List[float]] = {}
    metadata: Dict[int, VideoClusterMetadata] = {}

    for video_id, video in videos.items():
        interest_scores = video_viewer_interest_scores.get(video_id, Counter()) #Counter() 计数器字典，用于处理异常情况 
        #分析这个视频吸引的用户是喜欢什么类型的
        stats = video_engagement.get(
            video_id,
            {
                "watch_count": 0.0,
                "like_count": 0.0,
                "comment_count": 0.0,
                "share_count": 0.0,
                "finish_rate_sum": 0.0,
            },
        )

        watch_count = stats["watch_count"]
        if watch_count == 0:
            continue

        viewer_vector = normalize_counter(interest_scores, CATEGORY_ORDER)
        avg_finish_rate = stats["finish_rate_sum"] / watch_count
        like_rate = stats["like_count"] / watch_count
        share_rate = stats["share_count"] / watch_count

        feature_vectors[video_id] = viewer_vector + [
            min(watch_count / 50.0, 1.0),
            avg_finish_rate,
            like_rate,
            share_rate,
        ] #注意列表加法是拼接
        metadata[video_id] = {
            "title": video["title"],
            "category": video["category"],
            "watch_count": int(watch_count),
            "avg_finish_rate": round(avg_finish_rate, 4),
        }

    return feature_vectors, metadata


def cluster_videos(
    cluster_count: int = 5,
    sample_per_cluster: int = 6,
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> List[Dict[str, object]]:
    feature_vectors, metadata = build_video_feature_vectors(data_dir)
    assignments, _ = run_kmeans(feature_vectors, cluster_count)

    cluster_members: Dict[int, List[int]] = defaultdict(list)
    for video_id, cluster_id in assignments.items():
        cluster_members[cluster_id].append(video_id)

    results: List[Dict[str, object]] = []
    for cluster_id in sorted(cluster_members):
        member_ids = cluster_members[cluster_id]
        category_counter = Counter()
        finish_rates: List[float] = []

        for video_id in member_ids:
            info = metadata[video_id]
            category_counter.update([str(info["category"])])
            finish_rates.append(float(info["avg_finish_rate"]))

        representative_videos = []
        for video_id in member_ids[:sample_per_cluster]:
            info = metadata[video_id]
            representative_videos.append(
                {
                    "video_id": video_id,
                    "title": info["title"],
                    "category": info["category"],
                    "watch_count": info["watch_count"],
                }
            )

        avg_finish_rate = sum(finish_rates) / len(finish_rates) if finish_rates else 0.0

        results.append(
            {
                "cluster_id": cluster_id,
                "video_count": len(member_ids),
                "dominant_categories": [name for name, _ in category_counter.most_common(3)],
                "avg_finish_rate": round(avg_finish_rate, 4),
                "sample_videos": representative_videos,
            }
        )

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster videos by viewer similarity.")
    parser.add_argument("--clusters", type=int, default=5)
    parser.add_argument("--sample-per-cluster", type=int, default=6)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = cluster_videos(
        cluster_count=args.clusters,
        sample_per_cluster=args.sample_per_cluster,
        data_dir=args.data_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
