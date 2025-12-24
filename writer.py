import os
from pathlib import Path


def export_video_txt(state, video_id: str, videos_dir: Path):
    """Write categories to .txt file for a single video."""
    idx = state.video_index[video_id]
    parts = []
    for emoji, cat in state.categories.items():
        if cat["yes"][idx]:
            parts.append(f"+{emoji}")
        elif cat["no"][idx]:
            parts.append(f"-{emoji}")
    
    # video_id can include subfolder (e.g., "landscape/video.mp4")
    video_path = videos_dir / video_id
    txt_path = video_path.with_suffix(".txt")
    tmp = txt_path.with_suffix(".txt.tmp")
    
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(parts))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, txt_path)


def writer_loop(state, queue, videos_dir: Path):
    """Background process that handles state updates and writes to .txt files."""
    pending_videos = set()  # Videos modified since last snapshot
    
    while True:
        cmd = queue.get()

        if cmd["type"] == "SET":
            video_id = cmd["video_id"]
            idx = state.video_index[video_id]
            emoji = cmd["category"]
            state.add_category(emoji)
            state.extend_category(emoji)

            cat = state.categories[emoji]
            cat["yes"][idx] = cmd["state"] == "YES"
            cat["no"][idx] = cmd["state"] == "NO"
            
            pending_videos.add(video_id)

        elif cmd["type"] == "SNAPSHOT":
            # Write .txt files for all modified videos
            for video_id in pending_videos:
                export_video_txt(state, video_id, videos_dir)
            pending_videos.clear()
