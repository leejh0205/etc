"""A small push-to-talk personal voice assistant.

Press Enter to record, speak for a few seconds, and press Enter again to stop.
Type /quit to close the assistant.
"""

from __future__ import annotations

import os
import queue
import sys
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np
import pygame
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI

SAMPLE_RATE = 16_000
CHANNELS = 1
SYSTEM_PROMPT = (
    "You are Nova, a warm, concise personal voice assistant. "
    "Give helpful answers that sound natural when spoken aloud. "
    "Keep most replies under three short sentences unless detail is requested."
)


class VoiceAssistant:
    def __init__(self) -> None:
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to a .env file before starting."
            )

        self.client = OpenAI()
        self.voice = os.getenv("ASSISTANT_VOICE", "coral")
        self.chat_model = os.getenv("ASSISTANT_MODEL", "gpt-5-mini")
        self.history: list[dict[str, str]] = []
        pygame.mixer.init()

    def record_audio(self) -> Path:
        """Record from the default microphone until the user presses Enter."""
        frames: queue.Queue[np.ndarray] = queue.Queue()
        recording = threading.Event()
        recording.set()

        def callback(indata: np.ndarray, _frames: int, _time: object, status: sd.CallbackFlags) -> None:
            if status:
                print(f"\nMicrophone warning: {status}", file=sys.stderr)
            if recording.is_set():
                frames.put(indata.copy())

        def wait_for_stop() -> None:
            input()
            recording.clear()

        print("Listening... press Enter when you are finished.")
        stopper = threading.Thread(target=wait_for_stop, daemon=True)
        stopper.start()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=callback,
        ):
            while recording.is_set():
                sd.sleep(100)

        audio = []
        while not frames.empty():
            audio.append(frames.get())
        if not audio:
            raise RuntimeError("No audio was captured. Check your microphone permissions.")

        descriptor, file_name = tempfile.mkstemp(suffix=".wav")
        os.close(descriptor)
        path = Path(file_name)
        with wave.open(str(path), "wb") as audio_file:
            audio_file.setnchannels(CHANNELS)
            audio_file.setsampwidth(2)
            audio_file.setframerate(SAMPLE_RATE)
            audio_file.writeframes(np.concatenate(audio).tobytes())
        return path

    def transcribe(self, audio_path: Path) -> str:
        with audio_path.open("rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe", file=audio_file
            )
        return result.text.strip()

    def answer(self, user_text: str) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history[-8:])
        messages.append({"role": "user", "content": user_text})
        response = self.client.responses.create(model=self.chat_model, input=messages)
        reply = response.output_text.strip()
        self.history.extend(
            [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
        )
        return reply

    def speak(self, text: str) -> None:
        descriptor, file_name = tempfile.mkstemp(suffix=".mp3")
        os.close(descriptor)
        output_path = Path(file_name)
        try:
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts", voice=self.voice, input=text
            ) as response:
                response.stream_to_file(output_path)
            pygame.mixer.music.load(str(output_path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
        finally:
            pygame.mixer.music.unload()
            output_path.unlink(missing_ok=True)

    def run(self) -> None:
        print("Nova is ready. Press Enter to talk, or type /quit and press Enter to exit.")
        while True:
            command = input("\n> ").strip()
            if command.lower() in {"/quit", "/exit"}:
                print("Goodbye!")
                return
            if command:
                print("Please press Enter to record, or type /quit.")
                continue

            audio_path: Path | None = None
            try:
                audio_path = self.record_audio()
                print("Transcribing...")
                transcript = self.transcribe(audio_path)
                if not transcript:
                    print("I didn't catch that. Please try again.")
                    continue
                print(f"You: {transcript}")
                print("Thinking...")
                reply = self.answer(transcript)
                print(f"Nova: {reply}")
                self.speak(reply)
            except Exception as error:
                print(f"\nSomething went wrong: {error}", file=sys.stderr)
            finally:
                if audio_path:
                    audio_path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        VoiceAssistant().run()
    except RuntimeError as error:
        print(f"Setup error: {error}", file=sys.stderr)
        raise SystemExit(1)
