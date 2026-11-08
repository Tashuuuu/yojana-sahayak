# ONE real speech-to-text call and ONE real text-to-speech call.
import os
import sys
from pathlib import Path

os.environ["DRY_RUN"] = "0"                     # force real calls for this script only
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # let Python find the src folder

from src.voice import speak, transcribe          # noqa: E402

print("This will spend a small number of Gnani credits.")
if input("Type YES to continue: ").strip() != "YES":
    sys.exit("Cancelled.")

audio_path = Path("assets/test_hi.wav")
if not audio_path.exists():
    sys.exit("Put a 3-5 second recording at assets/test_hi.wav first.")

print("\n1) Speech-to-text ...")
stt = transcribe(audio_path.read_bytes())
print("   transcript:", stt["text"])
print("   language:", stt["detected_language_code"], "| request id:", stt["request_id"])

print("\n2) Text-to-speech ...")
wav = speak("आपका आवेदन स्वीकार किया गया है।", "hi")
Path("assets/test_out.wav").write_bytes(wav)
print("   saved assets/test_out.wav (", len(wav), "bytes ) — play it to listen")

print("\nNow open the Gnani dashboard and compare your credit balance with the number you wrote down.")