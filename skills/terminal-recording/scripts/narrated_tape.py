#!/usr/bin/env python3
"""
narrated_tape.py - Compile VHS tape files with AI narration

This tool processes VHS .tape files containing narration macros,
generates speech via ElevenLabs TTS, calculates real timings,
and outputs a compiled tape + audio files ready for final mixing.

Usage:
    python narrated_tape.py input.tape --output-dir ./build
    python narrated_tape.py input.tape --voice "Adam" --render
    python narrated_tape.py input.tape --timeline  # Show timing analysis

Narration Macros:
    # @voice eleven:<voice_name>     - Set ElevenLabs voice (default: Adam)
    # @narrate:before "text"         - Speak, then action
    # @narrate:during "text"         - Speak while action runs  
    # @narrate:after "text"          - Action, then speak
    # @narrate:wait                  - Wait for all pending speech
    # @exec-time:Xs                  - Hint: next command takes X seconds

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
class TimelineEvent:
    """An event in the timeline for diagnostic output."""
    time_ms: int
    duration_ms: int
    event_type: str  # 'narration', 'type', 'enter', 'sleep', 'hidden', 'show', 'exec'
    description: str
    line_number: int = 0
    issues: list = field(default_factory=list)


@dataclass
class TapeConfig:
    """Configuration extracted from tape file."""
    voice: str = "Adam"
    voice_id: Optional[str] = None
    output_file: Optional[str] = None
    typing_speed_ms: int = 50  # Default typing speed per character
    enter_delay_ms: int = 50   # Time for Enter key press
    segments: list = field(default_factory=list)
    exec_time_hints: dict = field(default_factory=dict)  # line_number -> ms


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
    Parse a tape file and extract narration macros, settings, and timing hints.
    
    Returns:
        tuple of (original_lines, TapeConfig with segments)
    """
    config = TapeConfig()
    lines = tape_path.read_text().splitlines()
    
    # Regex patterns
    voice_pattern = re.compile(r'#\s*@voice\s+eleven:(\w+)', re.IGNORECASE)
    narrate_pattern = re.compile(r'#\s*@narrate:(\w+)(?:\s+"([^"]*)")?', re.IGNORECASE)
    exec_time_pattern = re.compile(r'#\s*@exec-time:\s*(\d+(?:\.\d+)?)(ms|s)?', re.IGNORECASE)
    output_pattern = re.compile(r'^Output\s+(.+)$', re.IGNORECASE)
    typing_speed_pattern = re.compile(r'^Set\s+TypingSpeed\s+(\d+)(ms|s)?$', re.IGNORECASE)
    
    pending_exec_time = None  # Store exec-time hint for next command
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for voice setting
        voice_match = voice_pattern.match(stripped)
        if voice_match:
            config.voice = voice_match.group(1)
            continue
        
        # Check for output file
        output_match = output_pattern.match(stripped)
        if output_match:
            config.output_file = output_match.group(1).strip()
            continue
        
        # Check for TypingSpeed setting
        typing_match = typing_speed_pattern.match(stripped)
        if typing_match:
            value = int(typing_match.group(1))
            unit = typing_match.group(2) or 'ms'
            if unit.lower() == 's':
                value *= 1000
            config.typing_speed_ms = value
            continue
        
        # Check for exec-time hint
        exec_match = exec_time_pattern.match(stripped)
        if exec_match:
            value = float(exec_match.group(1))
            unit = exec_match.group(2) or 's'
            if unit.lower() == 's':
                value *= 1000
            pending_exec_time = int(value)
            continue
        
        # If we have a pending exec-time, apply it to the next Type or Enter
        if pending_exec_time is not None:
            if stripped.startswith('Type ') or stripped == 'Enter':
                config.exec_time_hints[i] = pending_exec_time
                pending_exec_time = None
            
        # Check for narration macro
        narrate_match = narrate_pattern.match(stripped)
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


def extract_type_text(line: str) -> Optional[str]:
    """Extract the text from a Type command."""
    match = re.match(r'^Type\s+"([^"]*)"$', line.strip())
    if match:
        return match.group(1)
    match = re.match(r"^Type\s+'([^']*)'$", line.strip())
    if match:
        return match.group(1)
    return None


def build_timeline(
    lines: list[str],
    config: TapeConfig
) -> tuple[list[TimelineEvent], list[dict]]:
    """
    Build a detailed timeline of all events for analysis.
    
    Returns:
        tuple of (timeline_events, narration_manifest)
    """
    timeline = []
    narration_manifest = []
    current_time_ms = 0
    in_hidden = False
    
    # Patterns
    sleep_pattern = re.compile(r'^Sleep\s+(\d+(?:\.\d+)?)(ms|s)?$', re.IGNORECASE)
    type_pattern = re.compile(r'^Type\s+["\'].*["\']$', re.IGNORECASE)
    
    # Build segment lookup
    segment_by_line = {seg.line_number: seg for seg in config.segments}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track Hide/Show
        if stripped == 'Hide':
            in_hidden = True
            timeline.append(TimelineEvent(
                time_ms=current_time_ms,
                duration_ms=0,
                event_type='hidden',
                description='Hide (stop recording)',
                line_number=i
            ))
            continue
        elif stripped == 'Show':
            in_hidden = False
            timeline.append(TimelineEvent(
                time_ms=current_time_ms,
                duration_ms=0,
                event_type='show',
                description='Show (resume recording)',
                line_number=i
            ))
            continue
        
        # Handle narration macros
        if i in segment_by_line:
            segment = segment_by_line[i]
            narration_manifest.append({
                "file": segment.audio_file,
                "start_ms": current_time_ms,
                "duration_ms": segment.duration_ms,
                "text": segment.text,
                "mode": segment.mode
            })
            timeline.append(TimelineEvent(
                time_ms=current_time_ms,
                duration_ms=segment.duration_ms,
                event_type='narration',
                description=f'🎙️ "{segment.text[:50]}..."' if len(segment.text) > 50 else f'🎙️ "{segment.text}"',
                line_number=i
            ))
            # For 'before' mode, audio plays then we wait
            if segment.mode == 'before':
                current_time_ms += segment.duration_ms
            continue
        
        # Skip other comments and macros
        if stripped.startswith('#') or stripped.startswith('# @'):
            continue
        
        # Handle Type commands
        if type_pattern.match(stripped):
            text = extract_type_text(stripped)
            if text:
                char_count = len(text)
                typing_duration = char_count * config.typing_speed_ms
                
                # Check for exec-time hint
                exec_time = config.exec_time_hints.get(i, 0)
                
                event = TimelineEvent(
                    time_ms=current_time_ms,
                    duration_ms=typing_duration,
                    event_type='type',
                    description=f'⌨️ Type "{text[:40]}..." ({char_count} chars)' if len(text) > 40 else f'⌨️ Type "{text}" ({char_count} chars)',
                    line_number=i
                )
                
                if exec_time:
                    event.description += f' [exec: {exec_time}ms]'
                
                timeline.append(event)
                current_time_ms += typing_duration
            continue
        
        # Handle Enter
        if stripped == 'Enter':
            exec_time = config.exec_time_hints.get(i, 0)
            duration = config.enter_delay_ms + exec_time
            
            event = TimelineEvent(
                time_ms=current_time_ms,
                duration_ms=duration,
                event_type='enter',
                description='⏎ Enter',
                line_number=i
            )
            if exec_time:
                event.description += f' [exec: {exec_time}ms]'
            
            timeline.append(event)
            current_time_ms += duration
            continue
        
        # Handle Sleep commands
        sleep_match = sleep_pattern.match(stripped)
        if sleep_match:
            value = float(sleep_match.group(1))
            unit = sleep_match.group(2) or 's'
            if unit.lower() == 's':
                value *= 1000
            duration = int(value)
            
            timeline.append(TimelineEvent(
                time_ms=current_time_ms,
                duration_ms=duration,
                event_type='sleep',
                description=f'💤 Sleep {stripped.split()[1]}',
                line_number=i
            ))
            current_time_ms += duration
            continue
    
    return timeline, narration_manifest


def analyze_sync_issues(timeline: list[TimelineEvent], narration_manifest: list[dict]) -> list[str]:
    """Analyze timeline for sync issues between narration and actions."""
    issues = []
    
    # Build a map of narration end times
    narration_events = [e for e in timeline if e.event_type == 'narration']
    
    for i, narr_event in enumerate(narration_events):
        narr_end_time = narr_event.time_ms + narr_event.duration_ms
        
        # Find the next non-narration event
        next_events = [e for e in timeline 
                       if e.time_ms >= narr_event.time_ms 
                       and e.event_type in ('type', 'enter')
                       and e.line_number > narr_event.line_number]
        
        if next_events:
            next_event = next_events[0]
            gap = next_event.time_ms - narr_end_time
            
            if gap < -500:  # Action starts more than 500ms before narration ends
                issues.append(
                    f"⚠️  Line {narr_event.line_number + 1}: Narration ends {-gap}ms AFTER action starts. "
                    f"Consider using @narrate:during or adding buffer time."
                )
            elif gap > 2000:  # More than 2s gap
                issues.append(
                    f"💡 Line {narr_event.line_number + 1}: {gap}ms gap between narration and next action. "
                    f"Consider tightening timing."
                )
    
    return issues


def print_timeline(timeline: list[TimelineEvent], narration_manifest: list[dict], config: TapeConfig):
    """Print a visual timeline for diagnostic purposes."""
    print("\n📊 Timeline Analysis")
    print("═" * 80)
    print(f"\n⚙️  Settings: TypingSpeed={config.typing_speed_ms}ms, EnterDelay={config.enter_delay_ms}ms")
    if config.exec_time_hints:
        print(f"   Exec-time hints: {len(config.exec_time_hints)} commands")
    print()
    print(f"{'Time':>8}  {'Duration':>8}  {'Event':<60}")
    print("─" * 80)
    
    for event in timeline:
        time_str = f"{event.time_ms/1000:.2f}s"
        dur_str = f"{event.duration_ms}ms" if event.duration_ms else ""
        
        # Color-code by type
        type_indicators = {
            'narration': '🎙️',
            'type': '⌨️',
            'enter': '⏎',
            'sleep': '💤',
            'hidden': '🙈',
            'show': '👁️',
            'exec': '⚡'
        }
        
        print(f"{time_str:>8}  {dur_str:>8}  {event.description:<60}")
    
    total_time = timeline[-1].time_ms + timeline[-1].duration_ms if timeline else 0
    print("─" * 80)
    print(f"{'Total':>8}  {total_time/1000:.2f}s")
    
    # Analyze sync issues
    issues = analyze_sync_issues(timeline, narration_manifest)
    if issues:
        print("\n⚠️  SYNC ISSUES DETECTED:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ No major sync issues detected.")
    
    print()


def calculate_timings(
    lines: list[str],
    config: TapeConfig
) -> tuple[list[str], list[dict], list[TimelineEvent]]:
    """
    Calculate real timings and generate compiled tape.
    
    Now accounts for:
    - TypingSpeed (per-character delay)
    - Enter key delay
    - exec-time hints for command execution
    
    Returns:
        tuple of (compiled_lines, audio_manifest, timeline)
    """
    compiled_lines = []
    audio_manifest = []
    current_time_ms = 0
    
    # Build timeline first for analysis
    timeline, _ = build_timeline(lines, config)
    
    # Track which segments we've processed
    segment_idx = 0
    pending_during = None  # Track 'during' narration
    
    # Patterns
    sleep_pattern = re.compile(r'^Sleep\s+(\d+(?:\.\d+)?)(ms|s)?$', re.IGNORECASE)
    type_pattern = re.compile(r'^Type\s+["\'].*["\']$', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip exec-time hints (they're already processed)
        if stripped.startswith('# @exec-time'):
            continue
        
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
        
        # Handle Type commands - account for typing time
        if type_pattern.match(stripped):
            text = extract_type_text(stripped)
            if text:
                typing_duration = len(text) * config.typing_speed_ms
                current_time_ms += typing_duration
            compiled_lines.append(line)
            continue
        
        # Handle Enter - account for enter delay and exec-time
        if stripped == 'Enter':
            exec_time = config.exec_time_hints.get(i, 0)
            current_time_ms += config.enter_delay_ms + exec_time
            compiled_lines.append(line)
            continue
        
        # Handle Sleep commands - track time
        sleep_match = sleep_pattern.match(stripped)
        if sleep_match:
            value = float(sleep_match.group(1))
            unit = sleep_match.group(2) or 's'
            if unit.lower() == 's':
                value *= 1000
            current_time_ms += int(value)
        
        # Pass through other lines
        compiled_lines.append(line)
    
    return compiled_lines, audio_manifest, timeline


def split_caption_text(text: str, max_chars_per_line: int = 42, max_lines: int = 2) -> list[str]:
    """
    Split long caption text into readable segments.
    
    Each segment will have at most max_lines lines,
    with each line having at most max_chars_per_line characters.
    Splits on word boundaries.
    
    Default values follow broadcast captioning standards:
    - BBC Subtitle Guidelines: max 37 chars/line
      https://www.bbc.co.uk/accessibility/forproducts/guides/subtitles/
    - Netflix Timed Text Style Guide: 42 chars/line for English
      https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617
    - DCMP Captioning Key: 32 chars/line, 2 lines max
      https://dcmp.org/learn/captioningkey
    
    We use 42 chars (Netflix standard) as default for readability on
    modern displays while staying within professional guidelines.
    """
    words = text.split()
    segments = []
    current_segment_lines = []
    current_line = ""
    
    for word in words:
        # Check if adding this word exceeds line length
        test_line = f"{current_line} {word}".strip()
        
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            # Line is full, start new line
            if current_line:
                current_segment_lines.append(current_line)
            
            # Check if segment is full (max_lines reached)
            if len(current_segment_lines) >= max_lines:
                segments.append("\n".join(current_segment_lines))
                current_segment_lines = []
            
            current_line = word
    
    # Don't forget the last line
    if current_line:
        current_segment_lines.append(current_line)
    if current_segment_lines:
        segments.append("\n".join(current_segment_lines))
    
    return segments if segments else [text]


def generate_srt_file(
    audio_manifest: list[dict],
    output_path: Path,
    max_chars_per_line: int = 42,
    max_lines: int = 2
) -> None:
    """
    Generate SRT subtitle file from audio manifest.
    
    Long captions are automatically split into multiple segments
    with timing distributed proportionally based on text length.
    
    Timing considerations follow reading speed guidelines:
    - Average reading speed: 150-180 words/minute (W3C WCAG)
      https://www.w3.org/WAI/media/av/captions/
    - Minimum caption duration: 1 second (FCC guidelines)
    - We use 500ms minimum per segment to allow for split captions
      while maintaining readability when segments are short.
    
    SRT format specification:
    - SubRip text file format (.srt)
    - Timestamps: HH:MM:SS,mmm --> HH:MM:SS,mmm
    - Blank line separates entries
    """
    
    def ms_to_srt_time(ms: int) -> str:
        """Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    
    srt_content = []
    subtitle_index = 1
    
    for segment in audio_manifest:
        if not segment.get('text'):
            continue
        
        text = segment['text']
        start_ms = segment['start_ms']
        total_duration_ms = segment['duration_ms']
        
        # Split long text into readable caption segments
        caption_segments = split_caption_text(text, max_chars_per_line, max_lines)
        
        if len(caption_segments) == 1:
            # Simple case: text fits in one caption
            end_ms = start_ms + total_duration_ms
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{ms_to_srt_time(start_ms)} --> {ms_to_srt_time(end_ms)}")
            srt_content.append(caption_segments[0])
            srt_content.append("")
            subtitle_index += 1
        else:
            # Distribute timing across segments proportionally by character count
            total_chars = sum(len(seg.replace("\n", " ")) for seg in caption_segments)
            current_start = start_ms
            
            for i, cap_text in enumerate(caption_segments):
                # Proportional duration based on character count
                char_count = len(cap_text.replace("\n", " "))
                segment_duration = int(total_duration_ms * char_count / total_chars)
                
                # Ensure minimum duration of 500ms per segment
                segment_duration = max(segment_duration, 500)
                
                # Last segment gets remaining time
                if i == len(caption_segments) - 1:
                    end_ms = start_ms + total_duration_ms
                else:
                    end_ms = current_start + segment_duration
                
                srt_content.append(f"{subtitle_index}")
                srt_content.append(f"{ms_to_srt_time(current_start)} --> {ms_to_srt_time(end_ms)}")
                srt_content.append(cap_text)
                srt_content.append("")
                
                subtitle_index += 1
                current_start = end_ms
    
    output_path.write_text("\n".join(srt_content))


def generate_ffmpeg_mix_command(
    video_file: str,
    audio_manifest: list[dict],
    output_file: str,
    subtitle_file: str = None
) -> str:
    """Generate FFmpeg command to mix video with narration audio and subtitles."""
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
    
    # Add subtitle file input if provided
    if subtitle_file:
        inputs.append(f"-i {subtitle_file}")
        subtitle_input_idx = len(inputs) - 1
    
    # Combine all delayed audio tracks
    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest:normalize=0[narration]"
    
    # Build output mappings
    if subtitle_file:
        # Map video, mixed audio, and subtitles
        cmd = f"""ffmpeg -y \\
  {' '.join(inputs)} \\
  -filter_complex "{filter_complex}" \\
  -map 0:v -map "[narration]" -map {subtitle_input_idx}:s \\
  -c:v copy -c:a aac -b:a 192k -c:s mov_text \\
  -metadata:s:s:0 language=eng -metadata:s:s:0 title="Narration" \\
  {output_file}"""
    else:
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
    parser.add_argument("--timeline", "-t", action="store_true",
                        help="Show detailed timeline analysis (no audio generation)")
    
    args = parser.parse_args()
    
    # Check for API key (not needed for timeline or dry-run)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key and not args.dry_run and not args.timeline:
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
    print(f"   TypingSpeed: {config.typing_speed_ms}ms per character")
    if config.exec_time_hints:
        print(f"   Exec-time hints: {len(config.exec_time_hints)} commands")
    print(f"   Found {len(config.segments)} narration segments:")
    
    for seg in config.segments:
        text_preview = (seg.text[:40] + "...") if seg.text and len(seg.text) > 40 else seg.text
        print(f"     - @narrate:{seg.mode} \"{text_preview}\"")
    
    # Timeline analysis mode
    if args.timeline:
        # For timeline, we need estimated durations - use placeholder values
        for i, seg in enumerate(config.segments):
            if seg.text:
                # Estimate ~150ms per word for speech
                word_count = len(seg.text.split())
                seg.duration_ms = max(1000, word_count * 150)
        
        timeline, narration_manifest = build_timeline(lines, config)
        print_timeline(timeline, narration_manifest, config)
        return
    
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
    compiled_lines, audio_manifest, timeline = calculate_timings(lines, config)
    
    # Show timeline analysis
    print_timeline(timeline, audio_manifest, config)
    
    # Write compiled tape
    compiled_tape_path = args.output_dir / f"{args.tape_file.stem}_compiled.tape"
    compiled_tape_path.write_text("\n".join(compiled_lines))
    print(f"   Compiled tape: {compiled_tape_path}")
    
    # Write audio manifest
    manifest_path = args.output_dir / "audio_manifest.json"
    manifest_path.write_text(json.dumps(audio_manifest, indent=2))
    print(f"   Audio manifest: {manifest_path}")
    
    # Generate SRT subtitle file
    srt_path = args.output_dir / "captions.srt"
    generate_srt_file(audio_manifest, srt_path)
    print(f"   Captions: {srt_path}")
    
    # Generate FFmpeg command
    video_output = args.output_dir / (config.output_file or "output.mp4")
    final_output = args.output_dir / f"{args.tape_file.stem}_final.mp4"
    
    ffmpeg_cmd = generate_ffmpeg_mix_command(
        str(video_output),
        audio_manifest,
        str(final_output),
        subtitle_file=str(srt_path)
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
