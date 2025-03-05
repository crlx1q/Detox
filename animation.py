import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import math


class AnimatedCanvas(ttk.Canvas):
    def __init__(self, root, image_path, **kwargs):
        super().__init__(root, **kwargs)
        self.pack()

        # Параметры анимации
        self.center_x = 200
        self.center_y = 200
        self.angle = 0  # Для пульсации

        # Темно-зеленый фоновой круг
        self.background_circle = self.create_oval(
            self.center_x - 160,
            self.center_y - 160,
            self.center_x + 160,
            self.center_y + 160,
            fill="#003D33",  # Тёмно-зелёный цвет
            outline=""
        )

        # Полупрозрачный градиентный круг
        self.gradient_circle = self.create_oval(
            self.center_x - 150,
            self.center_y - 150,
            self.center_x + 150,
            self.center_y + 150,
            fill="",  # Прозрачный фон
            outline="#1DBF73",  # Цвет контура
            width=5
        )

        # Загрузка изображения
        self.image = Image.open(image_path)
        self.image = self.image.resize((200, 200), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.image)

        # Отображение изображения
        self.image_item = self.create_image(self.center_x, self.center_y, image=self.tk_image)

        # Запуск анимации
        self.animate()

    def animate(self):
        """Анимация пульсации."""
        # Пульсация градиентного круга
        radius_offset = 10 * math.sin(math.radians(self.angle))
        new_width = int(5 + 3 * math.sin(math.radians(self.angle)))  # Приводим ширину к целому числу
        self.coords(
            self.gradient_circle,
            self.center_x - 150 - radius_offset,
            self.center_y - 150 - radius_offset,
            self.center_x + 150 + radius_offset,
            self.center_y + 150 + radius_offset
        )
        self.itemconfig(self.gradient_circle, width=new_width)

        # Увеличение угла
        self.angle = (self.angle + 2) % 360  # Замедляем пульсацию

        # Перезапуск анимации
        self.after(50, self.animate)  # Увеличиваем задержку для замедления


# Основное приложение с использованием ttkbootstrap
class MainApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")  # Можно менять тему (например, "darkly", "flatly", "minty")
        self.title("Анимация с Bootstrap")
        self.geometry("400x400")
        self.configure(bg="black")  # Устанавливаем черный фон
        self.resizable(False, False)

        # Добавляем Canvas с анимацией
        image_path = "detox.jpg"  # Укажите путь к вашему изображению
        self.canvas = AnimatedCanvas(self, image_path=image_path, width=400, height=400, bg="black", highlightthickness=0)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
