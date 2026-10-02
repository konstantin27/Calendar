import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
import calendar
import json
import os
import sys
import subprocess
from datetime import datetime, date, timedelta
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
    "_info4": "ЦВЕТА СМЕН: у каждой смены поле 'color'. Примеры: #ff9500, #00bfff, #ffcc00.",
    "_info5": "КЛАВИАТУРА: ←/→ листать месяцы, Enter — сегодня, F11 — полный экран, Esc — выход из него.",
    "_info6": "today_border_width: толщина красной рамки (не влияет на размер содержимого ячейки).",
    "_info7": "fullscreen_on_start: true — окно открывается сразу в полноэкранном режиме без рамки Windows.",
    "_info8": "ОТПУСКА: блок 'vacations' — фамилия → список периодов ['ГГГГ-ММ-ДД', 'ГГГГ-ММ-ДД']. Фамилия в отпуске перечёркивается и становится серой.",
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
    "vacations": {
        "Иванов И.": [["2026-06-01", "2026-06-14"]],
        "Кузнецов К.": [["2026-07-15", "2026-07-28"]]
    },
    "ui": {
        "window_width": 1100,
        "window_height": 900,
        "min_width": 800,
        "min_height": 650,
        "cell_min_height": 90,
        "font_day": 16,
        "font_holiday": 9,
        "font_names": 9,
        "font_clock": 26,
        "font_date": 11,
        "font_title": 16,
        "font_head": 10,
        "today_border_width": 3,
        "other_month_dim": 0.55,
        "fullscreen_on_start": False,
        "vacation_color": "#555555"
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


def dim_hex(hex_color, factor=0.55):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


# === Матричная палитра ===
BG          = "#000000"
BG_CELL     = "#050505"
GREEN       = "#00ff41"
GREEN_BRT   = "#7fff7f"
GREEN_DIM   = "#008f11"
GREEN_DRK   = "#003b00"
RED         = "#ff3333"
OTHER_MONTH = "#005500"
VACATION    = "#555555"

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

        self.is_fullscreen = False
        self.follow_today = True
        self.last_today = date.today()

        self.root.bind("<Left>",     self.key_prev_month)
        self.root.bind("<Right>",    self.key_next_month)
        self.root.bind("<Return>",   self.key_today)
        self.root.bind("<KP_Enter>", self.key_today)
        self.root.bind("<F11>",      self.toggle_fullscreen)
        self.root.bind("<Escape>",   self.exit_fullscreen)

        self.root.focus_set()

        now = datetime.now()
        self.year, self.month = now.year, now.month

        # === ВЕРХНЯЯ ПАНЕЛЬ ===
        top = tk.Frame(root, bg=BG)
        top.pack(side="top", fill="x", padx=8, pady=(5, 2))

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
        btn_small = {
            "font": ("Consolas", 8, "bold"),
            "bg": BG, "fg": GREEN_DIM, "bd": 0, "relief": "flat",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "padx": 5, "pady": 0, "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT
        }

        tk.Button(top, text="◀", command=self.prev_month,
                  **nav_btn_style).pack(side="left")
        tk.Button(top, text="ОБН", command=self.reload_config,
                  **btn_small).pack(side="left", padx=(3, 1))
        tk.Button(top, text="JSON", command=self.open_config,
                  **btn_small).pack(side="left", padx=(0, 1))
        tk.Button(top, text="⛶", command=self.toggle_fullscreen,
                  **btn_small).pack(side="left", padx=(0, 3))

        tk.Button(top, text="▶", command=self.next_month,
                  **nav_btn_style).pack(side="right")
        tk.Button(top, text="СЕГОДНЯ", command=self.go_today,
                  **btn_small).pack(side="right", padx=(0, 3))

        self.title_label = tk.Label(top, font=self.FONT_TITLE,
                                    bg=BG, fg=GREEN)
        self.title_label.pack(side="left", expand=True)

        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(side="bottom", fill="x", pady=(4, 8))

        self.time_label = tk.Label(clock_frame, font=self.FONT_CLOCK,
                                   bg=BG, fg=GREEN)
        self.time_label.pack()

        self.date_label = tk.Label(clock_frame, font=self.FONT_DATE,
                                   bg=BG, fg=GREEN_DIM)
        self.date_label.pack()

        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(side="top", fill="x", padx=8, pady=(3, 0))

        days_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days_short):
            tk.Label(self.head_frame, text=d, font=self.FONT_HEAD,
                     bg=GREEN_DRK, fg=GREEN_BRT,
                     anchor="center", justify="center"
                     ).grid(row=0, column=i, sticky="nsew", padx=1, pady=2)
            self.head_frame.grid_columnconfigure(i, weight=1, uniform="days")

        self.grid_frame = tk.Frame(root, bg=GREEN_DIM)
        self.grid_frame.pack(side="top", fill="both", expand=True,
                             padx=8, pady=(0, 3))

        self.build_calendar()
        self.update_clock()

        if self.ui.get("fullscreen_on_start", False):
            self.root.after(200, self._initial_fullscreen)

    def _initial_fullscreen(self):
        self.is_fullscreen = True
        self.root.attributes("-fullscreen", True)
        self.root.focus_set()
        # ★ Перестроить после того, как окно реально развернулось
        self.root.after(400, self._rebuild_calendar_safe)

    def _rebuild_calendar_safe(self):
        """Перестраивает календарь с гарантией, что размеры окна актуальны."""
        try:
            self.root.update_idletasks()
            self.build_calendar()
            self.root.update_idletasks()
        except Exception:
            pass

    # ============ Клавиатура ============
    def key_prev_month(self, event=None):
        self.prev_month()
        return "break"

    def key_next_month(self, event=None):
        self.next_month()
        return "break"

    def key_today(self, event=None):
        self.go_today()
        return "break"

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        self.root.focus_set()
        # ★ Перестроить через 400 мс — окно успевает войти в новый режим
        self.root.after(400, self._rebuild_calendar_safe)
        return "break"

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.root.after(400, self._rebuild_calendar_safe)
        return "break"

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

        self.vacations = {}
        raw_vac = self.config.get("vacations", {}) or {}
        for name, periods in raw_vac.items():
            parsed = []
            for p in periods:
                try:
                    s = datetime.strptime(p[0], "%Y-%m-%d").date()
                    e = datetime.strptime(p[1], "%Y-%m-%d").date()
                    parsed.append((s, e))
                except Exception:
                    pass
            self.vacations[name] = parsed

        ui = self.config.get("ui", {}) or {}
        self.ui = {**DEFAULT_UI, **ui}

    def apply_fonts(self):
        u = self.ui
        self.FONT_DAY   = ("Consolas", int(u["font_day"]), "bold")
        self.FONT_HOL   = ("Consolas", int(u["font_holiday"]), "bold")

        size = int(u["font_names"])

        self.FONT_NAME = tkfont.Font(
            family="Consolas", size=size, weight="normal"
        )
        try:
            self.FONT_NAME.configure(linespace=max(0, size - 2))
        except Exception:
            pass

        self.FONT_NAME_STRIKE = tkfont.Font(
            family="Consolas", size=size, weight="normal", overstrike=1
        )
        try:
            self.FONT_NAME_STRIKE.configure(linespace=max(0, size - 2))
        except Exception:
            pass

        self.FONT_TITLE = ("Consolas", int(u["font_title"]), "bold")
        self.FONT_HEAD  = ("Consolas", int(u["font_head"]), "bold")
        self.FONT_CLOCK = ("Consolas", int(u["font_clock"]), "bold")
        self.FONT_DATE  = ("Consolas", int(u["font_date"]), "bold")

    def get_team_for_date(self, target_date):
        if not self.teams or self.shift_days < 1:
            return None
        cycle = self.shift_days * len(self.teams)
        delta = (target_date - self.start_date).days
        pos = delta % cycle
        return self.teams[pos // self.shift_days]

    def is_on_vacation(self, name, target_date):
        periods = self.vacations.get(name, [])
        for start, end in periods:
            if start <= target_date <= end:
                return True
        return False

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

        self.vacations = {}
        raw_vac = self.config.get("vacations", {}) or {}
        for name, periods in raw_vac.items():
            parsed = []
            for p in periods:
                try:
                    s = datetime.strptime(p[0], "%Y-%m-%d").date()
                    e = datetime.strptime(p[1], "%Y-%m-%d").date()
                    parsed.append((s, e))
                except Exception:
                    pass
            self.vacations[name] = parsed

        ui_from_file = self.config.get("ui", {}) or {}
        self.ui = {**DEFAULT_UI, **ui_from_file}
        self.apply_fonts()

        self.title_label.config(font=self.FONT_TITLE)
        self.time_label.config(font=self.FONT_CLOCK)
        self.date_label.config(font=self.FONT_DATE)
        for w in self.head_frame.winfo_children():
            w.config(font=self.FONT_HEAD)

        self.root.geometry(
            f"{self.ui['window_width']}x{self.ui['window_height']}"
        )
        self.root.minsize(self.ui["min_width"], self.ui["min_height"])

        want_fs = bool(self.ui.get("fullscreen_on_start", False))
        if want_fs != self.is_fullscreen:
            self.is_fullscreen = want_fs
            self.root.attributes("-fullscreen", want_fs)

        self.root.after(200, self._rebuild_calendar_safe)
        self.root.update_idletasks()

        teams_info = "\n".join(
            [f"  • {t['name']}: {t['color']} — {len(t['members'])} чел."
             for t in self.teams]
        )
        vac_info = f"Отпусков: {len(self.vacations)} чел." if self.vacations else "Отпусков нет"
        mode = "столбиком" if self.names_in_column else "в строку"

        messagebox.showinfo(
            "НАСТРОЙКИ ОБНОВЛЕНЫ",
            f"Файл: {CONFIG_FILE}\n\n"
            f"Смен: {len(self.teams)}\n{teams_info}\n\n"
            f"{vac_info}\n"
            f"Фамилии: {mode}\n"
            f"Начало цикла: {self.start_date}\n"
            f"Длина смены: {self.shift_days} дн."
        )

    def open_config(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    messagebox.showerror(
                        "ОШИБКА",
                        f"Не удалось создать файл:\n{CONFIG_FILE}\n\n{e}"
                    )
                    return

            try:
                os.startfile(CONFIG_FILE)
                return
            except Exception:
                pass

            try:
                subprocess.Popen(["notepad.exe", CONFIG_FILE])
                return
            except Exception as e2:
                messagebox.showerror(
                    "ОШИБКА",
                    f"Не удалось открыть файл:\n{CONFIG_FILE}\n\n"
                    f"Попробуй открыть его вручную из папки с программой.\n\n"
                    f"Ошибка: {e2}"
                )
        except Exception as e:
            messagebox.showerror("ОШИБКА", f"Что-то пошло не так:\n{e}")

    # ============ Календарь ============
    def build_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.title_label.config(
            text=f"{MONTHS_RU_NOM[self.month-1]} {self.year}"
        )

        today = date.today()

        first_day = date(self.year, self.month, 1)
        if self.month == 12:
            first_day_next = date(self.year + 1, 1, 1)
        else:
            first_day_next = date(self.year, self.month + 1, 1)
        days_in_month = (first_day_next - first_day).days

        first_weekday = first_day.weekday()
        bw = int(self.ui.get("today_border_width", 3))

        for row in range(6):
            self.grid_frame.grid_rowconfigure(
                row, weight=1, minsize=self.ui["cell_min_height"])
            for col in range(7):
                self.grid_frame.grid_columnconfigure(
                    col, weight=1, uniform="days")

                idx = row * 7 + col

                if idx < first_weekday:
                    cell_date = first_day - timedelta(days=first_weekday - idx)
                    self._draw_day(row, col, cell_date, today, bw,
                                   is_other_month=True)
                elif idx < first_weekday + days_in_month:
                    cell_date = date(
                        self.year, self.month, idx - first_weekday + 1)
                    self._draw_day(row, col, cell_date, today, bw,
                                   is_other_month=False)
                else:
                    cell_date = first_day + timedelta(days=idx - first_weekday)
                    self._draw_day(row, col, cell_date, today, bw,
                                   is_other_month=True)

    def _draw_day(self, row, col, cell_date, today, bw, is_other_month):
        hol_name = RU_HOLIDAYS.get(cell_date)
        team = self.get_team_for_date(cell_date)

        is_today = (cell_date == today) and not is_other_month
        bg = BG_CELL
        dim_factor = float(self.ui.get("other_month_dim", 0.55))
        vac_color = self.ui.get("vacation_color", VACATION)

        cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
        cell_border.grid(row=row, column=col,
                         padx=1, pady=1, sticky="nsew")

        cell = tk.Frame(cell_border, bg=bg)
        cell.pack(fill="both", expand=True)

        inner = tk.Frame(cell, bg=bg)
        inner.pack(fill="both", expand=True, padx=3, pady=0)

        head = tk.Frame(inner, bg=bg)
        head.pack(fill="x", pady=0)
        head.grid_columnconfigure(0, weight=1)
        head.grid_columnconfigure(1, weight=0)
        head.grid_columnconfigure(2, weight=1)

        tk.Label(head, text="", bg=bg).grid(row=0, column=0, sticky="nsew")

        if is_other_month:
            if hol_name:
                day_fg = dim_hex(RED, dim_factor)
            elif team:
                day_fg = dim_hex(team["color"], dim_factor)
            else:
                day_fg = OTHER_MONTH
        else:
            if hol_name:
                day_fg = RED
            else:
                day_fg = team["color"] if team else GREEN_DIM

        tk.Label(
            head, text=str(cell_date.day), font=self.FONT_DAY,
            bg=bg, fg=day_fg
        ).grid(row=0, column=1)

        if hol_name:
            short = hol_name if len(hol_name) <= 16 else hol_name[:14] + "…"
            hol_fg = dim_hex(RED, dim_factor) if is_other_month else RED
            tk.Label(
                head, text=short, font=self.FONT_HOL,
                bg=bg, fg=hol_fg, anchor="e"
            ).grid(row=0, column=2, sticky="e", padx=(0, 4))

        # === ФАМИЛИИ ===
        if team:
            base_color = (dim_hex(team["color"], dim_factor)
                          if is_other_month else team["color"])
            vac_color_use = (dim_hex(vac_color, dim_factor)
                             if is_other_month else vac_color)

            if self.names_in_column:
                for member in team["members"]:
                    on_vac = self.is_on_vacation(member, cell_date)
                    if on_vac:
                        tk.Label(
                            inner, text=member,
                            font=self.FONT_NAME_STRIKE,
                            bg=bg, fg=vac_color_use,
                            anchor="n"
                        ).pack(anchor="n", fill="x")
                    else:
                        tk.Label(
                            inner, text=member,
                            font=self.FONT_NAME,
                            bg=bg, fg=base_color,
                            anchor="n"
                        ).pack(anchor="n", fill="x")
            else:
                any_vac = any(
                    self.is_on_vacation(m, cell_date) for m in team["members"]
                )
                names_text = ", ".join(team["members"])
                if any_vac:
                    tk.Label(
                        inner, text=names_text,
                        font=self.FONT_NAME_STRIKE,
                        bg=bg, fg=vac_color_use,
                        wraplength=250, justify="center", anchor="n"
                    ).pack(pady=0, anchor="n", fill="both", expand=True)
                else:
                    tk.Label(
                        inner, text=names_text,
                        font=self.FONT_NAME,
                        bg=bg, fg=base_color,
                        wraplength=250, justify="center", anchor="n"
                    ).pack(pady=0, anchor="n", fill="both", expand=True)

        if is_today:
            self._draw_today_frame(cell, bw)

    def _draw_today_frame(self, parent, bw):
        tk.Frame(parent, bg=RED, height=bw).place(x=0, y=0, relwidth=1)
        tk.Frame(parent, bg=RED, height=bw).place(
            x=0, rely=1.0, y=-bw, relwidth=1)
        tk.Frame(parent, bg=RED, width=bw).place(
            x=0, y=0, relheight=1)
        tk.Frame(parent, bg=RED, width=bw).place(
            relx=1.0, x=-bw, y=0, relheight=1)

    # ============ Часы ============
    def update_clock(self):
        now = datetime.now()
        today_now = now.date()

        weekday = WEEKDAYS_RU[now.weekday()]
        month = MONTHS_RU_GEN[now.month - 1]

        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=f"{weekday}, {now.day} {month} {now.year}"
        )

        day_changed = (today_now != self.last_today)
        month_changed = (self.year, self.month) != (today_now.year, today_now.month)

        if day_changed or (self.follow_today and month_changed):
            if self.follow_today:
                self.year, self.month = today_now.year, today_now.month
            self.last_today = today_now
            self.build_calendar()

        self.root.after(1000, self.update_clock)

    # ============ Навигация ============
    def prev_month(self):
        self.follow_today = False
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.build_calendar()

    def next_month(self):
        self.follow_today = False
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.build_calendar()

    def go_today(self):
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.follow_today = True
        self.last_today = now.date()
        self.build_calendar()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatrixShiftCalendar(root)
    root.mainloop()
