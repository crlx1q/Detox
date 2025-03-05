import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import json
import os
import webbrowser
from PIL import Image, ImageTk
import math
import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Progressbar

# Класс для анимированного холста
class AnimatedCanvas(ttk.Canvas):
    def __init__(self, root, image_path, **kwargs):
        super().__init__(root, **kwargs)
        self.pack()

        # Параметры анимации
        self.center_x = 100
        self.center_y = 100
        self.angle = 0  # Для пульсации

        # Фоновой круг
        self.background_circle = self.create_oval(
            self.center_x - 80,
            self.center_y - 80,
            self.center_x + 80,
            self.center_y + 80,
            fill="#003D33",  # Тёмно-зелёный цвет
            outline=""
        )

        # Градиентный круг
        self.gradient_circle = self.create_oval(
            self.center_x - 75,
            self.center_y - 75,
            self.center_x + 75,
            self.center_y + 75,
            fill="",  # Прозрачный фон
            outline="#1DBF73",  # Цвет контура
            width=3
        )

        # Загрузка и уменьшение изображения
        self.image = Image.open(image_path)
        self.image = self.image.resize((100, 100), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.image)

        # Отображение изображения
        self.image_item = self.create_image(self.center_x, self.center_y, image=self.tk_image)

        # Запуск анимации
        self.animate()

    def animate(self):
        """Анимация пульсации."""
        # Пульсация градиентного круга
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

        # Увеличение угла
        self.angle = (self.angle + 2) % 360

        # Перезапуск анимации
        self.after(50, self.animate)


# Класс окна обратного отсчета
class CountdownWindow:
    def __init__(self, parent, duration, theme="flatly", break_type="mini", strict_mode=False):
        self.parent = parent
        self.duration = duration  # В секундах
        self.remaining = duration
        self.break_type = break_type
        self.strict_mode = strict_mode

        # Создание нового окна
        self.window = tk.Toplevel(parent)
        self.window.title("Обратный отсчет")
        self.window.attributes('-fullscreen', True)
        self.window.attributes('-alpha', 0.9)
        self.window.configure(bg="#468f97")

        # Установка стиля
        self.style = Style(theme=theme)
        self.style.configure('TProgressbar', thickness=20, troughcolor="#468f97", background="#1DBF73")

        # Центральный фрейм для размещения элементов
        central_frame = tk.Frame(self.window, bg="#468f97")
        central_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Текст
        self.label = tk.Label(
            central_frame,
            text="Закройте глаза и считайте вдохи.",
            font=("Arial", 20),
            fg="white",
            bg="#468f97",
        )
        self.label.pack(pady=20)

        # Прогрессбар
        self.progress = Progressbar(
            central_frame,
            maximum=duration,  # Максимум – продолжительность в секундах
            orient="horizontal",
            mode="determinate",
            style="TProgressbar",
            length=400  # Задаем фиксированную длину
        )
        self.progress.pack(pady=10)
        self.progress["value"] = duration

        # Оставшееся время
        self.time_label = tk.Label(
            central_frame,
            text=f"{int(self.remaining)} сек осталось",
            font=("Arial", 16),
            fg="white",
            bg="#468f97",
        )
        self.time_label.pack(pady=10)

        # Кнопка "Пропустить", если не строгий режим
        if not self.strict_mode:
            self.skip_button = tk.Button(
                central_frame,
                text="Пропустить этот перерыв",
                font=("Arial", 14),
                bg="#468f97",
                fg="white",
                activebackground="#468f97",
                activeforeground="white",
                relief="flat",
                command=self.window.destroy,
            )
            self.skip_button.pack(pady=20)

        # Обработка закрытия окна
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Запуск анимации прогресс-бара
        self.update_progress()

    def update_progress(self):
        if self.remaining > 0:
            self.remaining -= 1  # Уменьшаем на 1 сек
            self.progress["value"] = self.remaining  # Уменьшаем на 1
            minutes, seconds = divmod(self.remaining, 60)
            self.time_label.config(text=f"{int(minutes)} мин {int(seconds)} сек осталось")
            self.window.after(1000, self.update_progress)  # Обновляем каждую секунду
        else:
            self.label.config(text="Время вышло!")
            self.time_label.config(text="")
            if not self.strict_mode:
                self.skip_button.config(text="Закрыть")
            # Добавляем задержку в 2 секунды перед закрытием окна
            self.window.after(2000, self.window.destroy)

    def on_close(self):
        self.window.destroy()


# Основное приложение с настройками Detox
class DetoxSettingsApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")  # Выберите тему по вашему вкусу

        # Настройки окна
        self.title("Настройки Detox")
        self.geometry("800x800")
        self.resizable(False, False)  # Запретить изменение размера окна
        self.settings_file = "settings.json"

        # Переменные для хранения состояния
        self.variables = {
            "autostart": ttk.BooleanVar(value=True),
            "break_mode": ttk.StringVar(value="fullscreen"),
            "exercise_tips": ttk.BooleanVar(value=True),
            "break_all_screens": ttk.BooleanVar(value=True),
            "track_idle": ttk.BooleanVar(value=True),
            "dnd_mode": ttk.BooleanVar(value=False),
            "language": ttk.StringVar(value="Русский"),
            "theme": ttk.StringVar(value="light"),  # По умолчанию светлая тема

            # Переменные для расписания
            "enable_short_breaks": ttk.BooleanVar(value=True),
            "short_break_duration": ttk.IntVar(value=20),  # В секундах
            "short_break_interval": ttk.IntVar(value=10),  # В минутах
            "enable_long_breaks": ttk.BooleanVar(value=True),
            "long_break_duration": ttk.IntVar(value=300),  # В секундах (5 минут)
            "long_break_interval": ttk.IntVar(value=30),  # В минутах

            # Новые переменные для уведомлений и откладывания перерывов
            "notify_before_short_break": ttk.BooleanVar(value=False),
            "allow_postpone_short_breaks": ttk.BooleanVar(value=True),
            "notify_before_long_break": ttk.BooleanVar(value=False),
            "allow_postpone_long_breaks": ttk.BooleanVar(value=True),

            # Переменные для строгого режима
            "strict_mode_mini_breaks": ttk.BooleanVar(value=False),
            "strict_mode_long_breaks": ttk.BooleanVar(value=False),

            # Дополнительные переменные, если нужно
            "autoupdate": ttk.BooleanVar(value=False),
            "detox_active": ttk.BooleanVar(value=False),  # Новая переменная для Detox
        }

        # Состояние Detox
        self.detox_active = False
        self.break_timer_mini = None
        self.break_timer_long = None
        self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
        self.long_remaining_time = self.variables["long_break_interval"].get() * 60

        # Создаем интерфейс сначала
        self.create_top_panel()
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)

        # Фрейм для содержания
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(pady=20, fill="both", expand=True)

        # Создаем фреймы для каждого раздела
        self.detox_frame = self.create_detox_frame()  # Новый фрейм Detox
        self.settings_frame = self.create_settings()
        self.schedule_frame = self.create_schedule_frame()
        self.theme_frame = self.create_theme_frame()
        self.about_frame = self.create_about_frame()
        self.support_frame = self.create_support_frame()

        # Загрузить настройки после создания всех фреймов
        self.load_settings()

        # Показываем фрейм Detox по умолчанию
        self.show_detox()

        # Установить тему при запуске
        self.apply_theme()

        # Добавить трассировку для изменений интервалов
        self.variables["short_break_interval"].trace("w", self.on_short_break_interval_change)
        self.variables["long_break_interval"].trace("w", self.on_long_break_interval_change)

    def get_current_theme_name(self):
        theme = self.variables["theme"].get()
        return "flatly" if theme == "light" else "darkly"

    def create_top_panel(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", pady=10)
        self.top_frame = top_frame  # Сохраняем ссылку на фрейм

        buttons = [
            ("Detox", self.show_detox),  # Перемещена кнопка Detox в начало
            ("Настройки", self.show_settings),
            ("Расписание", self.show_schedule),
            ("Тема", self.show_theme),
            ("О программе", self.show_about),
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

        # Кнопка смены темы
        theme_button = ttk.Button(
            top_frame,
            text="🌙" if self.variables["theme"].get() == "dark" else "☀️",
            bootstyle="link",
            command=self.toggle_theme,
        )
        theme_button.pack(side="right", padx=5)
        self.theme_button = theme_button

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

    def show_detox(self):
        self.hide_all_frames()
        self.detox_frame.pack(pady=20, fill="both", padx=20, expand=True)

    def hide_all_frames(self):
        for frame in (
            self.detox_frame,
            self.settings_frame,
            self.schedule_frame,
            self.theme_frame,
            self.about_frame,
            self.support_frame,
        ):
            frame.pack_forget()

    def create_settings(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        # Чекбоксы
        cb_autostart = ttk.Checkbutton(
            frame,
            text="Запускать Detox автоматически при входе в систему",
            variable=self.variables["autostart"],
            bootstyle="primary",
        )
        cb_autostart.pack(anchor="w", pady=5)

        lbl_breaks = ttk.Label(
            frame,
            text="Показывать перерывы:",
            font=("Arial", 10, "bold"),
        )
        lbl_breaks.pack(anchor="w", pady=10)

        # Радиокнопки
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

        # Другие чекбоксы
        options = {
            "Показывать идеи для упражнений во время перерывов": "exercise_tips",
            "Показывать перерывы на всех экранах": "break_all_screens",
            "Следить за неиспользованием системы": "track_idle",
            "Показывать перерывы даже в режиме 'Не беспокоить'": "dnd_mode",
        }
        for text, var_name in options.items():
            cb = ttk.Checkbutton(
                frame,
                text=text,
                variable=self.variables[var_name],
                bootstyle="primary",
            )
            cb.pack(anchor="w", pady=5)

        # Выбор языка
        lbl_language = ttk.Label(
            frame,
            text="Выбрать язык:",
            font=("Arial", 10, "bold"),
        )
        lbl_language.pack(anchor="w", pady=10)
        language_combobox = ttk.Combobox(
            frame,
            textvariable=self.variables["language"],
            state="readonly",
            bootstyle="primary",
        )
        language_combobox["values"] = ["Русский", "Английский"]
        language_combobox.pack(anchor="w", pady=5)
        language_combobox.set(self.variables["language"].get())

        # Переключатель Detox
        cb_detox = ttk.Checkbutton(
            frame,
            text="Включить Detox",
            variable=self.variables["detox_active"],
            bootstyle="primary",
            command=self.toggle_detox,
        )
        cb_detox.pack(anchor="w", pady=10)

        # Кнопки управления
        self.create_control_buttons(frame)
        return frame

    def create_control_buttons(self, parent_frame):
        # Кнопки управления (Сохранить и Сбросить настройки)
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

    def create_detox_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)

        # Интеграция уменьшенного анимированного холста вместо статичного логотипа
        try:
            # Определяем абсолютный путь к изображению
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "detox.png")

            # Создаем уменьшенный AnimatedCanvas
            animated_canvas = AnimatedCanvas(frame, image_path=image_path, width=200, height=200, bg="black", highlightthickness=0)
            animated_canvas.pack(pady=10)  # Уменьшено отступ для компактности
        except Exception as e:
            lbl_logo = ttk.Label(
                frame,
                text="Логотип не найден",
                font=("Arial", 14, "bold"),
                foreground="red",
            )
            lbl_logo.pack(pady=20)
            print(f"Ошибка при загрузке изображения: {e}")

        # Название Detox
        lbl_title = ttk.Label(
            frame,
            text="Detox",
            font=("Arial", 24, "bold"),
        )
        lbl_title.pack(pady=10)

        # Кнопки функций
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

        btn_pause = ttk.Button(
            btn_frame,
            text="Пауза",
            bootstyle="warning",
            command=self.pause_detox,
            width=25
        )
        btn_pause.pack(pady=5)

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

        # Метки для отображения оставшегося времени до перерывов
        lbl_mini_remaining = ttk.Label(
            frame,
            text="До мини перерыва осталось: 00 мин 00 сек",
            font=("Arial", 14),
        )
        lbl_mini_remaining.pack(pady=5)
        self.mini_remaining_label = lbl_mini_remaining

        lbl_long_remaining = ttk.Label(
            frame,
            text="До длинного перерыва осталось: 00 мин 00 сек",
            font=("Arial", 14),
        )
        lbl_long_remaining.pack(pady=5)
        self.long_remaining_label = lbl_long_remaining

        return frame

    def go_to_mini_break(self):
        if self.variables["enable_short_breaks"].get() and self.variables["detox_active"].get():
            duration = self.variables["short_break_duration"].get()
            strict_mode = self.variables["strict_mode_mini_breaks"].get()
            # Открываем окно обратного отсчета с корректной темой и параметрами
            CountdownWindow(
                parent=self,
                duration=duration,
                theme=self.get_current_theme_name(),
                break_type="mini",
                strict_mode=strict_mode
            )

    def go_to_long_break(self):
        if self.variables["enable_long_breaks"].get() and self.variables["detox_active"].get():
            duration = self.variables["long_break_duration"].get()
            strict_mode = self.variables["strict_mode_long_breaks"].get()
            # Открываем окно обратного отсчета с корректной темой и параметрами
            CountdownWindow(
                parent=self,
                duration=duration,
                theme=self.get_current_theme_name(),
                break_type="long",
                strict_mode=strict_mode
            )

    def pause_detox(self):
        self.stop_detox()

    def reset_detox(self):
        self.stop_detox()
        # Перезапустить Detox, чтобы таймеры начали отсчет заново на основе текущих настроек
        self.start_detox()

    def exit_detox(self):
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
            # Отменяем оба таймера, если они активны
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
        if not self.detox_active:
            return

        if self.mini_remaining_time > 0:
            self.mini_remaining_time -= 1
            minutes, seconds = divmod(self.mini_remaining_time, 60)
            if hasattr(self, 'mini_remaining_label'):
                self.mini_remaining_label.config(text=f"До мини перерыва осталось: {minutes} мин {seconds} сек")
            self.break_timer_mini = self.after(1000, self.update_mini_timer)
        else:
            if self.variables["enable_short_breaks"].get():
                CountdownWindow(
                    parent=self,
                    duration=self.variables["short_break_duration"].get(),
                    theme=self.get_current_theme_name(),
                    break_type="mini",
                    strict_mode=self.variables["strict_mode_mini_breaks"].get()
                )
            # Сброс таймера
            self.mini_remaining_time = self.variables["short_break_interval"].get() * 60
            self.break_timer_mini = self.after(1000, self.update_mini_timer)

    def start_long_timer(self):
        self.long_remaining_time = self.variables["long_break_interval"].get() * 60
        self.update_long_timer()

    def update_long_timer(self):
        if not self.detox_active:
            return

        if self.long_remaining_time > 0:
            self.long_remaining_time -= 1
            minutes, seconds = divmod(self.long_remaining_time, 60)
            if hasattr(self, 'long_remaining_label'):
                self.long_remaining_label.config(text=f"До длинного перерыва осталось: {minutes} мин {seconds} сек")
            self.break_timer_long = self.after(1000, self.update_long_timer)
        else:
            if self.variables["enable_long_breaks"].get():
                CountdownWindow(
                    parent=self,
                    duration=self.variables["long_break_duration"].get(),
                    theme=self.get_current_theme_name(),
                    break_type="long",
                    strict_mode=self.variables["strict_mode_long_breaks"].get()
                )
            # Сброс таймера
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

    def create_schedule_frame(self):
        """Создает интерфейс для раздела 'Расписание' с прокруткой."""
        frame = ttk.Frame(self.content_frame)

        # Создаем Canvas и Scrollbar
        canvas = ttk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Мини-перерывы
        lbl_short = ttk.Label(
            scrollable_frame,
            text="Мини-перерывы:",
            font=("Arial", 14, "bold"),
        )
        lbl_short.pack(anchor="w", pady=10)

        lbl_short_desc = ttk.Label(
            scrollable_frame,
            text="Мини-перерывы — это регулярные короткие перерывы, чтобы размяться и отдохнуть.",
            font=("Arial", 10),
            wraplength=700,
        )
        lbl_short_desc.pack(anchor="w", pady=5)

        cb_enable_short = ttk.Checkbutton(
            scrollable_frame,
            text="Включить мини-перерывы",
            variable=self.variables["enable_short_breaks"],
            bootstyle="primary",
        )
        cb_enable_short.pack(anchor="w", pady=5)

        # Продолжительность мини-перерывов
        duration_frame = ttk.Frame(scrollable_frame)
        duration_frame.pack(anchor="w", pady=5, fill="x")

        lbl_duration_short = ttk.Label(
            duration_frame,
            text="Продолжительность:",
            font=("Arial", 10),
        )
        lbl_duration_short.pack(side="left")

        self.short_break_duration_label = ttk.Label(
            duration_frame,
            text=f"{self.variables['short_break_duration'].get()} сек",
            font=("Arial", 10),
        )
        self.short_break_duration_label.pack(side="right", padx=10)

        self.variables["short_break_duration"].trace(
            "w", self.update_short_break_duration_label
        )

        scale_short_duration = ttk.Scale(
            scrollable_frame,
            variable=self.variables["short_break_duration"],
            from_=10,
            to=600,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_short_break_duration_label(),
        )
        scale_short_duration.pack(anchor="w", pady=5)

        # Интервал мини-перерывов
        interval_frame = ttk.Frame(scrollable_frame)
        interval_frame.pack(anchor="w", pady=5, fill="x")

        lbl_interval_short = ttk.Label(
            interval_frame,
            text="Каждые (минуты):",
            font=("Arial", 10),
        )
        lbl_interval_short.pack(side="left")

        self.short_break_interval_label = ttk.Label(
            interval_frame,
            text=f"{self.variables['short_break_interval'].get()} мин",
            font=("Arial", 10),
        )
        self.short_break_interval_label.pack(side="right", padx=10)

        self.variables["short_break_interval"].trace(
            "w", self.update_short_break_interval_label
        )

        scale_short_interval = ttk.Scale(
            scrollable_frame,
            variable=self.variables["short_break_interval"],
            from_=5,
            to=65,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_short_break_interval_label(),
        )
        scale_short_interval.pack(anchor="w", pady=5)

        # Дополнительные опции для мини-перерывов
        cb_notify_short = ttk.Checkbutton(
            scrollable_frame,
            text="Показывать уведомление перед началом мини-перерыва",
            variable=self.variables["notify_before_short_break"],
            bootstyle="primary",
        )
        cb_notify_short.pack(anchor="w", pady=5)

        cb_postpone_short = ttk.Checkbutton(
            scrollable_frame,
            text="Разрешить откладывать мини-перерывы",
            variable=self.variables["allow_postpone_short_breaks"],
            bootstyle="primary",
        )
        cb_postpone_short.pack(anchor="w", pady=5)

        # Длинные перерывы
        lbl_long = ttk.Label(
            scrollable_frame,
            text="Длинные перерывы:",
            font=("Arial", 14, "bold"),
        )
        lbl_long.pack(anchor="w", pady=10)

        lbl_long_desc = ttk.Label(
            scrollable_frame,
            text="Длинные перерывы менее регулярны, и предназначены для продолжительного отдыха от работы.",
            font=("Arial", 10),
            wraplength=700,
        )
        lbl_long_desc.pack(anchor="w", pady=5)

        cb_enable_long = ttk.Checkbutton(
            scrollable_frame,
            text="Включить длинные перерывы",
            variable=self.variables["enable_long_breaks"],
            bootstyle="primary",
        )
        cb_enable_long.pack(anchor="w", pady=5)

        # Продолжительность длинных перерывов
        long_duration_frame = ttk.Frame(scrollable_frame)
        long_duration_frame.pack(anchor="w", pady=5, fill="x")

        lbl_duration_long = ttk.Label(
            long_duration_frame,
            text="Продолжительность:",
            font=("Arial", 10),
        )
        lbl_duration_long.pack(side="left")

        self.long_break_duration_label = ttk.Label(
            long_duration_frame,
            text=f"{self.variables['long_break_duration'].get() // 60} мин",
            font=("Arial", 10),
        )
        self.long_break_duration_label.pack(side="right", padx=10)

        self.variables["long_break_duration"].trace(
            "w", self.update_long_break_duration_label
        )

        scale_long_duration = ttk.Scale(
            scrollable_frame,
            variable=self.variables["long_break_duration"],
            from_=5 * 60,  # 5 минут в секундах
            to=60 * 60,  # 60 минут в секундах
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_long_break_duration_label(),
        )
        scale_long_duration.pack(anchor="w", pady=5)

        # Интервал длинных перерывов
        long_interval_frame = ttk.Frame(scrollable_frame)
        long_interval_frame.pack(anchor="w", pady=5, fill="x")

        lbl_interval_long = ttk.Label(
            long_interval_frame,
            text="Каждые (минуты):",
            font=("Arial", 10),
        )
        lbl_interval_long.pack(side="left")

        self.long_break_interval_label = ttk.Label(
            long_interval_frame,
            text=f"{self.variables['long_break_interval'].get()} мин",
            font=("Arial", 10),
        )
        self.long_break_interval_label.pack(side="right", padx=10)

        self.variables["long_break_interval"].trace(
            "w", self.update_long_break_interval_label
        )

        scale_long_interval = ttk.Scale(
            scrollable_frame,
            variable=self.variables["long_break_interval"],
            from_=15,
            to=180,
            orient="horizontal",
            length=400,
            bootstyle="primary",
            command=lambda e: self.update_long_break_interval_label(),
        )
        scale_long_interval.pack(anchor="w", pady=5)

        # Дополнительные опции для длинных перерывов
        cb_notify_long = ttk.Checkbutton(
            scrollable_frame,
            text="Показывать уведомление перед началом длинного перерыва",
            variable=self.variables["notify_before_long_break"],
            bootstyle="primary",
        )
        cb_notify_long.pack(anchor="w", pady=5)

        cb_postpone_long = ttk.Checkbutton(
            scrollable_frame,
            text="Разрешить откладывать длинные перерывы",
            variable=self.variables["allow_postpone_long_breaks"],
            bootstyle="primary",
        )
        cb_postpone_long.pack(anchor="w", pady=5)

        # Строгий режим
        lbl_strict = ttk.Label(
            scrollable_frame,
            text="Строгий режим:",
            font=("Arial", 14, "bold"),
        )
        lbl_strict.pack(anchor="w", pady=10)

        lbl_strict_desc = ttk.Label(
            scrollable_frame,
            text="Строгий режим не позволяет откладывать ни мини-перерывы, ни длинные перерывы. Создан для поддержания дисциплины.",
            font=("Arial", 10),
            wraplength=700,
        )
        lbl_strict_desc.pack(anchor="w", pady=5)

        cb_strict_mini = ttk.Checkbutton(
            scrollable_frame,
            text="Включить строгий режим для мини-перерывов",
            variable=self.variables["strict_mode_mini_breaks"],
            bootstyle="primary",
        )
        cb_strict_mini.pack(anchor="w", pady=5)

        cb_strict_long = ttk.Checkbutton(
            scrollable_frame,
            text="Включить строгий режим для длинных перерывов",
            variable=self.variables["strict_mode_long_breaks"],
            bootstyle="primary",
        )
        cb_strict_long.pack(anchor="w", pady=5)

        # Кнопки сохранения и сброса
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

    def create_theme_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_theme = ttk.Label(
            frame,
            text="Тема",
            font=("Arial", 20, "bold"),
        )
        lbl_theme.pack(pady=20)

        lbl_theme_desc = ttk.Label(
            frame,
            text="Здесь можно изменить тему приложения",
            font=("Arial", 12),
        )
        lbl_theme_desc.pack()

        # Добавим опции для смены темы
        theme_options = ["light", "dark"]
        for theme in theme_options:
            rb = ttk.Radiobutton(
                frame,
                text=theme.capitalize(),
                variable=self.variables["theme"],
                value=theme,
                bootstyle="primary",
                command=self.apply_theme
            )
            rb.pack(anchor="w", pady=5)

        return frame

    def create_about_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)

        # Верхняя часть с названием приложения
        lbl_app = ttk.Label(
            frame,
            text="Detox",
            font=("Arial", 24, "bold"),
        )
        lbl_app.pack(pady=20)

        # Описание
        lbl_desc = ttk.Label(
            frame,
            text="Напоминания о перерывах",
            font=("Arial", 14),
        )
        lbl_desc.pack()

        # Версия приложения
        lbl_version = ttk.Label(
            frame,
            text="Версия 1.3.0",
            font=("Arial", 12),
        )
        lbl_version.pack(pady=10)

        # Автоматическое обновление (чекбокс)
        cb_autoupdate = ttk.Checkbutton(
            frame,
            text="Automatically check for app updates\n(Последняя версия 1.3.0)",
            variable=self.variables.get("autoupdate", ttk.BooleanVar(value=False)),
            bootstyle="primary",
        )
        cb_autoupdate.pack(pady=10)

        # Основной текст
        lbl_main_text = ttk.Label(
            frame,
            text=(
                "Чтобы узнать больше о функционале Detox, пройдите обучение, "
                "скачайте последнюю версию или свяжитесь с нами для получения поддержки."
            ),
            font=("Arial", 10),
            wraplength=500,
            justify="center",
        )
        lbl_main_text.pack(pady=20)

        # Ссылка (интерактивная)
        link = ttk.Label(
            frame,
            text="Посетите наш сайт.",
            font=("Arial", 10, "underline"),
            foreground="#00bfff",
            cursor="hand2",
        )
        link.pack()
        link.bind("<Button-1>", lambda e: self.open_website("http://yourwebsite.com"))

        # Разработчик
        lbl_developer = ttk.Label(
            frame,
            text="Разработано Алишером",
            font=("Arial", 10),
        )
        lbl_developer.pack(side="bottom", pady=20)

        return frame

    def create_support_frame(self):
        frame = ttk.Frame(self.content_frame, padding=10)
        lbl_support = ttk.Label(
            frame,
            text="Поддержать Detox",
            font=("Arial", 20, "bold"),
        )
        lbl_support.pack(pady=20)
        lbl_support_info = ttk.Label(
            frame,
            text="Здесь будет информация о том, как поддержать Detox",
            font=("Arial", 12),
        )
        lbl_support_info.pack()
        return frame

    def toggle_theme(self):
        current_theme = self.variables["theme"].get()  # 'light' или 'dark'
        new_theme = "dark" if current_theme == "light" else "light"
        self.variables["theme"].set(new_theme)
        self.apply_theme()

    def apply_theme(self):
        theme = self.variables["theme"].get()
        try:
            self.style.theme_use("flatly" if theme == "light" else "darkly")
            self.update_colors()
        except tk.TclError as e:
            print(f"Ошибка при применении темы: {e}")

    def update_colors(self):
        """Обновить цвета всех виджетов на основе текущей темы."""
        # ttkbootstrap автоматически применяет стили к виджетам
        # Обновляем текст кнопки смены темы
        self.theme_button.config(
            text="🌙" if self.variables["theme"].get() == "dark" else "☀️"
        )

    def reset_detox(self):
        self.stop_detox()
        # Перезапустить Detox, чтобы таймеры начали отсчет заново на основе текущих настроек
        self.start_detox()

    def reset_to_defaults(self):
        defaults = {
            "autostart": True,
            "break_mode": "fullscreen",
            "exercise_tips": True,
            "break_all_screens": True,
            "track_idle": True,
            "dnd_mode": False,
            "language": "Русский",
            "theme": "light",
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
            "detox_active": False,  # Сброс состояния Detox
        }
        for key, value in defaults.items():
            if key in self.variables:
                self.variables[key].set(value)
        self.stop_detox()
        self.apply_theme()
        self.save_settings()

    def save_settings(self):
        settings = {key: var.get() for key, var in self.variables.items()}
        with open(self.settings_file, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r", encoding="utf-8") as file:
                settings = json.load(file)
                for key, value in settings.items():
                    if key in self.variables:
                        self.variables[key].set(value)
                # Восстановить состояние Detox
                if self.variables["detox_active"].get():
                    self.start_detox()

    def open_website(self, url):
        webbrowser.open_new(url)

    def exit_detox(self):
        self.destroy()


if __name__ == "__main__":
    app = DetoxSettingsApp()
    app.mainloop()
