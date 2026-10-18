from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Problem:
    path: str
    severity: str
    check: str
    message: str

    def line(self) -> str:
        return f"{self.path}: {self.severity} {self.check}: {self.message}"

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "severity": self.severity, "check": self.check, "message": self.message}
