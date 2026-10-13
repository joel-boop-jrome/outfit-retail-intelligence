"""Frame-to-frame smoothing for live body-shape predictions (no CV deps)."""
from collections import Counter, deque
from typing import Optional


class ShapeSmoother:
    """Majority vote over the last `window` per-frame predictions.

    A single webcam frame is noisy (arms move, pose jitters), so the label
    shown to the user is the most common one over recent frames. `None`
    frames (no person found) are ignored for the vote but, after
    `patience` consecutive misses, the smoothed label is cleared.
    """

    def __init__(self, window: int = 15, patience: int = 30):
        self.window = window
        self.patience = patience
        self._votes: deque = deque(maxlen=window)
        self._misses = 0

    def update(self, label: Optional[str]) -> Optional[str]:
        if label is None:
            self._misses += 1
            if self._misses >= self.patience:
                self._votes.clear()
            return self.current
        self._misses = 0
        self._votes.append(label)
        return self.current

    @property
    def current(self) -> Optional[str]:
        if not self._votes:
            return None
        return Counter(self._votes).most_common(1)[0][0]
