from bitarray import bitarray

class State:
    def __init__(self):
        self.video_index = {}  # video_id -> idx
        self.index_video = []  # idx -> video_id
        self.categories = {}   # emoji -> {"yes": bitarray, "no": bitarray}
        self.performers = {}   # performer_name -> bitarray (1 = video has this performer)
        self.performer_info = {}  # performer_name -> {"urls": [...], "avatar": "/data/performers/X.jpg" or None}

    def add_video(self, video_id: str):
        if video_id in self.video_index:
            return
        idx = len(self.index_video)
        self.video_index[video_id] = idx
        self.index_video.append(video_id)
        for cat in self.categories.values():
            cat["yes"].append(0)
            cat["no"].append(0)
        for bits in self.performers.values():
            bits.append(0)

    def add_category(self, emoji: str):
        n = len(self.index_video)
        if emoji not in self.categories:
            self.categories[emoji] = {
                "yes": bitarray("0") * n,
                "no": bitarray("0") * n
            }

    def extend_category(self, emoji: str):
        """Extend bitarrays if the number of videos has increased."""
        n = len(self.index_video)
        cat = self.categories[emoji]
        if len(cat["yes"]) < n:
            cat["yes"].extend([0] * (n - len(cat["yes"])))
            cat["no"].extend([0] * (n - len(cat["no"])))

    def add_performer(self, name: str):
        """Register a performer (from performers/ folder). Creates bitarray if new."""
        n = len(self.index_video)
        if name not in self.performers:
            self.performers[name] = bitarray("0") * n
        if name not in self.performer_info:
            self.performer_info[name] = {"urls": [], "avatar": None}

    def extend_performer(self, name: str):
        """Extend performer bitarray if videos have been added."""
        n = len(self.index_video)
        bits = self.performers[name]
        if len(bits) < n:
            bits.extend([0] * (n - len(bits)))

    def get_video_performers(self, video_id: str) -> list[str]:
        """Get list of performer names associated with a video."""
        if video_id not in self.video_index:
            return []
        idx = self.video_index[video_id]
        return [name for name, bits in self.performers.items() if bits[idx]]
