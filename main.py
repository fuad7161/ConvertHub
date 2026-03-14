"""
High-quality English text-to-audio converter.

Uses Microsoft Edge neural TTS voices (very clear and natural).

Install dependency:
	pip install edge-tts

Examples:
	python main.py
	python main.py --input-file input.txt
	python main.py --voice en-US-GuyNeural --output narration.mp3
	python main.py --emotion cheerful
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import edge_tts


DEFAULT_VOICE = "en-US-GuyNeural"

EMOTION_PRESETS = {
	"neutral": {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"},
	"cheerful": {"rate": "+8%", "pitch": "+30Hz", "volume": "+2%"},
	"calm": {"rate": "-8%", "pitch": "-12Hz", "volume": "+0%"},
	"sad": {"rate": "-14%", "pitch": "-35Hz", "volume": "-2%"},
	"energetic": {"rate": "+12%", "pitch": "+20Hz", "volume": "+4%"},
}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Convert English text into a high-quality audio file (MP3)."
	)

	parser.add_argument(
		"--input-file",
		type=Path,
		default=Path("input.txt"),
		help="Path to a UTF-8 text file containing English text",
	)

	parser.add_argument(
		"--output",
		type=Path,
		default=None,
		help=(
			"Output audio file path. If not provided, a unique datetime name is "
			"created in audio/ folder"
		),
	)
	parser.add_argument(
		"--voice",
		type=str,
		default=DEFAULT_VOICE,
		help=(
			"Neural English voice, e.g. en-US-GuyNeural, en-US-ChristopherNeural, "
			"en-GB-SoniaNeural"
		),
	)
	parser.add_argument(
		"--emotion",
		type=str,
		choices=tuple(EMOTION_PRESETS.keys()),
		default="neutral",
		help="Emotion preset to reduce robotic tone",
	)
	parser.add_argument(
		"--rate",
		type=str,
		default=None,
		help="Speech rate like +0%%, -10%%, +15%% (overrides --emotion)",
	)
	parser.add_argument(
		"--pitch",
		type=str,
		default=None,
		help="Voice pitch like +0Hz, -20Hz, +40Hz (overrides --emotion)",
	)
	parser.add_argument(
		"--volume",
		type=str,
		default=None,
		help="Volume like +0%%, -5%%, +10%% (overrides --emotion)",
	)

	return parser.parse_args()


def get_text(args: argparse.Namespace) -> str:
	if not args.input_file.exists():
		raise FileNotFoundError(f"Input file not found: {args.input_file}")
	text = args.input_file.read_text(encoding="utf-8").strip()

	if not text:
		raise ValueError("Input text is empty. Provide non-empty English text.")

	return text


def get_output_path(args: argparse.Namespace) -> Path:
	if args.output is not None:
		return args.output

	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
	return Path("audio") / f"tts_{timestamp}.mp3"


def resolve_voice_settings(args: argparse.Namespace) -> tuple[str, str, str]:
	preset = EMOTION_PRESETS[args.emotion]
	rate = args.rate if args.rate is not None else preset["rate"]
	pitch = args.pitch if args.pitch is not None else preset["pitch"]
	volume = args.volume if args.volume is not None else preset["volume"]
	return rate, pitch, volume


async def text_to_audio(
	text: str,
	output_path: Path,
	voice: str,
	rate: str,
	pitch: str,
	volume: str,
) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	communicate = edge_tts.Communicate(
		text=text,
		voice=voice,
		rate=rate,
		pitch=pitch,
		volume=volume,
	)
	await communicate.save(str(output_path))


async def main() -> None:
	args = parse_args()
	text = get_text(args)
	output_path = get_output_path(args)
	rate, pitch, volume = resolve_voice_settings(args)
	await text_to_audio(
		text=text,
		output_path=output_path,
		voice=args.voice,
		rate=rate,
		pitch=pitch,
		volume=volume,
	)
	print(f"Audio generated successfully: {output_path}")


if __name__ == "__main__":
	asyncio.run(main())
