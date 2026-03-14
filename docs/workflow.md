## Feature list
- [ ] Different type of voice
- [ ] audio speed modify 

## Todo
make a desktop app so that anyone can use this. just by installing this



### female voice 
```python
python main.py --voice en-US-JennyNeural 
```

### Male voice
```
```


## 1) Setup

From this project folder, install dependency:

pip install edge-tts

## 2) Basic Run

Put your text in `input.txt`, then run:

python main.py

Output is generated automatically in `audio/` with a sortable datetime filename, for example:

audio/tts_20260314_153012_123456.mp3

## 3) Command Parameters

All parameters:

- `--input-file` (Path, default: `input.txt`)
	- Text file to read input from.

- `--output` (Path, optional)
	- Exact output file path.
	- If omitted, file is auto-created inside `audio/` with unique datetime name.

- `--voice` (str, default: `en-US-GuyNeural`)
	- Neural voice ID.
	- Examples: `en-US-GuyNeural`, `en-US-ChristopherNeural`, `en-US-JennyNeural`.

- `--emotion` (str, default: `neutral`)
	- Emotion preset to reduce robotic tone.
	- Choices: `neutral`, `cheerful`, `calm`, `sad`, `energetic`.

- `--rate` (str, optional)
	- Speech speed, e.g. `+0%`, `-10%`, `+15%`.
	- Overrides rate from `--emotion` preset.

- `--pitch` (str, optional)
	- Voice pitch, e.g. `+0Hz`, `-20Hz`, `+40Hz`.
	- Overrides pitch from `--emotion` preset.

- `--volume` (str, optional)
	- Volume, e.g. `+0%`, `-5%`, `+10%`.
	- Overrides volume from `--emotion` preset.

## 4) Examples

Use defaults (`input.txt`, male voice, neutral emotion):

python main.py

Use cheerful style:

python main.py --emotion cheerful

Use custom input file:

python main.py --input-file my_text.txt

Use custom output filename:

python main.py --output audio/story.mp3

Use custom male voice:

python main.py --voice en-US-ChristopherNeural

Manually tune voice:

python main.py --emotion calm --rate -6% --pitch -10Hz --volume +2%

## 5) Troubleshooting

- If you get shell errors, make sure you run plain commands (no Markdown link formatting).
- If command `python` fails, use:

python3 main.py


