# FRVM - Filtered Random Video Mosaic

A fast video categorization and search application using emoji tags, boolean expressions, and swipe gestures.

## Features

- **Emoji-based categorization**: Tag videos with any emoji
- **Tri-state logic**: Each category can be `+` (yes), `-` (no), or unset
- **Boolean search**: Query videos using electronic logic syntax (`!`, `.`, `+`, `?`, `()`)
- **Bitarray storage**: Efficient in-memory storage and blazing fast queries
- **Swipe gestures**: Navigate videos with touch/mouse gestures
- **JWT Authentication**: Three roles (guest, user, admin) with different permissions
- **Role-based backgrounds**: Different wallpapers per user role and orientation
- **Filter presets**: Quick-access named filters
- **Live video counter**: Real-time count of matching videos while typing filter
- **Persistent state**: Categories stored in `.txt` files alongside videos
- **Auto thumbnails**: Thumbnails generated automatically on first request

## Quick Start

### With Docker/Podman

```bash
# Build
podman build -t frvm:latest .

# Run (mount data folder containing videos and config)
podman run -d --name myvideos -p 8000:8000 \
  -v /path/to/your/data:/data:Z \
  frvm:latest
```

### Data Folder Structure

```
/data/
├── config.json           # Application configuration
├── landscape/            # Landscape videos (16:9)
│   ├── video1.mp4
│   ├── video1.txt        # Categories for video1
│   ├── video1.jpg        # Auto-generated thumbnail
│   ├── background.jpg    # Background for user/admin
│   └── background_guest.jpg  # Background for guest
├── portrait/             # Portrait videos (9:16)
│   └── ...
└── square/               # Square videos (1:1)
    └── ...
```

### Local Development

There are several ways to run the app locally:

#### Option 1: Direct Python (fastest for development)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run with your data folder
python main.py --data=/path/to/your/data

# Or with sample data
python main.py --data=./sample_app_data

# Custom port
python main.py --data=./sample_app_data --port=8080
```

#### Option 2: Uvicorn with hot-reload

```bash
source .venv/bin/activate
uvicorn main:app --reload --data=./sample_app_data
```

> **Note**: Arguments `--data` and `--port` are passed through to the app even with uvicorn.

#### Option 3: Podman/Docker (production-like)

```bash
# Build image
podman build -t frvm:latest .

# Run with local data folder
podman run -d --name frvm -p 8000:8000 \
  -v ./sample_app_data:/data:Z \
  frvm:latest
```

### Try with Sample Data

A `sample_app_data/` folder is included with demo videos to test the app:

```bash
# Build and run with sample data
podman build -t frvm:latest .
podman run -d --name frvm -p 8000:8000 \
  -v ./sample_app_data:/data:Z \
  frvm:latest
```

Then open http://localhost:8000 and login:
- **user** / `user_FRVM` (view only)
- **admin** / `admin_FRVM` (can edit categories)
- Or click "Guest" (filtered view, no 💧 water videos)

### Multiple Instances

You can run multiple servers with different data folders on different ports:

```bash
podman run -d --name frvm -p 8000:8000 -v ./sample_app_data:/data:Z frvm:latest
podman run -d --name myproject -p 8001:8000 -v /path/to/other/data:/data:Z frvm:latest
```

## Configuration (config.json)

```json
{
  "title": "Filtered Random Video Mosaic",
  "primaryColor": "#b069A4",
  "basePath": "",
  
  "backgrounds": {
    "guest": {
      "landscape": "/data/landscape/background_guest.jpg",
      "portrait": "/data/portrait/background_guest.jpg"
    },
    "user": {
      "landscape": "/data/landscape/background.jpg",
      "portrait": "/data/portrait/background.jpg"
    },
    "admin": {
      "landscape": "/data/landscape/background.jpg",
      "portrait": "/data/portrait/background.jpg"
    }
  },
  
  "categories": {
    "🐈": "Animals",
    "☀️": "Summer",
    "❄️": "Winter",
    "🏈": "Sport",
    "💧": "Water"
  },
  
  "presets": {
    "Winter Sports": "❄️.🏈",
    "no Animals": "!🐈"
  },
  
  "auth": {
    "jwtSecret": "YOUR_SECRET_KEY_HERE",
    "tokenExpireHours": 24,
    "guest": {
      "enabled": true,
      "filter": "!💧"
    },
    "users": {
      "admin": {
        "password": "admin123",
        "role": "admin",
        "filter": null
      }
    }
  }
}
```

## User Roles

| Role | View Videos | View Categories | Edit Categories | Filter Applied |
|------|-------------|-----------------|-----------------|----------------|
| guest | ✓ | ✓ | ✗ | Forced filter |
| user | ✓ | ✓ | ✗ | None |
| admin | ✓ | ✓ | ✓ | None |

## Category File Format

Each video can have a `.txt` file with the same name:

```
+🥗+🐈-👎
```

- `+emoji` = video HAS this category
- `-emoji` = video does NOT have this category
- (absent) = not evaluated yet

## Boolean Search Syntax

| Operator | Meaning | Example |
|----------|---------|--------|
| `!` | NOT (explicitly no) | `!🔞` |
| `?` | UNSET (not tagged) | `?🔞` |
| `.` | AND | `🥗.🐈` |
| (concat) | AND (implicit) | `🥗🐈` |
| `+` | OR | `🥗+🐈` |
| `()` | Grouping | `(🥗+🔥).💃` |

### Examples

```
🥗           → videos tagged with 🥗
!🥗          → videos explicitly marked as NOT having 🥗
?🥗          → videos where 🥗 is not yet tagged
🥗.🐈        → videos with both 🥗 AND 🐈
🥗+🐈        → videos with 🥗 OR 🐈
🥗.!👎       → videos with 🥗 and explicitly without 👎
(🥗+🔥).💃   → (🥗 OR 🔥) AND 💃
```

## Swipe Gestures (Player)

| Gesture | Action | Emoji |
|---------|--------|-------|
| Swipe ↑ Up | Next video | ⏭️ |
| Swipe ↓ Down | Toggle categories panel | - |
| Swipe ← Left | Restart video | ⏮️ → ▶️ |
| Swipe → Right | Fast forward (2x) | ⏩ → ▶️ |
| Swipe ↗️ ↖️ Up-diagonal | Toggle mute | 🔇 / 🔊 |
| Swipe ↘️ ↙️ Down-diagonal | Toggle cover/contain | 📺 / 🖼️ |

**Video fit modes:**
- 📺 `cover` = Fill screen (may crop edges)
- 🖼️ `contain` = Show entire video (may have black bars)

## Filter Panel

- **Left click** on emoji: Insert emoji
- **Right click** on emoji: Insert `!emoji` (NOT)
- **Preset buttons**: Quick-apply named filters
- **Live counter**: Shows matching videos per orientation

## API Endpoints

### Authentication

```
POST /api/login     → Login with username/password
POST /api/guest     → Login as guest
POST /api/logout    → Logout
GET  /api/me        → Get current user info
```

### Videos

```
GET /api/videos?orientation=portrait&expr=🥗&limit=10
GET /api/search/count?expr=🥗   → Count by orientation
GET /api/config                  → Public config
```

### Categories

```
GET  /categories                        → List all categories
GET  /video/{video_id}/categories       → Get video categories
POST /video/{video_id}/categories       → Update (admin only)
     Body: {"🥗": "YES", "👎": "NO", "🔥": "UNSET"}
```

## Reverse Proxy Setup (nginx)

The app supports deployment behind a reverse proxy at either a subdomain or a subpath.

### Option 1: Subdomain (recommended)

No `basePath` needed. Just proxy to the container:

```nginx
server {
    server_name videos.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Subpath

Set `basePath` in config.json and configure nginx to strip the prefix:

**config.json:**
```json
{
  "basePath": "/myvideos",
  ...
}
```

**nginx:**
```nginx
server {
    server_name example.com;
    
    location /myvideos/ {
        rewrite ^/myvideos(.*)$ $1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

With this setup, the app will be accessible at `https://example.com/myvideos/`

## Batch Category Assignment

If your videos are already organized in folders by category, you can use `prepare_cat.sh` to quickly assign categories in batch. It supports glob patterns for flexible file selection.

```bash
# Assign categories to all videos in a folder
./prepare_cat.sh ./data/landscape "+🏖️+☀️"

# Only files starting with "beach"
./prepare_cat.sh ./data/landscape/beach* "+🏖️+☀️"

# Only files containing "2024"
./prepare_cat.sh "./data/landscape/*2024*" "+📅"

# Overwrite existing category files
./prepare_cat.sh --replace ./data/landscape "+🏖️+☀️"

# Append categories to existing files
./prepare_cat.sh --append ./data/landscape "+🔥"
```

**Options:**
| Option | Behavior |
|--------|----------|
| (none) | Skip videos that already have a `.txt` file |
| `--replace` | Overwrite existing `.txt` files |
| `--append` | Append categories to existing `.txt` files |

**Glob patterns:**
| Pattern | Matches |
|---------|--------|
| `./folder` | All `.mp4` files in folder |
| `./folder/beach*` | Files starting with "beach" |
| `./folder/*2024*` | Files containing "2024" |
| `./folder/*.mp4` | Explicit `.mp4` extension |

> **Note:** If no extension is specified, `.mp4` is automatically added.

**Example workflow** for migrating pre-sorted videos:

```bash
# Videos sorted by theme in subfolders
./prepare_cat.sh ./beach_videos "+🏖️+☀️"
./prepare_cat.sh ./winter_videos "+❄️+⛷️"
./prepare_cat.sh ./pets "+🐈"

# Then move all videos to the data folder
mv ./beach_videos/*.mp4 ./beach_videos/*.txt ./data/landscape/
mv ./winter_videos/*.mp4 ./winter_videos/*.txt ./data/landscape/
mv ./pets/*.mp4 ./pets/*.txt ./data/portrait/
```

## Architecture

```
main.py         FastAPI app + endpoints
auth.py         JWT authentication
state.py        Bitarray-based state storage
logic.py        Boolean expression parser
writer.py       Background process for .txt writes
utils.py        Category file parsing
frontend/
  index.html    Login + grid selector
  player.html   Video player with swipe gestures
```

## License

MIT
