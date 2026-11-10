"""Bounded typed diagnostics, never operation admission or arbitrary serialization."""
from contextvars import ContextVar
import json
import re

TYPES = ('null', 'boolean', 'number', 'string', 'array', 'object', 'undefined', 'function', 'unknown')
CATEGORIES = ('unknown', 'missing', 'invalid', 'unsafe', 'unavailable', 'mismatch', 'oversized',
              'unexpected', 'valid', 'present', 'absent', 'denied', 'busy', 'stale')
DECISIONS = ('refuse', 'wait', 'retry', 'retain', 'ignore', 'complete')
MAX_COUNT = 2147483647
current_recorder = ContextVar('contract_event_recorder', default=None)


def describe(value):
    """Exact built-ins only; do not call user hooks. Lengths use JS UTF-16 units."""
    kind = type(value)
    if value is None: return {'type': 'null'}
    if kind is bool: return {'type': 'boolean'}
    if kind in (int, float): return {'type': 'number'}
    if kind is str: return {'type': 'string', 'length': len(value.encode('utf-16-le', 'surrogatepass')) // 2}
    if kind is list: return {'type': 'array', 'length': len(value)}
    if kind is dict: return {'type': 'object', 'length': len(value)}
    return {'type': 'unknown'}


def _integer(value, low=0, high=MAX_COUNT):
    return type(value) is int and low <= value <= high


def _bytes(value):
    return len(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode())


def normalize(event):
    try:
        if type(event) is not dict or type(event.get('schema')) is not int or event['schema'] != 1: return None
        result = {'schema': 1}
        for key in ('component', 'operation', 'phase', 'field', 'expected'):
            value = event.get(key)
            if type(value) is not str or len(value) > (64 if key == 'field' else 32) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', value): return None
            result[key] = value
        if type(event.get('decision')) is not str or event['decision'] not in DECISIONS: return None
        actual = event.get('actual')
        safe = {}
        if type(actual) is dict:
            for key in ('type', 'length', 'uid', 'gid', 'mode', 'size', 'limit', 'code', 'errno', 'os_code', 'reported_code', 'category'):
                value = actual.get(key)
                if key in ('type', 'category'):
                    if type(value) is str and value in (TYPES if key == 'type' else CATEGORIES): safe[key] = value
                elif _integer(value, -(2**31) if key in ('code', 'os_code', 'reported_code') else 0,
                              4095 if key in ('mode', 'errno') else 2**53-1 if key in ('length', 'size', 'limit') else MAX_COUNT):
                    safe[key] = value
        result.update(actual=safe, decision=event['decision'], count=event.get('count', 1) if _integer(event.get('count', 1), 1) else 1)
        for key in ('first', 'last'):
            if _integer(event.get(key), 0, 2**53-1): result[key] = event[key]
        # Reserve room for saturated repeat counts; timestamps are optional.
        for key in ('last', 'first'):
            if _bytes(dict(result, count=MAX_COUNT)) > 512: result.pop(key, None)
        return result if _bytes(dict(result, count=MAX_COUNT)) <= 512 else None
    except Exception:
        return None


class Recorder:
    """First event plus 31 recent unique events; at most 32 bounded comparisons."""
    def __init__(self, emit=None, context=None):
        self.emit = emit
        self.context = context if type(context) is dict else {}
        self.events = []
        self.dropped = 0
        self.suppressed = 0

    def record(self, event):
        try:
            if type(event) is dict:
                event = {key: event.get(key, self.context.get(key)) for key in
                         ('schema', 'component', 'operation', 'phase', 'field', 'expected', 'actual', 'decision', 'count', 'first', 'last')}
            clean = normalize(event)
            if clean is None:
                self.suppressed = min(MAX_COUNT, self.suppressed + 1)
                return
            identity = {k:v for k,v in clean.items() if k not in ('count', 'first', 'last')}
            for old in self.events:
                if identity == {k:v for k,v in old.items() if k not in ('count', 'first', 'last')}:
                    old['count'] = min(MAX_COUNT, old['count'] + clean['count'])
                    if 'last' in clean: old['last'] = clean['last']
                    return
            if len(self.events) == 32:
                del self.events[1]
                self.dropped = min(MAX_COUNT, self.dropped + 1)
            self.events.append(clean)
            while _bytes(self.events) > 16200:
                del self.events[1]
                self.dropped = min(MAX_COUNT, self.dropped + 1)
            if callable(self.emit): self.emit(json.loads(json.dumps(clean)))
        except Exception:
            pass

    def snapshot(self):
        return {'schema':1, 'events':safe_events(self.events), 'dropped':self.dropped, 'suppressed':self.suppressed}


def safe_events(values):
    try:
        if type(values) is dict:
            values = values.get('events') if type(values.get('schema')) is int and values['schema'] == 1 else None
        if type(values) is not list: return []
        # Scan only a bounded projection, never an unbounded remote list.
        result = [clean for value in values[:32] if (clean := normalize(value)) is not None]
        while _bytes(result) > 16200: del result[1]
        return result
    except Exception:
        return []


def record(event):
    try:
        recorder = current_recorder.get()
        if recorder is not None: recorder.record(event)
    except Exception:
        pass
