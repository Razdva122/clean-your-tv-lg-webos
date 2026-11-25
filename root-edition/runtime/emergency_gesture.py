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
