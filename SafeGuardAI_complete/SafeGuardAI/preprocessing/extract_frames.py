"""
Dataset utility: extract frames from the RLV dataset videos.

This script used to contain a hardcoded local Windows path. It is now portable:

Example:
  python -m preprocessing.extract_frames --dataset \"D:\\datasets\\Real Life Violence Dataset\"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def extract_frames(video_folder: Path, save_folder: Path, every_n: int = 10, size: int = 224) -> int:
    """
    Extract 1 frame per `every_n` frames from each video in `video_folder`.
    Writes resized JPEGs to `save_folder`.
    Returns number of frames written.
    """
    save_folder.mkdir(parents=True, exist_ok=True)

    frame_id = 0
    written = 0

    videos = sorted([p for p in video_folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES])
    if not videos:
        print(f"No videos found in: {video_folder}")
        return 0

    for video_path in videos:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Skipping unreadable video: {video_path}")
            continue

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % max(1, every_n) == 0:
                frame = cv2.resize(frame, (size, size))
                out_path = save_folder / f"{frame_id}.jpg"
                ok = cv2.imwrite(str(out_path), frame)
                if ok:
                    written += 1
                    frame_id += 1

            frame_count += 1

        cap.release()

    print(f"Finished extracting from {video_folder} → {save_folder} ({written} frames)")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract frames from RLV dataset videos.")
    ap.add_argument("--dataset", required=True, help="Path to 'Real Life Violence Dataset' directory")
    ap.add_argument("--out", default=str(Path("datasets") / "violence_frames"), help="Output base directory")
    ap.add_argument("--every-n", type=int, default=10, help="Keep one frame every N frames")
    ap.add_argument("--size", type=int, default=224, help="Output frame size (square, pixels)")
    args = ap.parse_args()

    dataset_path = Path(args.dataset)
    violence_path = dataset_path / "Violence"
    nonviolence_path = dataset_path / "NonViolence"

    out_base = Path(args.out)
    save_violence = out_base / "Violence"
    save_nonviolence = out_base / "NonViolence"

    if not violence_path.is_dir() or not nonviolence_path.is_dir():
        print("Dataset folder must contain 'Violence' and 'NonViolence' subfolders.")
        print(f"Got: {dataset_path}")
        return 2

    extract_frames(violence_path, save_violence, every_n=args.every_n, size=args.size)
    extract_frames(nonviolence_path, save_nonviolence, every_n=args.every_n, size=args.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())