# Text-to-Audio (Local, High-Quality)

Generate realistic English speech from text using local Python code + Edge neural voices.

## Features

- Reads text from `input.txt` (or custom file)
- Auto-generates MP3 files in `audio/` with sortable datetime names
- Stable synthesis with chunking + retry/backoff
- Expression control:
	- Automatic expression detection from plain text
	- Optional manual inline tags like `[cheerful]`, `[rate=-6%]`
- Voice identity stays consistent (pitch kept stable by default)

---

## 1) Requirements

- Python 3.10+ (recommended)
- Internet connection (Edge neural service is online)

---

## 2) Clone and Setup

```bash
git clone <your-repo-url>
cd text-to-audio
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python` points to Python 2 on your machine, use `python3` instead.

---

## 3) Input File

Put your text in `input.txt`.

Example:

```text
Hey, today was actually kind of fun, you know?
A bunch of the experiments went surprisingly well!
But some of them bombed, and that felt bad for a bit.
Still, every result taught me something.
```

---

## 4) Run

Basic run:

```bash
python main.py
```

This creates output like:

`audio/tts_20260315_101512_123456.mp3`

Desktop UI run:

```bash
python desktop_app.py
```

This opens a window where you can:
- paste/edit text
- choose voice and emotion settings
- enable/disable auto-expression detection
- click **Generate Audio** to create MP3

---

## 5) Common Commands

Use another input file:

```bash
python main.py --input-file notes.txt
```

Set custom output path:

```bash
python main.py --output audio/my_story.mp3
```

Set voice:

```bash
python main.py --voice en-US-ChristopherNeural
```

Use manual emotion preset:

```bash
python main.py --emotion calm
```

Manual tune values:

```bash
python main.py --rate -6% --volume +2%
```

Disable auto-expression detection:

```bash
python main.py --disable-auto-expression
```

Show all CLI options:

```bash
python main.py --help
```

---

## 6) Expression Modes

### A) Auto mode (default)
If your text has no tags, the app auto-detects expression sentence-by-sentence.

### B) Manual inline tags (optional)
You can embed tags directly in text:

- `[cheerful]`, `[calm]`, `[sad]`, `[energetic]`, `[neutral]`
- `[rate=-6%]`
- `[pitch=-10Hz]`
- `[volume=+2%]`
- Combined: `[rate=-4% pitch=-8Hz volume=+1%]`

Example:

```text
[cheerful] We made great progress today!
[calm] Let's review what we learned.
```

---

## 7) Parameters (Quick Reference)

- `--input-file` path to UTF-8 text file (default: `input.txt`)
- `--output` output MP3 path (default: auto timestamp in `audio/`)
- `--voice` TTS voice ID (default: `en-US-ChristopherNeural`)
- `--emotion` base preset (`neutral|cheerful|calm|sad|energetic`)
- `--rate` overrides speaking rate
- `--pitch` overrides pitch
- `--volume` overrides volume
- `--max-chars-per-chunk` chunk size for reliability
- `--retries` retry count per chunk
- `--retry-delay` exponential-backoff base seconds
- `--disable-auto-expression` disable automatic expression detection

---

## 8) Troubleshooting

- Error: `argument --rate: expected one argument`
	- Use either style:
		- `--rate -6%`
		- `--rate=-6%`

- Voice sounds robotic:
	- Try: `--emotion calm` or `--emotion cheerful`
	- Keep punctuation natural in text (`.`, `!`, `?`, `...`)

- Empty or missing input:
	- Ensure file exists and has non-empty text.
