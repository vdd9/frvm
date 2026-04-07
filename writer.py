import os
from pathlib import Path
from utils import format_performers_line


def export_video_txt(state, video_id: str, videos_dir: Path):
    """Write categories and performers to .txt file for a single video.
    Line 1: categories (+emoji-emoji)
    Line 2 (optional): performers (@Name1@Name2)
    """
    idx = state.video_index[video_id]
    
    # Line 1: categories
    cat_parts = []
    for emoji, cat in state.categories.items():
        if cat["yes"][idx]:
            cat_parts.append(f"+{emoji}")
        elif cat["no"][idx]:
            cat_parts.append(f"-{emoji}")
    
    # Line 2: performers
    perf_names = state.get_video_performers(video_id)
    perf_line = format_performers_line(perf_names)
    
    # Build content: categories on line 1, performers on line 2 if any
    content = "".join(cat_parts)
    if perf_line:
        content += "\n" + perf_line
    
    # video_id can include subfolder (e.g., "landscape/video.mp4")
    video_path = videos_dir / video_id
    txt_path = video_path.with_suffix(".txt")
    tmp = txt_path.with_suffix(".txt.tmp")
    
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
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

        elif cmd["type"] == "SET_PERFORMERS":
            video_id = cmd["video_id"]
            idx = state.video_index[video_id]
            performers = cmd["performers"]  # list of performer names
            
            # Clear all performer bits for this video, then set the new ones
            for name, bits in state.performers.items():
                bits[idx] = (name in performers)
            
            pending_videos.add(video_id)

        elif cmd["type"] == "SNAPSHOT":
            # Write .txt files for all modified videos
            for video_id in pending_videos:
                export_video_txt(state, video_id, videos_dir)
            pending_videos.clear()
