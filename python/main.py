import os
import time
from arduino.app_utils import App, Bridge
from arduino.app_bricks.llm import LargeLanguageModel
from arduino.app_bricks.asr import AutomaticSpeechRecognition
from arduino.app_peripherals.microphone import Microphone
from arduino.app_bricks.keyword_spotting import KeywordSpotting
from kokoro_tts import KokoroTTS
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from requests.exceptions import ReadTimeout, ConnectionError

print("="*50)
print("🚀 PHASE 1: Loading LOCAL LLM into RAM...")
print("="*50)

llm = LargeLanguageModel(
    model="genie:qwen3-4b", 
    system_prompt="You are a helpful voice assistant. Keep your answers brief, conversational, and maximum two sentences long. Whenever your answer includes a symbol or unit change it by its word; for example 86% = 86 percent and avoid emojis."
)
llm.with_memory(5)

try:
    print("⏳ Moving ~8GB of data to NPU. Please wait a moment...")
    llm.chat("Respond 'ok'")
    print("✅ Local LLM Loaded.")
except Exception as e:
    print(f"❌ Critical error loading LLM: {e}")

print("\n" + "="*50)
print("🎙️ INITIALIZING AUDIO & KOKORO TTS")
print("="*50)

# Initialize and warmup Kokoro TTS
tts = KokoroTTS()
print("⏳ Haciendo warmup de Kokoro TTS...")
tts.warmup()
print("✅ Kokoro TTS listo.")

mic_spotter = Microphone()
mic_asr = Microphone()
asr = AutomaticSpeechRecognition()

app_state = "IDLE" 
user_text = ""

def on_keyword_detected():
    global app_state
    if app_state == "IDLE":
        print("\n✨ Wake word 'VENTUNO' detected!")
        app_state = "LISTENING"

spotter = KeywordSpotting(mic=mic_spotter, confidence=0.90, debounce_sec=2.0)
spotter.on_detect("Ventuno", on_keyword_detected)

mic_spotter.start()
asr.start()
spotter.start()

# STATE 0: IDLE
Bridge.call("set_state", 0)
print("\n✅ All systems online! 💤 Listening for 'Ventuno'...")

def loop():
    global app_state, user_text
    
    if app_state == "IDLE":
        time.sleep(0.1)
        return

    elif app_state == "LISTENING":
        user_text = ""
        partial_text = "" 
        
        mic_asr.start()
        time.sleep(0.1) 
        
        # STATE 1: LISTENING
        Bridge.call("set_state", 1) 
        
        print("\n🟢 ASR ACTIVE: Tell me your command! (Speak now)...")
        
        try:
            with asr.transcribe_mic_stream(mic_asr, duration=7) as stream:
                for chunk in stream:
                    match chunk.type:
                        case "partial_text":
                            print(f"\r👂 Listening: {chunk.data}", end="", flush=True)
                            partial_text = chunk.data.strip()
                        case "full_text":
                            user_text = chunk.data.strip()
                            break 
                            
        # --- ASR EXCEPTION HANDLING ---
        except (ReadTimeout, ConnectionError) as e:
            print(f"\n⚠️ Container Connection Timeout: {e}")
            user_text = "" 
        except RuntimeError as e:
            print(f"\n⚠️ ASR Container Crashed (Timeout): {e}")
            user_text = "" 
        except Exception as e:
            if partial_text and not user_text:
                user_text = partial_text
            else:
                print(f"\n⚠️ Unexpected ASR Error: {e}")
                user_text = ""
        # ------------------------------

        if partial_text and not user_text:
            user_text = partial_text
            
        time.sleep(1.5) # Allow ASR hardware resources to release safely
        mic_asr.stop()
        
        if user_text:
            print(f"\n🗣️ You said: {user_text}")
            # STATE 2: PROCESSING
            Bridge.call("set_state", 2)
            app_state = "PROCESSING"
        else:
            print("\n🤷 No command heard or ASR timeout. Returning to sleep...")
            Bridge.call("set_state", 0) # Turn off LED matrix
            app_state = "IDLE"
            return 

    elif app_state == "PROCESSING":
        print("🧠 AI Thinking (Local): ", end="", flush=True)
        llm_response = ""
        
        try:
            time_zone = ZoneInfo("America/Santo_Domingo")
            local_time = datetime.now(time_zone)
            
            # Format the time
            formatted_time = local_time.strftime("%I:%M %p, %A, %B %d, %Y")
            
            # Build the invisible prompt for context injection
            enriched_prompt = f"[System info: The current local time and date is {formatted_time}]\n\nUser command: {user_text}"
            
            for chunk in llm.chat_stream(enriched_prompt):
                print(chunk, end="", flush=True)
                llm_response += chunk
            print() 
            
            time.sleep(0.5) # Allow NPU to release memory bus
            
            if llm_response:
                print("🔊 Speaking via Kokoro...")
                # STATE 3: SPEAKING
                Bridge.call("set_state", 3)
                
                # --- KOKORO TTS INTEGRATION ---
                # 1. Generate audio bytes
                wav_bytes = tts.synth(
                    llm_response,
                    voice="af_heart", 
                    speed=1.0,
                    lang="en-us"
                )
                
                # 2. Save temporary WAV file
                wav_path = "/tmp/assistant_response.wav"
                with open(wav_path, "wb") as f:
                    f.write(wav_bytes)
                
                # 3. Play audio forcing output to specific hardware (Razer Barracuda X)
                os.system(f"aplay -D plughw:1,0 {wav_path} -q")
                # ------------------------------
                
        # --- LLM / TTS EXCEPTION HANDLING ---
        except (ReadTimeout, ConnectionError, RuntimeError) as e:
            print(f"\n⚠️ Container Error during AI/TTS Processing: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error processing Local LLM/TTS: {e}")
        # ------------------------------------
            
        print("\n🔄 Returning to sleep mode...")
        Bridge.call("set_state", 0) # Turn off LED matrix
        app_state = "IDLE"

try:
    App.run(user_loop=loop)
except KeyboardInterrupt:
    print("\nStopping application...")
finally:
    mic_spotter.stop()
    mic_asr.stop()
    asr.stop()
    Bridge.call("set_state", 0) # Turn off LED matrix on exit