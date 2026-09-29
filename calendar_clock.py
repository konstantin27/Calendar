import tkinter as tk
import calendar
import json
import os
import sys
from datetime import datetime, date
import holidays


# === Определяем папку программы (работает и в .exe, и в .py) ===
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(get_base_dir(), "shifts.json")

DEFAULT_CONFIG = {
    "_info1": "Редактируй файл shifts.json и нажимай кнопку ОБНОВИТЬ в программе.",
    "_info2": "start_date — начало цикла, формат ГГГГ-ММ-ДД (любая дата, когда работала Смена 1)",
    "_info3": "shift_days — сколько дней подряд работает одна смена (для 3/3 это 3)",
    "_info4": "teams — список смен: name (название), color (цвет), members (фамилии)",
    "start_date": "2026-01-01",
    "shift_days": 3,
    "teams": [
        {
            "name": "Смена 1",
            "color": "#00ff41",
            "members": ["Иванов И.", "Петров П.", "Сидоров С."]
        },
        {
            "name": "Смена 2",
            "color": "#00bfff",
            "members": ["Кузнецов К.", "Смирнов С.", "Волков В."]
        }
    ]
}


def load_config():
    """Загружает shifts.json. Если файла нет — создаёт с примером."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Ошибка чтения shifts.json:", e)
        return DEFAULT_CONFIG


# === Матричная палитра ===
BG         = "#000000"
BG_CELL    = "#050505"
GREEN      = "#00ff41"
GREEN_BRT  = "#7fff7f"
GREEN_DIM  = "#008f11"
GREEN_DRK  = "#003b00"
RED        = "#ff3333"
ORANGE     = "#ff9500"

FONT_DAY   = ("Consolas", 12, "bold")
FONT_HOL   = ("Consolas", 6)
FONT_NAME  = ("Consolas", 7)
FONT_TITLE = ("Consolas", 20, "bold")
FONT_HEAD  = ("Consolas", 9, "bold")
FONT_TIME  = ("Consolas", 40, "bold")
FONT_INFO  = ("Consolas", 10, "bold")

# Русские названия дней недели и месяцев
WEEKDAYS_RU = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ",
               "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
MONTHS_RU_GEN = ["ЯНВАРЯ", "ФЕВРАЛЯ", "МАРТА", "АПРЕЛЯ", "МАЯ", "ИЮНЯ",
                 "ИЮЛЯ", "АВГУСТА", "СЕНТЯБРЯ", "ОКТЯБРЯ", "НОЯБРЯ", "ДЕКАБРЯ"]
MONTHS_RU_NOM = ["ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
                 "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"]

RU_HOLIDAYS = holidays.RU(years=range(2020, 2051))


class MatrixShiftCalendar:
    def __init__(self, root):
        self.root = root
        self.root.title("MATRIX // ГРАФИК СМЕН 3/3")
        self.root.geometry("960x920")
        self.root.minsize(760, 700)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.load_settings()

        now = datetime.now()
        self.year, self.month = now.year, now.month

        # === Верх: навигация + месяц ===
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=20, pady=(15, 5))

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

        # === Панель кнопок ===
        toolbar = tk.Frame(root, bg=BG)
        toolbar.pack(fill="x", padx=20, pady=(0, 5))

        btn_small = {
            "font": ("Consolas", 10, "bold"),
            "bg": BG, "fg": GREEN_DIM, "bd": 1, "relief": "solid",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "padx": 10, "pady": 3, "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT
        }
        tk.Button(toolbar, text="ОБНОВИТЬ", command=self.reload_config,
                  **btn_small).pack(side="left", padx=3)
        tk.Button(toolbar, text="ОТКРЫТЬ SHIFTS.JSON", command=self.open_config,
                  **btn_small).pack(side="left", padx=3)
        tk.Button(toolbar, text="СЕГОДНЯ", command=self.go_today,
                  **btn_small).pack(side="right", padx=3)

        # === Шапка дней недели ===
        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(fill="x", padx=20, pady=(8, 0))

        days_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days_short):
            tk.Label(self.head_frame, text=d, font=FONT_HEAD,
                     bg=GREEN_DRK, fg=GREEN_BRT, pady=4
                     ).grid(row=0, column=i, sticky="nsew")
            self.head_frame.grid_columnconfigure(i, weight=1)

        # === Сетка ===
        self.grid_frame = tk.Frame(root, bg=GREEN_DIM)
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # === Информация о сегодняшней смене ===
        self.today_info = tk.Label(
            root, text="", font=FONT_INFO, bg=BG, fg=GREEN_BRT,
            wraplength=900, justify="center"
        )
        self.today_info.pack(fill="x", pady=(0, 8))

        # === Часы ===
        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(fill="x", pady=(0, 10))

        self.time_label = tk.Label(clock_frame, font=FONT_TIME,
                                   bg=BG, fg=GREEN)
        self.time_label.pack()

        self.date_label = tk.Label(clock_frame, font=("Consolas", 12, "bold"),
                                   bg=BG, fg=GREEN_DIM)
        self.date_label.pack()

        self.build_calendar()
        self.update_clock()

    # ============ Загрузка настроек ============
    def load_settings(self):
        self.config = load_config()
        try:
            self.start_date = datetime.strptime(
                self.config["start_date"], "%Y-%m-%d"
            ).date()
        except Exception:
            self.start_date = date(2026, 1, 1)
        self.shift_days = int(self.config.get("shift_days", 3))
        self.teams = self.config.get("teams", [])
        if not self.teams:
            self.teams = DEFAULT_CONFIG["teams"]

    def get_team_for_date(self, target_date):
        """Возвращает смену, которая работает в указанный день."""
        if not self.teams or self.shift_days < 1:
            return None
        cycle = self.shift_days * len(self.teams)
        delta = (target_date - self.start_date).days
        pos = delta % cycle
        team_index = pos // self.shift_days
        return self.teams[team_index]

    def reload_config(self):
        self.load_settings()
        self.build_calendar()
        self.update_today_info()

    def open_config(self):
        if not os.path.exists(CONFIG_FILE):
            load_config()
        try:
            os.startfile(CONFIG_FILE)
        except Exception as e:
            print("Не удалось открыть файл:", e)

    # ============ Построение календаря ============
    def build_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.title_label.config(
            text=f"{MONTHS_RU_NOM[self.month-1]} {self.year}"
        )

        today = date.today()
        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        while len(weeks) < 6:
            weeks.append([0] * 7)

        for row, week in enumerate(weeks):
            self.grid_frame.grid_rowconfigure(row, weight=1)
            for col, day in enumerate(week):
                self.grid_frame.grid_columnconfigure(col, weight=1)

                cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
                cell_border.grid(row=row, column=col,
                                 padx=1, pady=1, sticky="nsew")

                if day == 0:
                    tk.Label(cell_border, text="", bg=BG_CELL).pack(
                        fill="both", expand=True)
                    continue

                d_obj = date(self.year, self.month, day)
                hol_name = RU_HOLIDAYS.get(d_obj)
                team = self.get_team_for_date(d_obj)

                is_today = (d_obj == today)
                team_color = team["color"] if team else GREEN_DIM
                bg = GREEN if is_today else BG_CELL

                cell = tk.Frame(cell_border, bg=bg)
                cell.pack(fill="both", expand=True)

                # Заголовок ячейки: число + цветной индикатор
                head = tk.Frame(cell, bg=bg)
                head.pack(fill="x", pady=(2, 0))

                day_fg = BG if is_today else (RED if hol_name else team_color)
                tk.Label(head, text=str(day), font=FONT_DAY,
                         bg=bg, fg=day_fg).pack(side="left", padx=(5, 2))

                if team and not is_today:
                    tk.Label(head, text="■", font=("Consolas", 9),
                             bg=bg, fg=team_color).pack(side="left")

                # Праздник
                if hol_name:
                    short = hol_name if len(hol_name) <= 30 else hol_name[:28] + "…"
                    tk.Label(cell, text=short, font=FONT_HOL,
                             bg=bg, fg=RED, wraplength=120, justify="center"
                             ).pack(padx=2, anchor="w")

                # Фамилии смены
                if team:
                    names_text = ", ".join(team["members"])
                    txt_fg = BG if is_today else team_color
                    tk.Label(cell, text=names_text, font=FONT_NAME,
                             bg=bg, fg=txt_fg,
                             wraplength=125, justify="left", anchor="nw"
                             ).pack(padx=4, pady=(1, 2), anchor="nw", fill="both")

        self.update_today_info()

    # ============ Информация о сегодняшней смене ============
    def update_today_info(self):
        today = date.today()
        team = self.get_team_for_date(today)
        hol = RU_HOLIDAYS.get(today)

        if team:
            line = f"СЕГОДНЯ НА СМЕНЕ: {team['name']}  ▸  {', '.join(team['members'])}"
        else:
            line = "СЕГОДНЯ: выходной"

        if hol:
            line = f"🎉 {hol}   |   " + line

        self.today_info.config(text=line)

    # ============ Часы ============
    def update_clock(self):
        now = datetime.now()
        weekday = WEEKDAYS_RU[now.weekday()]
        month = MONTHS_RU_GEN[now.month - 1]

        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=f"{weekday}, {now.day} {month} {now.year}"
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

    def go_today(self):
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.build_calendar()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatrixShiftCalendar(root)
    root.mainloop()
