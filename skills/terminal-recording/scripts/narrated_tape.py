#!/usr/bin/env python3
"""
narrated_tape.py - Compile VHS tape files with AI narration

This tool processes VHS .tape files containing narration macros,
generates speech via ElevenLabs TTS, calculates real timings,
and outputs a compiled tape + audio files ready for final mixing.

Usage:
    python narrated_tape.py input.tape --output-dir ./build
    python narrated_tape.py input.tape --voice "Adam" --render

Narration Macros:
    # @voice eleven:<voice_name>     - Set ElevenLabs voice (default: Adam)
    # @narrate:before "text"         - Speak, then action
    # @narrate:during "text"         - Speak while action runs  
    # @narrate:after "text"          - Action, then speak
    # @narrate:wait                  - Wait for all pending speech

Environment:
    ELEVENLABS_API_KEY - Required for TTS generation
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class NarrationSegment:
    """A single narration segment extracted from the tape file."""
    line_number: int
    mode: str  # 'before', 'during', 'after', 'wait'
    text: Optional[str]
    audio_file: Optional[str] = None
    duration_ms: int = 0
    start_time_ms: int = 0


@dataclass
class TapeConfig:
    """Configuration extracted from tape file."""
    voice: str = "Adam"
    voice_id: Optional[str] = None
    output_file: Optional[str] = None
    segments: list = field(default_factory=list)


# ElevenLabs voice name to ID mapping (common voices)
ELEVENLABS_VOICES = {
    "adam": "pNInz6obpgDQGcFmaJgB",
    "antoni": "ErXwobaYiN019PkySvjV", 
    "arnold": "VR6AewLTigWG4xSOukaG",
    "bella": "EXAVITQu4vr4xnSDxMaL",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "elli": "MF3mGyEYCl7XYWbV9V6O",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "sam": "yoZ06aMxZJJ28mfd3POQ",
}


def parse_tape_file(tape_path: Path) -> tuple[list[str], TapeConfig]:
    """
    Parse a tape file and extract narration macros.
    
    Returns:
        tuple of (original_lines, TapeConfig with segments)
    """
    config = TapeConfig()
    lines = tape_path.read_text().splitlines()
    
    # Regex patterns for narration macros
    voice_pattern = re.compile(r'#\s*@voice\s+eleven:(\w+)', re.IGNORECASE)
    narrate_pattern = re.compile(r'#\s*@narrate:(\w+)(?:\s+"([^"]*)")?', re.IGNORECASE)
    output_pattern = re.compile(r'^Output\s+(.+)$', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        # Check for voice setting
        voice_match = voice_pattern.match(line.strip())
        if voice_match:
            config.voice = voice_match.group(1)
            continue
        
        # Check for output file
        output_match = output_pattern.match(line.strip())
        if output_match:
            config.output_file = output_match.group(1).strip()
            continue
            
        # Check for narration macro
        narrate_match = narrate_pattern.match(line.strip())
        if narrate_match:
            mode = narrate_match.group(1).lower()
            text = narrate_match.group(2) if narrate_match.group(2) else None
            
            if mode not in ('before', 'during', 'after', 'wait'):
                print(f"Warning: Unknown narration mode '{mode}' on line {i+1}", file=sys.stderr)
                continue
                
            if mode != 'wait' and not text:
                print(f"Warning: Missing text for @narrate:{mode} on line {i+1}", file=sys.stderr)
                continue
            
            segment = NarrationSegment(
                line_number=i,
                mode=mode,
                text=text
            )
            config.segments.append(segment)
    
    # Resolve voice ID
    voice_lower = config.voice.lower()
    if voice_lower in ELEVENLABS_VOICES:
        config.voice_id = ELEVENLABS_VOICES[voice_lower]
    else:
        # Assume it's already a voice ID
        config.voice_id = config.voice
    
    return lines, config


def generate_audio_elevenlabs(
    text: str,
    voice_id: str,
    output_path: Path,
    api_key: str
) -> int:
    """
    Generate audio using ElevenLabs API.
    
    Returns:
        Duration in milliseconds
    """
    import requests
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",  # Latest fast model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")
    
    output_path.write_bytes(response.content)
    
    # Get duration using ffprobe
    duration_ms = get_audio_duration_ms(output_path)
    return duration_ms


def get_audio_duration_ms(audio_path: Path) -> int:
    """Get audio duration in milliseconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"ffprobe error: {result.stderr}")
    
    duration_sec = float(result.stdout.strip())
    return int(duration_sec * 1000)


def generate_all_audio(
    config: TapeConfig,
    output_dir: Path,
    api_key: str
) -> None:
    """Generate audio for all narration segments."""
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    for i, segment in enumerate(config.segments):
        if segment.mode == 'wait' or not segment.text:
            continue
        
        audio_file = audio_dir / f"segment_{i:03d}.mp3"
        print(f"  Generating audio {i+1}/{len(config.segments)}: \"{segment.text[:40]}...\"")
        
        try:
            duration_ms = generate_audio_elevenlabs(
                segment.text,
                config.voice_id,
                audio_file,
                api_key
            )
            segment.audio_file = str(audio_file)
            segment.duration_ms = duration_ms
            print(f"    → {duration_ms}ms ({audio_file.name})")
        except Exception as e:
            print(f"    → Error: {e}", file=sys.stderr)
            raise


def calculate_timings(
    lines: list[str],
    config: TapeConfig
) -> tuple[list[str], list[dict]]:
    """
    Calculate real timings and generate compiled tape.
    
    Returns:
        tuple of (compiled_lines, audio_manifest)
    """
    compiled_lines = []
    audio_manifest = []
    current_time_ms = 0
    
    # Track which segments we've processed
    segment_idx = 0
    pending_during = None  # Track 'during' narration
    
    # Pattern to detect Sleep commands and extract time
    sleep_pattern = re.compile(r'^Sleep\s+(\d+(?:\.\d+)?)(ms|s)?$', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip narration macro comments (they become timing)
        if stripped.startswith('# @narrate:') or stripped.startswith('# @voice'):
            # Check if this is a narration we need to handle
            if segment_idx < len(config.segments):
                segment = config.segments[segment_idx]
                if segment.line_number == i:
                    segment_idx += 1
                    
                    if segment.mode == 'before':
                        # Insert sleep for speech duration, then continue
                        segment.start_time_ms = current_time_ms
                        audio_manifest.append({
                            "file": segment.audio_file,
                            "start_ms": current_time_ms,
                            "duration_ms": segment.duration_ms,
                            "text": segment.text
                        })
                        # Add sleep to wait for narration
                        compiled_lines.append(f"# Narration: \"{segment.text[:50]}...\"")
                        compiled_lines.append(f"Sleep {segment.duration_ms}ms")
                        current_time_ms += segment.duration_ms
                        
                    elif segment.mode == 'during':
                        # Start narration now, actions run concurrently
                        segment.start_time_ms = current_time_ms
                        audio_manifest.append({
                            "file": segment.audio_file,
                            "start_ms": current_time_ms,
                            "duration_ms": segment.duration_ms,
                            "text": segment.text
                        })
                        pending_during = segment
                        compiled_lines.append(f"# Narration (during): \"{segment.text[:50]}...\"")
                        
                    elif segment.mode == 'after':
                        # Will be handled after the next action block
                        compiled_lines.append(f"# Narration (after): \"{segment.text[:50]}...\"")
                        # Queue it - we'll insert the sleep after next action
                        segment.start_time_ms = current_time_ms
                        audio_manifest.append({
                            "file": segment.audio_file,
                            "start_ms": current_time_ms,
                            "duration_ms": segment.duration_ms,
                            "text": segment.text
                        })
                        compiled_lines.append(f"Sleep {segment.duration_ms}ms")
                        current_time_ms += segment.duration_ms
                        
                    elif segment.mode == 'wait':
                        # Sync point - ensure all pending audio is complete
                        compiled_lines.append("# @wait - sync point")
                        if pending_during:
                            # Calculate remaining time for during narration
                            remaining = pending_during.duration_ms - (current_time_ms - pending_during.start_time_ms)
                            if remaining > 0:
                                compiled_lines.append(f"Sleep {remaining}ms")
                                current_time_ms += remaining
                            pending_during = None
            continue
        
        # Handle Sleep commands - track time
        sleep_match = sleep_pattern.match(stripped)
        if sleep_match:
            value = float(sleep_match.group(1))
            unit = sleep_match.group(2) or 's'
            if unit == 's':
                value *= 1000
            current_time_ms += int(value)
        
        # Pass through other lines
        compiled_lines.append(line)
    
    return compiled_lines, audio_manifest


def generate_ffmpeg_mix_command(
    video_file: str,
    audio_manifest: list[dict],
    output_file: str
) -> str:
    """Generate FFmpeg command to mix video with narration audio."""
    if not audio_manifest:
        return f"# No audio to mix\ncp {video_file} {output_file}"
    
    # Build filter complex for audio mixing
    inputs = [f"-i {video_file}"]
    filter_parts = []
    mix_inputs = []
    
    for i, segment in enumerate(audio_manifest):
        if not segment.get('file'):
            continue
        inputs.append(f"-i {segment['file']}")
        # adelay takes milliseconds, apply to both channels
        delay = segment['start_ms']
        filter_parts.append(f"[{i+1}:a]adelay={delay}|{delay}[a{i}]")
        mix_inputs.append(f"[a{i}]")
    
    if not mix_inputs:
        return f"# No audio segments\ncp {video_file} {output_file}"
    
    # Combine all delayed audio tracks
    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest:normalize=0[narration]"
    
    cmd = f"""ffmpeg -y \\
  {' '.join(inputs)} \\
  -filter_complex "{filter_complex}" \\
  -map 0:v -map "[narration]" \\
  -c:v copy -c:a aac -b:a 192k \\
  {output_file}"""
    
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Compile VHS tape files with AI narration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("tape_file", type=Path, help="Input .tape file with narration macros")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("./build"),
                        help="Output directory (default: ./build)")
    parser.add_argument("--voice", "-v", type=str, help="Override ElevenLabs voice name")
    parser.add_argument("--render", "-r", action="store_true",
                        help="Run VHS to render the video after compilation")
    parser.add_argument("--mix", "-m", action="store_true",
                        help="Also run FFmpeg to create final video with audio")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Parse and show plan without generating audio")
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: ELEVENLABS_API_KEY environment variable required", file=sys.stderr)
        sys.exit(1)
    
    # Parse tape file
    print(f"📼 Parsing {args.tape_file}...")
    lines, config = parse_tape_file(args.tape_file)
    
    if args.voice:
        config.voice = args.voice
        voice_lower = args.voice.lower()
        if voice_lower in ELEVENLABS_VOICES:
            config.voice_id = ELEVENLABS_VOICES[voice_lower]
        else:
            config.voice_id = args.voice
    
    print(f"   Voice: {config.voice} ({config.voice_id})")
    print(f"   Found {len(config.segments)} narration segments:")
    
    for seg in config.segments:
        text_preview = (seg.text[:40] + "...") if seg.text and len(seg.text) > 40 else seg.text
        print(f"     - @narrate:{seg.mode} \"{text_preview}\"")
    
    if args.dry_run:
        print("\n🔍 Dry run - no audio generated")
        return
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate audio
    print(f"\n🎙️  Generating audio via ElevenLabs...")
    generate_all_audio(config, args.output_dir, api_key)
    
    # Calculate timings and compile tape
    print(f"\n⏱️  Calculating timings...")
    compiled_lines, audio_manifest = calculate_timings(lines, config)
    
    # Write compiled tape
    compiled_tape_path = args.output_dir / f"{args.tape_file.stem}_compiled.tape"
    compiled_tape_path.write_text("\n".join(compiled_lines))
    print(f"   Compiled tape: {compiled_tape_path}")
    
    # Write audio manifest
    manifest_path = args.output_dir / "audio_manifest.json"
    manifest_path.write_text(json.dumps(audio_manifest, indent=2))
    print(f"   Audio manifest: {manifest_path}")
    
    # Generate FFmpeg command
    video_output = args.output_dir / (config.output_file or "output.mp4")
    final_output = args.output_dir / f"{args.tape_file.stem}_final.mp4"
    
    ffmpeg_cmd = generate_ffmpeg_mix_command(
        str(video_output),
        audio_manifest,
        str(final_output)
    )
    
    mix_script_path = args.output_dir / "mix_audio.sh"
    mix_script_path.write_text(f"#!/bin/bash\n\n{ffmpeg_cmd}\n")
    mix_script_path.chmod(0o755)
    print(f"   Mix script: {mix_script_path}")
    
    # Render if requested
    if args.render:
        print(f"\n🎬 Rendering video with VHS...")
        result = subprocess.run(
            ["vhs", str(compiled_tape_path)],
            cwd=args.output_dir
        )
        if result.returncode != 0:
            print("Error: VHS rendering failed", file=sys.stderr)
            sys.exit(1)
        print(f"   Video: {video_output}")
    
    # Mix if requested
    if args.mix and args.render:
        print(f"\n🔊 Mixing audio with video...")
        result = subprocess.run(["bash", str(mix_script_path)], cwd=args.output_dir)
        if result.returncode != 0:
            print("Error: FFmpeg mixing failed", file=sys.stderr)
            sys.exit(1)
        print(f"   Final video: {final_output}")
    
    print(f"\n✅ Done! Output in {args.output_dir}/")
    
    if not args.render:
        print(f"\nNext steps:")
        print(f"  1. Render video:  vhs {compiled_tape_path}")
        print(f"  2. Mix audio:     bash {mix_script_path}")


if __name__ == "__main__":
    main()
