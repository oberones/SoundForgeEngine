"""Exercise the documented evidence exporter against real prepared song material."""
import json
from pathlib import Path
import subprocess
import sys

from song import SONG_PATTERNS


def test_evidence_export_preserves_off_grid_song_voice_identities(tmp_path):
    """All presets export, including returning verses with quarter-beat ornaments."""
    root = Path(__file__).resolve().parents[1]
    baseline = root / 'docs/validation/generative-engine/improvements/baseline'
    result = subprocess.run(
        [sys.executable, str(root / 'tools/evaluate_generative_music.py'),
         '--output', str(tmp_path), '--comparison-baseline', str(baseline)],
        cwd=root, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    names = set(SONG_PATTERNS) | {'fugue-3', 'fugue-4'}
    assert {entry['name'] for entry in manifest['files']} == names
    for name in names:
        assert (tmp_path / f'{name}.mid').is_file()
        payload = json.loads((tmp_path / f'{name}.json').read_text())
        assert payload['events']
        assert all(event['voice'] is not None for event in payload['events'])
        assert payload['metrics']['melodic_interval_semitones'] is not None

    # Each ornament is consumed from local beat 8.75 at an empty beat-9 row.
    for name, beat, pitch in [('aaba', 121.0, 74), ('blues_twelve_bar', 169.0, 76)]:
        payload = json.loads((tmp_path / f'{name}.json').read_text())
        assert [event for event in payload['events'] if event['beat'] == beat] == [
            dict(beat=beat, pitch=pitch, velocity=73 if name == 'aaba' else 70,
                 duration=.4, voice=0)]
    comparison = json.loads((tmp_path / 'comparison/manifest.json').read_text())
    assert {(entry['name'], entry['version']) for entry in comparison['files']} == {
        (name, version) for name in names for version in ('baseline', 'current')}
