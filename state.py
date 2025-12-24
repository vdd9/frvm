from bitarray import bitarray

class State:
    def __init__(self):
        self.video_index = {}  # video_id -> idx
        self.index_video = []  # idx -> video_id
        self.categories = {}   # emoji -> {"yes": bitarray, "no": bitarray}

    def add_video(self, video_id: str):
        if video_id in self.video_index:
            return
        idx = len(self.index_video)
        self.video_index[video_id] = idx
        self.index_video.append(video_id)
        for cat in self.categories.values():
            cat["yes"].append(0)
            cat["no"].append(0)

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
