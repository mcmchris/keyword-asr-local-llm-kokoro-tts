# Local Edge AI Voice Assistant (Kokoro TTS Edition)

A fully offline, privacy-first voice assistant built with Arduino App Lab for the VENTUNO Q. It features a Local Large Language Model (LLM), real-time speech recognition, LED animations, and high-fidelity speech synthesis using Kokoro TTS.

## Project Structure

This project follows the standard Arduino App Lab multi-language architecture, with the addition of a custom module directory:

* `app.yaml`: Main application configuration.
* `assets/bricks/kokoro_tts/`: **Custom Brick module** integrating the Kokoro Text-to-Speech engine.
* `python/main.py`: The core Python backend managing the AI models, state machine, and hardware orchestration.
* `sketch/sketch.ino`: The C++ firmware handling the hardware-level LED matrix animations.
* `sketch/sketch.yaml`: Microcontroller build configuration.

## 🧩 Powered by Custom Bricks

This application takes full advantage of the **Custom Bricks** feature. 

Since the advanced Kokoro TTS model is not part of the standard built-in Bricks library, it is bundled directly into the project under the `assets/bricks/` directory. This allows the Python backend to seamlessly import and utilize the `KokoroTTS` class just like any native component (`from kokoro_tts import KokoroTTS`), demonstrating how developers can extend the Arduino App Lab ecosystem with their own state-of-the-art AI models.

## Bricks Used

This project leverages the following AI components to build the voice assistant pipeline:

* **Keyword Spotting:** A lightweight, always-on listener that detects the wake word to activate the system.
* **Automatic Speech Recognition (ASR):** Transcribes live audio from your microphone into text.
* **Large Language Model (LLM):** The core intelligence that processes your transcribed commands and generates intelligent responses.
* **Kokoro TTS (Custom Brick):** A custom-integrated, high-fidelity Text-to-Speech engine that converts the assistant's text responses back into spoken audio.

## Architecture & Workflow

### The Python Brain (`main.py`)
The Python application acts as the central orchestrator, chaining multiple AI models into a seamless pipeline:
1. **Keyword Spotting:** A lightweight model constantly monitors the microphone for the wake word: *"Ventuno"*.
2. **Automatic Speech Recognition (ASR):** Once awake, it records and transcribes the user's voice command.
3. **Context Injection:** The system dynamically reads the local hardware time via `zoneinfo` and injects it as an invisible system prompt, giving the offline LLM awareness of the current date and time.
4. **Local LLM:** The transcribed text is sent to the `genie:qwen3-4b` model running locally on the NPU.
5. **Text-to-Speech (Kokoro):** The generated response is synthesized into a temporary `.wav` file by the Custom Brick. The system then forces playback directly to a specific hardware device using native Linux audio protocols (`aplay -D plughw:1,0`).

To keep the hardware UI synchronized, Python uses `Bridge.call("set_state", X)` to broadcast the current status (Idle, Listening, Processing, Speaking) down to the microcontroller.

### The Hardware UI (`sketch.ino`)
The C++ sketch runs on the VENTUNO Q's MCU and listens for Remote Procedure Calls (RPC) from the Python environment. It updates the `currentState` variable to drive the onboard 104-LED matrix using a 3-bit grayscale color space.

The UI provides instant visual feedback based on the AI's state:
* **Idle (State 0):** The matrix clears completely to save power.
* **Listening & Processing (States 1 & 2):** Renders a scanner animation using a cubic falloff algorithm for a smooth visual tail. The scanner moves faster while actively capturing audio compared to when the LLM is thinking.
* **Speaking (State 3):** Generates organic voice waveforms using combined sine waves that dynamically pulse with the simulated volume of the TTS.

## Hardware Requirements

* USB Microphone (Connected to USB-A)
* USB Headset/Speaker (Connected to USB-A. Note: `main.py` maps the output explicitly to ALSA card 1, device 0).