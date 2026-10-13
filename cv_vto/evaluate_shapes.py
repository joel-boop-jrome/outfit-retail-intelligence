"""
Check the body-shape classifier against labelled photos.

    python -m cv_vto.evaluate_shapes                 # accuracy + confusion matrix
    python -m cv_vto.evaluate_shapes --tune          # also search the two thresholds
    python -m cv_vto.evaluate_shapes --dir other/folder

Expects <dir>/labels.csv (filename,label) and <dir>/photos/<filename>. See data/validation/README.md.
"""
import argparse
import csv
import itertools
import os
from collections import Counter

SHAPES = ["hourglass", "rectangle", "inverted_triangle", "pear"]


def load_labels(folder):
    path = os.path.join(folder, "labels.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. See data/validation/README.md for how to build the validation set.")
    with open(path, newline="") as fh:
        return [(r["filename"].strip(), r["label"].strip()) for r in csv.DictReader(fh) if r.get("filename")]


def confusion(pairs):
    table = {t: Counter() for t in SHAPES}
    for truth, pred in pairs:
        table[truth][pred or "no result"] += 1
    return table


def print_report(pairs, title):
    ok = sum(1 for t, p in pairs if t == p)
    print(f"\n{title}: accuracy {ok}/{len(pairs)} = {ok / max(len(pairs), 1):.0%}")
    cols = SHAPES + ["no result"]
    print(f"{'true \\ predicted':>20} " + " ".join(f"{c[:11]:>11}" for c in cols))
    for t, row in confusion(pairs).items():
        print(f"{t:>20} " + " ".join(f"{row.get(c, 0):>11}" for c in cols))


def main():
    import cv2
    from cv_vto.body_shape import BodyShapeEstimator, SHOULDER_HIP_TOLERANCE, WAIST_DEFINED_RATIO

    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/validation")
    ap.add_argument("--tune", action="store_true")
    args = ap.parse_args()

    labels = load_labels(args.dir)
    est = BodyShapeEstimator(static_image_mode=True)
    measured = []   # (truth, ratios or None)
    for fname, truth in labels:
        img = cv2.imread(os.path.join(args.dir, "photos", fname))
        if img is None:
            print(f"  could not read {fname}, skipped")
            continue
        landmarks, mask = est.analyze(img)
        ratios = est.compute_ratios(landmarks, mask) if landmarks is not None else None
        ok = ratios is not None and ratios.waist_measured
        measured.append((truth, ratios if ok else None))
        if ok:
            print(f"  {fname:28s} true={truth:18s} shoulder/hip={ratios.shoulder_to_hip:.2f} "
                  f"waist/hip={ratios.waist_width / ratios.hip_width:.2f}")
        else:
            print(f"  {fname:28s} true={truth:18s} -> could not measure (stand fully in view, arms slightly out)")

    def predict(tol, wr):
        return [(t, BodyShapeEstimator.classify(r, tol, wr) if r else None) for t, r in measured]

    print_report(predict(SHOULDER_HIP_TOLERANCE, WAIST_DEFINED_RATIO),
                 f"Current thresholds (tolerance {SHOULDER_HIP_TOLERANCE}, waist ratio {WAIST_DEFINED_RATIO})")
    if args.tune:
        best = max(((sum(t == p for t, p in predict(tol, wr)), tol, wr)
                    for tol, wr in itertools.product([0.04, 0.05, 0.07, 0.09, 0.12, 0.15],
                                                     [0.70, 0.75, 0.80, 0.85, 0.90])), key=lambda x: x[0])
        print(f"\nBest on this set: tolerance {best[1]}, waist ratio {best[2]} -> {best[0]}/{len(measured)} correct")
        print("With a small set this can over-fit. Report both numbers and keep a few photos aside to confirm.")


if __name__ == "__main__":
    main()
