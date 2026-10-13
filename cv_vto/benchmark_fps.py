"""
Measure how many frames per second the vision pipeline processes on THIS computer.

    python -m cv_vto.benchmark_fps                # live webcam for 10 seconds
    python -m cv_vto.benchmark_fps --image me.jpg # repeat one photo 200 times (no webcam needed)

The pipeline timed per frame: mirror -> MediaPipe Pose (+ body silhouette) -> width measurement ->
classification -> T-shirt overlay. It does not include the browser/WebRTC video transport used by the
Streamlit page, so the number is the processing ceiling. Run with --no-segmentation to see its cost.
"""
import argparse
import json
import os
import platform
import time
from datetime import date

import cv2

from cv_vto.body_shape import BodyShapeEstimator, estimate_tshirt_size
from cv_vto.garment_overlay import GarmentOverlay


def run(frames, use_segmentation, garment):
    est = BodyShapeEstimator(use_segmentation=use_segmentation)
    overlay = GarmentOverlay(garment, min_visibility=0.0)
    n, detected, t0 = 0, 0, time.perf_counter()
    for frame in frames:
        frame = cv2.flip(frame, 1)
        landmarks, mask = est.analyze(frame)
        if landmarks is not None:
            detected += 1
            ratios = est.compute_ratios(landmarks, mask)
            if ratios:
                est.classify(ratios)
                estimate_tshirt_size(ratios.size_width)
            frame = overlay.apply(frame, landmarks)
        n += 1
    dt = time.perf_counter() - t0
    est.close()
    return n / dt, 1000 * dt / n, detected, n


def webcam_frames(seconds):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("No webcam found. Use --image instead.")
    end = time.time() + seconds
    while time.time() < end:
        ok, frame = cap.read()
        if ok:
            yield frame
    cap.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image")
    ap.add_argument("--seconds", type=int, default=10)
    ap.add_argument("--garment", default="assets/garments/tshirt_navy.png")
    ap.add_argument("--no-segmentation", action="store_true")
    args = ap.parse_args()

    if args.image:
        img = cv2.resize(cv2.imread(args.image), (640, 480))
        frames = (img.copy() for _ in range(200))
    else:
        frames = webcam_frames(args.seconds)
    fps, ms, det, n = run(frames, not args.no_segmentation, args.garment)
    print(f"{fps:.1f} FPS  ({ms:.1f} ms per frame, person found in {det}/{n} frames, "
          f"segmentation {'off' if args.no_segmentation else 'on'})")
    print("Target in the abstract: 25+ FPS on a standard CPU.", "MET" if fps >= 25 else "NOT MET")
    os.makedirs("data", exist_ok=True)
    with open("data/fps_benchmark.json", "w") as fh:     # shown on the dashboard's "How it works" tab
        json.dump({"fps": round(fps, 1), "ms_per_frame": round(ms, 1), "segmentation": not args.no_segmentation,
                   "source": "image" if args.image else "webcam", "frames": n, "person_found": det,
                   "machine": f"{platform.system()} {platform.machine()}, {platform.processor() or 'CPU'}",
                   "date": date.today().isoformat()}, fh, indent=2)
    print("Saved data/fps_benchmark.json")


if __name__ == "__main__":
    main()
