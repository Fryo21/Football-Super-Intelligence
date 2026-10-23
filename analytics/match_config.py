
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class MatchConfig:
    """Define pitch dimensions and spatial analysis settings."""

    pitch_length: float = 105.0
    pitch_width: float = 68.0
    pressure_radius: float = 3.0

    def __post_init__(self):
        """Ensure all match settings are finite and positive."""

        values = (
            self.pitch_length,
            self.pitch_width,
            self.pressure_radius,
        )

        if not all(isfinite(value) and value > 0 for value in values):
            raise ValueError(
                "Match configuration values must be finite and positive"
            )
