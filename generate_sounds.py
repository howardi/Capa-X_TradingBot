import wave
import math
import struct
import os

def generate_tone(filename, frequency=440, duration=0.5, volume=0.5, sample_rate=44100, type='sine'):
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        
        data = []
        for i in range(n_samples):
            t = float(i) / sample_rate
            
            if type == 'sine':
                value = math.sin(2.0 * math.pi * frequency * t)
            elif type == 'square':
                value = 1.0 if math.sin(2.0 * math.pi * frequency * t) > 0 else -1.0
            elif type == 'sawtooth':
                value = 2.0 * (t * frequency - math.floor(t * frequency + 0.5))
            else:
                value = math.sin(2.0 * math.pi * frequency * t)
                
            # Apply envelope (fade in/out) to avoid clicks
            envelope = 1.0
            if i < 1000: envelope = i / 1000.0
            elif i > n_samples - 1000: envelope = (n_samples - i) / 1000.0
            
            sample = int(value * volume * envelope * 32767.0)
            data.append(struct.pack('<h', sample))
            
        wav_file.writeframes(b''.join(data))
    print(f"Generated {filename}")

def generate_sounds():
    base_dir = "assets/sounds"
    packs = {
        "default": {
            "connect": (880, 0.2, 0.5, 'sine'),
            "disconnect": (220, 0.4, 0.5, 'sawtooth'),
            "buy": (1200, 0.15, 0.4, 'sine'),
            "sell": (400, 0.3, 0.4, 'sine'),
            "alert": (600, 0.5, 0.5, 'square'),
            "ambient": (100, 5.0, 0.1, 'sine')
        },
        "retro": {
            "connect": (1000, 0.1, 0.5, 'square'), # 8-bit coin sound
            "disconnect": (150, 0.5, 0.5, 'sawtooth'), # Game over buzz
            "buy": (1500, 0.1, 0.4, 'square'), # 1-up
            "sell": (300, 0.2, 0.4, 'sawtooth'), # Damage
            "alert": (800, 0.3, 0.5, 'square'), # Warning
            "ambient": (50, 5.0, 0.1, 'sawtooth') # Low bit noise
        },
        "futuristic": {
            "connect": (1200, 0.3, 0.5, 'sine'), # Smooth ping
            "disconnect": (200, 0.6, 0.5, 'sine'), # Power down
            "buy": (2000, 0.1, 0.3, 'sine'), # High chirp
            "sell": (500, 0.2, 0.3, 'sine'), # Low bloop
            "alert": (1000, 0.4, 0.5, 'sawtooth'), # Sci-fi alarm
            "ambient": (150, 5.0, 0.05, 'sine') # Drone
        }
    }

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    for pack_name, sounds in packs.items():
        pack_dir = os.path.join(base_dir, pack_name)
        if not os.path.exists(pack_dir):
            os.makedirs(pack_dir)
            
        print(f"Generating pack: {pack_name}")
        for sound_name, params in sounds.items():
            freq, dur, vol, wave_type = params
            generate_tone(f"{pack_dir}/{sound_name}.wav", freq, dur, vol, type=wave_type)

    # Also generate flat files in base dir for backward compatibility (optional, or just copy default)
    # We will update sound engine to look in subdirs, but let's keep base working for now by copying default
    import shutil
    for f in os.listdir(os.path.join(base_dir, "default")):
        shutil.copy(os.path.join(base_dir, "default", f), os.path.join(base_dir, f))

if __name__ == "__main__":
    generate_sounds()
