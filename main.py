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
	python main.py  # with inline tags: [cheerful] text [calm] text [rate=-6% pitch=-8Hz]
	python main.py  # plain text supported: emotion is auto-detected per sentence
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
	"cheerful": {"rate": "+8%", "pitch": "+0Hz", "volume": "+2%"},
	"calm": {"rate": "-8%", "pitch": "+0Hz", "volume": "+0%"},
	"sad": {"rate": "-14%", "pitch": "+0Hz", "volume": "-2%"},
	"energetic": {"rate": "+12%", "pitch": "+0Hz", "volume": "+4%"},
}

EXPRESSION_PATTERN = re.compile(r"\[([^\[\]]+)\]")
POSITIVE_WORDS = {
	"great", "awesome", "amazing", "good", "love", "happy", "excellent",
	"fun", "nice", "wonderful", "fantastic", "brilliant", "yay", "yess",
}
NEGATIVE_WORDS = {
	"sad", "bad", "terrible", "awful", "hate", "angry", "upset", "bummed",
	"failed", "failure", "problem", "worst", "pain", "crappy", "bombed",
}
ENERGETIC_WORDS = {
	"wow", "yess", "let's go", "lets go", "super", "instantly", "incredible",
	"boom", "excited", "hype", "powerful",
}
CALM_WORDS = {
	"calm", "slowly", "gently", "steady", "softly", "relaxed", "breathe",
	"peaceful", "quiet", "still",
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
	parser.add_argument(
		"--disable-auto-expression",
		action="store_true",
		help=(
			"Disable automatic emotion detection for plain text (only manual --emotion "
			"or [expression] tags will be used)"
		),
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


def parse_expression_directive(
	directive: str,
	current: dict[str, str],
) -> dict[str, str]:
	"""Parse one [expression] directive and return updated voice settings."""
	normalized = directive.strip()
	lower_directive = normalized.lower()

	if lower_directive in EMOTION_PRESETS:
		return dict(EMOTION_PRESETS[lower_directive])

	updated = dict(current)
	parts = re.split(r"[,\s]+", normalized)
	for part in parts:
		if not part or "=" not in part:
			continue
		key, value = part.split("=", 1)
		key = key.strip().lower()
		value = value.strip()
		if key in {"rate", "pitch", "volume"} and value:
			updated[key] = value

	return updated


def parse_text_with_expressions(
	text: str,
	default_rate: str,
	default_pitch: str,
	default_volume: str,
	auto_detect_expressions: bool,
) -> list[tuple[str, str, str, str]]:
	"""Split text into styled segments using inline tags.

	Supported examples inside input text:
	- [cheerful]
	- [calm]
	- [sad]
	- [energetic]
	- [neutral]
	- [rate=-6%]
	- [pitch=-10Hz]
	- [volume=+2%]
	- [rate=-4% pitch=-8Hz volume=+1%]
	"""
	if auto_detect_expressions and not EXPRESSION_PATTERN.search(text):
		return parse_text_with_auto_expressions(
			text=text,
			default_rate=default_rate,
			default_pitch=default_pitch,
			default_volume=default_volume,
		)

	base_settings = {
		"rate": default_rate,
		"pitch": default_pitch,
		"volume": default_volume,
	}
	current_settings = dict(base_settings)

	segments: list[tuple[str, str, str, str]] = []
	last_index = 0

	for match in EXPRESSION_PATTERN.finditer(text):
		segment_text = text[last_index:match.start()].strip()
		if segment_text:
			segments.append(
				(
					segment_text,
					current_settings["rate"],
					current_settings["pitch"],
					current_settings["volume"],
				)
			)

		directive = match.group(1)
		current_settings = parse_expression_directive(directive, current_settings)
		last_index = match.end()

	remainder = text[last_index:].strip()
	if remainder:
		segments.append(
			(
				remainder,
				current_settings["rate"],
				current_settings["pitch"],
				current_settings["volume"],
			)
		)

	if not segments:
		raise ValueError("No speakable text found after parsing [expression] tags.")

	return segments


def detect_emotion_for_sentence(sentence: str) -> str:
	"""Heuristic emotion detection for plain text sentence."""
	text = sentence.lower().strip()
	if not text:
		return "neutral"

	words = re.findall(r"[a-z']+", text)
	pos_hits = sum(1 for w in words if w in POSITIVE_WORDS)
	neg_hits = sum(1 for w in words if w in NEGATIVE_WORDS)
	energetic_hits = sum(1 for w in words if w in ENERGETIC_WORDS)
	calm_hits = sum(1 for w in words if w in CALM_WORDS)

	exclamation_count = sentence.count("!")
	question_count = sentence.count("?")
	ellipsis_count = sentence.count("...") + sentence.count("…")

	if energetic_hits > 0 or exclamation_count >= 2:
		return "energetic"
	if neg_hits > pos_hits and (neg_hits > 0 or ellipsis_count > 0):
		return "sad"
	if calm_hits > 0 or ellipsis_count > 0:
		return "calm"
	if pos_hits > neg_hits or exclamation_count == 1:
		return "cheerful"
	if question_count > 0:
		return "calm"
	return "neutral"


def parse_text_with_auto_expressions(
	text: str,
	default_rate: str,
	default_pitch: str,
	default_volume: str,
) -> list[tuple[str, str, str, str]]:
	"""Auto-detect expression per sentence when no [expression] tags are given."""
	sentences = re.split(r"(?<=[.!?])\s+", text)
	segments: list[tuple[str, str, str, str]] = []

	for sentence in sentences:
		sentence = sentence.strip()
		if not sentence:
			continue

		emotion = detect_emotion_for_sentence(sentence)
		preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS["neutral"])

		# Keep timbre consistent: use default pitch unless user explicitly set --pitch.
		segments.append(
			(
				sentence,
				preset["rate"],
				default_pitch,
				preset["volume"],
			)
		)

	if not segments:
		raise ValueError("No speakable text found after automatic expression parsing.")

	return segments


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
	auto_detect_expressions: bool,
) -> None:
	output_path.parent.mkdir(parents=True, exist_ok=True)

	if max_chars_per_chunk < 300:
		raise ValueError("--max-chars-per-chunk must be at least 300")
	if retries < 1:
		raise ValueError("--retries must be >= 1")
	if retry_delay <= 0:
		raise ValueError("--retry-delay must be > 0")

	styled_segments = parse_text_with_expressions(
		text=text,
		default_rate=rate,
		default_pitch=pitch,
		default_volume=volume,
		auto_detect_expressions=auto_detect_expressions,
	)
	total_chunks = 0
	for segment_text, _, _, _ in styled_segments:
		total_chunks += len(split_text_into_chunks(segment_text, max_chars=max_chars_per_chunk))

	chunk_counter = 0

	with output_path.open("wb") as out_file:
		for segment_text, seg_rate, seg_pitch, seg_volume in styled_segments:
			chunks = split_text_into_chunks(segment_text, max_chars=max_chars_per_chunk)
			for chunk in chunks:
				chunk_counter += 1
				audio_bytes = await synthesize_chunk_with_retry(
					text=chunk,
					voice=voice,
					rate=seg_rate,
					pitch=seg_pitch,
					volume=seg_volume,
					retries=retries,
					retry_delay=retry_delay,
				)
				out_file.write(audio_bytes)
				print(f"Synthesized chunk {chunk_counter}/{total_chunks}")


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
		auto_detect_expressions=not args.disable_auto_expression,
	)
	print(f"Audio generated successfully: {output_path}")


if __name__ == "__main__":
	asyncio.run(main())
