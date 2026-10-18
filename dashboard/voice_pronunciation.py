"""Apply approved pronunciation units to aligned cloned speech, preserving sentence gaps."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave


def active_bounds(samples, start, end, rate):
    """Keep quiet edges outside the replacement, including trailing sentence silence."""
    step = max(1, rate // 200)
    regions = []
    for a in range(start, end, step):
        b = min(end, a + step)
        rms = math.sqrt(sum(v * v for v in samples[a:b]) / max(1, b - a))
        if rms > 180:
            regions.append((a, b))
    if not regions:
        raise ValueError('No voiced audio in pronunciation span')
    return max(start, regions[0][0] - rate // 500), min(end, regions[-1][1] + rate // 500)


def apply_approved_pronunciation(wav, words, config, assets):
    spec = config.get('approved_pronunciation_audio')
    if not spec or not spec.get('enabled'):
        return wav, words, None
    reference = Path(assets) / spec['file']
    if hashlib.sha256(reference.read_bytes()).hexdigest() != spec['sha256']:
        raise ValueError('Approved pronunciation reference hash mismatch')
    with wave.open(str(wav), 'rb') as handle:
        params = handle.getparams()
        if params.nchannels != 1 or params.sampwidth != 2:
            raise ValueError('Expected mono 16-bit source speech')
        raw = handle.readframes(handle.getnframes())
    rate = params.framerate
    samples = array('h', raw)
    reference_pcm = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(reference), '-f', 's16le',
        '-ac', '1', '-ar', str(rate), '-'])
    units = {}
    for token, bounds in spec['units'].items():
        a, b = [round(t * rate) for t in bounds]
        unit = array('h', reference_pcm[a * 2:b * 2])
        # Short edge fades avoid clicks without changing the internal vowel transition.
        fade = min(round(.003 * rate), len(unit) // 2)
        for j in range(fade):
            unit[j] = round(unit[j] * j / fade)
            unit[-j - 1] = round(unit[-j - 1] * j / fade)
        units[token] = unit.tobytes()
    pieces, adjusted, changes = [], [], []
    cursor, shift = 0, 0
    for index, word in enumerate(words):
        token = word['word'].strip('.,?!:;"«»()')
        updated = dict(word)
        updated['start'] = word['start'] + shift / rate
        if token in units:
            start, end = round(word['start'] * rate), round(word['end'] * rate)
            a, b = active_bounds(samples, start, end, rate)
            if a < cursor:
                raise ValueError('Overlapping pronunciation spans')
            padding = 0
            if word['word'].endswith(('.', '?', '!')):
                following = words[index + 1]['start'] if index + 1 < len(words) else len(samples) / rate
                padding = max(0, round(spec.get('sentence_pause_seconds', .4) * rate) - (round(following * rate) - b))
            unit = units[token]
            pieces.extend([raw[cursor * 2:a * 2], unit, b'\0\0' * padding])
            delta = len(unit) // 2 + padding - (b - a)
            changes.append({'word_index': index, 'token': token, 'original_span': [a / rate, b / rate],
                            'approved_unit_sha256': hashlib.sha256(unit).hexdigest(),
                            'inserted_sentence_padding_seconds': padding / rate})
            cursor = b
            shift += delta
        updated['end'] = word['end'] + shift / rate
        adjusted.append(updated)
    if not changes:
        return wav, adjusted, {'reference_sha256': spec['sha256'], 'replacements': []}
    pieces.append(raw[cursor * 2:])
    dest = Path(wav).with_name(Path(wav).stem + '-approved.wav')
    with wave.open(str(dest), 'wb') as handle:
        handle.setparams(params)
        handle.writeframes(b''.join(pieces))
    report = {'reference_sha256': spec['sha256'], 'replacements': changes,
              'source_pcm_sha256': hashlib.sha256(raw).hexdigest(), 'sentence_pauses_preserved': True}
    dest.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return dest, adjusted, report
