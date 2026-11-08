# src/voice.py, constants near the top. 

# Find this line:
# API_KEY = os.getenv("GNANI_API_KEY", "")

# Replace it with:
# STT_KEY = os.getenv("GNANI_STT_API_KEY", "")
# TTS_KEY = os.getenv("GNANI_TTS_API_KEY", "")



# src/voice.py, inside transcribe(). Two changes.

# Find the key check:
#     if not API_KEY:
#         raise RuntimeError("GNANI_API_KEY is missing. Put it in .env")

# Replace it with:
#     if not STT_KEY:
#         raise RuntimeError("GNANI_STT_API_KEY is missing. Put it in .env")

# In the requests.post(STT_URL, ...) call, 

# find:
#             headers={"X-API-Key-ID": API_KEY},

# Replace it with:
#             headers={"X-API-Key-ID": STT_KEY},



# src/voice.py, inside speak(). Two changes.

# Find the key check:
#     if not API_KEY:
#         raise RuntimeError("GNANI_API_KEY is missing. Put it in .env")

# Replace it with:
#     if not TTS_KEY:
#         raise RuntimeError("GNANI_TTS_API_KEY is missing. Put it in .env")

# In the requests.post(TTS_URL, ...) call

# find:
#             headers={"X-API-Key-ID": API_KEY, "Content-Type": "application/json"},

# Replace it with:
#             headers={"X-API-Key-ID": TTS_KEY, "Content-Type": "application/json"},