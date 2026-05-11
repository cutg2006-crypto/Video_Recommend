"""
F3: find users with similar interests for a target user.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, TypedDict, Union

try:
    from .utils import (
        DEFAULT_DATA_DIR,
        build_user_video_stats,
        cosine_similarity,
        load_user_profiles,
    )
except ImportError:
    from utils import DEFAULT_DATA_DIR, build_user_video_stats, cosine_similarity, load_user_profiles


class SimilarUserResult(TypedDict):
    user_id: int
    similarity_score: float
    interest_categories: List[str]
    active_level: str
    avg_finish_rate: float


def find_similar_users(
    target_user_id: int,
    top_n: int = 10,
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> List[SimilarUserResult]:
    users = load_user_profiles(data_dir)
    if target_user_id not in users:
        raise ValueError(f"User {target_user_id} does not exist.")

    _, _, user_category_scores, user_engagement = build_user_video_stats(data_dir)
    target_vector = dict(user_category_scores.get(target_user_id, {}))

    if not target_vector:
        raise ValueError(f"User {target_user_id} has no watch history.")

    results: List[SimilarUserResult] = []
    for user_id, category_scores in user_category_scores.items():
        if user_id == target_user_id:
            continue

        score = cosine_similarity(target_vector, dict(category_scores))
        if score <= 0:
            continue

        profile = users[user_id]
        stats = user_engagement[user_id]
        avg_finish_rate = stats["finish_rate_sum"] / stats["watch_count"]
        results.append(
            {
                "user_id": user_id,
                "similarity_score": round(score, 4),
                "interest_categories": profile["interest_categories"].split(";"),
                "active_level": profile["active_level"],
                "avg_finish_rate": round(avg_finish_rate, 4),
            }
        )

    results.sort(key=lambda item: item["similarity_score"], reverse=True)
    return results[:top_n]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find similar users for a target user.")
    parser.add_argument("user_id", type=int, help="Target user id")
    parser.add_argument("--top", type=int, default=10, help="Number of similar users")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = find_similar_users(
        target_user_id=args.user_id,
        top_n=args.top,
        data_dir=args.data_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
