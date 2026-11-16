"""Windows Raw Input X/G soundboard; Bundled pygame audio mixer."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import sys
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from app_paths import ROOT
import pygame
import wave
import time
import random
from sequence_trigger import SequenceTrigger, MusicPolicy
from key_settings import load_settings, bindings, LABELS
SETTINGS = load_settings()
KEY_ACTIONS = bindings(SETTINGS)

u = c.WinDLL('user32', use_last_error=True)
k = c.WinDLL('kernel32', use_last_error=True)
PROC = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
class WC(c.Structure):
    _fields_ = [('style', w.UINT), ('proc', PROC), ('extra', c.c_int), ('winextra', c.c_int), ('instance', w.HINSTANCE), ('icon', w.HICON), ('cursor', w.HANDLE), ('brush', w.HBRUSH), ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]
class Device(c.Structure):
    _fields_ = [('page', w.USHORT), ('usage', w.USHORT), ('flags', w.DWORD), ('target', w.HWND)]
class Header(c.Structure):
    _fields_ = [('type', w.DWORD), ('size', w.DWORD), ('device', w.HANDLE), ('param', w.WPARAM)]
class Keyboard(c.Structure):
    _fields_ = [('scan', w.USHORT), ('flags', w.USHORT), ('reserved', w.USHORT), ('key', w.USHORT), ('message', w.UINT), ('extra', w.ULONG)]

def api(lib, name, args, result):
    fn = getattr(lib, name)
    fn.argtypes, fn.restype = args, result
    return fn
api(u, 'DefWindowProcW', [w.HWND, w.UINT, w.WPARAM, w.LPARAM], c.c_ssize_t)
api(u, 'CreateWindowExW', [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, c.c_int, c.c_int, c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p], w.HWND)
api(u, 'RegisterClassW', [c.POINTER(WC)], w.ATOM)
api(u, 'UnregisterClassW', [w.LPCWSTR, w.HINSTANCE], w.BOOL)
api(u, 'RegisterRawInputDevices', [c.POINTER(Device), w.UINT, w.UINT], w.BOOL)
api(u, 'GetRawInputData', [w.HANDLE, w.UINT, c.c_void_p, c.POINTER(w.UINT), w.UINT], w.UINT)
api(u, 'GetMessageW', [c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT], w.BOOL)
api(u, 'DispatchMessageW', [c.POINTER(w.MSG)], c.c_ssize_t)
api(u, 'TranslateMessage', [c.POINTER(w.MSG)], w.BOOL)
api(u, 'DestroyWindow', [w.HWND], w.BOOL)
api(u, 'SetTimer', [w.HWND, c.c_size_t, w.UINT, c.c_void_p], c.c_size_t)
api(u, 'KillTimer', [w.HWND, c.c_size_t], w.BOOL)
api(k, 'GetModuleHandleW', [w.LPCWSTR], w.HMODULE)
SOUNDS = {0x58: (ROOT / '音频' / '我从来都不会输.wav'),
          0x47: (ROOT / '音频' / '我来同你玩.wav')}

MUSIC = (ROOT / '音频' / '嘉豪小曲_完整版.wav')
RANDOM_VOICE_PATHS = [ROOT / '音频' / name
                      for name in ('还未到收手的时候.wav', '我做事你放一百个心.wav')]
random_voice_sounds = []
trigger = SequenceTrigger()
policy = MusicPolicy()
music_gain = 1.0
audio_ready = False
enabled = True
volume = 100
voice_channel = None
voice_sounds = {}

def apply_volume():
    if voice_channel is not None:
        voice_channel.set_volume(volume / 100)
    if audio_ready:
        pygame.mixer.music.set_volume(volume / 100 * music_gain)

def stop_all():
    global music_gain
    if voice_channel is not None:
        voice_channel.stop()
    if audio_ready:
        pygame.mixer.music.stop()
    policy.stop()
    trigger.reset()
    music_gain = 1.0

def update_music(now=None):
    global music_gain
    if not audio_ready or not policy.active:
        return
    now = time.monotonic() if now is None else now
    if not pygame.mixer.music.get_busy():
        policy.stop()
        trigger.reset()
        music_gain = 1.0
        return
    music_gain = policy.gain(now)
    if not policy.active:
        pygame.mixer.music.stop()
        trigger.reset()
        music_gain = 1.0
        print('Music faded out. Next trigger starts from the beginning.', flush=True)
    apply_volume()

def play_voice(action):
    if action == 'jet':
        sound = random.choice([voice_sounds[0x58], voice_sounds[0x47]])
    elif action == 'cannon':
        sound = random.choice(random_voice_sounds)
    else:
        sound = voice_sounds[0x47]
    voice_channel.play(sound)

def on_press(key):
    global enabled, volume, music_gain
    update_music()
    action = KEY_ACTIONS.get(key)
    if action == 'toggle':
        enabled = not enabled
        trigger.reset()
        if not enabled:
            stop_all()
        print(f'Functions: {"ON" if enabled else "OFF"} | volume {volume}%', flush=True)
        return
    if not enabled:
        return
    if key in (0xBB, 0x6B, 0xBD, 0x6D):  # =/+ and -; numpad +/-
        trigger.reset()
        volume = max(0, min(100, volume + (10 if key in (0xBB, 0x6B) else -10)))
        apply_volume()
        print(f'Volume: {volume}%', flush=True)
        return
    now = time.monotonic()
    if trigger.feed(key, now):
        start = policy.renew(now)
        music_gain = 1.0
        apply_volume()
        if start:
            try:
                pygame.mixer.music.play(loops=0)
            except Exception:
                policy.stop()
                trigger.reset()
                raise
            print('Valid switching -> full music started', flush=True)
    if action in ('jet', 'c4', 'cannon'):
        play_voice(action)
        print(f'{action} -> playing voice', flush=True)

pressed = set()

@PROC
def callback(hwnd, message, wp, lp):
    if message == 0x113 and wp == 1:
        try:
            update_music()
        except Exception as error:
            print('Music update error:', error, flush=True)
    if message == 0xFF:
        try:
            size = w.UINT()
            hs = c.sizeof(Header)
            result = u.GetRawInputData(lp, 0x10000003, None, c.byref(size), hs)
            if result == 0xFFFFFFFF:
                raise c.WinError(c.get_last_error())
            buf = c.create_string_buffer(size.value)
            got = u.GetRawInputData(lp, 0x10000003, buf, c.byref(size), hs)
            if got == 0xFFFFFFFF:
                raise c.WinError(c.get_last_error())
            if got >= hs + c.sizeof(Keyboard):
                header = Header.from_buffer_copy(buf)
                if header.type == 1:
                    key = Keyboard.from_buffer_copy(buf, hs)
                    if key.key != 255:
                        token = (header.device, key.key)
                        if key.flags & 1:
                            pressed.discard(token)
                        elif token not in pressed:
                            pressed.add(token)
                            on_press(key.key)
        except Exception as error:
            print('Input/audio error:', error, flush=True)
    return u.DefWindowProcW(hwnd, message, wp, lp)

def main():
    global voice_channel, voice_sounds, random_voice_sounds, audio_ready
    for path in [*SOUNDS.values(), *RANDOM_VOICE_PATHS, MUSIC]:
        with wave.open(str(path), 'rb') as audio:
            print(f'Audio ready: {audio.getnframes() / audio.getframerate():.2f}s', flush=True)
    instance = k.GetModuleHandleW(None)
    wc = WC()
    wc.proc, wc.instance, wc.name = callback, instance, 'LocalSoundboardRawInput'
    if not u.RegisterClassW(c.byref(wc)):
        raise c.WinError(c.get_last_error())
    hwnd = None
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(2)
        voice_channel = pygame.mixer.Channel(0)
        voice_sounds = {key: pygame.mixer.Sound(str(path)) for key, path in SOUNDS.items()}
        random_voice_sounds = [pygame.mixer.Sound(str(path)) for path in RANDOM_VOICE_PATHS]
        pygame.mixer.music.load(str(MUSIC))
        audio_ready = True
        apply_volume()
        hwnd = u.CreateWindowExW(0, wc.name, 'Soundboard', 0, 0, 0, 0, 0, None, None, instance, None)
        if not hwnd:
            raise c.WinError(c.get_last_error())
        device = Device(1, 6, 0x100, hwnd)
        if not u.RegisterRawInputDevices(c.byref(device), 1, c.sizeof(Device)):
            raise c.WinError(c.get_last_error())
        if not u.SetTimer(hwnd, 1, 50, None):
            raise c.WinError(c.get_last_error())
        print('Raw Input registered successfully.', flush=True)
        if '--self-test' in sys.argv:
            print('Startup/audio checks passed.')
            return
        for action, label in LABELS.items():
            print(f'{label}: {SETTINGS[action]}')
        print('131313/313131/232323/323232 in 2s: full music')
        print('Valid group extends music; 8s idle then 3s fade. Gaps must be under 1s.')
        print(f'+/=: volume +10% | -: volume -10% | {SETTINGS["toggle"]}: toggle ALL functions')
        print(f'Functions: ON | volume {volume}%')
        print('Close this console window to stop. Run only one copy.', flush=True)
        msg = w.MSG()
        while True:
            result = u.GetMessageW(c.byref(msg), None, 0, 0)
            if result == -1:
                raise c.WinError(c.get_last_error())
            if result == 0:
                break
            u.TranslateMessage(c.byref(msg))
            u.DispatchMessageW(c.byref(msg))
    finally:
        stop_all()
        pygame.mixer.quit()
        audio_ready = False
        if hwnd:
            u.KillTimer(hwnd, 1)
            remove = Device(1, 6, 1, None)
            u.RegisterRawInputDevices(c.byref(remove), 1, c.sizeof(Device))
            u.DestroyWindow(hwnd)
        u.UnregisterClassW(wc.name, instance)


