"""Whether Windows says the user is busy with a full-screen game or presentation. The scoring waits then, because
the model and a game share the graphics card's memory; a film in a browser or a player needs little of it."""
import ctypes
import ctypes.wintypes
import sys

# SHQueryUserNotificationState answers: QUNS_BUSY, QUNS_RUNNING_D3D_FULL_SCREEN, QUNS_PRESENTATION_MODE
BUSY, D3D_FULL_SCREEN, PRESENTATION = 2, 3, 4
BUSY_STATES = {BUSY, D3D_FULL_SCREEN, PRESENTATION}
# Full-screen programs that are no games: browsers and video players (a game in a borderless window is BUSY too)
MEDIA_APPS = {
    "firefox.exe", "chrome.exe", "msedge.exe", "opera.exe", "brave.exe", "vivaldi.exe", "browser.exe", "arc.exe",
    "vlc.exe", "mpc-hc.exe", "mpc-hc64.exe", "mpc-be.exe", "mpc-be64.exe", "mpv.exe", "potplayer.exe",
    "potplayer64.exe", "potplayermini.exe", "potplayermini64.exe", "kmplayer.exe", "wmplayer.exe", "video.ui.exe",
    "microsoft.media.player.exe", "applicationframehost.exe", "telegram.exe", "discord.exe",
}
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def foreground_app() -> str:
    """The lower-case file name of the program whose window is in front ("" when Windows can't tell)."""
    try:
        window = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
        process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not process:
            return ""
        try:
            path = ctypes.create_unicode_buffer(1024)
            size = ctypes.wintypes.DWORD(len(path))
            if not ctypes.windll.kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
                return ""
        finally:
            ctypes.windll.kernel32.CloseHandle(process)
    except (AttributeError, OSError):
        return ""
    return path.value.rsplit("\\", 1)[-1].lower()


def windows_busy() -> bool:
    """True while a full-screen game or presentation runs; a full-screen browser or video player is no reason to
    wait. On other systems or when Windows can't tell, False."""
    if sys.platform != "win32":
        return False
    state = ctypes.c_int()
    try:
        result = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
    except (AttributeError, OSError):
        return False
    if result != 0 or state.value not in BUSY_STATES:
        return False
    return not (state.value == BUSY and foreground_app() in MEDIA_APPS)
