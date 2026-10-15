"""Listening content: checks, rubric/evidence linking, exact stitching, rendering with a mocked TTS."""

import random

from scripts.content import audio
from scripts.content.checks import check_listening_part
from scripts.content.offline import listening_rubrics
from scripts.content.tts import SAMPLE_RATE
from tests.listening_fixture import listening_part


def prepared(**kw):
    part = listening_part(**kw)
    listening_rubrics(part)
    return part


def test_good_part_passes_and_evidence_is_linked_to_lines():
    part = prepared()
    assert check_listening_part(part) == []
    assert [q.evidence.paragraph for g in part.groups for q in g.questions] == ["2", "3", "3"]
    assert part.groups[0].instructions == "Complete the form below.\nWrite ONE WORD AND/OR A NUMBER for each answer."
    assert part.groups[1].instructions == "Choose the correct letter, A, B or C."


def test_bad_parts_are_caught():
    part = prepared()
    part.groups[0].questions[0].answer = ["Hartly"]  # not what was said
    part.groups[0].questions[0], part.groups[0].questions[1] = part.groups[0].questions[1], part.groups[0].questions[0]
    part.script.lines[1].speaker = "ghost"
    part.groups[1].questions[0].options = part.groups[1].questions[0].options[:2]
    errors = " | ".join(check_listening_part(part))
    for expected in ["must appear verbatim in the recording", "follow the order of the recording",
                     "unknown speaker 'ghost'", "needs options A–C"]:
        assert expected in errors, expected


def test_stitching_gives_exact_timestamps():
    one_second = bytes(2 * SAMPLE_RATE)
    pcm, spans = audio.stitch([(one_second, 0.5), (one_second[: SAMPLE_RATE], 2.0), (one_second, 0)])
    assert spans == [(0, 1000), (1500, 2000), (4000, 5000)]
    assert audio.ms(len(pcm)) == 5000


def test_voices_are_distinct_and_fall_back_to_a_near_accent():
    part = listening_part()
    part.script.speakers[1].accent = "en-NZ"
    pool = {"en-GB": {"male": ["gb-m"], "female": ["gb-f"]}, "en-AU": {"male": ["au-m"]}}
    assert audio.assign_voices(part.script.speakers, pool, random.Random(1)) == {
        "narrator": "gb-m", "clerk": "au-m", "woman": "gb-f"}


def test_render_uses_one_tts_call_per_line_and_writes_segments(monkeypatch, tmp_path):
    calls = []

    def fake_tts(text, voice, provider):
        calls.append((voice, text))
        return bytes(2 * SAMPLE_RATE)  # exactly one second per line

    monkeypatch.setattr(audio, "synthesize", fake_tts)
    monkeypatch.setattr(audio, "encode_mp3", lambda pcm, out: None)
    monkeypatch.setattr(audio, "get_settings", lambda: type("S", (), {"content_dir": str(tmp_path), "elevenlabs_model": ""})())
    part = listening_part(with_audio=False)
    rendered = audio.render_part(part, "t-p1", "fake")
    assert len(calls) == 5 and rendered.url == "/media/audio/t-p1.mp3"
    # 1 s per line + 0.4 s gap after each, + the 5 s reading pause after line 0
    assert [(s.start_ms, s.end_ms) for s in rendered.segments][:2] == [(0, 1000), (6400, 7400)]
    assert rendered.duration_ms == 5 * 1400 + 5000
    audio.render_part(part, "t-p1", "fake")
    assert len(calls) == 5  # the second render comes from the cache


def test_fixed_voices_are_pinned_and_never_reused():
    part = listening_part()
    pool = {"en-GB": {"male": ["gb-m1", "gb-m2"], "female": ["gb-f"]}, "en-AU": {"male": ["au-m"]}}
    voices = audio.assign_voices(part.script.speakers, pool, random.Random(3), fixed={"narrator": "gb-m2"})
    assert voices == {"narrator": "gb-m2", "clerk": "au-m", "woman": "gb-f"}
