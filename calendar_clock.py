import tkinter as tk
import calendar
from datetime import datetime


# === Матричная палитра ===
BG         = "#000000"   # чёрный фон
BG_CELL    = "#050505"   # чуть светлее для ячеек
GREEN      = "#00ff41"   # неоновый зелёный
GREEN_BRT  = "#7fff7f"   # яркий
GREEN_DIM  = "#008f11"   # приглушённый
GREEN_DRK  = "#003b00"   # тёмно-зелёный (сетка, фон шапки)
WHITE_GRN  = "#ccffcc"   # почти белый с зеленцой

FONT_MAIN  = ("Consolas", 11)
FONT_DAY   = ("Consolas", 14, "bold")
FONT_TITLE = ("Consolas", 20, "bold")
FONT_HEAD  = ("Consolas", 10, "bold")
FONT_TIME  = ("Consolas", 46, "bold")


class MatrixCalendarClock:
    def __init__(self, root):
        self.root = root
        self.root.title("MATRIX // КАЛЕНДАРЬ")
        self.root.geometry("780x700")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        now = datetime.now()
        self.year, self.month = now.year, now.month

        # ============ ВЕРХ: навигация + месяц ============
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=20, pady=(20, 5))

        nav_style = {
            "font": ("Consolas", 16, "bold"),
            "bg": BG, "fg": GREEN,
            "bd": 1, "relief": "solid",
            "highlightthickness": 1,
            "highlightbackground": GREEN_DIM,
            "cursor": "hand2",
            "activebackground": GREEN_DRK,
            "activeforeground": GREEN_BRT,
        }
        tk.Button(top, text="◀", command=self.prev_month,
                  **nav_style, width=3).pack(side="left")

        self.title_label = tk.Label(
            top, font=FONT_TITLE, bg=BG, fg=GREEN
        )
        self.title_label.pack(side="left", expand=True)

        tk.Button(top, text="▶", command=self.next_month,
                  **nav_style, width=3).pack(side="right")

        # ============ ШАПКА ДНЕЙ НЕДЕЛИ ============
        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(fill="x", padx=20, pady=(10, 0))

        days_full = [
            "ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ",
            "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"
        ]
        for i, d in enumerate(days_full):
            tk.Label(
                self.head_frame, text=d,
                font=FONT_HEAD, bg=GREEN_DRK, fg=GREEN_BRT,
                pady=6
            ).grid(row=0, column=i, sticky="nsew")
            self.head_frame.grid_columnconfigure(i, weight=1)

        # ============ СЕТКА КАЛЕНДАРЯ ============
        # Фон рамки = цвет линий
        self.grid_frame = tk.Frame(root, bg=GREEN_DIM)
        self.grid_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.build_calendar()

        # ============ ЧАСЫ СНИЗУ ============
        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(fill="x", pady=(10, 5))

        tk.Label(
            clock_frame, text="━━━━━━━━━━━━━━━━━━━━━━━",
            font=("Consolas", 12), bg=BG, fg=GREEN_DIM
        ).pack(pady=(0, 5))

        self.time_label = tk.Label(
            clock_frame, font=FONT_TIME,
            bg=BG, fg=GREEN
        )
        self.time_label.pack()

        self.date_label = tk.Label(
            clock_frame, font=("Consolas", 13, "bold"),
            bg=BG, fg=GREEN_DIM
        )
        self.date_label.pack(pady=(0, 15))

        self.update_clock()

    # ============ Построение календаря ============
    def build_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        month_names = [
            "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
            "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"
        ]
        self.title_label.config(
            text=f"{month_names[self.month-1]} {self.year}"
        )

        today = datetime.now()
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)

        # Как на фото — всегда 6 строк
        while len(weeks) < 6:
            weeks.append([0] * 7)

        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                # Фон-рамка (даёт сетку)
                cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
                cell_border.grid(row=row, column=col,
                                 padx=1, pady=1, sticky="nsew")
                self.grid_frame.grid_rowconfigure(row, weight=1)
                self.grid_frame.grid_columnconfigure(col, weight=1)

                if day == 0:
                    tk.Label(cell_border, text="", bg=BG_CELL,
                             font=FONT_DAY, height=2).pack(
                        fill="both", expand=True)
                    continue

                is_weekend = col >= 5
                is_today = (
                    day == today.day
                    and self.month == today.month
                    and self.year == today.year
                )

                # === Логика цветов ===
                if is_today:
                    # Сегодня — яркая плашка
                    bg, fg = GREEN, BG
                    font = ("Consolas", 15, "bold")
                elif is_weekend:
                    # Выходные — яркий зелёный
                    bg, fg = BG_CELL, GREEN_BRT
                    font = FONT_DAY
                else:
                    # Будни — приглушённый зелёный
                    bg, fg = BG_CELL, GREEN
                    font = FONT_DAY

                tk.Label(
                    cell_border, text=str(day),
                    font=font, bg=bg, fg=fg, height=2
                ).pack(fill="both", expand=True)

    # ============ Часы ============
    def update_clock(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=now.strftime("%A, %d %B %Y").upper()
        )
        self.root.after(1000, self.update_clock)

    # ============ Навигация ============
    def prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.build_calendar()

    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.build_calendar()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatrixCalendarClock(root)
    root.mainloop()
