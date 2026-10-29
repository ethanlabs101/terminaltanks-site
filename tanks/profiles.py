"""Up to three named save profiles in one game; profile 1 is the original save.json, so nothing ever needs migrating."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


PROFILE_MAX = 3


def fmt_playtime(sec: float) -> str:
    """12345678 s -> '142D 21H 21M'; shows years and months once they exist (365-day years, 30-day months)."""
    m = max(0, int(sec)) // 60
    y, m = divmod(m, 525600)
    mo, m = divmod(m, 43200)
    d, m = divmod(m, 1440)
    h, mi = divmod(m, 60)
    parts = []
    for val, lab in ((y, "Y"), (mo, "MO"), (d, "D"), (h, "H")):
        if parts or val:
            parts.append(f"{val}{lab}")
    parts.append(f"{mi:02d}M" if parts else f"{mi}M")
    return " ".join(parts)


class ProfileBook:
    def __init__(self, base: Optional[Path]) -> None:
        self.base = base
        self.index_path = base.parent / "profiles.json" if base is not None else None
        self.profiles: list[dict] = [{"id": "1", "name": "PROFILE 1", "file": base.name if base else ""}]
        self.active = "1"
        if self.index_path is not None and self.index_path.exists():
            try:
                raw = json.loads(self.index_path.read_text(encoding="utf-8"))
                profs = [p for p in raw.get("profiles", []) if isinstance(p, dict) and isinstance(p.get("id"), str)
                         and isinstance(p.get("file"), str) and "/" not in p["file"] and "\\" not in p["file"]]
                if profs:
                    self.profiles = [{"id": p["id"], "name": str(p.get("name", "PROFILE"))[:14] or "PROFILE", "file": p["file"]} for p in profs[:PROFILE_MAX]]
                    self.active = raw.get("active") if raw.get("active") in {p["id"] for p in self.profiles} else self.profiles[0]["id"]
            except (OSError, ValueError, AttributeError):
                pass

    def path_of(self, pid: str) -> Optional[Path]:
        p = next((q for q in self.profiles if q["id"] == pid), None)
        return self.base.parent / p["file"] if (p and self.base is not None) else None

    def active_path(self) -> Optional[Path]:
        return self.path_of(self.active)

    def write(self) -> None:
        if self.index_path is None:
            return
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.index_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"active": self.active, "profiles": self.profiles}, indent=1), encoding="utf-8")
            os.replace(tmp, self.index_path)
        except OSError:
            pass

    def create(self, name: str) -> Optional[str]:
        if len(self.profiles) >= PROFILE_MAX or self.base is None:
            return None
        pid = next(str(i) for i in range(1, 10) if str(i) not in {p["id"] for p in self.profiles})
        self.profiles.append({"id": pid, "name": (name.strip() or f"PROFILE {pid}")[:14], "file": f"save_profile{pid}.json"})
        self.write()
        return pid

    def rename(self, pid: str, name: str) -> None:
        for p in self.profiles:
            if p["id"] == pid and name.strip():
                p["name"] = name.strip()[:14]
        self.write()

    def delete(self, pid: str) -> bool:
        if len(self.profiles) <= 1:
            return False
        p = next((q for q in self.profiles if q["id"] == pid), None)
        if p is None:
            return False
        path = self.path_of(pid)
        self.profiles = [q for q in self.profiles if q["id"] != pid]
        if self.active == pid:
            self.active = self.profiles[0]["id"]
        self.write()
        try:
            if path is not None and path.exists() and path != self.base:      # the original save file is never deleted by accident
                path.unlink()
            elif path is not None and path == self.base and path.exists():
                path.rename(path.with_suffix(".deleted.json"))
        except OSError:
            pass
        return True
