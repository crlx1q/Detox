import ttkbootstrap as ttk
from ttkbootstrap.constants import *
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
from PIL import Image
import threading
import datetime

# Класс для анимированного холста
class AnimatedCanvas(ttk.Canvas):
    def __init__(self, root, image_path, **kwargs):
        super().__init__(root, **kwargs)
        self.pack()
        self.center_x = 100
        self.center_y = 100
        self.angle = 0  # Для пульсации
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


# Окно обратного отсчёта
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
        # ### НОВОЕ: колбэки для фиксации пропусков и завершений
        on_skip=None,
        on_complete=None
    ):
        self.parent = parent
        self.duration = duration
        self.remaining = duration
        self.break_type = break_type
        self.strict_mode = strict_mode
        self.on_skip = on_skip
        self.on_complete = on_complete
        self.was_skipped = False  # флаг, что пользователь нажал "Пропустить"

        self.window = tk.Toplevel(parent)
        self.window.title("Обратный отсчёт")

        # Проверяем break_mode и включаем fullscreen только если он выбран
        if break_mode == "fullscreen":
            self.window.attributes('-fullscreen', True)
            self.window.attributes('-alpha', 0.9)
            self.window.configure(background="#468f97")
        else:
            # Обычный оконный режим
            self.window.geometry("400x300")
            self.window.configure(bg="#468f97")

        if sound_enabled:
            try:
                import winsound
                if os.path.exists("break_sound.wav"):
                    winsound.PlaySound("break_sound.wav", winsound.SND_ASYNC)
            except Exception as e:
                print("Ошибка воспроизведения звука:", e)

        self.style = Style(theme=theme)
        self.style.configure('TProgressbar', thickness=20, troughcolor="#468f97", background="#1DBF73")

        central_frame = tk.Frame(self.window, background="#468f97")
        central_frame.place(relx=0.5, rely=0.5, anchor='center')

        self.label = tk.Label(
            central_frame,
            text="Закройте глаза и считайте вдохи.",
            font=("Arial", 20),
            fg="white",
            background="#468f97",
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
            text=f"{int(self.remaining)} сек осталось",
            font=("Arial", 16),
            fg="white",
            background="#468f97",
        )
        self.time_label.pack(pady=10)

        # Если не strict_mode, даём кнопку "Пропустить"
        if not self.strict_mode:
            self.skip_button = tk.Button(
                central_frame,
                text="Пропустить этот перерыв",
                font=("Arial", 14),
                background="#468f97",
                fg="white",
                activebackground="#468f97",
                activeforeground="white",
                relief="flat",
                command=self.skip_break,
            )
            self.skip_button.pack(pady=20)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_progress()

    # Исправлено: вместо вызова destroy() вызывается on_close(), чтобы корректно сработал on_skip
    def skip_break(self):
        self.was_skipped = True
        self.on_close()

    def update_progress(self):
        if self.remaining > 0:
            self.remaining -= 1
            self.progress["value"] = self.remaining
            minutes, seconds = divmod(self.remaining, 60)
            self.time_label.config(text=f"{int(minutes)} мин {int(seconds)} сек осталось")
            self.window.after(1000, self.update_progress)
        else:
            # Перерыв завершён нормально
            self.label.config(text="Время вышло!")
            self.time_label.config(text="")
            if not self.strict_mode and hasattr(self, 'skip_button'):
                self.skip_button.config(text="Закрыть")
            # Через 2 секунды окно закрывается
            self.window.after(2000, self.window.destroy)

    def on_close(self):
        # Если окно закрыто раньше, чем время вышло (remaining > 0),
        # и не было нажатия skip_button — считаем это тоже пропуском
        if self.remaining > 0 and not self.was_skipped:
            self.was_skipped = True

        self.window.destroy()

        # Вызовем нужный колбэк
        if self.was_skipped and self.on_skip:
            self.on_skip()
        elif not self.was_skipped and self.on_complete:
            self.on_complete()


# Основное приложение
class DetoxSettingsApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Настройки Detox")
        self.geometry("800x800")
        self.resizable(False, False)
        self.settings_file = "settings.json"
        self.icon_image = tk.PhotoImage(file="detox.png")
        self.iconphoto(False, self.icon_image)

        self.variables = {
            "autostart":         ttk.BooleanVar(value=True),
            "break_mode":        ttk.StringVar(value="fullscreen"),
            "exercise_tips":     ttk.BooleanVar(value=True),
            "break_all_screens": ttk.BooleanVar(value=True),
            "track_idle":        ttk.BooleanVar(value=True),
            "dnd_mode":          ttk.BooleanVar(value=False),
            "language":          ttk.StringVar(value="Русский"),
            "theme":             ttk.StringVar(value="flatly"),
            "sound_on_break":    ttk.BooleanVar(value=False),
            "enable_short_breaks":  ttk.BooleanVar(value=True),
            "short_break_duration": ttk.IntVar(value=20),   # секунды
            "short_break_interval": ttk.IntVar(value=10),   # минуты
            "enable_long_breaks":   ttk.BooleanVar(value=True),
            "long_break_duration":  ttk.IntVar(value=300),  # секунды
            "long_break_interval":  ttk.IntVar(value=30),   # минуты
            "notify_before_short_break":    ttk.BooleanVar(value=False),
            "allow_postpone_short_breaks":  ttk.BooleanVar(value=True),
            "notify_before_long_break":     ttk.BooleanVar(value=False),
            "allow_postpone_long_breaks":   ttk.BooleanVar(value=True),
            "strict_mode_mini_breaks":      ttk.BooleanVar(value=False),
            "strict_mode_long_breaks":      ttk.BooleanVar(value=False),
            "autoupdate":         ttk.BooleanVar(value=False),
            "detox_active":       ttk.BooleanVar(value=False),
            "break_start_time":   tk.StringVar(value="22:00"),
            "break_end_time":     tk.StringVar(value="00:00"),
        }

        # ### НОВОЕ: расширяем stats, чтобы хранить пропуски и общее время
        self.stats = {
            "mini_breaks": 0,
            "long_breaks": 0,
            "total_breaks": 0,
            "total_runtime": 0,
            "mini_skipped": 0,
            "long_skipped": 0,
            "mini_time": 0,   # в секундах
            "long_time": 0,   # в секундах
        }

        self.detox_active = False
        self.paused = False
        self.break_count = 0
        self.break_timer_mini = None
        self.break_timer_long = None
        self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
        self.long_remaining_time = self.variables["long_break_interval"].get() * 60

        # Для подсчёта времени работы
        self.start_time = datetime.datetime.now()

        self.create_top_panel()
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(pady=20, fill="both", expand=True)

        self.detox_frame = self.create_detox_frame()
        self.settings_frame = self.create_settings()
        self.schedule_frame = self.create_schedule_frame()
        self.theme_frame = self.create_theme_frame()
        self.about_frame = self.create_about_frame()
        self.support_frame = self.create_support_frame()
        self.statistics_frame = self.create_statistics_frame()  # фрейм статистики

        self.load_settings()
        self.show_detox()
        self.apply_theme()

        self.variables["short_break_interval"].trace("w", self.on_short_break_interval_change)
        self.variables["long_break_interval"].trace("w", self.on_long_break_interval_change)

        if self.variables["detox_active"].get():
            self.start_detox()

    def get_current_theme_name(self):
        return self.variables["theme"].get()

    def create_top_panel(self):
        top_frame = tk.Frame(self, background="#F7F7F7")
        top_frame.pack(fill="x", pady=10)
        self.top_frame = top_frame

        # ### ИЗМЕНЕНИЕ: порядок кнопок, «Статистика» сразу после «Расписание»
        buttons = [
            ("Detox",            self.show_detox),
            ("Настройки",        self.show_settings),
            ("Расписание",       self.show_schedule),
            ("Статистика",       self.show_statistics),  # <- тут
            ("Тема",             self.show_theme),
            ("О программе",      self.show_about),
            ("Поддержать Detox", self.show_support),
        ]
        for btn_text, command in buttons:
            btn = ttk.Button(
                top_frame,
                text=btn_text,
                bootstyle="primary-outline",
                command=command,
            )
            btn.pack(side="left", padx=5)

        theme_button = ttk.Button(
            top_frame,
            text="🌙" if self.variables["theme"].get() == "darkly" else "☀️",
            bootstyle="link",
            command=self.toggle_theme,
        )
        theme_button.pack(side="right", padx=5)
        self.theme_button = theme_button

        minimize_button = ttk.Button(
            top_frame,
            text="Свернуть в трей",
            bootstyle="link",
            command=self.minimize_to_tray,
        )
        minimize_button.pack(side="right", padx=5)

    def show_detox(self):
        self.hide_all_frames()
        self.detox_frame.pack(pady=20, fill="both", padx=20, expand=True)

    def show_settings(self):
        self.hide_all_frames()
        self.settings_frame.pack(pady=20, fill="x", padx=20)

    def show_schedule(self):
        self.hide_all_frames()
        self.schedule_frame.pack(pady=20, fill="both", padx=20, expand=True)

    def show_theme(self):
        self.hide_all_frames()
        self.theme_frame.pack(pady=20, fill="x", padx=20)

    def show_about(self):
        self.hide_all_frames()
        self.about_frame.pack(pady=20, fill="x", padx=20)

    def show_support(self):
        self.hide_all_frames()
        self.support_frame.pack(pady=20, fill="x", padx=20)

    def show_statistics(self):
        self.hide_all_frames()
        self.update_statistics_labels()  # обновляем данные
        self.statistics_frame.pack(pady=20, fill="x", padx=20)

    def hide_all_frames(self):
        for frame in (
            self.detox_frame,
            self.settings_frame,
            self.schedule_frame,
            self.theme_frame,
            self.about_frame,
            self.support_frame,
            self.statistics_frame
        ):
            frame.pack_forget()

    def create_detox_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "detox.png")
            animated_canvas = AnimatedCanvas(frame, image_path=image_path, width=200, height=200, bg="black", highlightthickness=0)
            animated_canvas.pack(pady=10)
        except Exception as e:
            lbl_logo = ttk.Label(frame, text="Логотип не найден", font=("Arial", 14, "bold"), foreground="red")
            lbl_logo.pack(pady=20)
            print(f"Ошибка при загрузке изображения: {e}")

        lbl_title = ttk.Label(frame, text="Detox", font=("Arial", 24, "bold"))
        lbl_title.pack(pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)

        btn_mini_break = ttk.Button(
            btn_frame,
            text="Перейти к мини-перерыву",
            bootstyle="info",
            command=self.go_to_mini_break,
            width=25
        )
        btn_mini_break.pack(pady=5)

        btn_long_break = ttk.Button(
            btn_frame,
            text="Перейти к длинному перерыву",
            bootstyle="info",
            command=self.go_to_long_break,
            width=25
        )
        btn_long_break.pack(pady=5)

        self.btn_pause = ttk.Button(
            btn_frame,
            text="Пауза",
            bootstyle="warning",
            command=self.pause_detox,
            width=25
        )
        self.btn_pause.pack(pady=5)

        btn_reset = ttk.Button(
            btn_frame,
            text="Сбросить перерывы",
            bootstyle="danger",
            command=self.reset_detox,
            width=25
        )
        btn_reset.pack(pady=5)

        btn_exit = ttk.Button(
            btn_frame,
            text="Выход из Detox",
            bootstyle="danger-outline",
            command=self.exit_detox,
            width=25
        )
        btn_exit.pack(pady=5)

        lbl_mini_remaining = ttk.Label(frame, text="До мини перерыва осталось: 00 мин 00 сек", font=("Arial", 14))
        lbl_mini_remaining.pack(pady=5)
        self.mini_remaining_label = lbl_mini_remaining

        lbl_long_remaining = ttk.Label(frame, text="До длинного перерыва осталось: 00 мин 00 сек", font=("Arial", 14))
        lbl_long_remaining.pack(pady=5)
        self.long_remaining_label = lbl_long_remaining

        self.break_count_label = ttk.Label(frame, text="Перерывов: 0", font=("Arial", 14))
        self.break_count_label.pack(pady=5)

        return frame

    def update_break_count_label(self):
        self.break_count_label.config(text=f"Перерывов: {self.break_count}")

    def go_to_mini_break(self):
        if self.variables["enable_short_breaks"].get() and self.variables["detox_active"].get():
            # Если окно свернуто, оставляем его в трее (не разворачиваем)
            # if self.state() == "withdrawn":
            #     self.restore_from_tray()

            # Увеличиваем счётчики в статистике
            self.stats["mini_breaks"] += 1
            self.stats["total_breaks"] += 1
            self.break_count += 1
            self.update_break_count_label()

            # Создаём окно обратного отсчёта, передавая колбэки
            CountdownWindow(
                parent=self,
                duration=self.variables["short_break_duration"].get(),
                theme=self.get_current_theme_name(),
                break_type="mini",
                strict_mode=self.variables["strict_mode_mini_breaks"].get(),
                sound_enabled=self.variables["sound_on_break"].get(),
                break_mode=self.variables["break_mode"].get(),
                on_skip=lambda: self.stats.__setitem__("mini_skipped", self.stats["mini_skipped"] + 1),
                on_complete=lambda: self.stats.__setitem__(
                    "mini_time",
                    self.stats["mini_time"] + self.variables["short_break_duration"].get()
                ),
            )

            # Сброс таймера мини-перерыва
            self.mini_remaining_time = self.variables["short_break_interval"].get() * 60

    def go_to_long_break(self):
        if self.variables["enable_long_breaks"].get() and self.variables["detox_active"].get():
            # Если окно свернуто, оставляем его в трее (не разворачиваем)
            # if self.state() == "withdrawn":
            #     self.restore_from_tray()

            self.stats["long_breaks"] += 1
            self.stats["total_breaks"] += 1
            self.break_count += 1
            self.update_break_count_label()

            CountdownWindow(
                parent=self,
                duration=self.variables["long_break_duration"].get(),
                theme=self.get_current_theme_name(),
                break_type="long",
                strict_mode=self.variables["strict_mode_long_breaks"].get(),
                sound_enabled=self.variables["sound_on_break"].get(),
                break_mode=self.variables["break_mode"].get(),
                on_skip=lambda: self.stats.__setitem__("long_skipped", self.stats["long_skipped"] + 1),
                on_complete=lambda: self.stats.__setitem__(
                    "long_time",
                    self.stats["long_time"] + self.variables["long_break_duration"].get()
                ),
            )

            # Сброс таймера длинного перерыва
            self.long_remaining_time = self.variables["long_break_interval"].get() * 60

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
            self.btn_pause.config(text="Плей")
        else:
            self.paused = False
            self.update_mini_timer()
            self.update_long_timer()
            self.btn_pause.config(text="Пауза")

    def reset_detox(self):
        self.stop_detox()
        self.start_detox()

    def exit_detox(self):
        # Перед выходом — обновим время работы
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
        if self.mini_remaining_time > 0:
            self.mini_remaining_time -= 1
            minutes, seconds = divmod(self.mini_remaining_time, 60)
            self.mini_remaining_label.config(text=f"До мини перерыва осталось: {minutes} мин {seconds} сек")
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
        if self.long_remaining_time > 0:
            self.long_remaining_time -= 1
            minutes, seconds = divmod(self.long_remaining_time, 60)
            self.long_remaining_label.config(text=f"До длинного перерыва осталось: {minutes} мин {seconds} сек")
            self.break_timer_long = self.after(1000, self.update_long_timer)
        else:
            if self.variables["enable_long_breaks"].get():
                self.go_to_long_break()
            self.long_remaining_time = self.variables["long_break_interval"].get() * 60
            self.break_timer_long = self.after(1000, self.update_long_timer)

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

    def create_settings(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        cb_autostart = ttk.Checkbutton(
            frame,
            text="Запускать Detox автоматически при входе в систему",
            variable=self.variables["autostart"],
            bootstyle="primary",
        )
        cb_autostart.pack(anchor="w", pady=5)

        lbl_breaks = ttk.Label(frame, text="Показывать перерывы:", font=("Arial", 10, "bold"))
        lbl_breaks.pack(anchor="w", pady=10)

        radio_frame = ttk.Frame(frame)
        radio_frame.pack(anchor="w", pady=5)

        rb_window = ttk.Radiobutton(
            radio_frame,
            text="В окне",
            variable=self.variables["break_mode"],
            value="window",
            bootstyle="primary",
        )
        rb_window.pack(side="left", padx=5)

        rb_fullscreen = ttk.Radiobutton(
            radio_frame,
            text="На весь экран",
            variable=self.variables["break_mode"],
            value="fullscreen",
            bootstyle="primary",
        )
        rb_fullscreen.pack(side="left", padx=5)

        options = {
            "Показывать идеи для упражнений во время перерывов": "exercise_tips",
            "Показывать перерывы на всех экранах": "break_all_screens",
            "Следить за неиспользованием системы": "track_idle",
            "Показывать перерывы даже в режиме 'Не беспокоить'": "dnd_mode",
        }
        for text, var_name in options.items():
            cb = ttk.Checkbutton(frame, text=text, variable=self.variables[var_name], bootstyle="primary")
            cb.pack(anchor="w", pady=5)

        lbl_language = ttk.Label(frame, text="Выбрать язык:", font=("Arial", 10, "bold"))
        lbl_language.pack(anchor="w", pady=10)
        language_combobox = ttk.Combobox(frame, textvariable=self.variables["language"], state="readonly", bootstyle="primary")
        language_combobox["values"] = ["Русский", "Английский"]
        language_combobox.pack(anchor="w", pady=5)
        language_combobox.set(self.variables["language"].get())

        cb_sound = ttk.Checkbutton(
            frame,
            text="Включить звук при перерыве",
            variable=self.variables["sound_on_break"],
            bootstyle="primary",
        )
        cb_sound.pack(anchor="w", pady=5)

        cb_detox = ttk.Checkbutton(
            frame,
            text="Включить Detox",
            variable=self.variables["detox_active"],
            bootstyle="primary",
            command=self.toggle_detox,
        )
        cb_detox.pack(anchor="w", pady=10)

        self.create_control_buttons(frame)
        return frame

    def create_control_buttons(self, parent_frame):
        control_frame = ttk.Frame(parent_frame)
        control_frame.pack(pady=20)

        save_button = ttk.Button(
            control_frame,
            text="Сохранить настройки",
            bootstyle="success",
            command=self.save_settings,
        )
        save_button.pack(side="left", padx=10)

        reset_button = ttk.Button(
            control_frame,
            text="Восстановить настройки по умолчанию",
            bootstyle="danger-outline",
            command=self.reset_to_defaults,
        )
        reset_button.pack(side="left", padx=10)

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

        lbl_short = ttk.Label(scrollable_frame, text="Мини-перерывы:", font=("Arial", 14, "bold"))
        lbl_short.pack(anchor="w", pady=10)
        lbl_short_desc = ttk.Label(scrollable_frame, text="Мини-перерывы — это регулярные короткие перерывы...", font=("Arial", 10), wraplength=700)
        lbl_short_desc.pack(anchor="w", pady=5)

        cb_enable_short = ttk.Checkbutton(scrollable_frame, text="Включить мини-перерывы", variable=self.variables["enable_short_breaks"], bootstyle="primary")
        cb_enable_short.pack(anchor="w", pady=5)

        duration_frame = ttk.Frame(scrollable_frame)
        duration_frame.pack(anchor="w", pady=5, fill="x")
        lbl_duration_short = ttk.Label(duration_frame, text="Продолжительность (сек):", font=("Arial", 10))
        lbl_duration_short.pack(side="left")
        self.short_break_duration_label = ttk.Label(duration_frame, text=f"{self.variables['short_break_duration'].get()} сек", font=("Arial", 10))
        self.short_break_duration_label.pack(side="right", padx=10)
        self.variables["short_break_duration"].trace("w", self.update_short_break_duration_label)

        scale_short_duration = ttk.Scale(scrollable_frame, variable=self.variables["short_break_duration"], from_=10, to=600,
                                         orient="horizontal", length=400, bootstyle="primary",
                                         command=lambda e: self.update_short_break_duration_label())
        scale_short_duration.pack(anchor="w", pady=5)

        entry_short_duration = ttk.Entry(scrollable_frame, width=5)
        entry_short_duration.insert(0, str(self.variables["short_break_duration"].get()))
        entry_short_duration.pack(anchor="w", pady=5)
        entry_short_duration.bind("<Return>", lambda e: self.update_duration_from_entry("short_break_duration", entry_short_duration, scale_short_duration, "сек"))

        interval_frame = ttk.Frame(scrollable_frame)
        interval_frame.pack(anchor="w", pady=5, fill="x")
        lbl_interval_short = ttk.Label(interval_frame, text="Каждые (мин):", font=("Arial", 10))
        lbl_interval_short.pack(side="left")
        self.short_break_interval_label = ttk.Label(interval_frame, text=f"{self.variables['short_break_interval'].get()} мин", font=("Arial", 10))
        self.short_break_interval_label.pack(side="right", padx=10)
        self.variables["short_break_interval"].trace("w", self.update_short_break_interval_label)

        scale_short_interval = ttk.Scale(scrollable_frame, variable=self.variables["short_break_interval"], from_=5, to=65,
                                         orient="horizontal", length=400, bootstyle="primary",
                                         command=lambda e: self.update_short_break_interval_label())
        scale_short_interval.pack(anchor="w", pady=5)

        lbl_long = ttk.Label(scrollable_frame, text="Длинные перерывы:", font=("Arial", 14, "bold"))
        lbl_long.pack(anchor="w", pady=10)
        lbl_long_desc = ttk.Label(scrollable_frame, text="Длинные перерывы предназначены для продолжительного отдыха...", font=("Arial", 10), wraplength=700)
        lbl_long_desc.pack(anchor="w", pady=5)

        cb_enable_long = ttk.Checkbutton(scrollable_frame, text="Включить длинные перерывы", variable=self.variables["enable_long_breaks"], bootstyle="primary")
        cb_enable_long.pack(anchor="w", pady=5)

        long_duration_frame = ttk.Frame(scrollable_frame)
        long_duration_frame.pack(anchor="w", pady=5, fill="x")
        lbl_duration_long = ttk.Label(long_duration_frame, text="Продолжительность (мин):", font=("Arial", 10))
        lbl_duration_long.pack(side="left")
        self.long_break_duration_label = ttk.Label(long_duration_frame, text=f"{self.variables['long_break_duration'].get() // 60} мин", font=("Arial", 10))
        self.long_break_duration_label.pack(side="right", padx=10)
        self.variables["long_break_duration"].trace("w", self.update_long_break_duration_label)

        scale_long_duration = ttk.Scale(scrollable_frame, variable=self.variables["long_break_duration"], from_=5 * 60, to=60 * 60,
                                        orient="horizontal", length=400, bootstyle="primary",
                                        command=lambda e: self.update_long_break_duration_label())
        scale_long_duration.pack(anchor="w", pady=5)

        entry_long_duration = ttk.Entry(scrollable_frame, width=5)
        entry_long_duration.insert(0, str(self.variables["long_break_duration"].get() // 60))
        entry_long_duration.pack(anchor="w", pady=5)
        entry_long_duration.bind("<Return>", lambda e: self.update_duration_from_entry("long_break_duration", entry_long_duration, scale_long_duration, "мин"))

        long_interval_frame = ttk.Frame(scrollable_frame)
        long_interval_frame.pack(anchor="w", pady=5, fill="x")
        lbl_interval_long = ttk.Label(long_interval_frame, text="Каждые (мин):", font=("Arial", 10))
        lbl_interval_long.pack(side="left")
        self.long_break_interval_label = ttk.Label(long_interval_frame, text=f"{self.variables['long_break_interval'].get()} мин", font=("Arial", 10))
        self.long_break_interval_label.pack(side="right", padx=10)
        self.variables["long_break_interval"].trace("w", self.update_long_break_interval_label)

        scale_long_interval = ttk.Scale(scrollable_frame, variable=self.variables["long_break_interval"], from_=15, to=180,
                                        orient="horizontal", length=400, bootstyle="primary",
                                        command=lambda e: self.update_long_break_interval_label())
        scale_long_interval.pack(anchor="w", pady=5)

        lbl_schedule_time = ttk.Label(scrollable_frame, text="Время разрешённых перерывов (HH:MM):", font=("Arial", 10, "bold"))
        lbl_schedule_time.pack(anchor="w", pady=10)

        frm_time = ttk.Frame(scrollable_frame)
        frm_time.pack(anchor="w", pady=5)
        lbl_start = ttk.Label(frm_time, text="Начало:")
        lbl_start.pack(side="left", padx=5)
        entry_start_time = ttk.Entry(frm_time, width=10, textvariable=self.variables["break_start_time"])
        entry_start_time.pack(side="left", padx=5)
        lbl_end = ttk.Label(frm_time, text="Конец:")
        lbl_end.pack(side="left", padx=5)
        entry_end_time = ttk.Entry(frm_time, width=10, textvariable=self.variables["break_end_time"])
        entry_end_time.pack(side="left", padx=5)

        self.create_control_buttons(scrollable_frame)
        return frame

    def update_short_break_duration_label(self, *args):
        value = self.variables["short_break_duration"].get()
        text = f"{int(value)} сек"
        self.short_break_duration_label.config(text=text)

    def update_short_break_interval_label(self, *args):
        value = self.variables["short_break_interval"].get()
        self.short_break_interval_label.config(text=f"{int(value)} мин")

    def update_long_break_duration_label(self, *args):
        value = self.variables["long_break_duration"].get()
        minutes = int(value) // 60
        self.long_break_duration_label.config(text=f"{minutes} мин")

    def update_long_break_interval_label(self, *args):
        value = self.variables["long_break_interval"].get()
        self.long_break_interval_label.config(text=f"{int(value)} мин")

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

    def create_theme_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_theme = ttk.Label(frame, text="Тема", font=("Arial", 20, "bold"))
        lbl_theme.pack(pady=20)

        lbl_theme_desc = ttk.Label(frame, text="Здесь можно изменить тему приложения", font=("Arial", 12))
        lbl_theme_desc.pack(pady=5)

        themes = ["flatly", "darkly", "cosmo", "cyborg", "superhero", "minty"]
        lbl_select = ttk.Label(frame, text="Выберите тему:", font=("Arial", 10))
        lbl_select.pack(anchor="w", pady=5)

        theme_combobox = ttk.Combobox(frame, values=themes, textvariable=self.variables["theme"], state="readonly", bootstyle="primary")
        theme_combobox.pack(anchor="w", pady=5)
        theme_combobox.bind("<<ComboboxSelected>>", lambda e: self.apply_theme())

        return frame

    def create_about_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_app = ttk.Label(frame, text="Detox", font=("Arial", 24, "bold"))
        lbl_app.pack(pady=20)
        lbl_desc = ttk.Label(frame, text="Напоминания о перерывах", font=("Arial", 14))
        lbl_desc.pack()
        lbl_version = ttk.Label(frame, text="Версия 1.3.0", font=("Arial", 12))
        lbl_version.pack(pady=10)

        cb_autoupdate = ttk.Checkbutton(
            frame,
            text="Automatically check for app updates\n(Последняя версия 1.3.0)",
            variable=self.variables.get("autoupdate", ttk.BooleanVar(value=False)),
            bootstyle="primary"
        )
        cb_autoupdate.pack(pady=10)

        lbl_main_text = ttk.Label(
            frame,
            text=("Чтобы узнать больше о функционале Detox, пройдите обучение, "
                  "скачайте последнюю версию или свяжитесь с нами для поддержки."),
            font=("Arial", 10),
            wraplength=500,
            justify="center"
        )
        lbl_main_text.pack(pady=20)

        link = ttk.Label(frame, text="Посетите наш сайт.", font=("Arial", 10, "underline"),
                         foreground="#00bfff", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: self.open_website("http://yourwebsite.com"))

        lbl_developer = ttk.Label(frame, text="Разработано Алишером", font=("Arial", 10))
        lbl_developer.pack(side="bottom", pady=20)

        return frame

    def create_support_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_support = ttk.Label(frame, text="Поддержать Detox", font=("Arial", 20, "bold"))
        lbl_support.pack(pady=20)
        lbl_support_info = ttk.Label(frame, text="Здесь будет информация о том, как поддержать Detox", font=("Arial", 12))
        lbl_support_info.pack()
        return frame

    # ### НОВОЕ: создаём новый фрейм «Статистика»
    def create_statistics_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_title = ttk.Label(frame, text="Статистика", font=("Arial", 20, "bold"))
        lbl_title.pack(pady=10)

        self.lbl_stats_mini = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_mini.pack(pady=5)

        self.lbl_stats_long = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_long.pack(pady=5)

        self.lbl_stats_total = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_total.pack(pady=5)

        self.lbl_stats_mini_skipped = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_mini_skipped.pack(pady=5)

        self.lbl_stats_long_skipped = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_long_skipped.pack(pady=5)

        self.lbl_stats_break_time = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_break_time.pack(pady=5)

        self.lbl_stats_runtime = ttk.Label(frame, text="", font=("Arial", 12))
        self.lbl_stats_runtime.pack(pady=5)

        btn_clear = ttk.Button(frame, text="Очистить статистику", bootstyle="danger", command=self.clear_statistics)
        btn_clear.pack(pady=10)

        return frame

    # Обновляем текстовые поля статистики
    def update_statistics_labels(self):
        self.lbl_stats_mini.config(
            text=f"Коротких перерывов (пройдено): {self.stats['mini_breaks']}"
        )
        self.lbl_stats_long.config(
            text=f"Длинных перерывов (пройдено): {self.stats['long_breaks']}"
        )
        self.lbl_stats_total.config(
            text=f"Всего перерывов: {self.stats['total_breaks']}"
        )

        self.lbl_stats_mini_skipped.config(
            text=f"Пропущено мини-перерывов: {self.stats['mini_skipped']}"
        )
        self.lbl_stats_long_skipped.config(
            text=f"Пропущено длинных перерывов: {self.stats['long_skipped']}"
        )

        mini_minutes = self.stats['mini_time'] // 60
        mini_seconds = self.stats['mini_time'] % 60
        long_minutes = self.stats['long_time'] // 60
        long_seconds = self.stats['long_time'] % 60
        total_seconds = self.stats['mini_time'] + self.stats['long_time']
        total_minutes = total_seconds // 60
        total_rem_seconds = total_seconds % 60

        self.lbl_stats_break_time.config(
            text=(f"Общее время мини-перерывов: {mini_minutes} мин {mini_seconds} сек\n"
                  f"Общее время длинных перерывов: {long_minutes} мин {long_seconds} сек\n"
                  f"Всего времени отдыха: {total_minutes} мин {total_rem_seconds} сек")
        )

        total_runtime_minutes = self.stats['total_runtime'] // 60
        total_runtime_seconds = self.stats['total_runtime'] % 60
        self.lbl_stats_runtime.config(text=f"Время работы программы: ~{total_runtime_minutes} мин {total_runtime_seconds} сек")

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
        self.save_settings()  # сразу сохраним в JSON
        self.update_statistics_labels()

    def update_runtime_stat(self):
        now = datetime.datetime.now()
        elapsed = now - self.start_time
        seconds = int(elapsed.total_seconds())
        self.stats["total_runtime"] += seconds

    def toggle_theme(self):
        current_theme = self.variables["theme"].get()
        new_theme = "darkly" if current_theme != "darkly" else "flatly"
        self.variables["theme"].set(new_theme)
        self.apply_theme()

    def apply_theme(self):
        theme = self.variables["theme"].get()
        try:
            self.style.theme_use(theme)
            self.update_colors()
        except tk.TclError as e:
            print(f"Ошибка при применении темы: {e}")

    def update_colors(self):
        current_theme = self.variables["theme"].get()
        if current_theme == "flatly":
            color = "#F7F7F7"
        elif current_theme == "darkly":
            color = "#333333"
        elif current_theme == "cosmo":
            color = "#D8E3F0"
        elif current_theme == "cyborg":
            color = "#1C1C1C"
        elif current_theme == "superhero":
            color = "#2B3E50"
        elif current_theme == "minty":
            color = "#E0F2F1"
        else:
            color = "#F7F7F7"

        self.configure(background=color)
        if hasattr(self, "top_frame"):
            self.top_frame.configure(background=color)

        self.theme_button.config(text="🌙" if current_theme == "darkly" else "☀️")

    def reset_to_defaults(self):
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
        # Перед сохранением — обновим runtime
        self.update_runtime_stat()

        settings = {key: var.get() for key, var in self.variables.items()}
        # Добавим статистику
        settings["stats"] = self.stats

        with open(self.settings_file, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)

        # Обнуляем self.start_time, чтобы при следующем save считать время заново
        self.start_time = datetime.datetime.now()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r", encoding="utf-8") as file:
                data = json.load(file)
                for key, value in data.items():
                    if key in self.variables:
                        self.variables[key].set(value)
                    elif key == "stats" and isinstance(value, dict):
                        self.stats.update(value)

    def open_website(self, url):
        webbrowser.open_new(url)

    ### ТРЕЙ
    def create_tray_icon(self):
        image = Image.open("detox.png")
        self.tray_icon = Icon("Detox", image, "Detox", Menu())
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.after(1000, self.update_tray_menu)

    def update_tray_menu(self):
        mini_time = f"⏳ Мини: {self.mini_remaining_time // 60}м {self.mini_remaining_time % 60}с"
        long_time = f"⏳ Длинный: {self.long_remaining_time // 60}м {self.long_remaining_time % 60}с"

        menu = Menu(
            MenuItem("Detox", lambda icon, item: self.after(0, self.restore_from_tray), default=True),
            MenuItem(mini_time, lambda: None),
            MenuItem(long_time, lambda: None),
            Menu.SEPARATOR,
            MenuItem("Мини-перерыв", lambda icon, item: self.after(0, self.go_to_mini_break)),
            MenuItem("Длинный перерыв", lambda icon, item: self.after(0, self.go_to_long_break)),
            MenuItem("Пауза", lambda icon, item: self.after(0, self.pause_detox)),
            MenuItem("Выход", lambda icon, item: self.after(0, self.exit_detox))
        )
        self.tray_icon.menu = menu
        self.tray_icon.update_menu()
        self.after(1000, self.update_tray_menu)

    def minimize_to_tray(self):
        self.withdraw()
        self.create_tray_icon()


if __name__ == "__main__":
    app = DetoxSettingsApp()
    app.mainloop()
