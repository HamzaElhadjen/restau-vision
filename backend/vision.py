import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from .table_manager import TableManager


class VisionService:
    def __init__(self, table_manager: TableManager):
        self.table_manager = table_manager
        self.camera_index = int(os.getenv("RESTO_CAMERA_INDEX", "0"))
        self.model_name = os.getenv("RESTO_MODEL", "yolo11n.pt")
        self.confidence = float(os.getenv("RESTO_CONFIDENCE", "0.35"))
        self.width = int(os.getenv("RESTO_CAMERA_WIDTH", "1280"))
        self.height = int(os.getenv("RESTO_CAMERA_HEIGHT", "720"))
        self.capture = None
        self.model = None
        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        self.latest_jpeg = None
        self.camera_ok = False
        self.model_ok = False
        self.last_error = None
        self.fps = 0.0
        self.last_frame_at = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        if self.capture:
            self.capture.release()

    def _open_camera(self):
        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(
                f"Impossible d'ouvrir la webcam (index {self.camera_index}). "
                "Fermez les autres applications utilisant la caméra ou essayez RESTO_CAMERA_INDEX=1."
            )
        return cap

    def _run(self):
        try:
            self.model = YOLO(self.model_name)
            self.model_ok = True
            self.capture = self._open_camera()
            self.camera_ok = True
            previous = time.time()

            while self.running:
                ok, frame = self.capture.read()
                if not ok:
                    self.camera_ok = False
                    self.last_error = "La webcam ne fournit plus d'image."
                    time.sleep(0.3)
                    continue

                h, w = frame.shape[:2]
                points = []
                try:
                    results = self.model.track(
                        frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=[0],
                        conf=self.confidence,
                        verbose=False,
                    )
                    result = results[0]
                    if result.boxes is not None:
                        boxes = result.boxes
                        xyxy = boxes.xyxy.cpu().numpy()
                        ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(xyxy)
                        for box, track_id in zip(xyxy, ids):
                            x1, y1, x2, y2 = box
                            # Point d'ancrage au niveau des pieds, plus utile que le centre du torse.
                            px = float((x1 + x2) / 2 / w)
                            py = float(min(y2 / h, 0.999))
                            points.append((px, py, track_id))
                except Exception as exc:
                    self.last_error = f"Erreur de détection : {exc}"

                self.table_manager.update(points)
                annotated = self._draw(frame, results[0] if "results" in locals() else None, w, h)
                now = time.time()
                elapsed = max(now - previous, 1e-6)
                self.fps = 0.9 * self.fps + 0.1 * (1 / elapsed) if self.fps else 1 / elapsed
                previous = now
                self.last_frame_at = now

                encoded_ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if encoded_ok:
                    with self.lock:
                        self.latest_jpeg = encoded.tobytes()
                self.camera_ok = True
                self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            self.camera_ok = False
        finally:
            if self.capture:
                self.capture.release()
            self.running = False

    def _draw(self, frame, result, width, height):
        output = frame.copy()
        tables = self.table_manager.snapshot()
        for table in tables:
            polygon = np.array(
                [[int(x * width), int(y * height)] for x, y in table["polygon"]],
                dtype=np.int32,
            )
            color = (65, 190, 120) if table["occupied"] else (210, 170, 70)
            overlay = output.copy()
            cv2.fillPoly(overlay, [polygon], color)
            output = cv2.addWeighted(overlay, 0.12, output, 0.88, 0)
            cv2.polylines(output, [polygon], True, color, 2)
            x, y = polygon[0]
            label = f'{table["id"]} | {table["people_count"]} pers.'
            cv2.rectangle(output, (x, max(0, y - 28)), (x + 175, y), color, -1)
            cv2.putText(output, label, (x + 7, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (15, 20, 25), 2)

        if result is not None and result.boxes is not None:
            for box in result.boxes.xyxy.cpu().numpy():
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(output, (x1, y1), (x2, y2), (80, 210, 255), 2)
                cv2.putText(output, "PERSON", (x1, max(18, y1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 210, 255), 1)
        return output

    def get_jpeg(self):
        with self.lock:
            return self.latest_jpeg

    def status(self):
        return {
            "running": self.running,
            "camera_ok": self.camera_ok,
            "model_ok": self.model_ok,
            "camera_index": self.camera_index,
            "model": self.model_name,
            "fps": round(self.fps, 1),
            "last_error": self.last_error,
        }
