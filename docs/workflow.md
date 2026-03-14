# Text-to-Audio Workflow

## 1) Setup

Install dependency once:

```bash
pip install edge-tts
```

## 2) Basic Run

Put text in `input.txt`, then run:

```bash
python main.py
```

If `python` is not available:

```bash
python3 main.py
```

Default output is auto-created in `audio/` with sortable datetime name:

`audio/tts_YYYYMMDD_HHMMSS_microseconds.mp3`

---

## 3) Parameters (Grouped)

### A) Input Parameters

#### `--input-file`
- Type: `Path`
- Default: `input.txt`
- Purpose: Reads English text from file.
- Example:

```bash
python main.py --input-file chapter1.txt
```

### B) Output Parameters

#### `--output`
- Type: `Path`
- Default: auto-generated (`audio/tts_...mp3`)
- Purpose: Set exact output file name/path.
- Example:

```bash
python main.py --output audio/story.mp3
```

### C) Voice Selection Parameters

#### `--voice`
- Type: `str`
- Default: `en-US-GuyNeural`
- Purpose: Choose TTS voice.
- Example values:
  - `en-US-GuyNeural` (male)
  - `en-US-ChristopherNeural` (male)
  - `en-US-JennyNeural` (female)
  - `en-US-AriaNeural` (female)
- Example:

```bash
python main.py --voice en-US-ChristopherNeural
```

### D) Emotion Preset Parameters

#### `--emotion`
- Type: `str`
- Default: `neutral`
- Allowed values (all supported):
  - `neutral`
  - `cheerful`
  - `calm`
  - `sad`
  - `energetic`
- Purpose: Applies preset style by adjusting `rate`, `pitch`, and `volume`.
- Example:

```bash
python main.py --emotion cheerful
```

Preset mapping:

| Emotion | Rate | Pitch | Volume |
|---|---|---|---|
| neutral | +0% | +0Hz | +0% |
| cheerful | +8% | +30Hz | +2% |
| calm | -8% | -12Hz | +0% |
| sad | -14% | -35Hz | -2% |
| energetic | +12% | +20Hz | +4% |

### E) Manual Voice Tuning Parameters

These override emotion values if provided.

#### `--rate`
- Type: `str`
- Default: from selected `--emotion`
- Format: percent (examples: `+0%`, `-10%`, `+15%`)

#### `--pitch`
- Type: `str`
- Default: from selected `--emotion`
- Format: Hz (examples: `+0Hz`, `-20Hz`, `+40Hz`)

#### `--volume`
- Type: `str`
- Default: from selected `--emotion`
- Format: percent (examples: `+0%`, `-5%`, `+10%`)

Manual tuning example:

```bash
python main.py --emotion calm --rate -6% --pitch -10Hz --volume +2%
```

---

## 4) Complete Command Examples

Default run:

```bash
python main.py
```

Female voice:

```bash
python main.py --voice en-US-JennyNeural
```

Male voice:

```bash
python main.py --voice en-US-GuyNeural
```

Custom input + output:

```bash
python main.py --input-file notes.txt --output audio/notes.mp3
```

## 5) Quick Tip

To see parameters anytime:

```bash
python main.py --help
```


