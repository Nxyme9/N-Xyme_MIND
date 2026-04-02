"""Generate and play narration using Edge TTS."""

import asyncio
import edge_tts
import os
import subprocess

VOICE = "en-GB-RyanNeural"
OUTPUT = "data/audio/narration.mp3"

async def generate():
    print("Generating narration...")
    
    with open("scripts/narration.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    os.makedirs("data/audio", exist_ok=True)
    
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
    await communicate.save(OUTPUT)
    
    print(f"Saved to {OUTPUT}")

def play():
    print("Playing narration...")
    os.startfile(os.path.abspath(OUTPUT))

async def main():
    await generate()
    play()

if __name__ == "__main__":
    asyncio.run(main())
