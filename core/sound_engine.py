import base64
import os

class SoundEngine:
    def __init__(self, sound_dir="assets/sounds"):
        self.sound_dir = sound_dir
        self.sounds = {}
        self.enabled = True
        self.ambient_enabled = False
        self.current_pack = "default"
        self.available_packs = self._scan_packs()
        self._load_sounds()

    def _scan_packs(self):
        """Scan for available sound packs"""
        packs = ["default"]
        if os.path.exists(self.sound_dir):
            for d in os.listdir(self.sound_dir):
                path = os.path.join(self.sound_dir, d)
                if os.path.isdir(path) and d not in packs:
                    packs.append(d)
        return packs

    def set_pack(self, pack_name):
        """Switch sound pack"""
        if pack_name in self.available_packs:
            self.current_pack = pack_name
            self._load_sounds()
            return True
        return False

    def _load_sounds(self):
        """Pre-load sounds into base64 for embedding"""
        self.sounds = {} # Clear existing
        
        # Determine path: check pack subdir first, then base dir (legacy)
        pack_path = os.path.join(self.sound_dir, self.current_pack)
        target_dir = pack_path if os.path.exists(pack_path) else self.sound_dir
        
        if not os.path.exists(target_dir):
            return

        for filename in os.listdir(target_dir):
            if filename.endswith(".wav"):
                name = filename.split('.')[0]
                with open(os.path.join(target_dir, filename), "rb") as f:
                    data = f.read()
                    b64 = base64.b64encode(data).decode()
                    self.sounds[name] = f"data:audio/wav;base64,{b64}"

    def get_audio_html(self, sound_name):
        """Return HTML audio tag for a sound"""
        if not self.enabled:
            return ""
            
        src = self.sounds.get(sound_name)
        if src:
            # Autoplay with hidden attribute
            return f'<audio autoplay="true" style="display:none;"><source src="{src}" type="audio/wav"></audio>'
        return ""

    def get_ambient_html(self):
        """Return looping ambient sound HTML"""
        if not self.enabled or not self.ambient_enabled:
            return ""
            
        src = self.sounds.get('ambient')
        if src:
            return f'<audio autoplay="true" loop="true" style="display:none;"><source src="{src}" type="audio/wav"></audio><div style="position:fixed; bottom:10px; right:10px; opacity:0.5; font-size:0.8em;">🎵 Ambient</div>'
        return ""
