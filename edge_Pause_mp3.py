#!/usr/bin/env python3

import argparse
import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts


def split_sentences(text: str):
    # Simple sentence splitting on ., !, ?
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


async def create_speech(text, voice, output, rate):
    tts = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
    )
    await tts.save(str(output))


def create_silence(seconds, output):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(seconds),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def main():
    parser = argparse.ArgumentParser(
        description="Generate MP3 from text using Edge TTS with pauses between sentences."
    )

    parser.add_argument(
        "input",
        help="Input text file"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="output.mp3",
        help="Output MP3 file"
    )

    parser.add_argument(
        "-v",
        "--voice",
        default="en-US-AriaNeural",
        help="Edge voice"
    )

    parser.add_argument(
        "-p",
        "--pause",
        type=float,
        default=5,
        help="Pause between sentences in seconds"
    )

    parser.add_argument(
        "--rate",
        default="-5%",
        help="Speech rate, for example -10%% or +10%%"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8").strip()

    if not text:
        raise SystemExit("Input file is empty.")

    sentences = split_sentences(text)

    workdir = Path(".tts_parts")
    workdir.mkdir(exist_ok=True)

    parts = []

    print(f"Voice: {args.voice}")
    print(f"Pause: {args.pause} seconds")
    print(f"Sentences: {len(sentences)}")

    for i, sentence in enumerate(sentences, start=1):

        print(f"[{i}/{len(sentences)}] {sentence}")

        speech_file = workdir / f"speech_{i:04d}.mp3"

        await create_speech(
            sentence,
            args.voice,
            speech_file,
            args.rate
        )

        parts.append(speech_file)

        # Don't necessarily need silence after final sentence
        if i < len(sentences):

            silence_file = workdir / f"silence_{i:04d}.mp3"

            create_silence(
                args.pause,
                silence_file
            )

            parts.append(silence_file)

    concat_file = workdir / "concat.txt"

    with concat_file.open("w", encoding="utf-8") as f:
        for part in parts:
            f.write(
                f"file '{part.resolve()}'\n"
            )

    print("Creating final MP3...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            args.output,
        ],
        check=True,
    )

    print()
    print(f"Created: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
