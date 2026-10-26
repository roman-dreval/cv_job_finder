import ctypes
import sys

import pytest

from job_finder import busy


def answer(state, result=0):
    def fake(pointer):
        pointer._obj.value = state
        return result
    return fake


@pytest.mark.skipif(sys.platform != "win32", reason="the check asks Windows")
def test_a_film_in_full_screen_leaves_the_card_to_the_model(monkeypatch):
    monkeypatch.setattr(ctypes.windll.shell32, "SHQueryUserNotificationState", answer(2))  # a full-screen window
    for app in ("firefox.exe", "chrome.exe", "msedge.exe", "vlc.exe", "mpc-hc64.exe", "PotPlayerMini64.exe"):
        monkeypatch.setattr(busy, "foreground_app", lambda app=app: app.lower())
        assert busy.windows_busy() is False, app
    monkeypatch.setattr(busy, "foreground_app", lambda: "deadlock.exe")  # a game in a borderless window
    assert busy.windows_busy() is True
    monkeypatch.setattr(busy, "foreground_app", lambda: "")  # Windows can't tell which program: careful
    assert busy.windows_busy() is True
    monkeypatch.setattr(ctypes.windll.shell32, "SHQueryUserNotificationState", answer(3))  # exclusive: a game
    monkeypatch.setattr(busy, "foreground_app", lambda: "firefox.exe")
    assert busy.windows_busy() is True


@pytest.mark.skipif(sys.platform != "win32", reason="the check asks Windows")
def test_the_foreground_app_is_a_lower_case_file_name():
    name = busy.foreground_app()
    assert name == name.lower() and "\\" not in name


@pytest.mark.skipif(sys.platform != "win32", reason="the check asks Windows")
def test_busy_states(monkeypatch):
    monkeypatch.setattr(busy, "foreground_app", lambda: "game.exe")
    for state, expected in [(2, True), (3, True), (4, True), (5, False), (1, False)]:
        monkeypatch.setattr(ctypes.windll.shell32, "SHQueryUserNotificationState", answer(state))
        assert busy.windows_busy() is expected, state
    monkeypatch.setattr(ctypes.windll.shell32, "SHQueryUserNotificationState", answer(3, result=-1))
    assert busy.windows_busy() is False  # Windows could not tell: not busy
