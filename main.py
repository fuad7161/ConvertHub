"""
High-quality English text-to-audio converter.

Uses Microsoft Edge neural TTS voices (very clear and natural).

Install dependency:
	pip install edge-tts

Examples:
	python main.py
	python main.py --input-file input.txt
	python main.py --voice en-US-ChristopherNeural --output narration.mp3
	python main.py --emotion cheerful
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
import re
import sys

import edge_tts


DEFAULT_VOICE = "en-US-ChristopherNeural"

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
			"Neural English voice, e.g. en-US-ChristopherNeural, en-US-GuyNeural, "
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
	parser.add_argument(
		"--max-chars-per-chunk",
		type=int,
		default=2600,
		help="Max characters per request chunk for better stability (default: 2600)",
	)
	parser.add_argument(
		"--retries",
		type=int,
		default=3,
		help="Retry attempts per chunk if network/API fails (default: 3)",
	)
	parser.add_argument(
		"--retry-delay",
		type=float,
		default=1.2,
		help="Base retry delay in seconds; uses exponential backoff (default: 1.2)",
	)

	argv = normalize_cli_value_flags(sys.argv[1:])
	return parser.parse_args(argv)


def normalize_cli_value_flags(argv: list[str]) -> list[str]:
	"""Normalize flag/value pairs so negative values are parsed reliably.

	Examples converted:
	- --rate -6%      -> --rate=-6%
	- --pitch -10Hz   -> --pitch=-10Hz
	- --volume +2%    -> --volume=+2%
	"""
	value_flags = {"--rate", "--pitch", "--volume"}
	normalized: list[str] = []
	i = 0
	while i < len(argv):
		token = argv[i]
		if token in value_flags and i + 1 < len(argv):
			next_token = argv[i + 1]
			normalized.append(f"{token}={next_token}")
			i += 2
			continue

		normalized.append(token)
		i += 1

	return normalized


def get_text(args: argparse.Namespace) -> str:
	if not args.input_file.exists():
		raise FileNotFoundError(f"Input file not found: {args.input_file}")
	text = args.input_file.read_text(encoding="utf-8").strip()

	if not text:
		raise ValueError("Input text is empty. Provide non-empty English text.")

	return normalize_text(text)


def normalize_text(text: str) -> str:
	"""Clean and normalize punctuation/spacing for more natural prosody."""
	text = text.replace("\u2019", "'").replace("\u2018", "'")
	text = text.replace("\u201c", '"').replace("\u201d", '"')
	text = text.replace("\u2026", "...")
	text = text.replace("\u2013", "-").replace("\u2014", " - ")
	text = re.sub(r"\s+", " ", text).strip()

	# Ensure a tiny pause hint after sentence punctuation by normalizing spaces.
	text = re.sub(r"([.!?])(?=[A-Za-z])", r"\1 ", text)
	text = re.sub(r"\s+", " ", text).strip()
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


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
	"""Split long text by sentence boundaries to reduce failed TTS requests."""
	if len(text) <= max_chars:
		return [text]

	sentences = re.split(r"(?<=[.!?])\s+", text)
	chunks: list[str] = []
	current: list[str] = []
	current_len = 0

	for sentence in sentences:
		sentence = sentence.strip()
		if not sentence:
			continue

		# Hard-split very long sentence if needed.
		if len(sentence) > max_chars:
			words = sentence.split()
			buffer: list[str] = []
			buf_len = 0
			for word in words:
				add_len = len(word) + (1 if buffer else 0)
				if buf_len + add_len > max_chars:
					if buffer:
						chunks.append(" ".join(buffer))
					buffer = [word]
					buf_len = len(word)
				else:
					buffer.append(word)
					buf_len += add_len
			if buffer:
				chunks.append(" ".join(buffer))
			continue

		add_len = len(sentence) + (1 if current else 0)
		if current_len + add_len > max_chars:
			chunks.append(" ".join(current))
			current = [sentence]
			current_len = len(sentence)
		else:
			current.append(sentence)
			current_len += add_len

	if current:
		chunks.append(" ".join(current))

	return chunks


async def synthesize_chunk_with_retry(
	text: str,
	voice: str,
	rate: str,
	pitch: str,
	volume: str,
	retries: int,
	retry_delay: float,
) -> bytes:
	last_error: Exception | None = None

	for attempt in range(1, retries + 1):
		try:
			communicate = edge_tts.Communicate(
				text=text,
				voice=voice,
				rate=rate,
				pitch=pitch,
				volume=volume,
			)

			audio_parts: list[bytes] = []
			async for event in communicate.stream():
				if event.get("type") == "audio":
					audio_parts.append(event["data"])

			if not audio_parts:
				raise RuntimeError("No audio returned from TTS service.")

			return b"".join(audio_parts)
		except Exception as exc:
			last_error = exc
			if attempt >= retries:
				break
			await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))

	raise RuntimeError(f"TTS failed after {retries} attempts: {last_error}")


async def text_to_audio(
	text: str,
	output_path: Path,
	voice: str,
	rate: str,
	pitch: str,
	volume: str,
	max_chars_per_chunk: int,
	retries: int,
	retry_delay: float,
) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)

	if max_chars_per_chunk < 300:
		raise ValueError("--max-chars-per-chunk must be at least 300")
	if retries < 1:
		raise ValueError("--retries must be >= 1")
	if retry_delay <= 0:
		raise ValueError("--retry-delay must be > 0")

	chunks = split_text_into_chunks(text, max_chars=max_chars_per_chunk)

	with output_path.open("wb") as out_file:
		for i, chunk in enumerate(chunks, start=1):
			audio_bytes = await synthesize_chunk_with_retry(
				text=chunk,
				voice=voice,
				rate=rate,
				pitch=pitch,
				volume=volume,
				retries=retries,
				retry_delay=retry_delay,
			)
			out_file.write(audio_bytes)
			print(f"Synthesized chunk {i}/{len(chunks)}")


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
		max_chars_per_chunk=args.max_chars_per_chunk,
		retries=args.retries,
		retry_delay=args.retry_delay,
	)
	print(f"Audio generated successfully: {output_path}")


if __name__ == "__main__":
	asyncio.run(main())
