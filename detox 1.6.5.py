import ttkbootstrap as ttk  # Тема Bootstrap
from ttkbootstrap.constants import * # Константы ttkbootstrap
import json
import os
import webbrowser
from PIL import Image, ImageTk
import math
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import Style
from ttkbootstrap.widgets import Progressbar
from pystray import Icon, Menu, MenuItem
import threading  # Многопоточность
import datetime
import base64
import io  # Потоки ввода/вывода в памяти
import random
import cv2  # (OpenCV)
import numpy as np  # Работа с массивами
from pathlib import Path  # Объектно-ориентированная работа с путями
import time
import requests
import warnings
import atexit
import sys

# --- Автозапуск Windows(Новое) ---
try:
    import win32com.client
except ImportError:
    win32com = None

def get_startup_folder():
    return os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")

def get_shortcut_path(shortcut_name="Detox.lnk"):
    return os.path.join(get_startup_folder(), shortcut_name)

def enable_autostart(exe_path=None, shortcut_name="Detox.lnk"):
    if win32com is None:
        return
    if exe_path is None:
        exe_path = sys.executable
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(get_shortcut_path(shortcut_name))
    shortcut.Targetpath = exe_path
    shortcut.WorkingDirectory = os.path.dirname(exe_path)
    shortcut.Arguments = "--autostart"
    shortcut.save()

def disable_autostart(shortcut_name="Detox.lnk"):
    shortcut_path = get_shortcut_path(shortcut_name)
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)

APPDATA_DETOX_DIR = Path(os.getenv("APPDATA")) / "DetoxApp"
DETOX_IMAGE_PATH = APPDATA_DETOX_DIR / "detox.png"
HAARCASCADE_EYE_PATH = APPDATA_DETOX_DIR / "haarcascade_eye.xml"
warnings.filterwarnings("ignore", category=UserWarning, module='cv2')


#base64 код иконки detox.png
# ------------------------------
# Класс для анимированного логотипа Detox
# ------------------------------
class AnimatedCanvas(ttk.Canvas):
    def __init__(self, root, image_path=None, **kwargs):
        super().__init__(root, **kwargs)
        self.pack()
        self.center_x = 100
        self.center_y = 100
        self.angle = 0
        self.background_circle = self.create_oval(
            self.center_x - 80,
            self.center_y - 80,
            self.center_x + 80,
            self.center_y + 80,
            fill="#003D33",
            outline=""
        )
        self.gradient_circle = self.create_oval(
            self.center_x - 75,
            self.center_y - 75,
            self.center_x + 75,
            self.center_y + 75,
            fill="",
            outline="#1DBF73",
            width=3
        )
        if image_path is None:
            ensure_appdata_files()
            self.image = Image.open(DETOX_IMAGE_PATH)
        else:
            self.image = Image.open(image_path)
        self.image = self.image.resize((100, 100), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_item = self.create_image(self.center_x, self.center_y, image=self.tk_image)
        self.animate()

    def animate(self):
        radius_offset = 5 * math.sin(math.radians(self.angle))
        new_width = int(3 + 2 * math.sin(math.radians(self.angle)))
        self.coords(
            self.gradient_circle,
            self.center_x - 75 - radius_offset,
            self.center_y - 75 - radius_offset,
            self.center_x + 75 + radius_offset,
            self.center_y + 75 + radius_offset
        )
        self.itemconfig(self.gradient_circle, width=new_width)
        self.angle = (self.angle + 2) % 360
        self.after(50, self.animate)


# ------------------------------
# Класс для отслеживания глаз
# ------------------------------

# Создаём временный файл из Base64
def ensure_appdata_files():
    APPDATA_DETOX_DIR.mkdir(parents=True, exist_ok=True)
    # Сохраняем detox.png
    if not DETOX_IMAGE_PATH.exists():
        try:
            with open(DETOX_IMAGE_PATH, "wb") as f:
                f.write(base64.b64decode(DETOX_IMAGE_BASE64))
        except Exception as e:
            print("Ошибка сохранения detox.png:", e)
    # Сохраняем haarcascade_eye.xml
    if not HAARCASCADE_EYE_PATH.exists():
        try:
            with open(HAARCASCADE_EYE_PATH, "wb") as f:
                f.write(base64.b64decode(HAARCASCADE_EYE_XML))
        except Exception as e:
            print("Ошибка сохранения haarcascade_eye.xml:", e)

def get_haarcascade_eye_path():
    ensure_appdata_files()
    return str(HAARCASCADE_EYE_PATH)

class EyeTracker:
    def __init__(self, parent=None, show_feed=True, show_graphics=True):
        self.parent = parent
        self.running = False
        self.cap = None
        self.eyes_detected = False
        self.show_feed = show_feed
        self.show_graphics = show_graphics
        self.eye_cascade = cv2.CascadeClassifier(get_haarcascade_eye_path())
        self.frame = None
        self._should_destroy_windows = False
    
    def start(self):
        self.running = True
        self._should_destroy_windows = False
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[ERROR] Не удалось открыть камеру. Проверьте доступность устройства.")
            self.running = False
            return
        self.thread = threading.Thread(target=self._track_eyes)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        self._should_destroy_windows = True
        if self.cap:
            self.cap.release()
        if hasattr(self, 'thread') and self.thread.is_alive() and threading.current_thread() != self.thread:
            try:
                if not getattr(threading.current_thread(), "_is_shutting_down", False):
                    self.thread.join(timeout=1.0)
            except Exception:
                pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        
    def _track_eyes(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not ret:
                if self.running:
                    print("[WARN] Не удалось захватить кадр с камеры.")
                break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            eyes = self.eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=10, minSize=(20, 20))
            self.eyes_detected = len(eyes) >= 2
            
            display_frame = frame.copy()
            # --- Исправление: используем только латиницу для текста в OpenCV(т.к. он русский не поддерживает) ---
            if self.eyes_detected:
                status_text = "Look away!"  # Латиница, чтобы не было вопросиков
                color = (0, 0, 255)
            else:
                status_text = "Resting..."
                color = (0, 255, 0)
            cv2.putText(display_frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            if self.show_graphics:
                for (x, y, w, h) in eyes:
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            self.frame = display_frame
            
            if self.show_feed:
                cv2.imshow("Detox Eye Tracker", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        if self._should_destroy_windows:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
    
    def is_looking_at_screen(self):
        return self.eyes_detected
    
    def get_current_frame(self):
        return self.frame

    def show_graphics_only(self):
        blank_frame = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.rectangle(blank_frame, (100, 100), (150, 150), (255, 0, 0), -1)
        cv2.rectangle(blank_frame, (250, 100), (300, 150), (0, 255, 0), -1)
        cv2.putText(blank_frame, self.parent.translate("GraphicsOnlyMessage"), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow(self.parent.translate("GraphicsOnlyWindowTitle"), blank_frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


# ------------------------------
# Окно обратного отсчёта перерыва
# ------------------------------
class CountdownWindow:
    def __init__(
        self,
        parent,
        duration,
        theme="flatly",
        break_type="mini",
        strict_mode=False,
        sound_enabled=False,
        break_mode="fullscreen",
        use_camera=False,
        show_camera_feed=True,
        show_eye_graphics=True,
        on_skip=None,
        on_complete=None
    ):
        self.parent = parent
        self.duration = duration
        self.remaining = duration
        self.break_type = break_type
        self.strict_mode = strict_mode
        self.use_camera = use_camera and strict_mode
        self.timer_active = True
        self.show_camera_feed = show_camera_feed
        self.show_eye_graphics = show_eye_graphics
        self.on_skip = on_skip
        self.on_complete = on_complete
        self.was_skipped = False  # флажок, что пользователь нажал "Пропустить"

        # Список советов во время перерывов
        self.break_tips = [
            self.parent.translate("TipCloseEyes"),
            self.parent.translate("TipLookOutWindow"),
            self.parent.translate("TipShoulderRolls"),
            self.parent.translate("TipStretch"),
            self.parent.translate("TipEyeRolls"),
            self.parent.translate("TipLookFarThenNose")
        ]
        self.camera_tips = [
            self.parent.translate("TipStepAwayMonitor"),
            self.parent.translate("TipLookAwayScreen"),
            self.parent.translate("TipTurnAwayComputer"),
            self.parent.translate("TipLookAwayToContinue")
        ]
        # Выбираем совет на рандом
        random_tip = random.choice(self.camera_tips) if self.use_camera else random.choice(self.break_tips)

        self.window = tk.Toplevel(parent)
        self.window.title(self.parent.translate("CountdownWindowTitle"))

        # Полноэкранный режим, если выбран
        if break_mode == "fullscreen":
            self.window.attributes('-fullscreen', True)
            self.window.attributes('-alpha', 0.9)
            self.window.configure(background="#468f97")
        else:
            self.window.geometry("400x300")
            self.window.configure(bg="#468f97")

        # Тут у нас играет звук перерыва
        if sound_enabled:
            try:
                import winsound
                # Воспроизводим системный звук ошибки Windows ("тутун")
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception as e:
                print(self.parent.translate("SoundErrorMessage"), e)

        # А это тема как в системе
        if theme == "system":
            if hasattr(parent, '_get_system_theme'):
                theme = parent._get_system_theme()
            else:
                theme = "flatly"
        self.style = Style(theme=theme)
        self.style.configure('TProgressbar', thickness=20, troughcolor="#468f97", background="#1DBF73")

        central_frame = tk.Frame(self.window, background="#468f97")
        central_frame.place(relx=0.5, rely=0.5, anchor='center')

        self.label = tk.Label(
            central_frame,
            text=random_tip,
            font=("Arial", 20),
            fg="white",
            background="#468f97",
            wraplength=600
        )
        self.label.pack(pady=20)

        self.progress = Progressbar(
            central_frame,
            maximum=duration,
            orient="horizontal",
            mode="determinate",
            style="TProgressbar",
            length=300
        )
        self.progress.pack(pady=10)
        self.progress["value"] = duration

        self.time_label = tk.Label(
            central_frame,
            text=f"{int(self.remaining)} {self.parent.translate('SecondsLeft')}",
            font=("Arial", 16),
            fg="white",
            background="#468f97",
        )
        self.time_label.pack(pady=10)

        # Кнопочка для пропуска перерыва
        if not self.strict_mode:
            self.skip_button = tk.Button(
                central_frame,
                text=self.parent.translate("SkipBreakButton"),
                font=("Arial", 14),
                background="#468f97",
                fg="white",
                activebackground="#468f97",
                activeforeground="white",
                relief="flat",
                command=self.skip_break,
                takefocus=False
            )
            self.skip_button.pack(pady=20)
            self.skip_button.bind("<ButtonRelease-1>", lambda e: self.window.focus_set())

        if self.use_camera:
            self.status_label = tk.Label(
                central_frame,
                text=self.parent.translate("LookAwayScreenMessage"),
                font=("Arial", 14),
                fg="red",
                background="#468f97",
            )
            self.status_label.pack(pady=5)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.eye_tracker = None
        if self.use_camera:
            # Передаём parent в EyeTracker
            self.eye_tracker = EyeTracker(
                parent=self.parent,
                show_feed=self.show_camera_feed,
                show_graphics=self.show_eye_graphics
            )
            self.eye_tracker.start()
            self.check_gaze()
        self.update_progress()

    def check_gaze(self):
        if self.eye_tracker and self.remaining > 0:
            looking = self.eye_tracker.is_looking_at_screen()
            if looking:
                self.timer_active = False
                self.status_label.config(text=self.parent.translate("ScreenWarning"), fg="red")
            else:
                self.timer_active = True
                self.status_label.config(text=self.parent.translate("RestingMessage"), fg="green")
            self.window.after(500, self.check_gaze)

    def skip_break(self):
        self.was_skipped = True
        self.on_close()
        if self.window.winfo_exists():
            self.window.focus_set()

    def update_progress(self):
        if self.remaining > 0:
            if self.timer_active or not self.use_camera:
                self.remaining -= 1
                self.progress["value"] = self.remaining
            minutes, seconds = divmod(self.remaining, 60)
            self.time_label.config(text=f"{int(minutes)} {self.parent.translate('MinutesLeft')} {int(seconds)} {self.parent.translate('SecondsLeft')}")
            self.window.after(1000, self.update_progress)
        else:
            self.label.config(text=self.parent.translate("TimeUpMessage"))
            self.time_label.config(text="")
            if not self.strict_mode and hasattr(self, 'skip_button'):
                self.skip_button.config(text=self.parent.translate("CloseButton"))

            # Останавливаем EyeTracker, если он используется
            if self.eye_tracker:
                try:
                    self.eye_tracker.stop()
                except Exception:
                    pass

            # 2000 = 2 секунды не забудь
            self.window.after(2000, self.on_close)  # <--- Важно: теперь вызываем on_close для корректной статистики чтобы работала

    def on_close(self):
        if self.eye_tracker:
            try:
                self.eye_tracker.stop()
            except Exception:
                pass
        if self.remaining > 0 and not self.was_skipped:
            self.was_skipped = True

        # Подсчёт времени отдыха
        break_time = int(self.duration - self.remaining)
        self.window.destroy()

        if self.was_skipped and self.on_skip:
            self.on_skip(break_time)
        elif not self.was_skipped and self.on_complete:
            self.on_complete(break_time)


# ------------------------------
# Основное приложение
# ------------------------------

# Тут реализована работа с лицензиями и их проверка
SUPABASE_URL = "https://dkgqscjcfigkuwseagkx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRrZ3FzY2pjZmlna3V3c2VhZ2t4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1MzY4MDYsImV4cCI6MjA2MjExMjgwNn0.WGqVIhyfu02ec8e_qB7kNZ4X1t0quor0XO0ynf5nRcM"
LICENSE_TYPE_MAP = {
    "training": {"Русский": "Учебная", "English": "Training", "Казакша": "Оқу"},
    "developer": {"Русский": "Разработчик", "English": "Developer", "Казакша": "Бағдарламашы"}
}
LICENSE_SETTINGS_PATH = str(Path(os.getenv("APPDATA")) / "DetoxApp" / "license_settings.json")

def mask_license_key(license_key_str):
    if not license_key_str or '-' not in license_key_str:
        return license_key_str
    parts = license_key_str.split('-', 1)
    if len(parts) == 2:
        return f"*****-{parts[1]}"
    return license_key_str

def get_license_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def search_license_online(key):
    headers = get_license_headers()
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/licenses?license_key=eq.{key}&select=*",
            headers=headers, timeout=7
        )
        if res.status_code == 200:
            json_data = res.json()
            if json_data: return {'status': 'success', 'data': json_data[0]}
            return {'status': 'not_found', 'key': key}
        return {'status': 'server_error', 'code': res.status_code, 'text': res.text, 'key': key}
    except requests.exceptions.Timeout:
        return {'status': 'network_error', 'type': 'timeout',
                'message': "Не удалось подключиться к серверу (таймаут). Проверьте интернет-соединение."}
    except requests.exceptions.RequestException:
        return {'status': 'network_error', 'type': 'connection',
                'message': "Ошибка подключения к серверу. Проверьте интернет-соединение."}
    except Exception as e:
        return {'status': 'general_error', 'message': f"Произошла ошибка: {e}"}

def save_license_locally(license_data):
    data_to_save = {}
    if license_data and license_data.get("license_key"):
        data_to_save = {
            "license_key": license_data.get("license_key"),
            "type": license_data.get("type"),
            "expires": license_data.get("expires")
        }
    try:
        os.makedirs(os.path.dirname(LICENSE_SETTINGS_PATH), exist_ok=True)
        with open(LICENSE_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False

def load_license_from_local():
    try:
        if os.path.exists(LICENSE_SETTINGS_PATH):
            with open(LICENSE_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and data.get("license_key"): return data
        return {}
    except Exception:
        return {}

def format_days_left(expiry_str, translate):
    if expiry_str is None:
        return translate("LicenseUnlimited")
    if isinstance(expiry_str, str) and expiry_str.lower() in ["бессрочно", "unlimited", translate("LicenseUnlimited").lower()]:
        return translate("LicenseUnlimited")
    if not isinstance(expiry_str, str) or not expiry_str.strip():
        return "-"
    try:
        exp_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
        today = datetime.datetime.now().date()
        delta_days = (exp_date - today).days
        if delta_days < 0:
            return translate("LicenseExpired")
        if delta_days == 0:
            return translate("TodayExpiresWord")
        lang = translate("DaysWord")
        if hasattr(translate, "__self__"):
            language = translate.__self__.variables["language"].get()
        else:
            language = "Русский"
        if language == "Русский":
            if 11 <= (delta_days % 100) <= 19:
                days_word = translate("DaysWord")
            elif (delta_days % 10) == 1:
                days_word = translate("DayWord")
            elif 2 <= (delta_days % 10) <= 4:
                days_word = translate("Days234Word")
            else:
                days_word = translate("DaysWord")
        else:
            days_word = translate("DaysWord")
        return f"{delta_days} {days_word}"
    except ValueError:
        return "-"
    except Exception:
        return "-"

class DetoxSettingsApp(ttk.Window):
    def __init__(self):
        self._started_from_autostart = "--autostart" in sys.argv
        self.current_version = "1.6.4"
        super().__init__(themename="flatly")
        self.title("Detox")
        self.geometry("800x800")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_main_window_close)

        # Это у нас иконка
        self.after(0, self.set_icon)

        self.variables = {
            "autostart":         ttk.BooleanVar(value=True),  # автозапуск включён по умолчанию
            "break_mode":        ttk.StringVar(value="fullscreen"),
            "exercise_tips":     ttk.BooleanVar(value=True),
            "break_all_screens": ttk.BooleanVar(value=True),
            "track_idle":        ttk.BooleanVar(value=True),
            "dnd_mode":          ttk.BooleanVar(value=False),
            "language":          ttk.StringVar(value="Русский"),
            "theme":             ttk.StringVar(value="system"),
            "sound_on_break":    ttk.BooleanVar(value=False),
            "enable_short_breaks":  ttk.BooleanVar(value=True),
            "short_break_duration": ttk.IntVar(value=20),
            "short_break_interval": ttk.IntVar(value=10),
            "enable_long_breaks":   ttk.BooleanVar(value=True),
            "long_break_duration":  ttk.IntVar(value=300),
            "long_break_interval":  ttk.IntVar(value=30),
            "notify_before_short_break":    ttk.BooleanVar(value=False),
            "allow_postpone_short_breaks":  ttk.BooleanVar(value=True),
            "notify_before_long_break":     ttk.BooleanVar(value=False),
            "allow_postpone_long_breaks":   ttk.BooleanVar(value=True),
            "strict_mode_mini_breaks":      ttk.BooleanVar(value=False),
            "strict_mode_long_breaks":      ttk.BooleanVar(value=False),
            "autoupdate":         ttk.BooleanVar(value=False),
            "detox_active":       ttk.BooleanVar(value=True),
            "break_start_time":   tk.StringVar(value="12:00"),
            "break_end_time":     tk.StringVar(value="00:00"),
            "use_camera":         ttk.BooleanVar(value=False),
            "show_camera_feed":   ttk.BooleanVar(value=True),
            "show_eye_graphics":  ttk.BooleanVar(value=True),
            "enable_time_restriction": ttk.BooleanVar(value=False),
        }

        self.settings_file = Path(os.getenv("APPDATA")) / "DetoxApp" / "settings.json"
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        self.localization_file = self.settings_file.parent / "localization.json"
        self.translations = {}
        self.load_localization()

        # Дефолт настройки для первого старта
        self.stats = {
            "mini_breaks": 0,
            "long_breaks": 0,
            "total_breaks": 0,
            "total_runtime": 0,
            "mini_skipped": 0,
            "long_skipped": 0,
            "mini_time": 0,
            "long_time": 0,
        }

        self.detox_active = False
        self.paused = False
        self.break_timer_mini = None
        self.break_timer_long = None
        self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
        self.long_remaining_time = self.variables["long_break_interval"].get() * 60

        self.start_time = datetime.datetime.now()

        self.break_window_open = False
        self._pending_break = None      # Тип ожидающего перерыва: "mini" или "long"

        self._active_eye_tracker = None  # Для отслеживания активного EyeTracker
        atexit.register(self.close_eye_tracker_on_exit)

        self.create_top_panel()
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(pady=20, fill="both", expand=True)

        self.detox_frame = self.create_detox_frame()
        self.settings_frame = self.create_settings()
        self.schedule_frame = self.create_schedule_frame()
        self.theme_frame = self.create_theme_frame()
        self.about_frame = self.create_about_frame()
        self.statistics_frame = self.create_statistics_frame()

        self.load_settings()
        self._fix_language_variable()
        self.refresh_ui_texts()  # рефреш всего интерфейса на нужный язык
        self.apply_theme()

        self.variables["short_break_interval"].trace("w", self.on_short_break_interval_change)
        self.variables["long_break_interval"].trace("w", self.on_long_break_interval_change)

        if self.variables["detox_active"].get():
            self.start_detox()

        self._license_check_thread = None
        self.after(1000, self.background_license_check)
        self.after(2000, self.background_online_license_check)
        self.check_and_update_localization()
        
        # Проверка обновлений только если включен автоапдейт
        if self.variables["autoupdate"].get():
            self.after(3000, self.check_new_version_github)

        self.after(100, self.sync_autostart_setting)
        if self._started_from_autostart:
            self.after(5000, self.minimize_to_tray)

    def set_icon(self):
        try:
            ensure_appdata_files()
            self.icon_image = tk.PhotoImage(file=str(DETOX_IMAGE_PATH))
            self.iconphoto(False, self.icon_image)
        except Exception as e:
            print(self.translate("IconErrorMessage"), e)

    def load_localization(self): # Это три языка: Русский, English и Казакша
        if not self.localization_file.exists():
            default_translations = self.get_default_translations()
            with open(self.localization_file, "w", encoding="utf-8") as file:
                json.dump(default_translations, file, ensure_ascii=False, indent=4)
        with open(self.localization_file, "r", encoding="utf-8") as file:
            self.translations = json.load(file)

    def get_default_translations(self):
        # Это словарик с переводами на трех языках
        return {
            "Русский": {
                "MenuDetox": "Detox",
                "MenuSettings": "Настройки",
                "MenuSchedule": "Расписание",
                "MenuStatistics": "Статистика",
                "MenuTheme": "Тема",
                "MenuAbout": "О программе",
                "StartDetoxAutomatically": "Запускать Detox автоматически при входе в систему",
                "SaveSettingsButton": "Сохранить настройки",
                "RestoreDefaultsButton": "Восстановить настройки по умолчанию",
                "MiniBreakButton": "Мини-перерыв",
                "LongBreakButton": "Длинный перерыв",
                "PauseButton": "Пауза",
                "ResetBreaksButton": "Сбросить перерывы",
                "ExitDetoxButton": "Выход из Detox",
                "MiniBreakRemaining": "До мини-перерыва: {minutes} мин {seconds} сек",
                "LongBreakRemaining": "До длинного перерыва: {minutes} мин {seconds} сек",
                "ShowBreaksLabel": "Показывать перерывы:",
                "InWindowOption": "В окне",
                "FullscreenOption": "На весь экран",
                "ShowExerciseTipsOption": "Показывать идеи для упражнений во время перерывов",
                "ShowBreaksOnAllScreensOption": "Показывать перерывы на всех экранах",
                "TrackIdleTimeOption": "Следить за неиспользованием системы",
                "ShowBreaksInDNDModeOption": "Показывать перерывы даже в режиме 'Не беспокоить'",
                "SelectLanguageLabel": "Выбрать язык:",
                "EnableSoundOnBreakOption": "Включить звук при перерыве",
                "EnableDetoxOption": "Включить Detox",
                "CameraSettingsLabel": "Настройки камеры:",
                "UseCameraForEyeTrackingOption": "Использовать камеру для отслеживания глаз в строгом режиме",
                "ShowCameraFeedOption": "Показывать изображение с камеры",
                "ShowEyeGraphicsOption": "Показывать графику вокруг глаз",
                "MiniBreaksLabel": "Мини-перерывы:",
                "MiniBreaksDescription": "Регулярные короткие перерывы...",
                "EnableMiniBreaksOption": "Включить мини-перерывы",
                "MiniBreakDurationLabel": "Продолжительность (сек):",
                "SecondsUnit": "сек",
                "MiniBreakIntervalLabel": "Каждые (мин):",
                "MinutesUnit": "мин",
                "NotifyBeforeMiniBreakOption": "Уведомлять перед мини-перерывом",
                "AllowPostponeMiniBreaksOption": "Разрешать откладывать мини-перерывы",
                "LongBreaksLabel": "Длинные перерывы:",
                "LongBreaksDescription": "Длинные перерывы для продолжительного отдыха...",
                "EnableLongBreaksOption": "Включить длинные перерывы",
                "LongBreakDurationLabel": "Продолжительность (мин):",
                "LongBreakIntervalLabel": "Каждые (мин):",
                "NotifyBeforeLongBreakOption": "Уведомлять перед длинным перерывом",
                "AllowPostponeLongBreaksOption": "Разрешать откладывать длинные перерывы",
                "StrictModeLabel": "Строгий режим:",
                "StrictModeDescription": "В строгом режиме нельзя пропустить перерыв, а для продолжения нужно отвести взгляд от экрана.",
                "EnableStrictModeMiniBreaksOption": "Включить строгий режим для мини-перерывов",
                "EnableStrictModeLongBreaksOption": "Включить строгий режим для длинных перерывов",
                "AllowedBreakTimesLabel": "Время разрешённых перерывов (HH:MM):",
                "StartTimeLabel": "Начало:",
                "EndTimeLabel": "Конец:",
                "EnableTimeRestrictionOption": "Включить ограничение по времени",
                "ThemeLabel": "Тема",
                "ChangeThemeDescription": "Здесь можно изменить тему приложения",
                "SystemDefaultOption": "Как в системе",
                "FlatlyOption": "Flatly",
                "DarklyOption": "Darkly",
                "CosmoOption": "Cosmo",
                "CyborgOption": "Cyborg",
                "SuperheroOption": "Superhero",
                "MintyOption": "Minty",
                "SelectThemeLabel": "Выберите тему:",
                "BreakRemindersLabel": "Напоминания о перерывах",
                "VersionLabel": "Версия 1.6.4",
                "CheckForUpdatesOption": "Автоматически проверять обновления приложения",
                "CheckingForUpdates": "Проверка наличия обновлений...",
                "LatestVersionInstalled": "У вас установлена последняя версия",
                "UpdateAvailable": "Доступно обновление! Текущая/новая: {current}/{latest}",
                "VersionCheckError": "Ошибка проверки версии",
                "DownloadUpdateLink": "Скачать обновление",
                "LearnMoreAboutDetoxMessage": "Чтобы узнать больше о функционале Detox, пройдите обучение, скачайте последнюю версию или свяжитесь с нами для поддержки.",
                "VisitOurWebsiteLink": "Посетите наш сайт.",
                "DevelopedByLabel": "Разработано Алишером",
                "MiniBreaksStats": "Мини-перерывов: {count} (пропущено: {skipped})",
                "LongBreaksStats": "Длинных перерывов: {count} (пропущено: {skipped})",
                "BreakTimeStats": "Время мини: {minutes} мин {seconds} сек | Время длинных: {long_minutes} мин {long_seconds} сек | Всего отдыха: {total_minutes} мин {total_seconds} сек",
                "RuntimeStats": "Время работы: ~{minutes} мин {seconds} сек",
                "ClearStatisticsButton": "Очистить статистику",
                "MinimizeToTray": "Свернуть в трей",
                "MiniBreakTrayOption": "Мини-перерыв",
                "LongBreakTrayOption": "Длинный перерыв",
                "PauseTrayOption": "Пауза",
                "ExitTrayOption": "Выход",
                "MiniBreakTrayTitle": "Мини-перерыв",
                "LongBreakTrayTitle": "Длинный перерыв",
                "BreaksDisabledMessage": "Перерывы отключены по расписанию",
                "PlayButton": "Продолжить",
                "CountdownWindowTitle": "Перерыв",
                "SkipBreakButton": "Пропустить этот перерыв",
                "LookAwayScreenMessage": "Для продолжения таймера отведите взгляд.",
                "ScreenWarning": "Отойдите от экрана!",
                "RestingMessage": "Молодец! Отдыхаем...",
                "SecondsLeft": "сек осталось",
                "MinutesLeft": "мин",
                "TimeUpMessage": "Время вышло!",
                "CloseButton": "Закрыть",
                "TipCloseEyes": "Закройте глаза на 20 секунд.",
                "TipLookOutWindow": "Посмотрите в окно или вдаль.",
                "TipShoulderRolls": "Сделайте круговые движения плечами.",
                "TipStretch": "Потянитесь вверх и в стороны.",
                "TipEyeRolls": "Покрутите глазами по кругу.",
                "TipLookFarThenNose": "Посмотрите вдаль, затем на кончик носа.",
                "TipStepAwayMonitor": "Отойдите от монитора на время перерыва.",
                "TipLookAwayScreen": "Посмотрите в сторону от экрана.",
                "TipTurnAwayComputer": "Повернитесь от компьютера.",
                "TipLookAwayToContinue": "Отведите взгляд, чтобы продолжить.",
                "LicenseSectionTitle": "Лицензия Detox",
                "EnterLicenseKeyPrompt": "Введите новый ключ для проверки:",
                "CheckButton": "Проверить",
                "LicenseKeyLabel": "Ключ:",
                "LicenseTypeLabel": "Тип лицензии:",
                "LicenseExpiresLabel": "Дата окончания:",
                "LicenseDaysLeftLabel": "Осталось:",
                "LicenseStatusLabel": "Статус:",
                "LicenseInactiveStatus": "Лицензия не активна",
                "LicenseActiveUnlimitedStatus": "Действительна (бессрочно)",
                "LicenseExpiredStatus": "Срок действия истек",
                "LicenseActiveStatus": "Действительна ({days_left})",
                "LicenseOtherStatus": "Статус: {days_left}",
                "LicenseUnlimited": "Бессрочно",
                "LicenseExpired": "Истёк",
                "DaysWord": "дней",
                "DayWord": "день",
                "Days234Word": "дня",
                "TodayExpiresWord": "сегодня",
                "WarningTitle": "Внимание",
                "NotFoundTitle": "Не найдено",
                "NetworkErrorTitle": "Ошибка сети",
                "ServerErrorTitle": "Ошибка сервера",
                "UnknownErrorTitle": "Неизвестная ошибка",
                "LicenseCheckingOnline": "Проверка ключа '{key}...' онлайн",
                "LicenseNotFoundMsg": "Лицензионный ключ '{key}' не найден на сервере.",
                "LicenseNetworkErrorMsg": "Ошибка сети при проверке лицензии.",
                "TryAgainLater": "Повторите попытку позже.",
                "LicenseServerErrorMsg": "Сервер вернул ошибку (Код: {code}). Попробуйте позже.",
                "LicenseUnknownErrorMsg": "Произошла ошибка при проверке ключа."
            },
            "English": {
                "MenuDetox": "Detox",
                "MenuSettings": "Settings",
                "MenuSchedule": "Schedule",
                "MenuStatistics": "Statistics",
                "MenuTheme": "Theme",
                "MenuAbout": "About",
                "StartDetoxAutomatically": "Start Detox Automatically",
                "SaveSettingsButton": "Save Settings",
                "RestoreDefaultsButton": "Restore Defaults",
                "MiniBreakButton": "Mini Break",
                "LongBreakButton": "Long Break",
                "PauseButton": "Pause",
                "ResetBreaksButton": "Reset Breaks",
                "ExitDetoxButton": "Exit Detox",
                "MiniBreakRemaining": "Time until short break: {minutes} min {seconds} sec",
                "LongBreakRemaining": "Time until long break: {minutes} min {seconds} sec",
                "ShowBreaksLabel": "Show Breaks:",
                "InWindowOption": "In Window",
                "FullscreenOption": "Fullscreen",
                "ShowExerciseTipsOption": "Show Exercise Tips",
                "ShowBreaksOnAllScreensOption": "Show Breaks on All Screens",
                "TrackIdleTimeOption": "Track Idle Time",
                "ShowBreaksInDNDModeOption": "Show Breaks in DND Mode",
                "SelectLanguageLabel": "Select Language:",
                "EnableSoundOnBreakOption": "Enable Sound on Break",
                "EnableDetoxOption": "Enable Detox",
                "CameraSettingsLabel": "Camera Settings:",
                "UseCameraForEyeTrackingOption": "Use Camera for Eye Tracking",
                "ShowCameraFeedOption": "Show Camera Feed",
                "ShowEyeGraphicsOption": "Show Eye Graphics",
                "MiniBreaksLabel": "Short Breaks:",
                "MiniBreaksDescription": "Regular Short Breaks...",
                "EnableMiniBreaksOption": "Enable Short Breaks",
                "MiniBreakDurationLabel": "Duration (sec):",
                "SecondsUnit": "sec",
                "MiniBreakIntervalLabel": "Every (min):",
                "MinutesUnit": "min",
                "NotifyBeforeMiniBreakOption": "Notify Before Short Break",
                "AllowPostponeMiniBreaksOption": "Allow Postponing Short Breaks",
                "LongBreaksLabel": "Long Breaks:",
                "LongBreaksDescription": "Long Breaks for Rest...",
                "EnableLongBreaksOption": "Enable Long Breaks",
                "LongBreakDurationLabel": "Duration (min):",
                "LongBreakIntervalLabel": "Every (min):",
                "NotifyBeforeLongBreakOption": "Notify Before Long Break",
                "AllowPostponeLongBreaksOption": "Allow Postponing Long Breaks",
                "StrictModeLabel": "Strict Mode:",
                "StrictModeDescription": "In strict mode you can't skip a break, and to continue you need to look away from the screen.",
                "EnableStrictModeMiniBreaksOption": "Enable Strict Mode for Short Breaks",
                "EnableStrictModeLongBreaksOption": "Enable Strict Mode for Long Breaks",
                "AllowedBreakTimesLabel": "Allowed Break Times (HH:MM):",
                "StartTimeLabel": "Start:",
                "EndTimeLabel": "End:",
                "EnableTimeRestrictionOption": "Enable Time Restriction",
                "ThemeLabel": "Theme",
                "ChangeThemeDescription": "Change Theme",
                "SystemDefaultOption": "System Default",
                "FlatlyOption": "Flatly",
                "DarklyOption": "Darkly",
                "CosmoOption": "Cosmo",
                "CyborgOption": "Cyborg",
                "SuperheroOption": "Superhero",
                "MintyOption": "Minty",
                "SelectThemeLabel": "Select Theme:",
                "BreakRemindersLabel": "Break Reminders",
                "VersionLabel": "Version 1.6.4",
                "CheckForUpdatesOption": "Automatically check for app updates",
                "CheckingForUpdates": "Checking for updates...",
                "LatestVersionInstalled": "You have the latest version installed",
                "UpdateAvailable": "Update available! Current/latest: {current}/{latest}",
                "VersionCheckError": "Version check error",
                "DownloadUpdateLink": "Download update",
                "LearnMoreAboutDetoxMessage": "Learn more about Detox, download the latest version, or contact us for support.",
                "VisitOurWebsiteLink": "Visit Our Website.",
                "DevelopedByLabel": "Developed by Alisher",
                "MiniBreaksStats": "Short Breaks: {count} (Skipped: {skipped})",
                "LongBreaksStats": "Long Breaks: {count} (Skipped: {skipped})",
                "BreakTimeStats": "Short Time: {minutes} min {seconds} sec | Long Time: {long_minutes} min {long_seconds} sec | Total Rest: {total_minutes} min {total_seconds} sec",
                "RuntimeStats": "Runtime: ~{minutes} min {seconds} sec",
                "ClearStatisticsButton": "Clear Statistics",
                "MinimizeToTray": "Minimize to tray",
                "MiniBreakTrayOption": "Mini Break",
                "LongBreakTrayOption": "Long Break",
                "PauseTrayOption": "Pause",
                "ExitTrayOption": "Exit",
                "MiniBreakTrayTitle": "Mini Break",
                "LongBreakTrayTitle": "Long Break",
                "BreaksDisabledMessage": "Breaks disabled by schedule",
                "PlayButton": "Resume",
                "CountdownWindowTitle": "Break",
                "SkipBreakButton": "Skip This Break",
                "LookAwayScreenMessage": "Look Away to Continue Timer.",
                "ScreenWarning": "Step Away from the Screen!",
                "RestingMessage": "Good Job! Resting...",
                "SecondsLeft": "sec left",
                "MinutesLeft": "min",
                "TimeUpMessage": "Time's Up!",
                "CloseButton": "Close",
                "TipCloseEyes": "Close your eyes for 20 seconds.",
                "TipLookOutWindow": "Look out the window or into the distance.",
                "TipShoulderRolls": "Roll your shoulders in circles.",
                "TipStretch": "Stretch up and to the sides.",
                "TipEyeRolls": "Roll your eyes in a circle.",
                "TipLookFarThenNose": "Look far away, then at the tip of your nose.",
                "TipStepAwayMonitor": "Step away from the monitor during the break.",
                "TipLookAwayScreen": "Look away from the screen.",
                "TipTurnAwayComputer": "Turn away from the computer.",
                "TipLookAwayToContinue": "Look away to continue.",
                "LicenseSectionTitle": "Detox License",
                "EnterLicenseKeyPrompt": "Enter a new key for verification:",
                "CheckButton": "Check",
                "LicenseKeyLabel": "Key:",
                "LicenseTypeLabel": "License Type:",
                "LicenseExpiresLabel": "Expiration Date:",
                "LicenseDaysLeftLabel": "Days Left:",
                "LicenseStatusLabel": "Status:",
                "LicenseInactiveStatus": "License is inactive",
                "LicenseActiveUnlimitedStatus": "Active (Unlimited)",
                "LicenseExpiredStatus": "Expired",
                "LicenseActiveStatus": "Active ({days_left})",
                "LicenseOtherStatus": "Status: {days_left}",
                "LicenseUnlimited": "Unlimited",
                "LicenseExpired": "Expired",
                "DaysWord": "days",
                "DayWord": "day",
                "Days234Word": "days",
                "TodayExpiresWord": "today",
                "WarningTitle": "Warning",
                "NotFoundTitle": "Not Found",
                "NetworkErrorTitle": "Network Error",
                "ServerErrorTitle": "Server Error",
                "UnknownErrorTitle": "Unknown Error",
                "LicenseCheckingOnline": "Checking key '{key}...' online",
                "LicenseNotFoundMsg": "License key '{key}' not found on the server.",
                "LicenseNetworkErrorMsg": "Network error while checking the license.",
                "TryAgainLater": "Try again later.",
                "LicenseServerErrorMsg": "Server returned an error (Code: {code}). Try again later.",
                "LicenseUnknownErrorMsg": "An error occurred while checking the key."
            },
            "Казакша": {
                "MenuDetox": "Detox",
                "MenuSettings": "Баптаулар",
                "MenuSchedule": "Кесте",
                "MenuStatistics": "Статистика",
                "MenuTheme": "Тақырып",
                "MenuAbout": "Бағдарлама туралы",
                "StartDetoxAutomatically": "Жүйеге кіргенде Detox-ты автоматты түрде іске қосу",
                "SaveSettingsButton": "Баптауларды сақтау",
                "RestoreDefaultsButton": "Әдепкі баптауларды қалпына келтіру",
                "MiniBreakButton": "Шағын үзіліс",
                "LongBreakButton": "Ұзақ үзіліс",
                "PauseButton": "Кідіріс",
                "ResetBreaksButton": "Үзілістерді қалпына келтіру",
                "ExitDetoxButton": "Detox-тан шығу",
                "MiniBreakRemaining": "Шағын үзіліске дейін: {minutes} мин {seconds} сек",
                "LongBreakRemaining": "Ұзақ үзіліске дейін: {minutes} мин {seconds} сек",
                "ShowBreaksLabel": "Үзілістерді көрсету:",
                "InWindowOption": "Терезеде",
                "FullscreenOption": "Толық экранда",
                "ShowExerciseTipsOption": "Үзіліс кезінде жаттығу идеяларын көрсету",
                "ShowBreaksOnAllScreensOption": "Барлық экрандарда үзілістерді көрсету",
                "TrackIdleTimeOption": "Жүйенің бос тұру уақытын бақылау",
                "ShowBreaksInDNDModeOption": "'Мазаламау' режимінде де үзілістерді көрсету",
                "SelectLanguageLabel": "Тілді таңдаңыз:",
                "EnableSoundOnBreakOption": "Үзіліс кезінде дыбысты қосу",
                "EnableDetoxOption": "Detox-ты қосу",
                "CameraSettingsLabel": "Камера баптаулары:",
                "UseCameraForEyeTrackingOption": "Қатаң режимде көзді бақылау үшін камераны пайдалану",
                "ShowCameraFeedOption": "Камерадан кескінді көрсету",
                "ShowEyeGraphicsOption": "Көз айналасындағы графиканы көрсету",
                "MiniBreaksLabel": "Шағын үзілістер:",
                "MiniBreaksDescription": "Тұрақты қысқа үзілістер...",
                "EnableMiniBreaksOption": "Шағын үзілістерді қосу",
                "MiniBreakDurationLabel": "Ұзақтығы (сек):",
                "SecondsUnit": "сек",
                "MiniBreakIntervalLabel": "Әрбір (мин):",
                "MinutesUnit": "мин",
                "NotifyBeforeMiniBreakOption": "Шағын үзіліс алдында хабарлау",
                "AllowPostponeMiniBreaksOption": "Шағын үзілістерді кейінге қалдыруға рұқсат ету",
                "LongBreaksLabel": "Ұзақ үзілістер:",
                "LongBreaksDescription": "Ұзақ демалыс үшін ұзақ үзілістер...",
                "EnableLongBreaksOption": "Ұзақ үзілістерді қосу",
                "LongBreakDurationLabel": "Ұзақтығы (мин):",
                "LongBreakIntervalLabel": "Әрбір (мин):",
                "NotifyBeforeLongBreakOption": "Ұзақ үзіліс алдында хабарлау",
                "AllowPostponeLongBreaksOption": "Ұзақ үзілістерді кейінге қалдыруға рұқсат ету",
                "StrictModeLabel": "Қатаң режим:",
                "StrictModeDescription": "Қатаң режимде үзілісті өткізіп жіберуге болмайды, ал жалғастыру үшін көзді экраннан алу керек.",
                "EnableStrictModeMiniBreaksOption": "Шағын үзілістер үшін қатаң режимді қосу",
                "EnableStrictModeLongBreaksOption": "Ұзақ үзілістер үшін қатаң режимді қосу",
                "AllowedBreakTimesLabel": "Рұқсат етілген үзіліс уақыты (HH:MM):",
                "StartTimeLabel": "Басталуы:",
                "EndTimeLabel": "Аяқталуы:",
                "EnableTimeRestrictionOption": "Уақыт бойынша шектеуді қосу",
                "ThemeLabel": "Тақырып",
                "ChangeThemeDescription": "Мұнда қолданба тақырыбын өзгертуге болады",
                "SystemDefaultOption": "Жүйедегідей",
                "FlatlyOption": "Flatly",
                "DarklyOption": "Darkly",
                "CosmoOption": "Cosmo",
                "CyborgOption": "Cyborg",
                "SuperheroOption": "Superhero",
                "MintyOption": "Minty",
                "SelectThemeLabel": "Тақырыпты таңдаңыз:",
                "BreakRemindersLabel": "Үзіліс туралы еске салғыштар",
                "VersionLabel": "Нұсқасы 1.6.4",
                "CheckForUpdatesOption": "Қолданба жаңартуларын автоматты түрде тексеру",
                "CheckingForUpdates": "Жаңартуларды тексеру...",
                "LatestVersionInstalled": "Сізде соңғы нұсқа орнатылған",
                "UpdateAvailable": "Жаңарту қол жетімді! Ағымдағы/жаңа: {current}/{latest}",
                "VersionCheckError": "Нұсқаны тексеру қатесі",
                "DownloadUpdateLink": "Жаңартуды жүктеу",
                "LearnMoreAboutDetoxMessage": "Detox функциялары туралы көбірек білу үшін, оқудан өтіңіз, соңғы нұсқасын жүктеп алыңыз немесе қолдау алу үшін бізбен хабарласыңыз.",
                "VisitOurWebsiteLink": "Біздің сайтқа кіріңіз.",
                "DevelopedByLabel": "Әзірлеген Әлішер",
                "MiniBreaksStats": "Шағын үзілістер: {count} (өткізілген: {skipped})",
                "LongBreaksStats": "Ұзақ үзілістер: {count} (өткізілген: {skipped})",
                "BreakTimeStats": "Шағын уақыт: {minutes} мин {seconds} сек | Ұзақ уақыт: {long_minutes} мин {long_seconds} сек | Барлық демалыс: {total_minutes} мин {total_seconds} сек",
                "RuntimeStats": "Жұмыс уақыты: ~{minutes} мин {seconds} сек",
                "ClearStatisticsButton": "Статистиканы тазалау",
                "MinimizeToTray": "Трейге жинау",
                "MiniBreakTrayOption": "Шағын үзіліс",
                "LongBreakTrayOption": "Ұзақ үзіліс",
                "PauseTrayOption": "Кідіріс",
                "ExitTrayOption": "Шығу",
                "MiniBreakTrayTitle": "Шағын үзіліс",
                "LongBreakTrayTitle": "Ұзақ үзіліс",
                "BreaksDisabledMessage": "Үзілістер кесте бойынша өшірілген",
                "PlayButton": "Жалғастыру",
                "CountdownWindowTitle": "Үзіліс",
                "SkipBreakButton": "Бұл үзілісті өткізіп жіберу",
                "LookAwayScreenMessage": "Таймерді жалғастыру үшін көзіңізді басқа жаққа бұрыңыз.",
                "ScreenWarning": "Экраннан алшақ кетіңіз!",
                "RestingMessage": "Жарайсың! Демаламыз...",
                "SecondsLeft": "сек қалды",
                "MinutesLeft": "мин",
                "TimeUpMessage": "Уақыт бітті!",
                "CloseButton": "Жабу",
                "TipCloseEyes": "Көзіңізді 20 секундқа жұмыңыз.",
                "TipLookOutWindow": "Терезеге немесе алысқа қараңыз.",
                "TipShoulderRolls": "Иығыңызбен айналмалы қозғалыс жасаңыз.",
                "TipStretch": "Жоғарыға және жан-жаққа созылыңыз.",
                "TipEyeRolls": "Көзіңізбен айналдыра қозғаңыз.",
                "TipLookFarThenNose": "Алысқа, содан кейін мұрын ұшына қараңыз.",
                "TipStepAwayMonitor": "Үзіліс кезінде монитордан алшақ кетіңіз.",
                "TipLookAwayScreen": "Экраннан басқа жаққа қараңыз.",
                "TipTurnAwayComputer": "Компьютерден бұрылыңыз.",
                "TipLookAwayToContinue": "Жалғастыру үшін көзіңізді басқа жаққа бұрыңыз.",
                "LicenseSectionTitle": "Detox Лицензиясы",
                "EnterLicenseKeyPrompt": "Тексеру үшін жаңа кілт енгізіңіз:",
                "CheckButton": "Тексеру",
                "LicenseKeyLabel": "Кілт:",
                "LicenseTypeLabel": "Лицензия түрі:",
                "LicenseExpiresLabel": "Мерзімі аяқталады:",
                "LicenseDaysLeftLabel": "Қалды:",
                "LicenseStatusLabel": "Мәртебе:",
                "LicenseInactiveStatus": "Лицензия белсенді емес",
                "LicenseActiveUnlimitedStatus": "Белсенді (Шексіз)",
                "LicenseExpiredStatus": "Мерзімі аяқталды",
                "LicenseActiveStatus": "Белсенді ({days_left})",
                "LicenseOtherStatus": "Мәртебе: {days_left}",
                "LicenseUnlimited": "Шексіз",
                "LicenseExpired": "Аяқталды",
                "DaysWord": "күндер",
                "DayWord": "күн",
                "Days234Word": "күндер",
                "TodayExpiresWord": "бүгін",
                "WarningTitle": "Ескерту",
                "NotFoundTitle": "Табылмады",
                "NetworkErrorTitle": "Желі қатесі",
                "ServerErrorTitle": "Сервер қатесі",
                "UnknownErrorTitle": "Белгісіз қате",
                "LicenseCheckingOnline": "Кілтті тексеру '{key}...' онлайн",
                "LicenseNotFoundMsg": "Лицензия кілті '{key}' серверде табылмады.",
                "LicenseNetworkErrorMsg": "Лицензияны тексеру кезінде желі қатесі.",
                "TryAgainLater": "Кейінірек қайталап көріңіз.",
                "LicenseServerErrorMsg": "Сервер қатені қайтарды (Код: {code}). Кейінірек қайталап көріңіз.",
                "LicenseUnknownErrorMsg": "Кілтті тексеру кезінде қате болды."
            }
        }

    def check_and_update_localization(self): # Это для обновления словаря
        default_translations = self.get_default_translations()
        updated = False
        # Загружаем текущий файл
        if self.localization_file.exists():
            with open(self.localization_file, "r", encoding="utf-8") as file:
                current = json.load(file)
        else:
            current = {}

        for lang, default_dict in default_translations.items():
            if lang not in current:
                current[lang] = {}
                updated = True
            for key, value in default_dict.items():
                if key not in current[lang]:
                    current[lang][key] = value
                    updated = True
        # Если были изменения — сохраняем
        if updated:
            with open(self.localization_file, "w", encoding="utf-8") as file:
                json.dump(current, file, ensure_ascii=False, indent=4)
        self.translations = current

    def check_new_version_github(self):
        if hasattr(self, "version_status_label"):
            self.version_status_label.config(
                foreground="gray"
            )
            self.update_idletasks()
        if hasattr(self, "download_link"):
            self.download_link.config(text="")
            self.download_link.pack_forget()
        try:
            response = requests.get(
                "https://api.github.com/repos/crlx1q/detoxapp/releases/latest",
                timeout=5
            )
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "").strip()
                download_url = release_data.get("html_url", "")
                if latest_version and self._compare_versions(self.current_version, latest_version):
                    # Доступна новая версия
                    self._version_settings["latest_version_status"] = False
                    self._version_settings["new_version"] = latest_version
                    self._version_settings["download_url"] = download_url
                    self._version_settings["current_version"] = self.current_version
                    self.save_version_settings()
                    if hasattr(self, "version_status_label"):
                        self.version_status_label.config(
                            text=self.translate("UpdateAvailable").format(
                                current=self.current_version,
                                latest=latest_version
                            ),
                            foreground="red"
                        )
                    if hasattr(self, "download_link") and download_url:
                        self.download_link.config(
                            text=self.translate("DownloadUpdateLink"),
                            foreground="#00bfff",
                            cursor="hand2"
                        )
                        self.download_link.bind("<Button-1>",
                            lambda e, url=download_url: self.open_website(url))
                        self.download_link.pack(pady=5)
                else:
                    # У пользователя последняя версия стоит
                    self._version_settings["latest_version_status"] = True
                    self._version_settings["new_version"] = ""
                    self._version_settings["download_url"] = ""
                    self._version_settings["current_version"] = self.current_version
                    self.save_version_settings()
                    if hasattr(self, "version_status_label"):
                        self.version_status_label.config(
                            text=self.translate("LatestVersionInstalled"),
                            foreground="green"
                        )
                    if hasattr(self, "download_link"):
                        self.download_link.pack_forget()
            else:
                # Ошибка проверки
                if hasattr(self, "version_status_label"):
                    self.version_status_label.config(
                        text=self.translate("VersionCheckError"),
                        foreground="orange"
                    )
        except Exception as e:
            print(f"Ошибка при проверке обновлений: {e}")
            if hasattr(self, "version_status_label"):
                self.version_status_label.config(
                    text=self.translate("VersionCheckError"),
                    foreground="orange"
                )
        # Если включена автопроверка, запускаем снова через 24 часа
        if self.variables["autoupdate"].get():
            self.after(24*60*60*1000, self.check_new_version_github)

    def save_version_settings(self):
        if self.settings_file.exists():
            with open(self.settings_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        else:
            data = {}
        data.update({
            "autoupdate": self.variables["autoupdate"].get(),
            "latest_version_status": self._version_settings.get("latest_version_status", True),
            "current_version": self.current_version,
            "new_version": self._version_settings.get("new_version", ""),
            "download_url": self._version_settings.get("download_url", "")
        })
        with open(self.settings_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def translate(self, key):
        language = self.variables["language"].get()
        if language.lower().startswith("англ"):
            language = "English"
        elif language.lower().startswith("рус"):
            language = "Русский"
        return self.translations.get(language, {}).get(key, key)

    def _fix_language_variable(self):
        lang = self.variables["language"].get()
        if lang.lower().startswith("англ"):
            self.variables["language"].set("English")
        elif lang.lower().startswith("рус"):
            self.variables["language"].set("Русский")
        if hasattr(self, "settings_frame"):
            for child in self.settings_frame.winfo_children():
                if isinstance(child, ttk.LabelFrame) or isinstance(child, ttk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, ttk.Combobox):
                            subchild.set(self.variables["language"].get())
                elif isinstance(child, ttk.Combobox):
                    child.set(self.variables["language"].get())

    # ------------------------------
    # Вспомогательные методы
    # ------------------------------
    def get_current_theme_name(self):
        return self.variables["theme"].get()

    def create_top_panel(self):
        if hasattr(self, "top_frame") and self.top_frame.winfo_exists():
            self.top_frame.destroy()
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side="top", fill="x", pady=10)
        self.top_frame = top_frame

        self.top_buttons = []
        buttons = [
            (self.translate("MenuDetox"), self.show_detox),
            (self.translate("MenuSettings"), self.show_settings),
            (self.translate("MenuSchedule"), self.show_schedule),
            (self.translate("MenuStatistics"), self.show_statistics),
            (self.translate("MenuTheme"), self.show_theme),
            (self.translate("MenuAbout"), self.show_about),
        ]
        for btn_text, command in buttons:
            btn = ttk.Button(
                top_frame,
                text=btn_text,
                bootstyle="primary-outline",
                command=lambda c=command: (c(), self.focus_set()),
                takefocus=False
            )
            btn.pack(side="left", padx=5)
            self.top_buttons.append(btn)

        # Светлая тема солнце - темная луна
        theme_icon = "🌙" if self.variables["theme"].get() == "darkly" else "☀️"
        self.theme_button = ttk.Button(
            top_frame,
            text=theme_icon,
            bootstyle="link",
            command=lambda: (self.toggle_theme(), self.focus_set()),
            takefocus=False
        )
        self.theme_button.pack(side="right", padx=5)

        self.minimize_button = ttk.Button(
            top_frame,
            text=self.translate("MinimizeToTray"),
            bootstyle="link",
            command=lambda: (self.minimize_to_tray(), self.focus_set()),
            takefocus=False
        )
        self.minimize_button.pack(side="right", padx=5)

    def show_detox(self):
        self.hide_all_frames()
        self.detox_frame.pack(pady=20, fill="both", padx=20, expand=True)

    def show_settings(self):
        self.hide_all_frames()
        self.settings_frame.pack(pady=20, fill="x", padx=20)

    def show_schedule(self):
        self.hide_all_frames()
        self.schedule_frame.pack(pady=20, fill="both", expand=True, padx=20)

    def show_theme(self):
        self.hide_all_frames()
        self.theme_frame.pack(pady=20, fill="x", padx=20)

    def show_about(self):
        self.hide_all_frames()
        self.about_frame.pack(pady=20, fill="x", padx=20)

    def show_statistics(self):
        self.hide_all_frames()
        self._statistics_live_update = True
        self.update_statistics_labels()
        self.statistics_frame.pack(pady=20, fill="x", padx=20)
        self._schedule_statistics_update()

    def hide_all_frames(self):
        self._statistics_live_update = False
        for frame in (
            self.detox_frame,
            self.settings_frame,
            self.schedule_frame,
            self.theme_frame,
            self.about_frame,
            self.statistics_frame
        ):
            frame.pack_forget()

    def _schedule_statistics_update(self):
        if getattr(self, '_statistics_live_update', False):
            self.update_statistics_labels()
            self.after(1000, self._schedule_statistics_update)

    def update_statistics_labels(self):
        self.lbl_stats_mini.config(
            text=self.translate("MiniBreaksStats").format(count=self.stats['mini_breaks'], skipped=self.stats['mini_skipped'])
        )
        self.lbl_stats_long.config(
            text=self.translate("LongBreaksStats").format(count=self.stats['long_breaks'], skipped=self.stats['long_skipped'])
        )

        # Суммарное время отдыха в статах
        mini_m = self.stats['mini_time'] // 60
        mini_s = self.stats['mini_time'] % 60
        long_m = self.stats['long_time'] // 60
        long_s = self.stats['long_time'] % 60
        total_s = self.stats['mini_time'] + self.stats['long_time']
        total_m = total_s // 60
        total_s_rem = total_s % 60

        self.lbl_stats_break_time.config(
            text=self.translate("BreakTimeStats").format(minutes=mini_m, seconds=mini_s, long_minutes=long_m, long_seconds=long_s, total_minutes=total_m, total_seconds=total_s_rem)
        )

        # Время работы программы в реальном времени)
        now = datetime.datetime.now()
        elapsed = now - self.start_time
        session_seconds = int(elapsed.total_seconds())
        total_runtime = self.stats['total_runtime'] + session_seconds
        runtime_m = total_runtime // 60
        runtime_s = total_runtime % 60
        self.lbl_stats_runtime.config(
            text=self.translate("RuntimeStats").format(minutes=runtime_m, seconds=runtime_s)
        )

    # ------------------------------
    # Вспомогательный метод для обновления интерфейса после смены лицензии
    # ------------------------------
    def refresh_license_ui(self):
        # Это нужно для обновления интерфейса после смены лицензии
        self.detox_frame.destroy()
        self.detox_frame = self.create_detox_frame()
        self.settings_frame.destroy()
        self.settings_frame = self.create_settings()
        self.schedule_frame.destroy()
        self.schedule_frame = self.create_schedule_frame()
        self.theme_frame.destroy()
        self.theme_frame = self.create_theme_frame()
        self.about_frame.destroy()
        self.about_frame = self.create_about_frame()
        self.statistics_frame.destroy()
        self.statistics_frame = self.create_statistics_frame()
        self.show_detox()
        self.apply_theme()
        self._fix_language_variable()

    # ------------------------------
    # Фрейм «Detox»
    # ------------------------------
    def create_detox_frame(self):
        frame = ttk.Frame(self.content_frame, padding=20)
        animated_canvas = AnimatedCanvas(frame, image_path=None, width=200, height=200, bg="black", highlightthickness=0)
        animated_canvas.pack(pady=10)

        lbl_title = ttk.Label(frame, text=self.translate("MenuDetox"), font=("Roboto", 24, "bold"))
        lbl_title.pack(pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        license_status = self.get_license_status()
        btn_state = "normal" if license_status == "active" else "disabled"

        btn_mini_break = ttk.Button(
            btn_frame,
            text=self.translate("MiniBreakButton"),
            bootstyle="success",
            command=lambda: (self.go_to_mini_break(), self.focus_set()),
            width=25,
            takefocus=False,
            state=btn_state
        )
        btn_mini_break.pack(pady=5)

        btn_long_break = ttk.Button(
            btn_frame,
            text=self.translate("LongBreakButton"),
            bootstyle="info",
            command=lambda: (self.go_to_long_break(), self.focus_set()),
            width=25,
            takefocus=False,
            state=btn_state
        )
        btn_long_break.pack(pady=5)

        self.btn_pause = ttk.Button(
            btn_frame,
            text=self.translate("PauseButton"),
            bootstyle="warning",
            command=lambda: (self.pause_detox(), self.focus_set()),
            width=25,
            takefocus=False
        )
        self.btn_pause.pack(pady=5)

        btn_reset = ttk.Button(
            btn_frame,
            text=self.translate("ResetBreaksButton"),
            bootstyle="danger",
            command=lambda: (self.reset_detox(), self.focus_set()),
            width=25,
            takefocus=False
        )
        btn_reset.pack(pady=5)

        btn_exit = ttk.Button(
            btn_frame,
            text=self.translate("ExitDetoxButton"),
            bootstyle="danger-outline",
            command=self.exit_detox,
            width=25,
            takefocus=False
        )
        btn_exit.pack(pady=5)

        lbl_mini_remaining = ttk.Label(frame, text=self.translate("MiniBreakRemaining").format(minutes=0, seconds=0), font=("Roboto", 14))
        lbl_mini_remaining.pack(pady=5)
        self.mini_remaining_label = lbl_mini_remaining

        lbl_long_remaining = ttk.Label(frame, text=self.translate("LongBreakRemaining").format(minutes=0, seconds=0), font=("Roboto", 14))
        lbl_long_remaining.pack(pady=5)
        self.long_remaining_label = lbl_long_remaining

        return frame

    def go_to_mini_break(self):
        if self.variables["enable_short_breaks"].get() and self.variables["detox_active"].get():
            if self.break_window_open:
                self._pending_break = "mini"
                return
            self.break_window_open = True
            self.stats["mini_breaks"] += 1
            self.stats["total_breaks"] += 1
            CountdownWindow(
                parent=self,
                duration=self.variables["short_break_duration"].get(),
                theme=self.get_current_theme_name(),
                break_type="mini",
                strict_mode=self.variables["strict_mode_mini_breaks"].get(),
                sound_enabled=self.variables["sound_on_break"].get(),
                break_mode=self.variables["break_mode"].get(),
                use_camera=self.variables["use_camera"].get(),
                show_camera_feed=self.variables["show_camera_feed"].get(),
                show_eye_graphics=self.variables["show_eye_graphics"].get(),
                on_skip=lambda t: self._on_break_close("mini", t, skipped=True),
                on_complete=lambda t: self._on_break_close("mini", t, skipped=False),
            )
            # Сохраняем ссылку на EyeTracker для корректного завершения
            if hasattr(self, 'break_window_open') and self.break_window_open:
                self._active_eye_tracker = getattr(self, 'eye_tracker', None)
            self.mini_remaining_time = self.variables["short_break_interval"].get() * 60

    def go_to_long_break(self):
        if self.variables["enable_long_breaks"].get() and self.variables["detox_active"].get():
            if self.break_window_open:
                self._pending_break = "long"
                return
            self.break_window_open = True
            self.stats["long_breaks"] += 1
            self.stats["total_breaks"] += 1
            CountdownWindow(
                parent=self,
                duration=self.variables["long_break_duration"].get(),
                theme=self.get_current_theme_name(),
                break_type="long",
                strict_mode=self.variables["strict_mode_long_breaks"].get(),
                sound_enabled=self.variables["sound_on_break"].get(),
                break_mode=self.variables["break_mode"].get(),
                use_camera=self.variables["use_camera"].get(),
                show_camera_feed=self.variables["show_camera_feed"].get(),
                show_eye_graphics=self.variables["show_eye_graphics"].get(),
                on_skip=lambda t: self._on_break_close("long", t, skipped=True),
                on_complete=lambda t: self._on_break_close("long", t, skipped=False),
            )
            if hasattr(self, 'break_window_open') and self.break_window_open:
                self._active_eye_tracker = getattr(self, 'eye_tracker', None)
            self.long_remaining_time = self.variables["long_break_interval"].get() * 60

    def close_eye_tracker_on_exit(self):
        # Корректно останавливаем EyeTracker при завершении программы
        try:
            if hasattr(self, '_active_eye_tracker') and self._active_eye_tracker:
                self._active_eye_tracker.stop()
        except Exception:
            pass

    def _on_break_close(self, break_type, seconds, skipped=False):
        self.break_window_open = False
        self._add_break_time(break_type, seconds, skipped)
        # Если был запрошен другой перерыв во время текущего — запускаем его
        if self._pending_break == "mini":
            self._pending_break = None
            self.after(100, self.go_to_mini_break)
        elif self._pending_break == "long":
            self._pending_break = None
            self.after(100, self.go_to_long_break)

    def _add_break_time(self, break_type, seconds, skipped=False):

        if break_type == "mini":
            self.stats["mini_time"] += seconds
            if skipped:
                self.stats["mini_skipped"] += 1
        else:
            self.stats["long_time"] += seconds
            if skipped:
                self.stats["long_skipped"] += 1
        self.update_statistics_labels()
        self.save_settings()

    def restore_from_tray(self, icon=None, item=None):
        if hasattr(self, "tray_icon"):
            self.tray_icon.stop()
        self.deiconify()

    def pause_detox(self):
        if not self.paused:
            self.paused = True
            if self.break_timer_mini:
                self.after_cancel(self.break_timer_mini)
                self.break_timer_mini = None
            if self.break_timer_long:
                self.after_cancel(self.break_timer_long)
                self.break_timer_long = None
            self.btn_pause.config(text=self.translate("PlayButton"))
        else:
            self.paused = False
            self.update_mini_timer()
            self.update_long_timer()
            self.btn_pause.config(text=self.translate("PauseButton"))

    def reset_detox(self):
        self.stop_detox()
        self.start_detox()

    def exit_detox(self):
        self.update_runtime_stat()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()

    def toggle_detox(self):
        if self.variables["detox_active"].get():
            self.start_detox()
        else:
            self.stop_detox()

    def start_detox(self):
        if not self.detox_active:
            self.detox_active = True
            self.variables["detox_active"].set(True)
            self.start_mini_timer()
            self.start_long_timer()

    def stop_detox(self):
        if self.detox_active:
            self.detox_active = False
            self.variables["detox_active"].set(False)
            if self.break_timer_mini:
                self.after_cancel(self.break_timer_mini)
                self.break_timer_mini = None
            if self.break_timer_long:
                self.after_cancel(self.break_timer_long)
                self.break_timer_long = None

    def start_mini_timer(self):
        self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
        self.update_mini_timer()

    def update_mini_timer(self):
        if not self.detox_active or self.paused:
            return
        if self.variables["enable_time_restriction"].get() and not self.is_within_allowed_time():
            self.mini_remaining_label.config(text=self.translate("BreaksDisabledMessage"))
            self.break_timer_mini = self.after(1000, self.update_mini_timer)
            return
        if self.mini_remaining_time > 0:
            self.mini_remaining_time -= 1
            minutes, seconds = divmod(self.mini_remaining_time, 60)
            self.mini_remaining_label.config(text=self.translate("MiniBreakRemaining").format(minutes=minutes, seconds=seconds))
            self.break_timer_mini = self.after(1000, self.update_mini_timer)
        else:
            if self.variables["enable_short_breaks"].get():
                self.go_to_mini_break()
            self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
            self.break_timer_mini = self.after(1000, self.update_mini_timer)

    def start_long_timer(self):
        self.long_remaining_time = self.variables["long_break_interval"].get() * 60
        self.update_long_timer()

    def update_long_timer(self):
        if not self.detox_active or self.paused:
            return
        if self.variables["enable_time_restriction"].get() and not self.is_within_allowed_time():
            self.long_remaining_label.config(text=self.translate("BreaksDisabledMessage"))
            self.break_timer_long = self.after(1000, self.update_long_timer)
            return
        if self.long_remaining_time > 0:
            self.long_remaining_time -= 1
            minutes, seconds = divmod(self.long_remaining_time, 60)
            self.long_remaining_label.config(text=self.translate("LongBreakRemaining").format(minutes=minutes, seconds=seconds))
            self.break_timer_long = self.after(1000, self.update_long_timer)
        else:
            if self.variables["enable_long_breaks"].get():
                self.go_to_long_break()
            self.long_remaining_time = self.variables["long_break_interval"].get() * 60
            self.break_timer_long = self.after(1000, self.update_long_timer)

    def is_within_allowed_time(self):
        start_time = self.variables["break_start_time"].get()
        end_time = self.variables["break_end_time"].get()
        now = datetime.datetime.now().time()

        try:
            start = datetime.datetime.strptime(start_time, "%H:%M").time()
            end = datetime.datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            return True

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def on_short_break_interval_change(self, *args):
        if self.detox_active:
            if self.break_timer_mini:
                self.after_cancel(self.break_timer_mini)
                self.break_timer_mini = None
            self.start_mini_timer()

    def on_long_break_interval_change(self, *args):
        if self.detox_active:
            if self.break_timer_long:
                self.after_cancel(self.break_timer_long)
                self.break_timer_long = None
            self.start_long_timer()

    def background_license_check(self):
        # Проверка лицензии в фоне при запуске.
        # Если ключ удалён или срок истёк — показать предупреждение.
        license_data = load_license_from_local()
        expired = False
        removed = False
        if not license_data or not license_data.get("license_key"):
            removed = True
        else:
            expires = license_data.get("expires")
            if expires and expires not in ("Бессрочно", None):
                try:
                    exp_date = datetime.datetime.strptime(expires, "%Y-%m-%d").date()
                    today = datetime.datetime.now().date()
                    if (exp_date - today).days < 0:
                        expired = True
                except Exception:
                    pass
        if hasattr(self, "_about_license_refresh_display"):
            self._about_license_refresh_display()
        # Можно повторять проверку раз в сутки, если нужно:
        # self.after(24*60*60*1000, self.background_license_check)

    def background_online_license_check(self):
        license_data = load_license_from_local()
        key = license_data.get("license_key") if license_data else None
        if not key:
            return
        result = search_license_online(key)
        updated = False
        if result['status'] == 'success':
            save_license_locally(result['data'])
            updated = True
        elif result['status'] == 'not_found':
            save_license_locally(None)
            updated = True
        # Показываем предупреждение, если нет интернета
        if result['status'] == 'network_error':
            messagebox.showwarning(
                "Лицензия",
                result.get('message', "Не удалось проверить лицензию: нет соединения с интернетом.")
            )
        if updated:
            self.after(0, self._after_online_license_update, result)

    def _after_online_license_update(self, result):
        if hasattr(self, "_about_license_refresh_display"):
            self._about_license_refresh_display()
        if result['status'] == 'not_found':
            messagebox.showwarning("Лицензия", "Лицензионный ключ был удалён или не найден на сервере.\nНекоторые функции могут быть недоступны.")
        elif result['status'] == 'success':
            expires = result['data'].get("expires")
            if expires and expires not in ("Бессрочно", None):
                try:
                    exp_date = datetime.datetime.strptime(expires, "%Y-%m-%d").date()
                    today = datetime.datetime.now().date()
                    if (exp_date - today).days < 0:
                        messagebox.showerror("Лицензия", "Срок действия вашей лицензии истёк (по данным сервера).\nПожалуйста, обновите лицензию для продолжения работы.")
                except Exception:
                    pass

    def get_license_status(self):
        data = load_license_from_local()
        if not data or not data.get("license_key"):
            return "none"
        expires = data.get("expires")
        if expires and expires not in ("Бессрочно", None):
            try:
                exp_date = datetime.datetime.strptime(expires, "%Y-%m-%d").date()
                today = datetime.datetime.now().date()
                if (exp_date - today).days < 0:
                    return "expired"
            except Exception:
                return "expired"
        return "active"

    # ------------------------------
    # Фрейм «Настройки»
    # ------------------------------
    def create_settings(self):
        frame = ttk.Frame(self.content_frame, padding=20)
        cb_autostart = ttk.Checkbutton(
            frame,
            text="Запускать Detox автоматически в трее при входе в систему",  # изменено описание
            variable=self.variables["autostart"],
            bootstyle="primary",
            # command не нужен, используем trace
        )
        cb_autostart.pack(anchor="w", pady=5)

        lbl_breaks = ttk.Label(frame, text=self.translate("ShowBreaksLabel"), font=("Roboto", 14, "bold"))
        lbl_breaks.pack(anchor="w", pady=10)

        radio_frame = ttk.Frame(frame)
        radio_frame.pack(anchor="w", pady=5)

        rb_window = ttk.Radiobutton(
            radio_frame,
            text=self.translate("InWindowOption"),
            variable=self.variables["break_mode"],
            value="window",
            bootstyle="primary",
        )
        rb_window.pack(side="left", padx=5)

        rb_fullscreen = ttk.Radiobutton(
            radio_frame,
            text=self.translate("FullscreenOption"),
            variable=self.variables["break_mode"],
            value="fullscreen",
            bootstyle="primary",
        )
        rb_fullscreen.pack(side="left", padx=5)

        options = {
            self.translate("ShowExerciseTipsOption"): "exercise_tips",
            self.translate("ShowBreaksOnAllScreensOption"): "break_all_screens",
            self.translate("TrackIdleTimeOption"): "track_idle",
            self.translate("ShowBreaksInDNDModeOption"): "dnd_mode",
        }
        for text, var_name in options.items():
            cb = ttk.Checkbutton(frame, text=text, variable=self.variables[var_name], bootstyle="primary")
            cb.pack(anchor="w", pady=5)

        lbl_language = ttk.Label(frame, text=self.translate("SelectLanguageLabel"), font=("Roboto", 14, "bold"))
        lbl_language.pack(anchor="w", pady=10)
        language_combobox = ttk.Combobox(frame, textvariable=self.variables["language"], state="readonly", bootstyle="primary")
        language_combobox["values"] = ["Русский", "English", "Казакша"]
        language_combobox.pack(anchor="w", pady=5)
        language_combobox.set(self.variables["language"].get())
        def on_language_change(event=None):
            lang = self.variables["language"].get()
            if lang.lower().startswith("англ"):
                self.variables["language"].set("English")
            elif lang.lower().startswith("рус"):
                self.variables["language"].set("Русский")
            elif lang.lower().startswith("каз"):
                self.variables["language"].set("Казакша")
            self.refresh_ui_texts()
            self.save_settings()
        language_combobox.bind("<<ComboboxSelected>>", on_language_change)

        cb_sound = ttk.Checkbutton(
            frame,
            text=self.translate("EnableSoundOnBreakOption"),
            variable=self.variables["sound_on_break"],
            bootstyle="primary",
        )
        cb_sound.pack(anchor="w", pady=5)

        cb_detox = ttk.Checkbutton(
            frame,
            text=self.translate("EnableDetoxOption"),
            variable=self.variables["detox_active"],
            bootstyle="primary",
            command=self.toggle_detox,
        )
        cb_detox.pack(anchor="w", pady=10)

        lbl_camera = ttk.Label(frame, text=self.translate("CameraSettingsLabel"), font=("Roboto", 14, "bold"))
        lbl_camera.pack(anchor="w", pady=10)

        license_status = self.get_license_status()

        cb_use_camera = ttk.Checkbutton(
            frame,
            text=self.translate("UseCameraForEyeTrackingOption"),
            variable=self.variables["use_camera"],
            bootstyle="primary",
            command=self.toggle_camera_settings,
            state="normal" if license_status == "active" else "disabled"
        )
        cb_use_camera.pack(anchor="w", pady=5)

        self.camera_settings_frame = ttk.Frame(frame)
        cb_show_camera = ttk.Checkbutton(
            self.camera_settings_frame,
            text=self.translate("ShowCameraFeedOption"),
            variable=self.variables["show_camera_feed"],
            bootstyle="primary",
        )
        cb_show_camera.pack(anchor="w", pady=5)
        
        cb_show_graphics = ttk.Checkbutton(
            self.camera_settings_frame,
            text=self.translate("ShowEyeGraphicsOption"),
            variable=self.variables["show_eye_graphics"],
            bootstyle="primary",
        )
        cb_show_graphics.pack(anchor="w", pady=5)
        
        if self.variables["use_camera"].get():
            self.camera_settings_frame.pack(anchor="w", padx=20, pady=5)

        self.create_control_buttons(frame)
        return frame

    def toggle_camera_settings(self):
        if self.variables["use_camera"].get():
            self.camera_settings_frame.pack(anchor="w", padx=20, pady=5)
        else:
            self.camera_settings_frame.pack_forget()

    def create_control_buttons(self, parent_frame):
        control_frame = ttk.Frame(parent_frame)
        control_frame.pack(pady=20)

        save_button = ttk.Button(
            control_frame,
            text=self.translate("SaveSettingsButton"),
            bootstyle="success",
            command=lambda: (self.save_settings(), self.focus_set()),
            takefocus=False
        )
        save_button.pack(side="left", padx=10)

        reset_button = ttk.Button(
            control_frame,
            text=self.translate("RestoreDefaultsButton"),
            bootstyle="danger-outline",
            command=lambda: (self.reset_to_defaults(), self.focus_set()),
            takefocus=False
        )
        reset_button.pack(side="left", padx=10)

    def refresh_ui_texts(self):
        menu_keys = ["MenuDetox", "MenuSettings", "MenuSchedule", "MenuStatistics", "MenuTheme", "MenuAbout"]
        for i, key in enumerate(menu_keys):
            self.top_buttons[i].config(text=self.translate(key))
        self.minimize_button.config(text=self.translate("MinimizeToTray"))
        self.theme_button.config(text="🌙" if self.variables["theme"].get() == "darkly" else "☀️")

        self.detox_frame.destroy()
        self.detox_frame = self.create_detox_frame()
        self.settings_frame.destroy()
        self.settings_frame = self.create_settings()
        self.schedule_frame.destroy()
        self.schedule_frame = self.create_schedule_frame()
        self.theme_frame.destroy()
        self.theme_frame = self.create_theme_frame()
        self.about_frame.destroy()
        self.about_frame = self.create_about_frame()
        self.statistics_frame.destroy()
        self.statistics_frame = self.create_statistics_frame()
        self.show_detox()
        self.apply_theme()
        self._fix_language_variable()

    # ------------------------------
    # Фрейм «Расписание» (с учётом нового блока «Строгий режим»)
    # ------------------------------
    def create_schedule_frame(self):
        frame = ttk.Frame(self.content_frame)
        canvas = ttk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

        license_status = self.get_license_status()

        # Мини-перерывы
        lbl_short = ttk.Label(scrollable_frame, text=self.translate("MiniBreaksLabel"), font=("Roboto", 14, "bold"))
        lbl_short.pack(anchor="w", pady=10)

        lbl_short_desc = ttk.Label(
            scrollable_frame,
            text=self.translate("MiniBreaksDescription"),
            font=("Roboto", 10),
            wraplength=700
        )
        lbl_short_desc.pack(anchor="w", pady=5)

        cb_enable_short = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("EnableMiniBreaksOption"),
            variable=self.variables["enable_short_breaks"],
            bootstyle="primary"
        )
        cb_enable_short.pack(anchor="w", pady=5)

        duration_frame = ttk.Frame(scrollable_frame)
        duration_frame.pack(anchor="w", pady=5, fill="x")
        lbl_duration_short = ttk.Label(duration_frame, text=self.translate("MiniBreakDurationLabel"), font=("Roboto", 10))
        lbl_duration_short.pack(side="left")
        self.short_break_duration_label = ttk.Label(duration_frame, text=f"{self.variables['short_break_duration'].get()} {self.translate('SecondsUnit')}", font=("Roboto", 10))
        self.short_break_duration_label.pack(side="right", padx=10)
        self.variables["short_break_duration"].trace("w", self.update_short_break_duration_label)

        scale_short_duration = ttk.Scale(
            scrollable_frame,
            variable=self.variables["short_break_duration"],
            from_=10, to=600,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_short_break_duration_label()
        )
        scale_short_duration.pack(anchor="w", pady=5)

        entry_short_duration = ttk.Entry(scrollable_frame, width=5)
        entry_short_duration.insert(0, str(self.variables["short_break_duration"].get()))
        entry_short_duration.pack(anchor="w", pady=5)
        entry_short_duration.bind(
            "<Return>",
            lambda e: self.update_duration_from_entry(
                "short_break_duration",
                entry_short_duration,
                scale_short_duration,
                self.translate("SecondsUnit")
            )
        )

        interval_frame = ttk.Frame(scrollable_frame)
        interval_frame.pack(anchor="w", pady=5, fill="x")
        lbl_interval_short = ttk.Label(interval_frame, text=self.translate("MiniBreakIntervalLabel"), font=("Roboto", 10))
        lbl_interval_short.pack(side="left")
        self.short_break_interval_label = ttk.Label(interval_frame, text=f"{self.variables['short_break_interval'].get()} {self.translate('MinutesUnit')}", font=("Roboto", 10))
        self.short_break_interval_label.pack(side="right", padx=10)
        self.variables["short_break_interval"].trace("w", self.update_short_break_interval_label)

        scale_short_interval = ttk.Scale(
            scrollable_frame,
            variable=self.variables["short_break_interval"],
            from_=5, to=65,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_short_break_interval_label()
        )
        scale_short_interval.pack(anchor="w", pady=5)

        # Уведомления/откладывание(в разработке)
        cb_notify_short = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("NotifyBeforeMiniBreakOption"),
            variable=self.variables["notify_before_short_break"],
            bootstyle="primary"
        )
        cb_notify_short.pack(anchor="w", pady=5)

        cb_postpone_short = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("AllowPostponeMiniBreaksOption"),
            variable=self.variables["allow_postpone_short_breaks"],
            bootstyle="primary"
        )
        cb_postpone_short.pack(anchor="w", pady=5)

        # Длинные перерывы
        lbl_long = ttk.Label(scrollable_frame, text=self.translate("LongBreaksLabel"), font=("Roboto", 14, "bold"))
        lbl_long.pack(anchor="w", pady=10)

        lbl_long_desc = ttk.Label(
            scrollable_frame,
            text=self.translate("LongBreaksDescription"),
            font=("Roboto", 10),
            wraplength=700
        )
        lbl_long_desc.pack(anchor="w", pady=5)

        cb_enable_long = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("EnableLongBreaksOption"),
            variable=self.variables["enable_long_breaks"],
            bootstyle="primary"
        )
        cb_enable_long.pack(anchor="w", pady=5)

        long_duration_frame = ttk.Frame(scrollable_frame)
        long_duration_frame.pack(anchor="w", pady=5, fill="x")
        lbl_duration_long = ttk.Label(long_duration_frame, text=self.translate("LongBreakDurationLabel"), font=("Roboto", 10))
        lbl_duration_long.pack(side="left")
        self.long_break_duration_label = ttk.Label(long_duration_frame, text=f"{self.variables['long_break_duration'].get() // 60} {self.translate('MinutesUnit')}", font=("Roboto", 10))
        self.long_break_duration_label.pack(side="right", padx=10)
        self.variables["long_break_duration"].trace("w", self.update_long_break_duration_label)

        scale_long_duration = ttk.Scale(
            scrollable_frame,
            variable=self.variables["long_break_duration"],
            from_=5 * 60, to=60 * 60,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_long_break_duration_label()
        )
        scale_long_duration.pack(anchor="w", pady=5)

        entry_long_duration = ttk.Entry(scrollable_frame, width=5)
        entry_long_duration.insert(0, str(self.variables["long_break_duration"].get() // 60))
        entry_long_duration.pack(anchor="w", pady=5)
        entry_long_duration.bind(
            "<Return>",
            lambda e: self.update_duration_from_entry(
                "long_break_duration",
                entry_long_duration,
                scale_long_duration,
                self.translate("MinutesUnit")
            )
        )

        long_interval_frame = ttk.Frame(scrollable_frame)
        long_interval_frame.pack(anchor="w", pady=5, fill="x")
        lbl_interval_long = ttk.Label(long_interval_frame, text=self.translate("LongBreakIntervalLabel"), font=("Roboto", 10))
        lbl_interval_long.pack(side="left")
        self.long_break_interval_label = ttk.Label(long_interval_frame, text=f"{self.variables['long_break_interval'].get()} {self.translate('MinutesUnit')}", font=("Roboto", 10))
        self.long_break_interval_label.pack(side="right", padx=10)
        self.variables["long_break_interval"].trace("w", self.update_long_break_interval_label)

        scale_long_interval = ttk.Scale(
            scrollable_frame,
            variable=self.variables["long_break_interval"],
            from_=15, to=180,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_long_break_interval_label()
        )
        scale_long_interval.pack(anchor="w", pady=5)

        cb_notify_long = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("NotifyBeforeLongBreakOption"),
            variable=self.variables["notify_before_long_break"],
            bootstyle="primary"
        )
        cb_notify_long.pack(anchor="w", pady=5)

        cb_postpone_long = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("AllowPostponeLongBreaksOption"),
            variable=self.variables["allow_postpone_long_breaks"],
            bootstyle="primary"
        )
        cb_postpone_long.pack(anchor="w", pady=5)

        # Блок «Строгий режим»
        strict_frame = ttk.Frame(scrollable_frame, padding=10)
        strict_frame.pack(anchor="w", fill="x", pady=15)

        lbl_strict_title = ttk.Label(strict_frame, text=self.translate("StrictModeLabel"), font=("Roboto", 12, "bold"))
        lbl_strict_title.pack(anchor="w", pady=5)

        lbl_strict_desc = ttk.Label(strict_frame,
                                    text=self.translate("StrictModeDescription"),
                                    font=("Roboto", 9),
                                    wraplength=700)
        lbl_strict_desc.pack(anchor="w", pady=5)

        cb_strict_short = ttk.Checkbutton(
            strict_frame,
            text=self.translate("EnableStrictModeMiniBreaksOption"),
            variable=self.variables["strict_mode_mini_breaks"],
            bootstyle="primary"
        )
        cb_strict_short.pack(anchor="w", pady=3)

        cb_strict_long = ttk.Checkbutton(
            strict_frame,
            text=self.translate("EnableStrictModeLongBreaksOption"),
            variable=self.variables["strict_mode_long_breaks"],
            bootstyle="primary"
        )
        cb_strict_long.pack(anchor="w", pady=3)

        # Время разрешённых перерывов
        lbl_schedule_time = ttk.Label(scrollable_frame, text=self.translate("AllowedBreakTimesLabel"), font=("Roboto", 10, "bold"))
        lbl_schedule_time.pack(anchor="w", pady=10)

        frm_time = ttk.Frame(scrollable_frame)
        frm_time.pack(anchor="w", pady=5)
        lbl_start = ttk.Label(frm_time, text=self.translate("StartTimeLabel"))
        lbl_start.pack(side="left", padx=5)
        entry_start_time = ttk.Entry(frm_time, width=10, textvariable=self.variables["break_start_time"])
        entry_start_time.pack(side="left", padx=5)
        lbl_end = ttk.Label(frm_time, text=self.translate("EndTimeLabel"))
        lbl_end.pack(side="left", padx=5)
        entry_end_time = ttk.Entry(frm_time, width=10, textvariable=self.variables["break_end_time"])
        entry_end_time.pack(side="left", padx=5)

        cb_enable_time_restriction = ttk.Checkbutton(
            scrollable_frame,
            text=self.translate("EnableTimeRestrictionOption"),
            variable=self.variables["enable_time_restriction"],
            bootstyle="primary"
        )
        cb_enable_time_restriction.pack(anchor="w", pady=5)

        # После создания всех элементов расписания:
        if license_status != "active":
            for child in scrollable_frame.winfo_children():
                try:
                    child.configure(state="disabled")
                except Exception:
                    pass
                # Для вложенных фреймов
                if hasattr(child, "winfo_children"):
                    for subchild in child.winfo_children():
                        try:
                            subchild.configure(state="disabled")
                        except Exception:
                            pass

        self.create_control_buttons(scrollable_frame)
        return frame

    def update_short_break_duration_label(self, *args):
        value = self.variables["short_break_duration"].get()
        text = f"{int(value)} {self.translate('SecondsUnit')}"
        self.short_break_duration_label.config(text=text)

    def update_short_break_interval_label(self, *args):
        value = self.variables["short_break_interval"].get()
        self.short_break_interval_label.config(text=f"{int(value)} {self.translate('MinutesUnit')}")

    def update_long_break_duration_label(self, *args):
        value = self.variables["long_break_duration"].get()
        minutes = int(value) // 60
        self.long_break_duration_label.config(text=f"{minutes} {self.translate('MinutesUnit')}")

    def update_long_break_interval_label(self, *args):
        value = self.variables["long_break_interval"].get()
        self.long_break_interval_label.config(text=f"{int(value)} {self.translate('MinutesUnit')}")

    def update_duration_from_entry(self, var_name, entry_widget, scale_widget, unit):
        try:
            value = int(entry_widget.get())
            if var_name == "long_break_duration":
                value_seconds = value * 60
                self.variables[var_name].set(value_seconds)
                scale_widget.set(value_seconds)
            else:
                self.variables[var_name].set(value)
                scale_widget.set(value)
        except ValueError:
            pass

    # ------------------------------
    # Фрейм «Тема»
    # ------------------------------
    def create_theme_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_theme = ttk.Label(frame, text=self.translate("ThemeLabel"), font=("Roboto", 20, "bold"))
        lbl_theme.pack(pady=20)

        lbl_theme_desc = ttk.Label(frame, text=self.translate("ChangeThemeDescription"), font=("Roboto", 12))
        lbl_theme_desc.pack(pady=5)

        license_status = self.get_license_status()
        # Только system, flatly, darkly если лицензия неактивна
        if license_status == "active":
            theme_options = [
                (self.translate("SystemDefaultOption"), "system"),
                (self.translate("FlatlyOption"), "flatly"),
                (self.translate("DarklyOption"), "darkly"),
                (self.translate("CosmoOption"), "cosmo"),
                (self.translate("CyborgOption"), "cyborg"),
                (self.translate("SuperheroOption"), "superhero"),
                (self.translate("MintyOption"), "minty"),
                ("Vapor", "vapor"),
            ]
        else:
            theme_options = [
                (self.translate("SystemDefaultOption"), "system"),
                (self.translate("FlatlyOption"), "flatly"),
                (self.translate("DarklyOption"), "darkly"),
            ]

        self._theme_display_to_internal = {d: i for d, i in theme_options}
        self._theme_internal_to_display = {i: d for d, i in theme_options}

        lbl_select = ttk.Label(frame, text=self.translate("SelectThemeLabel"), font=("Roboto", 10))
        lbl_select.pack(anchor="w", pady=5)

        theme_combobox = ttk.Combobox(
            frame,
            values=[d for d, i in theme_options],
            state="readonly" if license_status == "active" else "disabled",
            bootstyle="primary"
        )
        theme_combobox.pack(anchor="w", pady=5)
        current_internal = self.variables["theme"].get()
        display = self._theme_internal_to_display.get(current_internal, self.translate("FlatlyOption"))
        theme_combobox.set(display)

        def on_theme_select(event=None):
            display = theme_combobox.get()
            internal = self._theme_display_to_internal.get(display, "flatly")
            self.variables["theme"].set(internal)
            self.apply_theme()
        theme_combobox.bind("<<ComboboxSelected>>", on_theme_select)
        self._theme_combobox = theme_combobox

        self.after(100, self._track_system_theme)
        return frame

    def _track_system_theme(self):
        if self.variables["theme"].get() == "system":
            new_theme = self._get_system_theme()
            if getattr(self, '_last_system_theme', None) != new_theme:
                self._last_system_theme = new_theme
                self.style.theme_use(new_theme)
        self.after(1000, self._track_system_theme)

    def _get_system_theme(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize") as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "flatly" if value == 1 else "darkly"
        except Exception:
            return "flatly"

    def apply_theme(self):
        theme = self.variables["theme"].get()
        if theme == "system":
            theme = self._get_system_theme()
        try:
            self.style.theme_use(theme)
        except Exception as e:
            print(self.translate("ThemeErrorMessage"), e)
        if hasattr(self, '_theme_combobox'):
            display = self._theme_internal_to_display.get(self.variables["theme"].get(), self.translate("FlatlyOption"))
            self._theme_combobox.set(display)
        self.update_theme_button_icon()

    def update_theme_button_icon(self):
        theme = self.variables["theme"].get()
        if theme == "system":
            theme = self._get_system_theme()
        icon = "🌙" if theme == "darkly" else "☀️"
        if hasattr(self, "theme_button"):
            self.theme_button.config(text=icon)

    # ------------------------------
    # Фрейм «О программе»
    # ------------------------------
    def create_about_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_app = ttk.Label(frame, text=self.translate("MenuDetox"), font=("Roboto", 24, "bold"))
        lbl_app.pack(pady=20)
        lbl_desc = ttk.Label(frame, text=self.translate("BreakRemindersLabel"), font=("Roboto", 14))
        lbl_desc.pack()
        
        self._init_version_settings()
        latest_status = self._version_settings.get("latest_version_status", True)
        new_version = self._version_settings.get("new_version", "")
        download_url = self._version_settings.get("download_url", "")
        if latest_status:
            version_status = self.translate("LatestVersionInstalled")
            version_color = "green"
        else:
            version_status = self.translate("UpdateAvailable").format(
                current=self.current_version,
                latest=new_version
            )
            version_color = "red"
        self.version_status_label = ttk.Label(
            frame,
            text=version_status,
            font=("Roboto", 12),
            foreground=version_color
        )
        self.version_status_label.pack(pady=10)
        self.download_link = ttk.Label(
            frame,
            text=self.translate("DownloadUpdateLink") if not latest_status and download_url else "",
            font=("Roboto", 10, "underline"),
            foreground="#00bfff",
            cursor="hand2"
        )
        if not latest_status and download_url:
            self.download_link.bind("<Button-1>", lambda e: self.open_website(download_url))
            self.download_link.pack(pady=5)

        cb_autoupdate = ttk.Checkbutton(
            frame,
            text=self.translate("CheckForUpdatesOption"),
            variable=self.variables.get("autoupdate", ttk.BooleanVar(value=False)),
            bootstyle="primary",
            command=lambda: self.toggle_autoupdate()
        )
        cb_autoupdate.pack(pady=10)

        # --- ВСТРОЕННЫЙ МЕНЕДЖЕР ЛИЦЕНЗИЙ ---
        license_section = ttk.LabelFrame(frame, text=self.translate("LicenseSectionTitle"), padding="10")
        license_section.pack(fill="x", pady=20)

        # Ввод ключа
        ttk.Label(license_section, text=self.translate("EnterLicenseKeyPrompt")).grid(row=0, column=0, sticky="w", pady=(0,5), columnspan=2)
        self.license_key_var = tk.StringVar()
        entry_key = ttk.Entry(license_section, textvariable=self.license_key_var, width=35)
        entry_key.grid(row=1, column=0, sticky="ew", ipady=2)
        btn_check = ttk.Button(
            license_section,
            text=self.translate("CheckButton"),
            bootstyle="primary",
            command=self._about_license_check,
            takefocus=False
        )
        btn_check.grid(row=1, column=1, padx=(10,0), sticky="ns")
        license_section.grid_columnconfigure(0, weight=1)

        # Информация о лицензии
        info_frame = ttk.Frame(license_section)
        info_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15,0))
        labels = [
            self.translate("LicenseKeyLabel"),
            self.translate("LicenseTypeLabel"),
            self.translate("LicenseExpiresLabel"),
            self.translate("LicenseDaysLeftLabel"),
            self.translate("LicenseStatusLabel")
        ]
        self._license_info_vars = {}
        self._license_status_label = None
        for i, text in enumerate(labels):
            ttk.Label(info_frame, text=text, font="-weight bold").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value="-")
            lbl = ttk.Label(info_frame, textvariable=var, wraplength=300)
            lbl.grid(row=i, column=1, sticky="w", pady=2)
            self._license_info_vars[text.replace(":", "").replace(" ", "_").lower()] = var
            if text == self.translate("LicenseStatusLabel"): self._license_status_label = lbl
        info_frame.grid_columnconfigure(1, weight=1)

        # При запуске сразу показать статус лицензии
        self._about_license_refresh_display()

        lbl_developer = ttk.Frame(frame)
        lbl_developer.pack(side="bottom", pady=20, fill="x")
        
        version_label = ttk.Label(lbl_developer, text=self.translate("VersionLabel"), font=("Roboto", 10))
        version_label.pack(side="left", padx=(0, 20))
        
        developer_label = ttk.Label(lbl_developer, text=self.translate("DevelopedByLabel"), font=("Roboto", 10))
        developer_label.pack(side="right")
        
        return frame

    def toggle_autoupdate(self):
        self.save_version_settings()
        if self.variables["autoupdate"].get():
            self.check_new_version_github()

    def _about_license_refresh_display(self, custom_status_msg=None, custom_status_color=None):
        data = self._about_license_load_local()
        if data and data.get("license_key"):
            self.license_data = data
        else:
            self.license_data = None

        # Ключи для перевода
        key_label = self.translate("LicenseKeyLabel").replace(":", "").replace(" ", "_").lower()
        type_label = self.translate("LicenseTypeLabel").replace(":", "").replace(" ", "_").lower()
        expires_label = self.translate("LicenseExpiresLabel").replace(":", "").replace(" ", "_").lower()
        left_label = self.translate("LicenseDaysLeftLabel").replace(":", "").replace(" ", "_").lower()
        status_label = self.translate("LicenseStatusLabel").replace(":", "").replace(" ", "_").lower()

        # Заполняем поля
        if self.license_data and self.license_data.get("license_key"):
            key = self.license_data.get("license_key", "-")
            self._license_info_vars[key_label].set(mask_license_key(key))
            raw_type = self.license_data.get("type")
            lang = self.variables["language"].get()
            if lang.lower().startswith("англ"):
                lang = "English"
            elif lang.lower().startswith("рус"):
                lang = "Русский"
            elif lang.lower().startswith("каз"):
                lang = "Казакша"
            mapped_type = "-"
            if raw_type:
                mapped_type = LICENSE_TYPE_MAP.get(raw_type.lower(), {}).get(lang, raw_type)
            self._license_info_vars[type_label].set(mapped_type)
            expires_str = self.license_data.get("expires")
            self._license_info_vars[expires_label].set(expires_str if expires_str is not None else "-")
            self._license_info_vars[left_label].set(format_days_left(expires_str, self.translate))
        else:
            for k in [key_label, type_label, expires_label, left_label]:
                self._license_info_vars[k].set("-")

        # Статус
        status_text = self.translate("LicenseInactiveStatus")
        status_color = "orange"
        if self.license_data and self.license_data.get("license_key"):
            days_left = self._license_info_vars[left_label].get()
            if days_left == self.translate("LicenseUnlimited"):
                status_text = self.translate("LicenseActiveUnlimitedStatus")
                status_color = "green"
            elif days_left == self.translate("LicenseExpired"):
                status_text = self.translate("LicenseExpiredStatus")
                status_color = "red"
            elif any(word in days_left for word in [self.translate("DaysWord"), self.translate("DayWord"), self.translate("Days234Word"), self.translate("TodayExpiresWord")]):
                status_text = self.translate("LicenseActiveStatus").format(days_left=days_left)
                status_color = "green"
            else:
                status_text = self.translate("LicenseOtherStatus").format(days_left=days_left)
                status_color = "orange"
        if custom_status_msg: status_text = custom_status_msg
        if custom_status_color: status_color = custom_status_color
        self._license_info_vars[status_label].set(status_text)
        if self._license_status_label:
            self._license_status_label.config(foreground=status_color)

    def _about_license_check(self):
        key = self.license_key_var.get().strip()
        if not key:
            messagebox.showwarning(self.translate("WarningTitle"), self.translate("EnterLicenseKeyPrompt"))  # исправлено
            return
        display_key = mask_license_key(key)
        self._license_info_vars[self.translate("LicenseStatusLabel").replace(":", "").replace(" ", "_").lower()].set(
            self.translate("LicenseCheckingOnline").format(key=display_key[:20])
        )
        if self._license_status_label: self._license_status_label.config(foreground="#007bff")
        self.update_idletasks()
        result = search_license_online(key)
        license_changed = False
        if result['status'] == 'success':
            self.license_data = result['data']
            save_license_locally(self.license_data)
            license_changed = True
        elif result['status'] == 'not_found':
            messagebox.showerror(self.translate("NotFoundTitle"),
                                 self.translate("LicenseNotFoundMsg").format(key=mask_license_key(result.get('key', key))))
            if self.license_data and self.license_data.get("license_key") == key:
                self.license_data = None
                save_license_locally(None)
                license_changed = True
        elif result['status'] == 'network_error':
            messagebox.showerror(self.translate("NetworkErrorTitle"),
                                 self.translate("LicenseNetworkErrorMsg") + "\n" + self.translate("TryAgainLater"))
        elif result['status'] == 'server_error':
            messagebox.showerror(self.translate("ServerErrorTitle"),
                                 self.translate("LicenseServerErrorMsg").format(code=result.get('code')))
        else:
            messagebox.showerror(self.translate("UnknownErrorTitle"),
                                 result.get('message', self.translate("LicenseUnknownErrorMsg")))
        self.license_key_var.set("")
        self._about_license_refresh_display()
        if license_changed:
            self.refresh_license_ui()

    def _about_license_load_local(self):
        try:
            if os.path.exists(LICENSE_SETTINGS_PATH):
                with open(LICENSE_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data and data.get("license_key"): return data
            return {}
        except Exception:
            return {}

    def _init_version_settings(self):
        if self.settings_file.exists():
            with open(self.settings_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        else:
            data = {}
        changed = False
        if "autoupdate" not in data:
            data["autoupdate"] = False
            changed = True
        if "latest_version_status" not in data:
            data["latest_version_status"] = True
            changed = True
        if "current_version" not in data:
            data["current_version"] = self.current_version
            changed = True
        if "new_version" not in data:
            data["new_version"] = ""
            changed = True
        if changed:
            with open(self.settings_file, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        self._version_settings = data

    def _compare_versions(self, current, latest):
        """
        Сравнивает версии и возвращает True, если latest > current
        """
        current = current.lower().strip()
        latest = latest.lower().strip()
        if current.startswith(('v', 'r')):
            current = current[1:]
        if latest.startswith(('v', 'r')):
            latest = latest[1:]
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            for i in range(len(current_parts)):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            return False
        except Exception:
            return current != latest

    # ------------------------------
    # Фрейм «Статистика» (компактная)
    # ------------------------------
    def create_statistics_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_title = ttk.Label(frame, text=self.translate("MenuStatistics"), font=("Roboto", 20, "bold"))
        lbl_title.pack(pady=10)

        self.lbl_stats_mini = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_mini.pack(anchor="w", pady=2)

        self.lbl_stats_long = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_long.pack(anchor="w", pady=2)

        self.lbl_stats_mini_skipped = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_mini_skipped.pack(anchor="w", pady=2)

        self.lbl_stats_long_skipped = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_long_skipped.pack(anchor="w", pady=2)

        self.lbl_stats_break_time = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_break_time.pack(anchor="w", pady=2)

        self.lbl_stats_runtime = ttk.Label(frame, text="", font=("Roboto", 11))
        self.lbl_stats_runtime.pack(anchor="w", pady=2)

        btn_clear = ttk.Button(
            frame,
            text=self.translate("ClearStatisticsButton"),
            bootstyle="danger",
            command=lambda: (self.clear_statistics(), self.focus_set()),
            takefocus=False
        )
        btn_clear.pack(pady=10)

        return frame

    def clear_statistics(self):
        self.stats = {
            "mini_breaks": 0,
            "long_breaks": 0,
            "total_breaks": 0,
            "total_runtime": 0,
            "mini_skipped": 0,
            "long_skipped": 0,
            "mini_time": 0,
            "long_time": 0
        }
        self.save_settings()  # Это для сохранения
        self.update_statistics_labels()

    def update_runtime_stat(self):
        """
        При каждом выходе или сохранении обновляем общий счётчик времени,
        чтобы потом показать в статистике.
        """
        now = datetime.datetime.now()
        elapsed = now - self.start_time
        seconds = int(elapsed.total_seconds())
        self.stats["total_runtime"] += seconds
        self.start_time = datetime.datetime.now()

    def toggle_theme(self):
        current_theme = self.variables["theme"].get()
        new_theme = "darkly" if current_theme != "darkly" else "flatly"
        self.variables["theme"].set(new_theme)
        self.apply_theme()
        self.update_theme_button_icon()

    def reset_to_defaults(self): # Сброс на дефолт настройки
        defaults = {
            "autostart": True,
            "break_mode": "fullscreen",
            "exercise_tips": True,
            "break_all_screens": True,
            "track_idle": True,
            "dnd_mode": False,
            "language": "Русский",
            "theme": "flatly",
            "sound_on_break": False,
            "enable_short_breaks": True,
            "short_break_duration": 20,
            "short_break_interval": 10,
            "enable_long_breaks": True,
            "long_break_duration": 300,
            "long_break_interval": 30,
            "notify_before_short_break": False,
            "allow_postpone_short_breaks": True,
            "notify_before_long_break": False,
            "allow_postpone_long_breaks": True,
            "strict_mode_mini_breaks": False,
            "strict_mode_long_breaks": False,
            "autoupdate": False,
            "detox_active": False,
            "break_start_time": "22:00",
            "break_end_time": "00:00",
            "use_camera": False,
            "show_camera_feed": True,
            "show_eye_graphics": True,
            "enable_time_restriction": False,
        }
        for key, value in defaults.items():
            if key in self.variables:
                if isinstance(self.variables[key].get(), bool):
                    self.variables[key].set(bool(value))
                elif isinstance(self.variables[key].get(), int):
                    self.variables[key].set(int(value))
                else:
                    self.variables[key].set(value)

        self.stop_detox()
        self.apply_theme()
        self.save_settings()

    def save_settings(self):
        self.update_runtime_stat()

        lang = self.variables["language"].get()
        if lang.lower().startswith("англ"):
            self.variables["language"].set("English")
        elif lang.lower().startswith("рус"):
            self.variables["language"].set("Русский")
        elif lang.lower().startswith("каз"):
            self.variables["language"].set("Казакша")

        settings = {key: var.get() for key, var in self.variables.items()}
        settings["stats"] = self.stats
        settings["autoupdate"] = self.variables["autoupdate"].get()
        settings["latest_version_status"] = self._version_settings.get("latest_version_status", True)
        settings["current_version"] = self.current_version
        settings["new_version"] = self._version_settings.get("new_version", "")
        settings["download_url"] = self._version_settings.get("download_url", "")

        with open(self.settings_file, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)

    def load_settings(self):
        if self.settings_file.exists():
            with open(self.settings_file, "r", encoding="utf-8") as file:
                data = json.load(file)
                for key, value in data.items():
                    if key in self.variables:
                        if key == "language":
                            if str(value).lower().startswith("англ"):
                                self.variables[key].set("English")
                            elif str(value).lower().startswith("рус"):
                                self.variables[key].set("Русский")
                            elif str(value).lower().startswith("каз"):
                                self.variables[key].set("Казакша")
                            else:
                                self.variables[key].set(value)
                        else:
                            self.variables[key].set(value)
                    elif key == "stats" and isinstance(value, dict):
                        self.stats.update(value)
                self._version_settings = {
                    "autoupdate": data.get("autoupdate", False),
                    "latest_version_status": data.get("latest_version_status", True),
                    "current_version": data.get("current_version", self.current_version),
                    "new_version": data.get("new_version", ""),
                    "download_url": data.get("download_url", "")
                }
        else:
            self._init_version_settings()

    def open_website(self, url):
        webbrowser.open_new(url)

    # ------------------------------
    # Логика системного трея
    # ------------------------------
    def create_tray_icon(self):
        # Загружаем фотку из файла detox.png
        ensure_appdata_files()
        image = Image.open(DETOX_IMAGE_PATH)
        self.tray_icon = Icon("Detox", image, "Detox", Menu())
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.after(1000, self.update_tray_menu)

    def update_tray_menu(self): # Тут весь функционал трея
        mini_time = f"{self.mini_remaining_time // 60}{self.translate('MinutesUnit')} {self.mini_remaining_time % 60}{self.translate('SecondsUnit')}"
        long_time = f"{self.long_remaining_time // 60}{self.translate('MinutesUnit')} {self.long_remaining_time % 60}{self.translate('SecondsUnit')}"

        license_status = self.get_license_status()

        menu = Menu(
            MenuItem("Detox", lambda icon, item: self.after(0, self.restore_from_tray), default=True),
            Menu.SEPARATOR,
            MenuItem(
                self.translate("MiniBreakTrayOption"),
                lambda icon, item: self.after(0, self.go_to_mini_break),
                enabled=(license_status == "active")
            ),
            MenuItem(
                self.translate("LongBreakTrayOption"),
                lambda icon, item: self.after(0, self.go_to_long_break),
                enabled=(license_status == "active")
            ),
            MenuItem(self.translate("PauseTrayOption"), lambda icon, item: self.after(0, self.pause_detox)),
            MenuItem(self.translate("ExitTrayOption"), lambda icon, item: self.after(0, self.exit_detox))
        )
        self.tray_icon.menu = menu
        self.tray_icon.update_menu()
        self.after(1000, self.update_tray_menu)
        self.tray_icon.title = f"{self.translate('MiniBreakTrayTitle')}: {mini_time} | {self.translate('LongBreakTrayTitle')}: {long_time}"

    def minimize_to_tray(self):
        self.withdraw()
        self.create_tray_icon()

    def _on_main_window_close(self):
        self.update_runtime_stat()
        self.save_settings()
        # Корректно останавливаем EyeTracker перед завершением
        self.close_eye_tracker_on_exit()
        if hasattr(self, '_license_check_thread') and self._license_check_thread is not None:
            if self._license_check_thread.is_alive():
                try:
                    self._license_check_thread.join(timeout=2)
                except Exception:
                    pass
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()
        
    def sync_autostart_setting(self):
        # Синхронизировать автозапуск с настройкой
        if self.variables["autostart"].get():
            enable_autostart()
        else:
            disable_autostart()
        if not hasattr(self, "_autostart_trace_set"):
            self.variables["autostart"].trace_add("write", self.on_autostart_change)
            self._autostart_trace_set = True

    def on_autostart_change(self, *args):
        if self.variables["autostart"].get():
            enable_autostart()
        else:
            disable_autostart()

if __name__ == "__main__":
    ensure_appdata_files()
    app = DetoxSettingsApp()
    app.mainloop()