"""
F7: cluster users with similar viewing interests.
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
        build_user_video_stats,
        load_user_profiles,
        normalize_counter,
        run_kmeans,
    )
except ImportError:
    from utils import (
        CATEGORY_ORDER,
        DEFAULT_DATA_DIR,
        build_user_video_stats,
        load_user_profiles,
        normalize_counter,
        run_kmeans,
    )


class UserClusterMetadata(TypedDict):
    interest_categories: List[str]
    active_level: str
    watch_count: int
    avg_finish_rate: float


def build_user_feature_vectors(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[Dict[int, List[float]], Dict[int, UserClusterMetadata]]:
    users = load_user_profiles(data_dir)
    _, _, user_category_scores, user_engagement = build_user_video_stats(data_dir)

    feature_vectors: Dict[int, List[float]] = {}
    metadata: Dict[int, UserClusterMetadata] = {}

    for user_id, profile in users.items():
        category_scores = user_category_scores.get(user_id, Counter())
        category_vector = normalize_counter(category_scores, CATEGORY_ORDER)
        stats = user_engagement.get(
            user_id,
            {
                "watch_count": 0.0,
                "like_count": 0.0,
                "comment_count": 0.0,
                "share_count": 0.0,
                "finish_rate_sum": 0.0,
            },
        )

        watch_count = stats["watch_count"]
        avg_finish_rate = (
            stats["finish_rate_sum"] / watch_count if watch_count else 0.0
        )
        like_rate = stats["like_count"] / watch_count if watch_count else 0.0
        share_rate = stats["share_count"] / watch_count if watch_count else 0.0

        feature_vectors[user_id] = category_vector + [
            min(watch_count / 100.0, 1.0),
            avg_finish_rate,
            like_rate,
            share_rate,
        ]
        metadata[user_id] = {
            "interest_categories": profile["interest_categories"].split(";"),
            "active_level": profile["active_level"],
            "watch_count": int(watch_count),
            "avg_finish_rate": round(avg_finish_rate, 4),
        }

    return feature_vectors, metadata


def cluster_users(
    cluster_count: int = 5,
    sample_per_cluster: int = 8,
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> List[Dict[str, object]]:
    feature_vectors, metadata = build_user_feature_vectors(data_dir)
    assignments, _ = run_kmeans(feature_vectors, cluster_count)

    cluster_members: Dict[int, List[int]] = defaultdict(list)
    for user_id, cluster_id in assignments.items():
        cluster_members[cluster_id].append(user_id)

    results: List[Dict[str, object]] = []
    for cluster_id in sorted(cluster_members):
        member_ids = cluster_members[cluster_id]
        category_counter = Counter()
        active_level_counter = Counter()
        finish_rates: List[float] = []

        for user_id in member_ids:
            info = metadata[user_id]
            category_counter.update(info["interest_categories"])
            active_level_counter.update([str(info["active_level"])])
            finish_rates.append(float(info["avg_finish_rate"]))

        top_categories = [name for name, _ in category_counter.most_common(3)]
        avg_finish_rate = sum(finish_rates) / len(finish_rates) if finish_rates else 0.0
        sample_users = member_ids[:sample_per_cluster]

        results.append(
            {
                "cluster_id": cluster_id,
                "user_count": len(member_ids),
                "top_interest_categories": top_categories,
                "dominant_active_level": active_level_counter.most_common(1)[0][0],
                "avg_finish_rate": round(avg_finish_rate, 4),
                "sample_user_ids": sample_users,
            }
        )

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster users by viewing interests.")
    parser.add_argument("--clusters", type=int, default=5)
    parser.add_argument("--sample-per-cluster", type=int, default=8)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = cluster_users(
        cluster_count=args.clusters,
        sample_per_cluster=args.sample_per_cluster,
        data_dir=args.data_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
