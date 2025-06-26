# src/QuPRS/pathsum/statistics.py


class StatisticsManager:
    """
    Manages and tracks statistics for pathsum reduction rules.
    This class encapsulates the state and logic for statistical tracking.
    """

    def __init__(self):
        self.reset_reduction_counts()
        self._reduction_enabled = True

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"reduction_counts={self._reduction_counts}, "
            f"hitrate={self.get_reduction_hitrate()})"
        )

    def get_reduction_counts(self) -> dict:
        """Get a copy of all reduction rule counts."""
        return self._reduction_counts.copy()

    def get_reduction_count(self, key: str) -> int:
        """Get the count for a specific reduction rule."""
        return self._reduction_counts.get(key, 0)

    def increment_reduction_count(self, key: str, value: int = 1):
        """Increase the count for a specific reduction rule."""
        if key in self._reduction_counts:
            self._reduction_counts[key] += value

    def get_reduction_hitrate(self) -> float:
        """Calculate the hit rate of reduction rules."""
        total = self._reduction_counts["total"]
        if total == 0:
            return 0.0
        else:
            hit = (
                self._reduction_counts["Elim"]
                + self._reduction_counts["HH"]
                + self._reduction_counts["omega"]
            )
            return hit / total

    def reset_reduction_counts(self):
        """Reset all reduction rule counts to 0."""
        self._reduction_counts = {
            "total": 0,
            "Elim": 0,
            "HH": 0,
            "omega": 0,
        }

    def set_reduction_switch(self, value: bool) -> None:
        """Set the global switch for reduction functionality."""
        self._reduction_enabled = value

    def is_reduction_enabled(self) -> bool:
        """Check if reduction functionality is enabled."""
        return self._reduction_enabled
