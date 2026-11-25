"""Three released short Home presses; passive policy, never consumes input."""
class TripleHome:
    def __init__(self):
        self.down = None
        self.taps = []
        self.last = None
        self.fired = False
    def event(self, kind, code, value, now):
        if kind == 0 and code == 3:
            raise ValueError('Input events dropped')
        if self.fired or kind != 1:
            return False
        if self.last is not None and now < self.last:
            self.down = None; self.taps = []
        self.last = now
        # Firmware cursor-show notification is not a physical button press.
        # Observing it must not discard Home taps; input is never consumed.
        if code == 1198:
            return False
        if code != 773:
            if value: self.down = None; self.taps = []
            return False
        if value == 1:
            if self.down is not None: self.taps = []
            self.down = now
        elif value == 2:
            self.down = None; self.taps = []
        elif value == 0:
            start = self.down; self.down = None
            if start is None or not 40 <= now - start <= 500:
                self.taps = []; return False
            self.taps = [t for t in self.taps if now - t <= 2000]
            self.taps.append(start)
            if len(self.taps) == 3:
                self.fired = True
                return True
        else:
            raise ValueError('Invalid key value')
        return False


class LongBack:
    """One stock-Home visit per hold; independent of emergency recovery."""
    def __init__(self, generation=lambda: True):
        self.down = None
        self.fired = False
        self.generation = generation
        self.started_generation = None
    def event(self, kind, code, value, now):
        if kind == 1 and code == 412:
            if value == 1 and self.down is None:
                self.down = now
                self.fired = False
                self.started_generation = self.generation()
            elif value == 0:
                self.down = None
                self.fired = False
    def tick(self, now):
        if self.down is not None and not self.fired and now - self.down >= 1200:
            self.fired = True
            return self.started_generation is not None and self.started_generation == self.generation()
        return False
