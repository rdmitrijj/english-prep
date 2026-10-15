"""A tiny Listening part (narrator + two speakers, three questions) that passes every part-level check."""

from scripts.content.schema import CPart

LINES = [
    ("narrator", "Part 1. You will hear a woman booking a bike tour. First, look at questions 1 to 3.", 5),
    ("clerk", "Good morning, Riverside Cycle Tours. How can I help?", 0),
    ("woman", "Hi, I'd like to book the coastal tour for Saturday. My surname is Hartley.", 0),
    ("clerk", "Lovely. The coastal tour leaves at nine fifteen from the harbour gate, not the station.", 0),
    ("narrator", "That is the end of Part 1.", 0),
]


def q(number, prompt, answer, quote, options=None):
    return {"number": number, "prompt": prompt, "options": options, "answer": answer, "difficulty": 1,
            "sub_skill": "detail", "evidence": {"paragraph": "", "quote": quote},
            "explanation": {"correct": "Stated directly.", "distractors": []}}


def listening_part(with_audio: bool = True) -> CPart:
    lines = [{"speaker": s, "text": t, "pause_after_s": p} for s, t, p in LINES]
    starts = [0, 2000, 4000, 6000, 8000]
    return CPart.model_validate({
        "number": 1, "context": "social_dialogue", "topic": "travel-transport",
        "script": {"speakers": [
            {"id": "narrator", "role": "Narrator", "accent": "en-GB", "gender": "male"},
            {"id": "clerk", "role": "Tour company clerk", "accent": "en-AU", "gender": "male"},
            {"id": "woman", "role": "Customer", "accent": "en-GB", "gender": "female"},
        ], "lines": lines},
        "audio": {"url": "/media/audio/fixture-p1.mp3", "duration_ms": 9000, "tts_provider": "fake",
                  "voices": {"narrator": "a", "clerk": "b", "woman": "c"},
                  "segments": [{"speaker": ln["speaker"], "accent": "en-GB", "start_ms": s, "end_ms": s + 1500,
                                "text": ln["text"]} for ln, s in zip(lines, starts)]} if with_audio else None,
        "groups": [
            {"qtype": "form_completion", "instructions": "", "max_words": 1, "allow_number": True, "options": None,
             "layout": {"title": "Tour booking", "template": "Surname: {1}\nMeeting point: the harbour {2}",
                        "table": None, "steps": None},
             "questions": [q(1, "Surname", ["Hartley"], "My surname is Hartley"),
                           q(2, "Meeting point", ["gate"], "from the harbour gate")]},
            {"qtype": "mcq", "instructions": "", "options": None, "layout": None, "questions": [
                q(3, "What time does the tour leave?", ["B"], "leaves at nine fifteen",
                  options=[{"letter": "A", "text": "8.45"}, {"letter": "B", "text": "9.15"}, {"letter": "C", "text": "9.50"}]),
            ]},
        ],
    })
