from collections import deque

class SequenceTrigger:
    """Six alternating presses in 2s qualify a group; <1s gaps extend it."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.events = deque(maxlen=6)
        self.pair = None
        self.qualified = False

    def feed(self, key, now):
        key = {0x61:49, 0x62:50, 0x63:51}.get(key, key)
        if key not in (49,50,51):
            self.reset()
            return False
        if self.events:
            previous, timestamp = self.events[-1]
            pair = frozenset((previous,key))
            if now - timestamp >= 1.0 or pair not in (frozenset((49,51)),frozenset((50,51))):
                self.reset()
            elif pair != self.pair:
                self.reset()
                self.events.append((previous,timestamp))
                self.pair = pair
        self.events.append((key,now))
        if len(self.events) == 6 and now - self.events[0][1] <= 2.0:
            self.qualified = True
        return self.qualified

class MusicPolicy:
    def __init__(self):
        self.stop()

    def stop(self):
        self.active = False
        self.last_valid = None

    def renew(self, now):
        start = not self.active
        self.active = True
        self.last_valid = now
        return start

    def gain(self, now):
        if not self.active:
            return 0.0
        elapsed = now - self.last_valid
        if elapsed >= 11.0:
            self.stop()
            return 0.0
        if elapsed <= 8.0:
            return 1.0
        # Smooth cosine fade over the next three seconds.
        import math
        return (1.0 + math.cos(math.pi * (elapsed - 8.0) / 3.0)) / 2.0
