import tkinter as tk
from tkinter import messagebox
import calendar
import json
import os
import sys
from datetime import datetime, date
import holidays


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(get_base_dir(), "shifts.json")

DEFAULT_CONFIG = {
    "_info1": "Фамилии, даты, цвета, размеры — всё здесь. После правки нажми ОБНОВИТЬ в программе.",
    "_info2": "start_date: начало цикла (ГГГГ-ММ-ДД). shift_days: сколько дней подряд работает смена (3 для 3/3).",
    "_info3": "names_in_column: true — фамилии столбиком, false — в строку через запятую.",
    "_info4": "ЦВЕТА СМЕН: у каждой смены поле 'color'. Примеры: #ff9500 (оранжевый), #00bfff (голубой), #ffcc00 (жёлтый).",
    "start_date": "2026-01-01",
    "shift_days": 3,
    "names_in_column": True,
    "teams": [
        {
            "name": "Смена 1",
            "color": "#00ff41",
            "members": ["Иванов И.", "Петров П.", "Сидоров С.", "Морозов М."]
        },
        {
            "name": "Смена 2",
            "color": "#00bfff",
            "members": ["Кузнецов К.", "Смирнов С.", "Волков В.", "Соколов С."]
        }
    ],
    "ui": {
        "window_width": 1100,
        "window_height": 900,
        "min_width": 800,
        "min_height": 650,
        "cell_min_height": 70,
        "font_day": 16,
        "font_holiday": 9,
        "font_names": 8,
        "font_clock": 26,
        "font_date": 11,
        "font_title": 16,
        "font_head": 10,
        "font_info": 10
    }
}

DEFAULT_UI = DEFAULT_CONFIG["ui"]


def load_config():
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
        self.root.configure(bg=BG)

        self.load_settings()
        self.apply_fonts()

        self.root.geometry(f"{self.ui['window_width']}x{self.ui['window_height']}")
        self.root.minsize(self.ui["min_width"], self.ui["min_height"])
        self.root.resizable(True, True)

        now = datetime.now()
        self.year, self.month = now.year, now.month

        # === Верхняя панель ===
        top = tk.Frame(root, bg=BG)
        top.pack(side="top", fill="x", padx=10, pady=(6, 2))

        nav_btn_style = {
            "font": ("Consolas", 12, "bold"),
            "bg": BG, "fg": GREEN,
            "bd": 0, "relief": "flat",
            "highlightthickness": 1,
            "highlightbackground": GREEN_DIM,
            "cursor": "hand2",
            "activebackground": GREEN_DRK,
            "activeforeground": GREEN_BRT,
            "width": 2, "padx": 2, "pady": 0,
        }
        tk.Button(top, text="◀", command=self.prev_month,
                  **nav_btn_style).pack(side="left")

        self.title_label = tk.Label(top, font=self.FONT_TITLE,
                                    bg=BG, fg=GREEN)
        self.title_label.pack(side="left", expand=True)

        tk.Button(top, text="▶", command=self.next_month,
                  **nav_btn_style).pack(side="right")

        # === Панель кнопок ===
        toolbar = tk.Frame(root, bg=BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=(0, 4))

        btn_small = {
            "font": ("Consolas", 9, "bold"),
            "bg": BG, "fg": GREEN_DIM, "bd": 0, "relief": "flat",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "padx": 8, "pady": 1, "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT
        }
        tk.Button(toolbar, text="ОБНОВИТЬ", command=self.reload_config,
                  **btn_small).pack(side="left", padx=2)
        tk.Button(toolbar, text="ОТКРЫТЬ SHIFTS.JSON", command=self.open_config,
                  **btn_small).pack(side="left", padx=2)
        tk.Button(toolbar, text="СЕГОДНЯ", command=self.go_today,
                  **btn_small).pack(side="right", padx=2)

        # === Часы и информация — прижаты к низу ===
        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(side="bottom", fill="x", pady=(0, 8))

        self.time_label = tk.Label(clock_frame, font=self.FONT_CLOCK,
                                   bg=BG, fg=GREEN)
        self.time_label.pack()

        self.date_label = tk.Label(clock_frame, font=self.FONT_DATE,
                                   bg=BG, fg=GREEN_DIM)
        self.date_label.pack()

        self.today_info = tk.Label(
            root, text="", font=self.FONT_INFO, bg=BG, fg=GREEN_BRT,
            wraplength=1000, justify="center"
        )
        self.today_info.pack(side="bottom", fill="x", pady=(0, 4))

        # === Шапка дней недели ===
        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(side="top", fill="x", padx=10, pady=(4, 0))

        days_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days_short):
            tk.Label(self.head_frame, text=d, font=self.FONT_HEAD,
                     bg=GREEN_DRK, fg=GREEN_BRT, pady=3
                     ).grid(row=0, column=i, sticky="nsew")
            self.head_frame.grid_columnconfigure(i, weight=1)

        # === Сетка календаря ===
        self.grid_frame = tk.Frame(root, bg=GREEN_DIM)
        self.grid_frame.pack(side="top", fill="both", expand=True,
                             padx=10, pady=(0, 4))

        self.build_calendar()
        self.update_clock()

    # ============ Настройки ============
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

        self.names_in_column = bool(self.config.get("names_in_column", True))

        ui = self.config.get("ui", {}) or {}
        self.ui = {**DEFAULT_UI, **ui}

    def apply_fonts(self):
        u = self.ui
        self.FONT_DAY   = ("Consolas", int(u["font_day"]), "bold")
        self.FONT_HOL   = ("Consolas", int(u["font_holiday"]), "bold")
        self.FONT_NAME  = ("Consolas", int(u["font_names"]))
        self.FONT_TITLE = ("Consolas", int(u["font_title"]), "bold")
        self.FONT_HEAD  = ("Consolas", int(u["font_head"]), "bold")
        self.FONT_CLOCK = ("Consolas", int(u["font_clock"]), "bold")
        self.FONT_DATE  = ("Consolas", int(u["font_date"]), "bold")
        self.FONT_INFO  = ("Consolas", int(u["font_info"]), "bold")

    def get_team_for_date(self, target_date):
        if not self.teams or self.shift_days < 1:
            return None
        cycle = self.shift_days * len(self.teams)
        delta = (target_date - self.start_date).days
        pos = delta % cycle
        return self.teams[pos // self.shift_days]

    def reload_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = f.read()
            new_cfg = json.loads(raw)
        except FileNotFoundError:
            messagebox.showerror("ОШИБКА", f"Не найден файл:\n{CONFIG_FILE}")
            return
        except json.JSONDecodeError as e:
            messagebox.showerror(
                "ОШИБКА JSON",
                f"В файле shifts.json опечатка:\n\n{e}\n\n"
                f"Проверь запятые и кавычки."
            )
            return

        self.config = new_cfg
        try:
            self.start_date = datetime.strptime(
                self.config["start_date"], "%Y-%m-%d"
            ).date()
        except Exception:
            self.start_date = date(2026, 1, 1)

        self.shift_days = int(self.config.get("shift_days", 3))
        self.teams = self.config.get("teams", []) or DEFAULT_CONFIG["teams"]
        self.names_in_column = bool(self.config.get("names_in_column", True))

        ui_from_file = self.config.get("ui", {}) or {}
        self.ui = {**DEFAULT_UI, **ui_from_file}
        self.apply_fonts()

        self.title_label.config(font=self.FONT_TITLE)
        self.today_info.config(font=self.FONT_INFO)
        self.time_label.config(font=self.FONT_CLOCK)
        self.date_label.config(font=self.FONT_DATE)
        for w in self.head_frame.winfo_children():
            w.config(font=self.FONT_HEAD)

        self.root.geometry(
            f"{self.ui['window_width']}x{self.ui['window_height']}"
        )
        self.root.minsize(self.ui["min_width"], self.ui["min_height"])

        self.build_calendar()
        self.root.update_idletasks()

        teams_info = "\n".join(
            [f"  • {t['name']}: {t['color']} — {len(t['members'])} чел."
             for t in self.teams]
        )
        mode = "столбиком" if self.names_in_column else "в строку"

        messagebox.showinfo(
            "НАСТРОЙКИ ОБНОВЛЕНЫ",
            f"Файл: {CONFIG_FILE}\n\n"
            f"Смен: {len(self.teams)}\n{teams_info}\n\n"
            f"Фамилии: {mode}\n"
            f"Начало цикла: {self.start_date}\n"
            f"Длина смены: {self.shift_days} дн.\n\n"
            f"Шрифт фамилий: {self.ui['font_names']}\n"
            f"Высота ячейки: {self.ui['cell_min_height']}"
        )

    def open_config(self):
        if not os.path.exists(CONFIG_FILE):
            load_config()
        try:
            os.startfile(CONFIG_FILE)
        except Exception as e:
            print("Не удалось открыть файл:", e)

    # ============ Календарь ============
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
            self.grid_frame.grid_rowconfigure(
                row, weight=1, minsize=self.ui["cell_min_height"])
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
                bg = BG_CELL

                cell = tk.Frame(cell_border, bg=bg)
                cell.pack(fill="both", expand=True)

                # === ВЕРХНЯЯ СТРОКА: число + праздник справа ===
                head = tk.Frame(cell, bg=bg)
                head.pack(fill="x", pady=(2, 0))

                if is_today:
                    # Сегодня — число на цветной плашке
                    day_label = tk.Label(
                        head, text=str(day), font=self.FONT_DAY,
                        bg=team_color, fg=BG, padx=4
                    )
                else:
                    day_fg = RED if hol_name else team_color
                    day_label = tk.Label(
                        head, text=str(day), font=self.FONT_DAY,
                        bg=bg, fg=day_fg
                    )
                day_label.pack(side="left", padx=(5, 3))

                # === Название праздника — СПРАВА от числа ===
                if hol_name:
                    short = hol_name if len(hol_name) <= 22 else hol_name[:20] + "…"
                    tk.Label(
                        head, text=short, font=self.FONT_HOL,
                        bg=bg, fg=RED, anchor="w"
                    ).pack(side="left", fill="x", expand=True, padx=(0, 4))

                # === Фамилии под числом ===
                if team:
                    if self.names_in_column:
                        names_text = "\n".join(team["members"])
                    else:
                        names_text = ", ".join(team["members"])

                    tk.Label(
                        cell, text=names_text, font=self.FONT_NAME,
                        bg=bg, fg=team_color,
                        wraplength=200, justify="left", anchor="nw"
                    ).pack(padx=5, pady=(1, 2), anchor="nw",
                           fill="both", expand=True)

        self.update_today_info()

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
