import asyncio
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .table_manager import TableManager
from .vision import VisionService

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "tables.json"

occupy_seconds = float(os.getenv("RESTO_OCCUPY_SECONDS", "2"))
vacate_seconds = float(os.getenv("RESTO_VACATE_SECONDS", "5"))

table_manager = TableManager(CONFIG_PATH, occupy_seconds, vacate_seconds)
vision = VisionService(table_manager)

app = FastAPI(title="RESTO-VISION", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")


@app.on_event("startup")
def startup():
    vision.start()


@app.on_event("shutdown")
def shutdown():
    vision.stop()


@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "frontend" / "index.html").read_text(encoding="utf-8")


@app.get("/api/state")
def get_state():
    tables = table_manager.snapshot()
    occupied = [t for t in tables if t["occupied"]]
    total_people = sum(t["people_count"] for t in tables)
    average = (
        sum(t["occupied_seconds"] for t in occupied) / len(occupied)
        if occupied else 0
    )
    return {
        "tables": tables,
        "summary": {
            "total_tables": len(tables),
            "occupied_tables": len(occupied),
            "free_tables": len(tables) - len(occupied),
            "people_detected": total_people,
            "average_occupancy_seconds": int(average),
        },
        "camera": vision.status(),
    }


@app.get("/api/camera/status")
def camera_status():
    return vision.status()


@app.get("/api/video")
def video():
    async def stream():
        while True:
            frame = vision.get_jpeg()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(0.04)
    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/health")
def health():
    return JSONResponse({"ok": True, "service": "RESTO-VISION"})
