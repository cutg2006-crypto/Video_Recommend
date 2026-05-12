"""
F4: recommend related videos for a target user based on watch history.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple, Union

try:
    from .similarity import find_similar_users
    from .utils import DEFAULT_DATA_DIR, build_user_video_stats, load_videos_by_id
except ImportError:
    from similarity import find_similar_users
    from utils import DEFAULT_DATA_DIR, build_user_video_stats, load_videos_by_id


def build_global_popularity(
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> Tuple[Dict[int, float], Dict[str, Dict[int, float]]]:
    videos = load_videos_by_id(data_dir)
    file_path = Path(data_dir) / "watch_logs.csv"

    popularity_scores: Dict[int, float] = defaultdict(float)
    category_video_popularity: DefaultDict[str, DefaultDict[int, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    with file_path.open("r", encoding="utf-8", newline="") as file:
        import csv

        reader = csv.DictReader(file)
        for row in reader:
            video_id = int(row["video_id"])
            finish_rate = float(row["finish_rate"])
            liked = int(row["liked"])
            commented = int(row["commented"])
            shared = int(row["shared"])
            category = videos[video_id]["category"]

            score = 1.0 + finish_rate + liked * 0.8 + commented * 0.6 + shared * 1.0
            popularity_scores[video_id] += score
            category_video_popularity[category][video_id] += score

    return dict(popularity_scores), { #注意：dict和defaultdict亦有区别
        category: dict(video_popularity)
        for category, video_popularity in category_video_popularity.items()
    }


def recommend_videos(
    target_user_id: int,
    top_n: int = 10,
    similar_user_count: int = 20,
    data_dir: Union[Path, str] = DEFAULT_DATA_DIR,
) -> List[Dict[str, object]]:
    videos = load_videos_by_id(data_dir)
    user_video_scores, user_seen_videos, user_category_scores, _ = build_user_video_stats(data_dir)

    if target_user_id not in user_seen_videos:
        raise ValueError(f"User {target_user_id} has no watch history.")

    seen_videos = user_seen_videos[target_user_id]
    category_scores = user_category_scores[target_user_id]
    similar_users = find_similar_users(
        target_user_id=target_user_id,
        top_n=similar_user_count,
        data_dir=data_dir,
    )
    popularity_scores, category_video_popularity = build_global_popularity(data_dir)

    candidate_scores: Dict[int, float] = defaultdict(float)

    for user in similar_users:
        similar_user_id = int(user["user_id"])
        similarity_score = float(user["similarity_score"])

        for video_id, raw_score in user_video_scores[similar_user_id].items():
            if video_id in seen_videos: #如果在已经看过的视频里，则不再推荐
                continue
            candidate_scores[video_id] += raw_score * similarity_score

    favorite_categories_dict = {
        category:scores
        for category, scores in sorted(
            category_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3] #只取前三个
    }

    favorite_categories = [
        category
        for category,_ in favorite_categories_dict.items()
    ]

    favorite_scores = [
        scores 
        for _,scores in favorite_categories_dict.items()
    ]

    max_scores = max(favorite_scores)

    favorite_scores =[
        score / max_scores
        for score in favorite_scores    
    ]

    for category in favorite_categories:
        if category == favorite_categories[0]:
            normalized_scores = favorite_scores[0]
        elif category == favorite_categories[1]:
            normalized_scores = favorite_scores[1]
        else:
            normalized_scores = favorite_scores[2]
        ranked_category_videos = sorted(
            category_video_popularity[category].items(),
            key=lambda item: item[1],
            reverse=True,
        )[:100] #按照降序选出前100高分的该品类视频
        for video_id, popularity in ranked_category_videos:
            if video_id in seen_videos:
                continue
            candidate_scores[video_id] += popularity * 0.15 * normalized_scores

    if not candidate_scores: #如果候选名单依旧是空的，就改用热门视频推荐
        for video_id, popularity in sorted(
            popularity_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            if video_id in seen_videos:
                continue
            candidate_scores[video_id] = popularity * 0.1
            if len(candidate_scores) >= top_n :
                break

    ranked_videos = sorted(
        candidate_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:top_n]

    recommendations: List[Dict[str, object]] = []
    for video_id, score in ranked_videos:
        video = videos[video_id]
        recommendations.append(
            {
                "video_id": video_id,
                "title": video["title"],
                "category": video["category"],
                "tags": video["tags"].split(";"),
                "recommend_score": round(score, 4),#round(a,b)把a四舍五入，保留b位小数
                "reason": build_reason(video["category"], favorite_categories),
            }
        )

    return recommendations


def build_reason(video_category: str, favorite_categories: List[str]) -> str:
    if video_category in favorite_categories:
        return f"Matches the user's preferred category: {video_category}"
    return "Popular among users with similar interests"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend videos for a target user.")
    parser.add_argument("user_id", type=int, help="Target user id")
    parser.add_argument("--top", type=int, default=10, help="Number of recommended videos")
    parser.add_argument(
        "--similar-users",
        type=int,
        default=20,
        help="Number of similar users used in collaborative filtering",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = recommend_videos(
        target_user_id=args.user_id,
        top_n=args.top,
        similar_user_count=args.similar_users,
        data_dir=args.data_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
