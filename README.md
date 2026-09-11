# Nova: Python voice assistant

Nova is a small push-to-talk assistant. It records your microphone, sends the clip for transcription, asks an AI model for a response, and speaks that response aloud.

## Setup (Windows PowerShell)

1. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`, then replace `your_api_key_here` with an OpenAI API key. Keep this file private.

4. Start it:

   ```powershell
   python python.py
   ```

Press Enter to start recording, speak, then press Enter again to stop. Type `/quit` to close it.

## Next features

* Add wake-word detection.
* Add local actions such as opening applications or creating reminders, with an explicit confirmation step.
* Replace push-to-talk with OpenAI Realtime for more natural, low-latency conversation.
