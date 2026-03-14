"""
High-quality English text-to-audio converter.

Uses Microsoft Edge neural TTS voices (very clear and natural).

Install dependency:
	pip install edge-tts

Examples:
	python main.py
	python main.py --input-file input.txt --output speech.mp3
	python main.py --voice en-US-JennyNeural --output narration.mp3
"""

import argparse
import asyncio
from pathlib import Path

import edge_tts


DEFAULT_VOICE = "en-US-AriaNeural"


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
		default=Path("output.mp3"),
		help="Output audio file path (default: output.mp3)",
	)
	parser.add_argument(
		"--voice",
		type=str,
		default=DEFAULT_VOICE,
		help=(
			"Neural English voice, e.g. en-US-AriaNeural, en-US-JennyNeural, "
			"en-GB-SoniaNeural"
		),
	)
	parser.add_argument(
		"--rate",
		type=str,
		default="+0%",
		help="Speech rate like +0%%, -10%%, +15%%",
	)
	parser.add_argument(
		"--pitch",
		type=str,
		default="+0Hz",
		help="Voice pitch like +0Hz, -20Hz, +40Hz",
	)

	return parser.parse_args()


def get_text(args: argparse.Namespace) -> str:
	if not args.input_file.exists():
		raise FileNotFoundError(f"Input file not found: {args.input_file}")
	text = args.input_file.read_text(encoding="utf-8").strip()

	if not text:
		raise ValueError("Input text is empty. Provide non-empty English text.")

	return text


async def text_to_audio(
	text: str,
	output_path: Path,
	voice: str,
	rate: str,
	pitch: str,
) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)
	communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
	await communicate.save(str(output_path))


async def main() -> None:
	args = parse_args()
	text = get_text(args)
	await text_to_audio(
		text=text,
		output_path=args.output,
		voice=args.voice,
		rate=args.rate,
		pitch=args.pitch,
	)
	print(f"Audio generated successfully: {args.output}")


if __name__ == "__main__":
	asyncio.run(main())
