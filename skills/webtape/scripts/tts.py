#!/usr/bin/env python3
"""
TTS integration for WebTape.

Supports multiple TTS backends:
1. ElevenLabs (requires ELEVENLABS_API_KEY) - High quality
2. Google TTS (gTTS) - Free fallback

Usage:
    # With ElevenLabs
    ELEVENLABS_API_KEY=xxx python tts.py "Hello" -v rachel
    
    # With Google TTS (fallback)
    python tts.py "Hello" --gtts
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ElevenLabs voice IDs (common voices)
VOICE_IDS = {
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "antoni": "ErXwobaYiN019PkySvjV",
    "bella": "EXAVITQu4vr4xnSDxMaL",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "elli": "MF3mGyEYCl7XYWbV9V6O",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
    "arnold": "VR6AewLTigWG4xSOukaG",
    "sam": "yoZ06aMxZJJ28mfd3POQ",
    "nicole": "piTKgcLEGmPE4e6mEKli",
}

# Google TTS language/accent options
GTTS_ACCENTS = {
    "us": "en",      # US English
    "uk": "en-uk",   # UK English  
    "au": "en-au",   # Australian English
    "in": "en-in",   # Indian English
}

DEFAULT_MODEL = "eleven_monolingual_v1"
API_BASE = "https://api.elevenlabs.io/v1"

# Check for gTTS availability
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


def get_api_key() -> Optional[str]:
    """Get ElevenLabs API key from environment."""
    return os.environ.get("ELEVENLABS_API_KEY")


def get_voice_id(voice_name: str) -> str:
    """Get voice ID from name or return the name if it looks like an ID."""
    voice_lower = voice_name.lower()
    if voice_lower in VOICE_IDS:
        return VOICE_IDS[voice_lower]
    # Assume it's already a voice ID
    return voice_name


def generate_speech_gtts(
    text: str,
    output_path: Optional[str] = None,
    lang: str = "en",
    slow: bool = False,
) -> Optional[Path]:
    """
    Generate speech using Google TTS (free fallback).
    
    Args:
        text: Text to convert to speech
        output_path: Path for output MP3 file
        lang: Language code (en, en-uk, en-au, en-in)
        slow: Speak slowly
    
    Returns:
        Path to generated audio file, or None on error
    """
    if not GTTS_AVAILABLE:
        print("Warning: gTTS not installed. Run: pip install gTTS")
        return None
    
    try:
        # Determine output path
        if output_path is None:
            import tempfile
            fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="tts_")
            os.close(fd)
        
        output_file = Path(output_path)
        
        # Generate speech
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(output_file))
        
        return output_file
        
    except Exception as e:
        print(f"gTTS Error: {e}")
        return None


def generate_speech_elevenlabs(
    text: str,
    voice: str = "rachel",
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Optional[Path]:
    """
    Generate speech audio from text using ElevenLabs.
    
    Args:
        text: Text to convert to speech
        voice: Voice name (e.g., 'rachel', 'adam') or voice ID
        output_path: Path for output MP3 file (auto-generated if None)
        model: ElevenLabs model ID
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity boost (0-1)
    
    Returns:
        Path to generated audio file, or None on error
    """
    api_key = get_api_key()
    if not api_key:
        return None
    
    voice_id = get_voice_id(voice)
    url = f"{API_BASE}/text-to-speech/{voice_id}"
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        }
    }
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                # Determine output path
                if output_path is None:
                    import tempfile
                    fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="tts_")
                    os.close(fd)
                
                output_file = Path(output_path)
                output_file.write_bytes(response.read())
                return output_file
            else:
                return None
                
    except urllib.error.HTTPError as e:
        # Silently fail - will fallback to gTTS
        return None
    except urllib.error.URLError as e:
        return None
    except Exception as e:
        return None


def generate_speech(
    text: str,
    voice: str = "rachel",
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    use_gtts: bool = False,
) -> Optional[Path]:
    """
    Generate speech audio from text.
    
    Tries ElevenLabs first, falls back to Google TTS if unavailable.
    
    Args:
        text: Text to convert to speech
        voice: Voice name (e.g., 'rachel', 'adam') or voice ID
        output_path: Path for output MP3 file (auto-generated if None)
        model: ElevenLabs model ID
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity boost (0-1)
        use_gtts: Force use of Google TTS
    
    Returns:
        Path to generated audio file, or None on error
    """
    # If forced to use gTTS or no ElevenLabs key
    if use_gtts or not get_api_key():
        if GTTS_AVAILABLE:
            return generate_speech_gtts(text, output_path)
        else:
            print("Warning: No TTS backend available")
            return None
    
    # Try ElevenLabs first
    result = generate_speech_elevenlabs(
        text, voice, output_path, model, stability, similarity_boost
    )
    
    # Fallback to gTTS if ElevenLabs fails
    if result is None and GTTS_AVAILABLE:
        print("  (Using Google TTS fallback)")
        return generate_speech_gtts(text, output_path)
    
    return result


def get_audio_duration(audio_path: Path) -> float:
    """
    Get duration of audio file in seconds.
    
    Uses ffprobe if available, otherwise estimates from file size.
    """
    try:
        import imageio_ffmpeg
        ffprobe = imageio_ffmpeg.get_ffmpeg_exe().replace("ffmpeg", "ffprobe")
        
        import subprocess
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    
    # Fallback: estimate based on file size (very rough for MP3)
    # Assuming ~128kbps MP3: 16KB per second
    file_size = audio_path.stat().st_size
    return file_size / 16000


def list_voices():
    """List available voices (both preset and from API if key available)."""
    print("Preset voices:")
    for name, vid in VOICE_IDS.items():
        print(f"  {name}: {vid}")
    
    api_key = get_api_key()
    if api_key:
        print("\nFetching voices from ElevenLabs API...")
        try:
            url = f"{API_BASE}/voices"
            req = urllib.request.Request(
                url,
                headers={"xi-api-key": api_key},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                print(f"\nYour ElevenLabs voices ({len(data.get('voices', []))}):")
                for voice in data.get("voices", []):
                    print(f"  {voice['name']}: {voice['voice_id']}")
        except Exception as e:
            print(f"Could not fetch voices: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ElevenLabs TTS for WebTape")
    parser.add_argument("text", nargs="?", help="Text to convert to speech")
    parser.add_argument("-v", "--voice", default="rachel", help="Voice name or ID")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    
    args = parser.parse_args()
    
    if args.list_voices:
        list_voices()
    elif args.text:
        result = generate_speech(args.text, voice=args.voice, output_path=args.output)
        if result:
            print(f"Audio saved to: {result}")
        else:
            sys.exit(1)
    else:
        parser.print_help()
