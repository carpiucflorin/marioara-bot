from __future__ import annotations

import asyncio
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import winsound
from dataclasses import dataclass
from typing import Optional

import edge_tts


class VoiceError(RuntimeError):
    pass


@dataclass
class VoiceConfig:
    voice: str = "ro-RO-AlinaNeural"
    rate: str = "-8%"
    volume: str = "+5%"
    pitch: str = "+0Hz"


class VoiceEngine:
    def __init__(self, config: Optional[VoiceConfig] = None, enabled: bool = True):
        self.config = config or VoiceConfig()
        self.enabled = enabled
        self._tmp_dir = tempfile.mkdtemp(prefix="marioara_voice_")
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._ffmpeg = self._find_ffmpeg()

    @staticmethod
    def _find_ffmpeg() -> str:
        found = shutil.which("ffmpeg")
        if found:
            return found
        candidates = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise VoiceError(
            "ffmpeg nu a fost găsit. Instalează ffmpeg (winget install Gyan.FFmpeg) "
            "sau adaugă-l în PATH."
        )

    def is_available(self) -> bool:
        return self.enabled and bool(self._ffmpeg)

    def set_voice(self, voice: str) -> None:
        self.config.voice = voice

    def _ensure_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    def _run_worker(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while not self._stop_event.is_set() or not self._queue.empty():
                try:
                    text = self._queue.get(timeout=0.3)
                except queue.Empty:
                    continue
                try:
                    wav_path = loop.run_until_complete(self._synthesize(text))
                    if wav_path and os.path.exists(wav_path):
                        winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                except Exception as exc:
                    print(f"[voice] eroare redare: {exc}")
                finally:
                    self._queue.task_done()
        finally:
            loop.close()

    async def _synthesize(self, text: str) -> Optional[str]:
        text = (text or "").strip()
        if not text:
            return None
        short = "".join(c for c in text[:24] if c.isalnum() or c in "-_") or "msg"
        mp3_path = os.path.join(self._tmp_dir, f"{short}.mp3")
        wav_path = os.path.join(self._tmp_dir, f"{short}.wav")
        communicate = edge_tts.Communicate(
            text,
            self.config.voice,
            rate=self.config.rate,
            volume=self.config.volume,
            pitch=self.config.pitch,
        )
        await communicate.save(mp3_path)
        result = subprocess.run(
            [
                self._ffmpeg, "-y", "-loglevel", "error",
                "-i", mp3_path,
                "-ar", "22050", "-ac", "1", wav_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not os.path.exists(wav_path):
            raise VoiceError(f"conversie ffmpeg eșuată: {result.stderr.strip()}")
        try:
            os.remove(mp3_path)
        except OSError:
            pass
        return wav_path

    def speak(self, text: str) -> None:
        if not self.is_available():
            return
        self._ensure_worker()
        self._queue.put(text)

    def speak_blocking(self, text: str) -> None:
        if not self.is_available():
            return
        loop = asyncio.new_event_loop()
        try:
            wav_path = loop.run_until_complete(self._synthesize(text))
        finally:
            loop.close()
        if wav_path and os.path.exists(wav_path):
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)

    def stop(self) -> None:
        self._stop_event.set()
        winsound.PlaySound(None, winsound.SND_PURGE)

    def cleanup(self) -> None:
        self.stop()
        try:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        except OSError:
            pass
