
"""Configuration for FSI match replay."""

import math
import os
from dataclasses import dataclass

from config.paths import ROOT


@dataclass(frozen=True)
class ReplayConfig:
    """Control the playback rate of prepared match records."""

    speed: float = float(os.getenv("FSI_REPLAY_SPEED", "1.0"))

    def __post_init__(self):
        if not math.isfinite(self.speed) or self.speed <= 0:
            raise ValueError("Replay speed must be finite and positive")
