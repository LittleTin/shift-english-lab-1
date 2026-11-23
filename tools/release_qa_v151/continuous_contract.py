"""Shared continuous formal audio contract used by authoring and locks."""
from decimal import Decimal, ROUND_HALF_UP
import math

RATE = 48000
MAX_SAMPLES = 80 * 60 * RATE
SILENCE_ROLES = frozenset({'answer', 'gap', 'intro'})


def at48(seconds):
    return int((Decimal(str(seconds)) * RATE).to_integral_value(rounding=ROUND_HALF_UP))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def check_sample_count(obj, key, expected, message):
    if key in obj:
        require(type(obj[key]) is int and obj[key] == expected, message)


def timeline(plan):
    """Validate logical length and frame coverage in absolute 48 kHz coordinates."""
    seconds = plan.get('duration')
    require(finite(seconds) and 0 < seconds <= MAX_SAMPLES / RATE,
            'formal duration must be positive and at most 80 minutes')
    total = at48(seconds)
    require(0 < total <= MAX_SAMPLES and abs(seconds - total / RATE) < 1e-9,
            'formal duration is not an exact 48 kHz sample length')
    check_sample_count(plan, 'sampleRate', RATE, 'formal sample rate must be 48000')
    check_sample_count(plan, 'totalSamples', total, 'formal totalSamples disagrees with duration')
    frames = plan.get('frames')
    require(isinstance(frames, list) and frames, 'empty formal timeline')
    spans = []
    cursor = 0
    for i, frame in enumerate(frames):
        require(isinstance(frame, dict), f'invalid formal timeline at frame {i}')
        start, length = frame.get('at'), frame.get('duration')
        require(finite(start) and finite(length) and 0 <= start < seconds and 0 < length <= seconds,
                f'invalid formal timeline at frame {i}')
        a = at48(start)
        # Round absolute endpoints, not the component lengths separately:
        # legacy plans round timestamps to decimal seconds before writing.
        b = at48(Decimal(str(start)) + Decimal(str(length)))
        require(a == cursor and a < b <= total, f'formal gap, overlap or invalid range at frame {i}')
        spans.append((a, b))
        cursor = b
    require(cursor == total, 'formal frame coverage disagrees with declared duration')
    return total, spans


def geometry(plan, test):
    if 'groupAudio' not in plan:
        return {}
    total, spans = timeline(plan)
    media = plan['groupAudio']
    require(type(media) is dict and media, 'invalid or empty formal group-audio map')
    groups = {}
    for i, (frame, (a, b)) in enumerate(zip(plan['frames'], spans, strict=True)):
        gid = frame['groupId']
        group = groups.setdefault(gid, [])
        require(not group or group[-1]['index'] == i - 1, f'formal group not contiguous: {gid}')
        group.append(dict(index=i, start=a, end=b, kind=frame['kind'], role=frame['role']))
    require(set(groups) == set(media), 'formal group audio map must have exactly one entry per formal group')
    result = {}
    for gid, group in groups.items():
        entry = media[gid]
        path = f'audio/formal-groups/{test}/{gid}.ogg'
        require(type(entry) is dict and set(entry) in ({'src', 'duration'}, {'src', 'duration', 'totalSamples'})
                and entry['src'] == path, f'wrong formal URL/fields for {gid}')
        start, end = group[0]['start'], group[-1]['end']
        size = end - start
        seconds = entry['duration']
        require(finite(seconds) and abs(seconds - size / RATE) < 1e-9,
                f'wrong sample-exact group duration: {gid}')
        check_sample_count(entry, 'totalSamples', size, f'wrong group totalSamples: {gid}')
        result[gid] = dict(src=path, seconds=seconds, size=size, start=start, end=end,
                           frames=[dict(frame, start=frame['start'] - start, end=frame['end'] - start)
                                   for frame in group])
    require(sum(group['size'] for group in result.values()) == total,
            'continuous Opus schedule does not equal declared formal sample length')
    return result


def role(row, gid):
    return dict(url=row['src'], role='formal-group-audio', group=gid, start=0, end=row['seconds'],
                startSample48k=0, endSample48k=row['size'])


def owner(test, gid, path):
    return f'{test}/groups/{gid}/media/{path}'
