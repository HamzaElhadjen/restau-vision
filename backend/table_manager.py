import json
import time
from pathlib import Path
from threading import Lock


class TableManager:
    """Associe les détections aux zones et gère les états avec temporisation."""

    def __init__(self, config_path: Path, occupy_seconds: float = 2.0, vacate_seconds: float = 5.0):
        self.config_path = config_path
        self.occupy_seconds = occupy_seconds
        self.vacate_seconds = vacate_seconds
        self.lock = Lock()
        self.tables = {}
        self._load_config()

    def _load_config(self):
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        now = time.time()
        with self.lock:
            self.tables = {}
            for item in data.get("tables", []):
                self.tables[item["id"]] = {
                    "id": item["id"],
                    "name": item.get("name", item["id"]),
                    "polygon": item["polygon"],
                    "occupied": False,
                    "people_count": 0,
                    "started_at": None,
                    "occupied_seconds": 0,
                    "candidate_since": None,
                    "last_seen": now,
                }

    @staticmethod
    def _inside_polygon(point, polygon):
        # Algorithme ray-casting, coordonnées normalisées.
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    def update(self, people_points):
        """people_points: liste de (x_norm, y_norm, track_id)."""
        now = time.time()
        counts = {table_id: set() for table_id in self.tables}
        for x, y, track_id in people_points:
            for table_id, table in self.tables.items():
                if self._inside_polygon((x, y), table["polygon"]):
                    counts[table_id].add(track_id if track_id is not None else f"{x:.3f}-{y:.3f}")
                    break

        with self.lock:
            for table_id, table in self.tables.items():
                count = len(counts[table_id])
                table["people_count"] = count
                desired_occupied = count > 0

                if desired_occupied == table["occupied"]:
                    table["candidate_since"] = None
                else:
                    if table["candidate_since"] is None:
                        table["candidate_since"] = now
                    delay = self.occupy_seconds if desired_occupied else self.vacate_seconds
                    if now - table["candidate_since"] >= delay:
                        table["occupied"] = desired_occupied
                        table["candidate_since"] = None
                        if desired_occupied:
                            table["started_at"] = now
                            table["occupied_seconds"] = 0
                        else:
                            if table["started_at"] is not None:
                                table["occupied_seconds"] = int(now - table["started_at"])
                            table["started_at"] = None

                if table["occupied"] and table["started_at"] is not None:
                    table["occupied_seconds"] = int(now - table["started_at"])
                table["last_seen"] = now

    def snapshot(self):
        with self.lock:
            result = []
            for t in self.tables.values():
                result.append({
                    "id": t["id"],
                    "name": t["name"],
                    "occupied": t["occupied"],
                    "people_count": t["people_count"],
                    "occupied_seconds": t["occupied_seconds"],
                    "started_at": t["started_at"],
                    "polygon": t["polygon"],
                    "status": "OCCUPIED" if t["occupied"] else "FREE",
                })
            return result
