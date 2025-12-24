from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from multiprocessing import Queue, Process
from pathlib import Path
import random
import subprocess
import json
import argparse
import sys

from state import State
from writer import writer_loop
from logic import evaluate
from utils import parse_compact_categories
from auth import AuthManager

# Parse arguments
def parse_args():
    parser = argparse.ArgumentParser(description="FRVM - Filtered Random Video Mosaic")
    parser.add_argument("--data", type=str, default="/data", help="Path to data directory")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    # Handle both direct execution and uvicorn import
    # Filter out uvicorn args to avoid conflicts
    known_args, _ = parser.parse_known_args()
    return known_args

args = parse_args()

# Set paths
DATA_DIR = Path(args.data)
FRONTEND_DIR = Path(__file__).parent / "frontend"
CONFIG_FILE = DATA_DIR / "config.json"

# Orientation subfolders
ORIENTATIONS = ["square", "landscape", "portrait"]

# Load config
def load_config() -> dict:
    """Load config from data folder or return defaults."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {
        "title": "FRVM",
        "primaryColor": "#ff69b4",
        "backgroundColor": "#000000",
        "auth": {
            "jwtSecret": "default_secret_please_change",
            "tokenExpireHours": 24,
            "users": {}
        },
        "grid": {
            "landscape": [
                {"cols": 1, "rows": 1}, None, {"cols": 4, "rows": 1},
                {"cols": 2, "rows": 1}, None, {"cols": 2, "rows": 2},
                {"cols": 3, "rows": 1}, None, {"cols": 3, "rows": 3}
            ],
            "portrait": [
                {"cols": 1, "rows": 1}, {"cols": 1, "rows": 2}, {"cols": 1, "rows": 3},
                None, None, None,
                {"cols": 1, "rows": 4}, {"cols": 1, "rows": 5}, {"cols": 2, "rows": 2}
            ]
        }
    }

config = load_config()
auth_manager = AuthManager(config)

# Base path for reverse proxy setups (e.g., "/myapp" if behind nginx at domain.com/myapp/)
BASE_PATH = config.get("basePath", "")

app = FastAPI()
queue = Queue()


def iter_all_videos():
    """Iterate over all video files in all orientation subfolders."""
    for orientation in ORIENTATIONS:
        folder = DATA_DIR / orientation
        if folder.exists():
            for video_file in folder.glob("*.mp4"):
                yield orientation, video_file


# Load state from .txt files (scanning all orientation subfolders)
state = State()
for orientation, video_file in iter_all_videos():
    # video_id includes orientation prefix: "landscape/video.mp4"
    video_id = f"{orientation}/{video_file.name}"
    state.add_video(video_id)
    txt_file = video_file.with_suffix(".txt")
    if txt_file.exists():
        text = txt_file.read_text(encoding="utf-8")
        if text.strip():
            cats = parse_compact_categories(text)
            for emoji, val in cats.items():
                state.add_category(emoji)
                state.extend_category(emoji)
                idx = state.video_index[video_id]
                state.categories[emoji]["yes"][idx] = (val == "YES")
                state.categories[emoji]["no"][idx] = (val == "NO")

# Start writer process (writes to .txt files)
writer = Process(target=writer_loop, args=(state, queue, DATA_DIR))
writer.start()


# ---------------- Auth Endpoints ----------------

@app.post("/api/login")
async def login(request: Request):
    """Authenticate user and return JWT token."""
    try:
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
    except:
        raise HTTPException(status_code=400, detail="Invalid request body")
    
    result = auth_manager.authenticate(username, password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    response = JSONResponse(content=result)
    # Set cookie for browser-based auth
    response.set_cookie(
        key="auth_token",
        value=result["token"],
        max_age=result["expiresIn"],
        httponly=True,
        samesite="strict"
    )
    return response


@app.post("/api/guest")
async def login_as_guest():
    """Login as guest (no password required)."""
    result = auth_manager.create_guest_token()
    if not result:
        raise HTTPException(status_code=403, detail="Guest access is disabled")
    
    response = JSONResponse(content=result)
    response.set_cookie(
        key="auth_token",
        value=result["token"],
        max_age=result["expiresIn"],
        httponly=True,
        samesite="strict"
    )
    return response


@app.post("/api/logout")
async def logout():
    """Clear auth cookie."""
    response = JSONResponse(content={"ok": True})
    response.delete_cookie("auth_token")
    return response


@app.get("/api/me")
async def get_current_user(request: Request):
    """Get current user info from token."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "username": user["sub"],
        "role": user["role"],
        "filter": user.get("filter")
    }


# ---------------- Category Endpoints ----------------

@app.get("/categories")
async def list_categories(request: Request):
    """Get list of all existing categories."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return list(state.categories.keys())


@app.post("/video/{video_id:path}/categories")
async def update_video_categories(video_id: str, categories: dict[str, str], request: Request):
    """Update categories for a video (admin only)."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit categories")
    
    # Update state in main process (for immediate reads)
    if video_id not in state.video_index:
        return {"error": "Video not found"}
    idx = state.video_index[video_id]
    
    for emoji, val in categories.items():
        # Ensure category exists
        state.add_category(emoji)
        state.extend_category(emoji)
        
        cat = state.categories[emoji]
        cat["yes"][idx] = (val == "YES")
        cat["no"][idx] = (val == "NO")
        
        # Also send to writer for persistence
        queue.put({
            "type": "SET",
            "video_id": video_id,
            "category": emoji,
            "state": val
        })
    
    queue.put({"type": "SNAPSHOT"})
    return {"ok": True}


@app.get("/video/{video_id:path}/categories")
async def get_video_categories(video_id: str, request: Request):
    """Get current categories for a video."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if video_id not in state.video_index:
        return {"error": "Video not found"}
    idx = state.video_index[video_id]
    result = {}
    for emoji, cat in state.categories.items():
        if cat["yes"][idx]:
            result[emoji] = "YES"
        elif cat["no"][idx]:
            result[emoji] = "NO"
    return result


# ---------------- Video Serving ----------------

# Mount data folder for static serving
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


def generate_thumbnail(video_path: Path, thumb_path: Path):
    """Generate a thumbnail from the first frame of a video."""
    try:
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "4",
            str(thumb_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Thumbnail generation failed for {video_path.name}: {e}")


def get_video_categories_dict(video_id: str) -> dict:
    """Get categories for a video as {emoji: "YES"|"NO"}."""
    if video_id not in state.video_index:
        return {}
    idx = state.video_index[video_id]
    result = {}
    for emoji, cat in state.categories.items():
        if cat["yes"][idx]:
            result[emoji] = "YES"
        elif cat["no"][idx]:
            result[emoji] = "NO"
    return result


@app.get("/api/videos")
async def get_video_playlist(
    request: Request,
    orientation: str = Query(None, description="Filter by orientation: square, landscape, portrait"),
    expr: str = Query(None, description="Boolean expression to filter by categories"),
    limit: int = 10
):
    """Get a random playlist of videos with thumbnails."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    all_categories = list(state.categories.keys())
    
    # Apply guest filter if present
    user_filter = user.get("filter")
    if user_filter:
        expr = f"({user_filter}).({expr})" if expr else user_filter
    
    # If expression provided, filter by categories first
    if expr:
        bits = evaluate(expr, state.categories)
        matching_ids = [state.index_video[i] for i, b in enumerate(bits) if b]
        
        # Filter by orientation if specified
        if orientation and orientation in ORIENTATIONS:
            matching_ids = [vid for vid in matching_ids if vid.startswith(f"{orientation}/")]
        
        if not matching_ids:
            return {"categories": all_categories, "videos": []}
        
        selected_ids = random.sample(matching_ids, min(limit, len(matching_ids)))
        
        videos = []
        for video_id in selected_ids:
            video_path = DATA_DIR / video_id
            
            video_url = f"{BASE_PATH}/data/{video_id}"
            thumb_file = video_path.with_suffix(".jpg")
            thumb_url = f"{BASE_PATH}/data/{video_id}".replace(".mp4", ".jpg")
            
            if not thumb_file.exists():
                generate_thumbnail(video_path, thumb_file)
            
            videos.append({
                "id": video_id,
                "url": video_url,
                "poster": thumb_url if thumb_file.exists() else None,
                "cats": get_video_categories_dict(video_id)
            })
        
        return {"categories": all_categories, "videos": videos}
    
    # No expression: collect video files based on orientation filter only
    video_files = []
    
    if orientation and orientation in ORIENTATIONS:
        folder = DATA_DIR / orientation
        if folder.exists():
            video_files = list(folder.glob("*.mp4"))
    else:
        for ori in ORIENTATIONS:
            folder = DATA_DIR / ori
            if folder.exists():
                video_files.extend(folder.glob("*.mp4"))
    
    if not video_files:
        return {"categories": all_categories, "videos": []}

    selected = random.sample(video_files, min(limit, len(video_files)))

    videos = []
    for file in selected:
        ori = file.parent.name if file.parent.name in ORIENTATIONS else ""
        video_id = f"{ori}/{file.name}" if ori else file.name
        video_url = f"{BASE_PATH}/data/{ori}/{file.name}" if ori else f"{BASE_PATH}/data/{file.name}"
        thumb_file = file.with_suffix(".jpg")
        thumb_url = f"{BASE_PATH}/data/{ori}/{file.stem}.jpg" if ori else f"{BASE_PATH}/data/{file.stem}.jpg"

        if not thumb_file.exists():
            generate_thumbnail(file, thumb_file)

        videos.append({
            "id": video_id,
            "url": video_url,
            "poster": thumb_url if thumb_file.exists() else None,
            "cats": get_video_categories_dict(video_id)
        })

    return {"categories": all_categories, "videos": videos}


# ---------------- Config ----------------

@app.get("/api/search/count")
async def search_count(request: Request, expr: str = Query("", description="Boolean expression")):
    """Count videos matching expression by orientation."""
    user = auth_manager.get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Apply guest filter if present
    user_filter = user.get("filter")
    if user_filter:
        expr = f"({user_filter}).({expr})" if expr else user_filter
    
    # Get matching video IDs
    if expr:
        try:
            bits = evaluate(expr, state.categories)
            matching_ids = [state.index_video[i] for i, b in enumerate(bits) if b]
        except Exception:
            matching_ids = []
    else:
        matching_ids = list(state.video_index.keys())
    
    # Count by orientation
    counts = {"portrait": 0, "square": 0, "landscape": 0, "total": 0}
    for vid in matching_ids:
        for ori in ORIENTATIONS:
            if vid.startswith(f"{ori}/"):
                counts[ori] += 1
                break
        counts["total"] += 1
    
    return counts


@app.get("/api/config")
def get_config():
    """Get public UI config (no auth required for login page)."""
    auth_config = config.get("auth", {})
    guest_config = auth_config.get("guest", {})
    
    # Merge config categories (with tooltips) with actual state categories
    config_categories = config.get("categories", {})
    all_cats = list(state.categories.keys())
    categories_with_tooltips = {cat: config_categories.get(cat, "") for cat in all_cats}
    
    return {
        "title": config.get("title", "FRVM"),
        "primaryColor": config.get("primaryColor", "#ff69b4"),
        "backgroundColor": config.get("backgroundColor", "#000000"),
        "backgrounds": config.get("backgrounds", {
            "landscape": "/data/landscape/background.jpg",
            "portrait": "/data/portrait/background.jpg"
        }),
        "guestEnabled": guest_config.get("enabled", False),
        "categories": categories_with_tooltips,
        "presets": config.get("presets", {}),
        "grid": config.get("grid", {}),
        "basePath": BASE_PATH
    }


# ---------------- Frontend Serving ----------------

# Serve static frontend files (JS, CSS, images)
static_dir = FRONTEND_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/view")
def serve_player():
    return FileResponse(FRONTEND_DIR / "player.html")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting FRVM server...")
    print(f"  Data directory: {DATA_DIR}")
    print(f"  Frontend directory: {FRONTEND_DIR}")
    print(f"  Listening on: {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)