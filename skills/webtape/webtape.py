#!/usr/bin/env python3
"""
WebTape - VHS-like declarative browser recording tool.

A proof of concept for creating web app demo videos using a simple DSL
similar to charmbracelet/vhs tape files.

Example .webtape file:
    Output demo.mp4
    Set Width 1280
    Set Height 720
    
    Navigate "http://localhost:3000"
    Sleep 1s
    
    # @narrate:before "Let me show you the login form"
    Click "button#login"
    Type "#email" "user@example.com"
    Sleep 2s
"""

import asyncio
import re
import sys
import os
import tempfile
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# Import TTS module (optional)
try:
    from scripts.tts import generate_speech, get_audio_duration, get_voice_id
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


@dataclass
class WebTapeConfig:
    """Configuration parsed from Set commands."""
    output: str = "output.mp4"
    width: int = 1280
    height: int = 720
    framerate: int = 30
    typing_speed: int = 50  # ms per character
    theme: str = "light"
    voice: Optional[str] = None
    narration_enabled: bool = True


@dataclass 
class NarrationSegment:
    """Audio segment for narration."""
    audio_path: Path
    start_time: float  # seconds from video start
    duration: float
    text: str


@dataclass
class Action:
    """A single action to perform."""
    command: str
    args: list = field(default_factory=list)
    narration: Optional[dict] = None  # {"mode": "before|during|after", "text": "..."}
    line_number: int = 0


class WebTapeParser:
    """Parse .webtape files into actions."""
    
    def __init__(self, content: str):
        self.content = content
        self.config = WebTapeConfig()
        self.actions: list[Action] = []
        self._pending_narration: Optional[dict] = None
    
    def parse(self) -> tuple[WebTapeConfig, list[Action]]:
        lines = self.content.strip().split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Handle narration macros
            if line.startswith('# @voice '):
                # e.g., # @voice eleven:rachel
                voice = line.split('# @voice ')[1].strip()
                self.config.voice = voice
                continue
            
            if line.startswith('# @narrate:'):
                # e.g., # @narrate:before "Welcome to the demo"
                match = re.match(r'# @narrate:(before|during|after)\s+"([^"]+)"', line)
                if match:
                    self._pending_narration = {
                        "mode": match.group(1),
                        "text": match.group(2)
                    }
                continue
            
            # Skip regular comments
            if line.startswith('#'):
                continue
            
            # Parse commands
            action = self._parse_line(line, i)
            if action:
                # Attach any pending narration
                if self._pending_narration:
                    action.narration = self._pending_narration
                    self._pending_narration = None
                self.actions.append(action)
        
        return self.config, self.actions
    
    def _parse_line(self, line: str, line_num: int) -> Optional[Action]:
        # Handle Output command
        if line.startswith('Output '):
            match = re.match(r'Output\s+"?([^"]+)"?', line)
            if match:
                self.config.output = match.group(1)
            return None
        
        # Handle Set commands
        if line.startswith('Set '):
            match = re.match(r'Set\s+(\w+)\s+"?([^"]+)"?', line)
            if match:
                key, value = match.groups()
                key_lower = key.lower()
                if key_lower == 'width':
                    self.config.width = int(value)
                elif key_lower == 'height':
                    self.config.height = int(value)
                elif key_lower == 'framerate':
                    self.config.framerate = int(value)
                elif key_lower == 'typingspeed':
                    self.config.typing_speed = int(value.replace('ms', ''))
                elif key_lower == 'theme':
                    self.config.theme = value.strip('"')
            return None
        
        # Parse action commands
        # Format: Command "arg1" "arg2" ...
        match = re.match(r'(\w+)(.*)', line)
        if match:
            cmd = match.group(1)
            args_str = match.group(2).strip()
            args = re.findall(r'"([^"]*)"', args_str)
            
            # Handle time arguments like "2s" or "500ms"
            if not args:
                time_match = re.match(r'\s*(\d+(?:ms|s))', args_str)
                if time_match:
                    args = [time_match.group(1)]
            
            return Action(command=cmd, args=args, line_number=line_num)
        
        return None


class WebTapeRunner:
    """Execute webtape actions using Playwright."""
    
    def __init__(self, config: WebTapeConfig, actions: list[Action], verbose: bool = False):
        self.config = config
        self.actions = actions
        self.verbose = verbose
        self.browser = None
        self.context = None
        self.page = None
        self.narration_segments: list[NarrationSegment] = []
        self.current_time: float = 0.0  # Track elapsed time for narration sync
        self.temp_dir: Optional[Path] = None
    
    def log(self, msg: str):
        if self.verbose:
            print(f"  [webtape] {msg}")
    
    async def run(self):
        """Execute all actions and produce video output."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="webtape_"))
        audio_dir = self.temp_dir / "audio"
        audio_dir.mkdir()
        
        async with async_playwright() as p:
            self.log(f"Launching browser (headless, {self.config.width}x{self.config.height})")
            
            video_dir = self.temp_dir / "video"
            video_dir.mkdir()
            
            self.browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            self.context = await self.browser.new_context(
                viewport={"width": self.config.width, "height": self.config.height},
                record_video_dir=str(video_dir),
                record_video_size={"width": self.config.width, "height": self.config.height}
            )
            
            self.page = await self.context.new_page()
            
            try:
                for action in self.actions:
                    await self._execute_action(action, audio_dir)
                
                # Small delay before closing to ensure final frames are captured
                await asyncio.sleep(0.5)
                self.current_time += 0.5
                
            finally:
                # Close page and context to finalize video
                await self.page.close()
                await self.context.close()
                await self.browser.close()
            
            # Find the recorded video
            video_files = list(video_dir.glob("*.webm"))
            if video_files:
                source_video = video_files[0]
                output_path = Path(self.config.output)
                
                # Mix audio if we have narration segments
                if self.narration_segments and TTS_AVAILABLE:
                    self.log(f"Mixing {len(self.narration_segments)} narration segment(s)...")
                    final_video = self._mix_audio_with_video(source_video, output_path)
                    if final_video:
                        output_path = final_video
                    else:
                        # Fall back to video without audio
                        output_path = self._convert_video(source_video, output_path)
                else:
                    output_path = self._convert_video(source_video, output_path)
                
                print(f"✓ Video saved to: {output_path}")
                
                # Cleanup temp directory
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            else:
                print("Warning: No video file was produced")
    
    def _convert_video(self, source: Path, output: Path) -> Path:
        """Convert video to output format."""
        if output.suffix.lower() == '.webm':
            shutil.copy(source, output)
            return output
        
        self.log(f"Converting to {output.suffix}...")
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            subprocess.run([
                ffmpeg_path, '-y', '-i', str(source),
                '-c:v', 'libx264', '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                str(output)
            ], check=True, capture_output=True)
            return output
        except Exception as e:
            print(f"Warning: Could not convert video: {e}")
            output = output.with_suffix('.webm')
            shutil.copy(source, output)
            return output
    
    def _mix_audio_with_video(self, video_path: Path, output_path: Path) -> Optional[Path]:
        """Mix narration audio segments with video."""
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            self.log("imageio-ffmpeg not available for audio mixing")
            return None
        
        if not self.narration_segments:
            return None
        
        # Create a combined audio track using ffmpeg filter_complex
        # First, create silence for the full video duration
        temp_audio = self.temp_dir / "combined_audio.mp3"
        
        # Build ffmpeg command for mixing audio
        # We'll create an audio mix using amix or amerge
        inputs = ['-i', str(video_path)]
        filter_parts = []
        
        for i, segment in enumerate(self.narration_segments):
            inputs.extend(['-i', str(segment.audio_path)])
            # Delay each audio segment to its start time
            delay_ms = int(segment.start_time * 1000)
            filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        
        # Mix all audio streams
        audio_refs = ''.join(f'[a{i}]' for i in range(len(self.narration_segments)))
        filter_parts.append(f"{audio_refs}amix=inputs={len(self.narration_segments)}:duration=longest[aout]")
        
        filter_complex = ';'.join(filter_parts)
        
        # Build final command
        cmd = [ffmpeg_path, '-y']
        cmd.extend(inputs)
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            str(output_path)
        ])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return output_path
            else:
                self.log(f"Audio mixing failed: {result.stderr[:200]}")
                return None
        except Exception as e:
            self.log(f"Audio mixing error: {e}")
            return None
    
    async def _execute_action(self, action: Action, audio_dir: Path):
        """Execute a single action."""
        cmd = action.command.lower()
        args = action.args
        
        self.log(f"Line {action.line_number}: {action.command} {args}")
        
        # Handle "before" narration - speak first, then do action
        if action.narration and action.narration['mode'] == 'before':
            await self._handle_narration(action.narration, audio_dir)
        
        # Handle "during" narration - start speaking and do action simultaneously
        narration_task = None
        if action.narration and action.narration['mode'] == 'during':
            # Generate audio but don't wait for it
            narration_task = asyncio.create_task(
                self._handle_narration(action.narration, audio_dir, wait=False)
            )
        
        if cmd == 'navigate':
            url = args[0] if args else 'about:blank'
            await self.page.goto(url)
            
        elif cmd == 'click':
            selector = args[0] if args else 'body'
            await self.page.click(selector)
            
        elif cmd == 'type':
            if len(args) >= 2:
                selector, text = args[0], args[1]
                # Type with delay for visual effect
                await self.page.type(selector, text, delay=self.config.typing_speed)
            elif len(args) == 1:
                # Type into currently focused element
                await self.page.keyboard.type(args[0], delay=self.config.typing_speed)
                
        elif cmd == 'fill':
            if len(args) >= 2:
                selector, text = args[0], args[1]
                await self.page.fill(selector, text)
                
        elif cmd == 'press':
            key = args[0] if args else 'Enter'
            await self.page.keyboard.press(key)
            
        elif cmd == 'sleep':
            duration = self._parse_time(args[0]) if args else 1.0
            await asyncio.sleep(duration)
            self.current_time += duration
            
        elif cmd == 'wait':
            selector = args[0] if args else 'body'
            await self.page.wait_for_selector(selector)
            
        elif cmd == 'scroll':
            direction = args[0].lower() if args else 'down'
            amount = int(args[1]) if len(args) > 1 else 300
            if direction == 'down':
                await self.page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == 'up':
                await self.page.evaluate(f"window.scrollBy(0, -{amount})")
                
        elif cmd == 'screenshot':
            # Take a screenshot (useful for debugging)
            filename = args[0] if args else 'screenshot.png'
            await self.page.screenshot(path=filename)
            self.log(f"  Screenshot saved: {filename}")
            
        elif cmd == 'hover':
            selector = args[0] if args else 'body'
            await self.page.hover(selector)
            
        elif cmd == 'highlight':
            # Add visual highlight to an element (for demos)
            selector = args[0] if args else 'body'
            await self.page.evaluate(f'''
                const el = document.querySelector("{selector}");
                if (el) {{
                    el.style.outline = "3px solid #ff0000";
                    el.style.outlineOffset = "2px";
                }}
            ''')
            
        elif cmd == 'unhighlight':
            selector = args[0] if args else 'body'
            await self.page.evaluate(f'''
                const el = document.querySelector("{selector}");
                if (el) {{
                    el.style.outline = "";
                    el.style.outlineOffset = "";
                }}
            ''')
        
        # Wait for "during" narration to complete if applicable
        if narration_task:
            await narration_task
        
        # Handle "after" narration - do action first, then speak
        if action.narration and action.narration['mode'] == 'after':
            await self._handle_narration(action.narration, audio_dir)
    
    async def _handle_narration(self, narration: dict, audio_dir: Path, wait: bool = True):
        """Generate and track narration audio."""
        if not TTS_AVAILABLE:
            self.log(f"  Narration (TTS unavailable): {narration['text']}")
            # Still pause to maintain timing expectations
            await asyncio.sleep(1.0)
            self.current_time += 1.0
            return
        
        if not self.config.narration_enabled:
            return
        
        voice = self.config.voice or "rachel"
        # Handle "eleven:voicename" format
        if ":" in voice:
            voice = voice.split(":")[-1]
        
        text = narration['text']
        self.log(f"  Generating narration: \"{text[:50]}...\"" if len(text) > 50 else f"  Generating narration: \"{text}\"")
        
        # Generate audio file
        audio_path = audio_dir / f"narration_{len(self.narration_segments):03d}.mp3"
        result = generate_speech(text, voice=voice, output_path=str(audio_path))
        
        if result:
            duration = get_audio_duration(result)
            
            # Record the segment for later mixing
            segment = NarrationSegment(
                audio_path=result,
                start_time=self.current_time,
                duration=duration,
                text=text
            )
            self.narration_segments.append(segment)
            self.log(f"  Audio: {duration:.1f}s @ {self.current_time:.1f}s")
            
            if wait:
                # Wait for the narration duration (video keeps recording)
                await asyncio.sleep(duration)
                self.current_time += duration
        else:
            # TTS failed, just add a pause
            await asyncio.sleep(1.0)
            self.current_time += 1.0
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time strings like '2s' or '500ms' to seconds."""
        time_str = time_str.strip()
        if time_str.endswith('ms'):
            return float(time_str[:-2]) / 1000
        elif time_str.endswith('s'):
            return float(time_str[:-1])
        else:
            return float(time_str)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='WebTape - VHS-like declarative browser recording',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example .webtape file:
    Output demo.mp4
    Set Width 1280
    Set Height 720
    
    # @voice eleven:rachel
    
    Navigate "https://example.com"
    Sleep 1s
    
    # @narrate:before "Let me show you this feature"
    Click "a.nav-link"
    Sleep 2s
        """
    )
    parser.add_argument('tapefile', nargs='?', help='Path to .webtape file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output', help='Override output filename')
    parser.add_argument('--no-narration', action='store_true', 
                        help='Disable TTS narration (video only)')
    parser.add_argument('--voice', help='Override voice (e.g., rachel, adam)')
    parser.add_argument('--list-voices', action='store_true',
                        help='List available TTS voices and exit')
    
    args = parser.parse_args()
    
    # Handle --list-voices
    if args.list_voices:
        if TTS_AVAILABLE:
            from scripts.tts import list_voices
            list_voices()
        else:
            print("TTS not available. Install with: pip install requests")
        sys.exit(0)
    
    # Require tapefile for normal operation
    if not args.tapefile:
        parser.print_help()
        sys.exit(1)
    
    # Read tape file
    tape_path = Path(args.tapefile)
    if not tape_path.exists():
        print(f"Error: File not found: {tape_path}")
        sys.exit(1)
    
    content = tape_path.read_text()
    
    # Parse
    parser_obj = WebTapeParser(content)
    config, actions = parser_obj.parse()
    
    # Override options
    if args.output:
        config.output = args.output
    if args.no_narration:
        config.narration_enabled = False
    if args.voice:
        config.voice = args.voice
    
    # Count narrations
    narration_count = sum(1 for a in actions if a.narration)
    
    print(f"WebTape: {tape_path}")
    print(f"  Output: {config.output}")
    print(f"  Size: {config.width}x{config.height}")
    print(f"  Actions: {len(actions)}")
    if narration_count > 0:
        tts_status = "enabled" if config.narration_enabled and TTS_AVAILABLE else "disabled"
        print(f"  Narrations: {narration_count} ({tts_status})")
        if config.voice:
            print(f"  Voice: {config.voice}")
    
    # Run
    runner = WebTapeRunner(config, actions, verbose=args.verbose)
    asyncio.run(runner.run())


if __name__ == '__main__':
    main()
