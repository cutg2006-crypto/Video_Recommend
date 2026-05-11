"""
Mock data generator for a short-video recommendation project.

The generated CSV files cover:
- F1: at least 100,000 video records
- F2: at least 10,000 users and simulated viewing behavior

Run:
    python modules/data_generator.py
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Union


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data"


CATEGORY_TAGS = {
    "food": ["cooking", "snack", "restaurant", "dessert", "recipe", "street_food"],
    "game": ["mobile_game", "moba", "fps", "strategy", "walkthrough", "esports"],
    "tech": ["ai", "phone", "programming", "digital", "robot", "software"],
    "music": ["pop", "guitar", "piano", "cover", "concert", "dance"],
    "movie": ["clip", "review", "actor", "trailer", "drama", "animation"],
    "sports": ["basketball", "football", "fitness", "running", "table_tennis", "match"],
    "study": ["english", "math", "exam", "reading", "campus", "skill"],
    "funny": ["meme", "sketch", "daily_fun", "joke", "reaction", "challenge"],
    "travel": ["city", "landscape", "hotel", "guide", "vlog", "culture"],
    "life": ["pet", "home", "fashion", "makeup", "family", "workplace"],
}

GENDERS = ["female", "male", "unknown"]
ACTIVE_LEVELS = ["low", "medium", "high"]
ACTIVE_LEVEL_WEIGHTS = [0.25, 0.55, 0.20]
ACTIVE_LEVEL_LOG_RANGES = {
    "low": (30, 60),
    "medium": (61, 120),
    "high": (121, 180),
}


@dataclass(frozen=True)
class GeneratedFiles:
    videos: Path
    users: Path
    watch_logs: Path


@dataclass(frozen=True)
class UserProfile:
    interests: List[str]
    active_level: str


def random_time_within_days(days: int, now: datetime) -> datetime:
    return now - timedelta(
        days=random.randint(0, days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )


def random_time_between(start: datetime, end: datetime) -> datetime:
    if start >= end:
        return start
    delta_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta_seconds))


def choose_tags(category: str, min_count: int = 2, max_count: int = 4) -> List[str]:
    tags = CATEGORY_TAGS[category]
    count = random.randint(min_count, min(max_count, len(tags)))
    return random.sample(tags, count)


def generate_finish_rate(is_preferred: bool) -> float:
    if is_preferred:
        return round(random.betavariate(4.2, 1.8), 3)
    return round(random.betavariate(1.8, 3.8), 3)


def generate_engagement_flags(
    is_preferred: bool,
    finish_rate: float,
) -> Tuple[int, int, int]:
    if is_preferred:
        liked_score = random.betavariate(3.8, 2.2) * 0.60 + finish_rate * 0.40
        commented_score = random.betavariate(3.0, 2.8) * 0.35 + finish_rate * 0.65
        shared_score = random.betavariate(2.4, 3.0) * 0.25 + finish_rate * 0.75
    else:
        liked_score = random.betavariate(1.8, 4.5) * 0.70 + finish_rate * 0.30
        commented_score = random.betavariate(1.5, 5.0) * 0.50 + finish_rate * 0.50
        shared_score = random.betavariate(1.3, 5.5) * 0.35 + finish_rate * 0.65

    liked = int(liked_score > 0.58)
    commented = int(commented_score > 0.62 and finish_rate > 0.30)
    shared = int(shared_score > 0.72 and finish_rate > 0.55)
    return liked, commented, shared


def generate_videos(
    output_file: Path,
    video_count: int,
    now: datetime,
) -> Tuple[Dict[str, List[int]], Dict[int, datetime]]:
    category_to_video_ids = {category: [] for category in CATEGORY_TAGS}
    video_publish_times: Dict[int, datetime] = {}

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "video_id",
                "title",
                "category",
                "tags",
                "author_id",
                "duration_seconds",
                "publish_time",
                "description",
            ],
        )
        writer.writeheader()

        categories = list(CATEGORY_TAGS)
        for video_id in range(1, video_count + 1):
            category = random.choice(categories)
            tags = choose_tags(category)
            duration = random.randint(8, 180)
            author_id = random.randint(1, max(1000, video_count // 20))
            publish_time = random_time_within_days(60, now)

            category_to_video_ids[category].append(video_id)
            video_publish_times[video_id] = publish_time

            writer.writerow(
                {
                    "video_id": video_id,
                    "title": f"{category.title()} Video {video_id}",
                    "category": category,
                    "tags": ";".join(tags),
                    "author_id": author_id,
                    "duration_seconds": duration,
                    "publish_time": publish_time.isoformat(timespec="seconds"),
                    "description": (
                        f"A short video about {category}, including "
                        f"{', '.join(tags)}."
                    ),
                }
            )

    return category_to_video_ids, video_publish_times


def generate_users(output_file: Path, user_count: int) -> Dict[int, UserProfile]:
    user_profiles: Dict[int, UserProfile] = {}
    categories = list(CATEGORY_TAGS)

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "user_id",
                "age",
                "gender",
                "interest_categories",
                "active_level",
            ],
        )
        writer.writeheader()

        for user_id in range(1, user_count + 1):
            interest_count = random.randint(2, 4)
            interests = random.sample(categories, interest_count)
            active_level = random.choices(
                ACTIVE_LEVELS,
                weights=ACTIVE_LEVEL_WEIGHTS,
                k=1,
            )[0]
            user_profiles[user_id] = UserProfile(
                interests=interests,
                active_level=active_level,
            )

            writer.writerow(
                {
                    "user_id": user_id,
                    "age": random.randint(13, 60),
                    "gender": random.choice(GENDERS),
                    "interest_categories": ";".join(interests),
                    "active_level": active_level,
                }
            )

    return user_profiles


def generate_watch_logs(
    output_file: Path,
    user_count: int,
    user_profiles: Dict[int, UserProfile],
    category_to_video_ids: Dict[str, List[int]],
    video_publish_times: Dict[int, datetime],
    now: datetime,
) -> int:
    categories = list(CATEGORY_TAGS)
    recent_watch_start = now - timedelta(days=45)
    log_id = 1

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "log_id",
                "user_id",
                "video_id",
                "watch_seconds",
                "finish_rate",
                "liked",
                "commented",
                "shared",
                "watch_time",
            ],
        )
        writer.writeheader()

        for user_id in range(1, user_count + 1):
            profile = user_profiles[user_id]
            interests = profile.interests
            active_level = profile.active_level
            min_logs, max_logs = ACTIVE_LEVEL_LOG_RANGES[active_level]
            watch_count = random.randint(min_logs, max_logs)

            for _ in range(watch_count):
                if random.random() < 0.80:
                    category = random.choice(interests)
                else:
                    category = random.choice(categories)

                video_id = random.choice(category_to_video_ids[category])
                is_preferred = category in interests
                finish_rate = generate_finish_rate(is_preferred)
                watch_seconds = random.randint(3, 180)
                liked, commented, shared = generate_engagement_flags(
                    is_preferred,
                    finish_rate,
                )

                publish_time = video_publish_times[video_id]
                watch_time = random_time_between(
                    max(publish_time, recent_watch_start),
                    now,
                )

                writer.writerow(
                    {
                        "log_id": log_id,
                        "user_id": user_id,
                        "video_id": video_id,
                        "watch_seconds": watch_seconds,
                        "finish_rate": finish_rate,
                        "liked": liked,
                        "commented": commented,
                        "shared": shared,
                        "watch_time": watch_time.isoformat(timespec="seconds"),
                    }
                )
                log_id += 1

    return log_id - 1


def generate_mock_data(
    output_dir: Union[Path, str] = DEFAULT_OUTPUT_DIR,
    video_count: int = 100_000,
    user_count: int = 10_000,
    seed: int = 20260511,
) -> GeneratedFiles:
    random.seed(seed)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    videos_file = output_path / "videos.csv"
    users_file = output_path / "users.csv"
    watch_logs_file = output_path / "watch_logs.csv"
    now = datetime.now()

    category_to_video_ids, video_publish_times = generate_videos(
        videos_file,
        video_count,
        now,
    )
    user_profiles = generate_users(users_file, user_count)
    log_count = generate_watch_logs(
        watch_logs_file,
        user_count,
        user_profiles,
        category_to_video_ids,
        video_publish_times,
        now,
    )

    print(f"Generated {video_count} videos -> {videos_file}")
    print(f"Generated {user_count} users -> {users_file}")
    print(f"Generated {log_count} watch logs -> {watch_logs_file}")

    return GeneratedFiles(
        videos=videos_file,
        users=users_file,
        watch_logs=watch_logs_file,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate mock short-video recommendation data."
    )
    parser.add_argument("--videos", type=int, default=100_000)
    parser.add_argument("--users", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_mock_data(
        output_dir=args.output,
        video_count=args.videos,
        user_count=args.users,
        seed=args.seed,
    )
