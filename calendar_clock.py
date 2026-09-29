import tkinter as tk
import calendar
from datetime import datetime, date
import holidays


# === Матричная палитра ===
BG         = "#000000"
BG_CELL    = "#050505"
GREEN      = "#00ff41"
GREEN_BRT  = "#7fff7f"
GREEN_DIM  = "#008f11"
GREEN_DRK  = "#003b00"
RED        = "#ff3333"   # для праздников

FONT_DAY   = ("Consolas", 14, "bold")
FONT_HOL   = ("Consolas", 7)
FONT_TITLE = ("Consolas", 20, "bold")
FONT_HEAD  = ("Consolas", 10, "bold")
FONT_TIME  = ("Consolas", 46, "bold")

# Праздники России на 2020–2050 (запас на 25 лет вперёд)
RU_HOLIDAYS = holidays.RU(years=range(2020, 2051))


class MatrixCalendarClock:
    def __init__(self, root):
        self.root = root
        self.root.title("MATRIX // КАЛЕНДАРЬ")
        self.root.geometry("820x760")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        now = datetime.now()
        self.year, self.month = now.year, now.month

        # === Верх: навигация + месяц ===
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

        self.title_label = tk.Label(top, font=FONT_TITLE, bg=BG, fg=GREEN)
        self.title_label.pack(side="left", expand=True)

        tk.Button(top, text="▶", command=self.next_month,
                  **nav_style, width=3).pack(side="right")

        # === Шапка дней недели ===
        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(fill="x", padx=20, pady=(10, 0))

        days_full = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ",
                     "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
        for i, d in enumerate(days_full):
            tk.Label(self.head_frame, text=d, font=FONT_HEAD,
                     bg=GREEN_DRK, fg=GREEN_BRT, pady=6
                     ).grid(row=0, column=i, sticky="nsew")
            self.head_frame.grid_columnconfigure(i, weight=1)

        # === Сетка календаря ===
        self.grid_frame = tk.Frame(root, bg=GREEN_DIM)
        self.grid_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.build_calendar()

        # === Часы снизу ===
        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(fill="x", pady=(5, 5))

        tk.Label(clock_frame, text="━━━━━━━━━━━━━━━━━━━━━━━",
                 font=("Consolas", 12), bg=BG, fg=GREEN_DIM).pack(pady=(0, 5))

        self.time_label = tk.Label(clock_frame, font=FONT_TIME,
                                   bg=BG, fg=GREEN)
        self.time_label.pack()

        self.date_label = tk.Label(clock_frame, font=("Consolas", 13, "bold"),
                                   bg=BG, fg=GREEN_DIM)
        self.date_label.pack(pady=(0, 15))

        self.update_clock()

    def build_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        month_names = ["ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
                       "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"]
        self.title_label.config(text=f"{month_names[self.month-1]} {self.year}")

        today = datetime.now()
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        while len(weeks) < 6:
            weeks.append([0] * 7)

        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
                cell_border.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
                self.grid_frame.grid_rowconfigure(row, weight=1, minsize=62)
                self.grid_frame.grid_columnconfigure(col, weight=1)

                if day == 0:
                    tk.Label(cell_border, text="", bg=BG_CELL, height=2).pack(
                        fill="both", expand=True)
                    continue

                # === Проверка праздника ===
                d_obj = date(self.year, self.month, day)
                hol_name = RU_HOLIDAYS.get(d_obj)

                is_weekend = col >= 5
                is_today = (day == today.day and
                            self.month == today.month and
                            self.year == today.year)

                # === Цвета ===
                if is_today:
                    bg, fg, name_fg = GREEN, BG, BG
                    font = ("Consolas", 15, "bold")
                elif hol_name:
                    bg, fg, name_fg = BG_CELL, RED, RED
                    font = ("Consolas", 14, "bold")
                elif is_weekend:
                    bg, fg, name_fg = BG_CELL, GREEN_BRT, GREEN_BRT
                    font = FONT_DAY
                else:
                    bg, fg, name_fg = BG_CELL, GREEN, GREEN
                    font = FONT_DAY

                # === Ячейка ===
                cell = tk.Frame(cell_border, bg=bg)
                cell.pack(fill="both", expand=True)

                tk.Label(cell, text=str(day), font=font, bg=bg, fg=fg
                         ).pack(pady=(4, 0))

                if hol_name:
                    short = hol_name if len(hol_name) <= 22 else hol_name[:20] + "…"
                    tk.Label(cell, text=short, font=FONT_HOL,
                             bg=bg, fg=name_fg,
                             wraplength=100, justify="center"
                             ).pack(pady=(0, 2), padx=2)

    def update_clock(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y").upper())
        self.root.after(1000, self.update_clock)

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
