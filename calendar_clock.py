import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as tkfont
import calendar
import json
import os
import sys
import subprocess
import copy
from datetime import datetime, date, timedelta
import holidays


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(get_base_dir(), "shifts.json")

DEFAULT_CONFIG = {
    "_info1": "Этот файл можно редактировать через окно НАСТРОЙКИ в программе.",
    "_info2": "start_date: начало цикла. shift_days: сколько дней работает смена (3 для 3/3).",
    "_info3": "names_in_column: true — фамилии столбиком.",
    "_info4": "vacations: фамилия → список периодов [['ГГГГ-ММ-ДД','ГГГГ-ММ-ДД'], ...]",
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
        "cell_min_height": 70,
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


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Ошибка сохранения:", e)
        return False


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
BG_PANEL    = "#0a0a0a"
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


# ================================================================
# ОКНО НАСТРОЕК
# ================================================================
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        self.cfg = copy.deepcopy(config)

        self.title("НАСТРОЙКИ")
        self.configure(bg=BG)
        self.geometry("900x760")
        self.minsize(750, 600)
        self.transient(parent)
        self.grab_set()

        # Стили ttk
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL,
                        foreground=GREEN_DIM, padding=[15, 6],
                        font=("Consolas", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", GREEN_BRT)])
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=GREEN_BRT,
                        font=("Consolas", 10))
        style.configure("TEntry", fieldbackground=BG_PANEL,
                        foreground=GREEN_BRT, insertcolor=GREEN)
        style.configure("TCombobox", fieldbackground=BG_PANEL,
                        background=BG_PANEL, foreground=GREEN_BRT,
                        arrowcolor=GREEN)
        style.map("TCombobox",
                  fieldbackground=[("readonly", BG_PANEL)],
                  foreground=[("readonly", GREEN_BRT)])

        # Заголовок
        tk.Label(self, text="⚙  НАСТРОЙКИ", font=("Consolas", 16, "bold"),
                 bg=BG, fg=GREEN).pack(pady=(10, 5))

        # Вкладки
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # Вкладки
        self.tab_main = tk.Frame(self.notebook, bg=BG)
        self.tab_teams = tk.Frame(self.notebook, bg=BG)
        self.tab_vac = tk.Frame(self.notebook, bg=BG)
        self.tab_ui = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_main, text="  Основные  ")
        self.notebook.add(self.tab_teams, text="  Смены  ")
        self.notebook.add(self.tab_vac, text="  Отпуска  ")
        self.notebook.add(self.tab_ui, text="  Внешний вид  ")

        self._build_tab_main()
        self._build_tab_teams()
        self._build_tab_vacations()
        self._build_tab_ui()

        # Кнопки внизу
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        btn_style = {
            "font": ("Consolas", 11, "bold"),
            "bg": BG_PANEL, "fg": GREEN_BRT,
            "bd": 1, "relief": "solid",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT,
            "padx": 20, "pady": 6, "cursor": "hand2"
        }
        tk.Button(btn_frame, text="✔  СОХРАНИТЬ", command=self._save,
                  **btn_style).pack(side="right", padx=5)
        tk.Button(btn_frame, text="✖  ОТМЕНА", command=self.destroy,
                  **btn_style).pack(side="right", padx=5)

        self.bind("<Escape>", lambda e: self.destroy())

    # ---------- Вкладка "Основные" ----------
    def _build_tab_main(self):
        f = self.tab_main

        tk.Label(f, text="Дата начала цикла (любая дата, когда работала Смена 1):",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(20, 3))
        self.e_start = tk.Entry(f, font=("Consolas", 11),
                                bg=BG_PANEL, fg=GREEN_BRT,
                                insertbackground=GREEN, width=20)
        self.e_start.pack(anchor="w", padx=20)
        self.e_start.insert(0, str(self.cfg.get("start_date", "2026-01-01")))

        tk.Label(f, text="Формат: ГГГГ-ММ-ДД (например, 2026-01-01)",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(2, 15))

        tk.Label(f, text="Сколько дней работает одна смена (для 3/3 это 3):",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(0, 3))
        self.e_days = tk.Entry(f, font=("Consolas", 11),
                               bg=BG_PANEL, fg=GREEN_BRT,
                               insertbackground=GREEN, width=10)
        self.e_days.pack(anchor="w", padx=20)
        self.e_days.insert(0, str(self.cfg.get("shift_days", 3)))

        tk.Label(f, text="Фамилии в ячейке:",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(20, 3))
        self.v_col = tk.BooleanVar(value=bool(self.cfg.get("names_in_column", True)))
        tk.Radiobutton(f, text="Столбиком (каждая фамилия на своей строке)",
                       variable=self.v_col, value=True,
                       font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                       selectcolor=BG_PANEL, activebackground=BG,
                       activeforeground=GREEN_BRT
                       ).pack(anchor="w", padx=30)
        tk.Radiobutton(f, text="В строку через запятую",
                       variable=self.v_col, value=False,
                       font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                       selectcolor=BG_PANEL, activebackground=BG,
                       activeforeground=GREEN_BRT
                       ).pack(anchor="w", padx=30)

    # ---------- Вкладка "Смены" ----------
    def _build_tab_teams(self):
        f = self.tab_teams

        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(top, text="Смены и их работники:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(side="left")

        tk.Button(top, text="+ Добавить смену", command=self._add_team,
                  font=("Consolas", 10, "bold"),
                  bg=BG_PANEL, fg=GREEN_BRT, bd=1, relief="solid",
                  highlightthickness=1, highlightbackground=GREEN_DIM,
                  padx=10, pady=3, cursor="hand2"
                  ).pack(side="right")

        # Скроллируемая область
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self.teams_frame = tk.Frame(canvas, bg=BG)

        canvas.create_window((0, 0), window=self.teams_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=5)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=5)

        self.teams_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._render_teams()

    def _render_teams(self):
        for w in self.teams_frame.winfo_children():
            w.destroy()

        for i, team in enumerate(self.cfg.get("teams", [])):
            self._render_one_team(i, team)

    def _render_one_team(self, idx, team):
        card = tk.Frame(self.teams_frame, bg=BG_PANEL,
                        highlightthickness=1, highlightbackground=GREEN_DIM)
        card.pack(fill="x", pady=5, padx=5)

        # Заголовок смены
        head = tk.Frame(card, bg=BG_PANEL)
        head.pack(fill="x", padx=8, pady=(8, 3))

        tk.Label(head, text=f"Смена #{idx + 1}", font=("Consolas", 10, "bold"),
                 bg=BG_PANEL, fg=GREEN).pack(side="left")

        tk.Button(head, text="🗑 Удалить", command=lambda i=idx: self._del_team(i),
                  font=("Consolas", 9), bg=BG_PANEL, fg=RED,
                  bd=0, relief="flat", activebackground=BG,
                  activeforeground="#ff8888", cursor="hand2"
                  ).pack(side="right")

        # Название
        row1 = tk.Frame(card, bg=BG_PANEL)
        row1.pack(fill="x", padx=8, pady=3)
        tk.Label(row1, text="Название:", font=("Consolas", 10),
                 bg=BG_PANEL, fg=GREEN_BRT, width=11, anchor="w").pack(side="left")
        e_name = tk.Entry(row1, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN)
        e_name.pack(side="left", fill="x", expand=True)
        e_name.insert(0, team.get("name", ""))

        def _upd_name(e, i=idx, entry=e_name):
            try:
                self.cfg["teams"][i]["name"] = entry.get()
            except Exception:
                pass
        e_name.bind("<KeyRelease>", _upd_name)

        # Цвет
        row2 = tk.Frame(card, bg=BG_PANEL)
        row2.pack(fill="x", padx=8, pady=3)
        tk.Label(row2, text="Цвет:", font=("Consolas", 10),
                 bg=BG_PANEL, fg=GREEN_BRT, width=11, anchor="w").pack(side="left")
        e_color = tk.Entry(row2, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                           insertbackground=GREEN, width=12)
        e_color.pack(side="left")
        e_color.insert(0, team.get("color", "#00ff41"))

        color_preview = tk.Label(row2, text="   ", bg=team.get("color", "#00ff41"))
        color_preview.pack(side="left", padx=5)

        tk.Label(row2, text="(HEX-код, например #ff9500)",
                 font=("Consolas", 9), bg=BG_PANEL, fg=GREEN_DIM
                 ).pack(side="left", padx=5)

        def _upd_color(e, i=idx, entry=e_color, prev=color_preview):
            val = entry.get().strip()
            try:
                self.cfg["teams"][i]["color"] = val
                prev.config(bg=val)
            except Exception:
                pass
        e_color.bind("<KeyRelease>", _upd_color)

        # Фамилии
        tk.Label(card, text="Работники:", font=("Consolas", 10),
                 bg=BG_PANEL, fg=GREEN_BRT, anchor="w"
                 ).pack(fill="x", padx=8, pady=(8, 2))

        members_frame = tk.Frame(card, bg=BG_PANEL)
        members_frame.pack(fill="x", padx=8, pady=2)

        for j, member in enumerate(team.get("members", [])):
            self._render_member(members_frame, idx, j, member)

        tk.Button(card, text="+ Фамилия",
                  command=lambda i=idx: self._add_member(i),
                  font=("Consolas", 9, "bold"),
                  bg=BG, fg=GREEN_BRT, bd=1, relief="solid",
                  highlightthickness=1, highlightbackground=GREEN_DIM,
                  padx=8, pady=2, cursor="hand2"
                  ).pack(anchor="w", padx=8, pady=(3, 8))

    def _render_member(self, parent, team_idx, member_idx, member):
        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill="x", pady=1)

        e = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                     insertbackground=GREEN)
        e.pack(side="left", fill="x", expand=True)
        e.insert(0, member)

        def _upd(e2=e, t=team_idx, m=member_idx):
            try:
                self.cfg["teams"][t]["members"][m] = e2.get()
            except Exception:
                pass
        e.bind("<KeyRelease>", _upd)

        tk.Button(row, text="✖",
                  command=lambda t=team_idx, m=member_idx: self._del_member(t, m),
                  font=("Consolas", 10, "bold"),
                  bg=BG_PANEL, fg=RED, bd=0, relief="flat",
                  activebackground=BG, activeforeground="#ff8888",
                  padx=6, cursor="hand2"
                  ).pack(side="right")

    def _add_team(self):
        self.cfg.setdefault("teams", []).append({
            "name": f"Смена {len(self.cfg.get('teams', [])) + 1}",
            "color": "#ffcc00",
            "members": ["Новый работник"]
        })
        self._render_teams()
        self._render_vacations()

    def _del_team(self, idx):
        if len(self.cfg.get("teams", [])) <= 1:
            messagebox.showwarning("ВНИМАНИЕ", "Нельзя удалить последнюю смену", parent=self)
            return
        if messagebox.askyesno("УДАЛИТЬ СМЕНУ",
                               f"Удалить «{self.cfg['teams'][idx].get('name', '')}»?",
                               parent=self):
            self.cfg["teams"].pop(idx)
            self._render_teams()
            self._render_vacations()

    def _add_member(self, team_idx):
        self.cfg["teams"][team_idx].setdefault("members", []).append("Новый")
        self._render_teams()
        self._render_vacations()

    def _del_member(self, team_idx, member_idx):
        self.cfg["teams"][team_idx]["members"].pop(member_idx)
        self._render_teams()
        self._render_vacations()

    # ---------- Вкладка "Отпуска" ----------
    def _build_tab_vacations(self):
        f = self.tab_vac

        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(top, text="Отпуска работников:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(side="left")

        tk.Button(top, text="+ Добавить отпуск", command=self._add_vacation,
                  font=("Consolas", 10, "bold"),
                  bg=BG_PANEL, fg=GREEN_BRT, bd=1, relief="solid",
                  highlightthickness=1, highlightbackground=GREEN_DIM,
                  padx=10, pady=3, cursor="hand2"
                  ).pack(side="right")

        tk.Label(f, text="Формат даты: ГГГГ-ММ-ДД. Можно добавить несколько периодов одному человеку.",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(0, 5))

        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self.vac_frame = tk.Frame(canvas, bg=BG)

        canvas.create_window((0, 0), window=self.vac_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=5)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=5)

        self.vac_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._render_vacations()

    def _get_all_members(self):
        result = []
        for t in self.cfg.get("teams", []):
            for m in t.get("members", []):
                if m and m not in result:
                    result.append(m)
        return result

    def _render_vacations(self):
        for w in self.vac_frame.winfo_children():
            w.destroy()

        all_members = self._get_all_members()

        # Собираем плоский список: (имя, индекс_периода, дата1, дата2)
        rows = []
        for name, periods in self.cfg.get("vacations", {}).items():
            for i, p in enumerate(periods):
                rows.append((name, i, p[0], p[1]))

        if not rows:
            tk.Label(self.vac_frame, text="Отпусков нет. Нажми «+ Добавить отпуск».",
                     font=("Consolas", 10), bg=BG, fg=GREEN_DIM
                     ).pack(anchor="w", pady=15, padx=5)
            return

        for row_idx, (name, pidx, d1, d2) in enumerate(rows):
            row = tk.Frame(self.vac_frame, bg=BG_PANEL,
                           highlightthickness=1, highlightbackground=GREEN_DIM)
            row.pack(fill="x", pady=3, padx=5)

            tk.Label(row, text="Работник:", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(8, 3), pady=6)

            combo = ttk.Combobox(row, values=all_members, state="readonly",
                                 font=("Consolas", 10), width=18)
            combo.pack(side="left", padx=3, pady=6)
            combo.set(name)

            def _chg_name(event, old=name, pi=pidx, cb=combo):
                new = cb.get()
                if not new or new == old:
                    return
                vacations = self.cfg.setdefault("vacations", {})
                if old in vacations and pi < len(vacations[old]):
                    period = vacations[old].pop(pi)
                    if not vacations[old]:
                        del vacations[old]
                    vacations.setdefault(new, []).append(period)
                    self._render_vacations()
            combo.bind("<<ComboboxSelected>>", _chg_name)

            tk.Label(row, text="с", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(10, 3))

            e1 = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN, width=12)
            e1.pack(side="left", padx=3, pady=6)
            e1.insert(0, d1)

            tk.Label(row, text="по", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(8, 3))

            e2 = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN, width=12)
            e2.pack(side="left", padx=3, pady=6)
            e2.insert(0, d2)

            def _upd_dates(ev=None, n=name, pi=pidx, ee1=e1, ee2=e2):
                try:
                    self.cfg["vacations"][n][pi] = [ee1.get(), ee2.get()]
                except Exception:
                    pass
            e1.bind("<KeyRelease>", _upd_dates)
            e2.bind("<KeyRelease>", _upd_dates)

            tk.Button(row, text="🗑", command=lambda n=name, pi=pidx: self._del_vacation(n, pi),
                      font=("Consolas", 10), bg=BG_PANEL, fg=RED,
                      bd=0, relief="flat", activebackground=BG,
                      activeforeground="#ff8888", padx=8, cursor="hand2"
                      ).pack(side="right", padx=5)

    def _add_vacation(self):
        all_members = self._get_all_members()
        if not all_members:
            messagebox.showwarning("ВНИМАНИЕ",
                                   "Сначала добавь работников на вкладке «Смены»",
                                   parent=self)
            return
        name = all_members[0]
        today = date.today()
        d1 = today.strftime("%Y-%m-%d")
        d2 = (today + timedelta(days=13)).strftime("%Y-%m-%d")
        self.cfg.setdefault("vacations", {}).setdefault(name, []).append([d1, d2])
        self._render_vacations()

    def _del_vacation(self, name, period_idx):
        vacations = self.cfg.get("vacations", {})
        if name in vacations and period_idx < len(vacations[name]):
            vacations[name].pop(period_idx)
            if not vacations[name]:
                del vacations[name]
            self._render_vacations()

    # ---------- Вкладка "Внешний вид" ----------
    def _build_tab_ui(self):
        f = self.tab_ui

        tk.Label(f, text="Размеры окна и шрифтов:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(15, 10))

        # Сетка параметров
        grid = tk.Frame(f, bg=BG)
        grid.pack(fill="x", padx=20)

        params = [
            ("window_width",  "Ширина окна"),
            ("window_height", "Высота окна"),
            ("cell_min_height", "Мин. высота ячейки"),
            ("font_day",      "Размер числа дня"),
            ("font_names",    "Размер фамилий"),
            ("font_holiday",  "Размер праздника"),
            ("font_clock",    "Размер часов"),
            ("font_date",     "Размер даты"),
            ("font_title",    "Размер названия месяца"),
            ("font_head",     "Размер дней недели"),
            ("today_border_width", "Толщина красной рамки"),
            ("other_month_dim", "Приглушение чужого месяца (0–1)"),
        ]

        self.ui_entries = {}
        for i, (key, label) in enumerate(params):
            r = i // 2
            c = (i % 2) * 2

            tk.Label(grid, text=label + ":", font=("Consolas", 10),
                     bg=BG, fg=GREEN_BRT, anchor="w"
                     ).grid(row=r, column=c, sticky="w", padx=(0, 5), pady=3)

            e = tk.Entry(grid, font=("Consolas", 10), bg=BG_PANEL,
                         fg=GREEN_BRT, insertbackground=GREEN, width=8)
            e.grid(row=r, column=c + 1, sticky="w", padx=(0, 25), pady=3)
            e.insert(0, str(self.cfg.get("ui", {}).get(key, DEFAULT_UI.get(key, ""))))
            self.ui_entries[key] = e

        # Цвет отпуска
        tk.Label(f, text="Цвет отпуска (HEX):", font=("Consolas", 10),
                 bg=BG, fg=GREEN_BRT).pack(anchor="w", padx=20, pady=(15, 3))
        color_row = tk.Frame(f, bg=BG)
        color_row.pack(anchor="w", padx=20)
        self.e_vac_color = tk.Entry(color_row, font=("Consolas", 10),
                                    bg=BG_PANEL, fg=GREEN_BRT,
                                    insertbackground=GREEN, width=10)
        self.e_vac_color.pack(side="left")
        self.e_vac_color.insert(0, str(self.cfg.get("ui", {}).get("vacation_color", "#555555")))
        self.vac_color_prev = tk.Label(color_row, text="   ",
                                        bg=self.e_vac_color.get())
        self.vac_color_prev.pack(side="left", padx=5)

        def _upd_vac_color(e=None):
            try:
                self.vac_color_prev.config(bg=self.e_vac_color.get())
            except Exception:
                pass
        self.e_vac_color.bind("<KeyRelease>", _upd_vac_color)

        # Чекбокс "полный экран при запуске"
        self.v_fs = tk.BooleanVar(value=bool(self.cfg.get("ui", {}).get("fullscreen_on_start", False)))
        tk.Checkbutton(f, text="Запускать сразу в полноэкранном режиме",
                       variable=self.v_fs,
                       font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                       selectcolor=BG_PANEL, activebackground=BG,
                       activeforeground=GREEN_BRT
                       ).pack(anchor="w", padx=20, pady=(15, 3))

    # ---------- Сохранение ----------
    def _save(self):
        # Основные
        self.cfg["start_date"] = self.e_start.get().strip()
        try:
            self.cfg["shift_days"] = int(self.e_days.get().strip())
        except Exception:
            messagebox.showerror("ОШИБКА",
                                 "«Длина смены» должна быть числом",
                                 parent=self)
            return

        self.cfg["names_in_column"] = bool(self.v_col.get())

        # UI-параметры
        ui = self.cfg.setdefault("ui", {})
        for key, entry in self.ui_entries.items():
            val = entry.get().strip()
            if not val:
                continue
            try:
                if key in ("other_month_dim",):
                    ui[key] = float(val)
                else:
                    ui[key] = int(val)
            except Exception:
                messagebox.showerror("ОШИБКА",
                                     f"Значение «{key}» должно быть числом",
                                     parent=self)
                return

        ui["vacation_color"] = self.e_vac_color.get().strip()
        ui["fullscreen_on_start"] = bool(self.v_fs.get())

        # Валидация отпусков
        for name, periods in self.cfg.get("vacations", {}).items():
            for p in periods:
                try:
                    datetime.strptime(p[0], "%Y-%m-%d")
                    datetime.strptime(p[1], "%Y-%m-%d")
                except Exception:
                    messagebox.showerror(
                        "ОШИБКА",
                        f"Неверная дата у «{name}»:\n{p[0]} — {p[1]}\n\n"
                        f"Формат: ГГГГ-ММ-ДД",
                        parent=self
                    )
                    return

        # Валидация start_date
        try:
            datetime.strptime(self.cfg["start_date"], "%Y-%m-%d")
        except Exception:
            messagebox.showerror("ОШИБКА",
                                 "Дата начала цикла в формате ГГГГ-ММ-ДД",
                                 parent=self)
            return

        if save_config(self.cfg):
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("ОШИБКА", "Не удалось сохранить файл",
                                 parent=self)


# ================================================================
# ГЛАВНОЕ ОКНО
# ================================================================
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

        # ВЕРХНЯЯ ПАНЕЛЬ
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
            "padx": 6, "pady": 0, "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT
        }

        tk.Button(top, text="◀", command=self.prev_month,
                  **nav_btn_style).pack(side="left")
        tk.Button(top, text="⚙ НАСТРОЙКИ", command=self.open_settings,
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

        # Часы
        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(side="bottom", fill="x", pady=(4, 8))

        self.time_label = tk.Label(clock_frame, font=self.FONT_CLOCK,
                                   bg=BG, fg=GREEN)
        self.time_label.pack()

        self.date_label = tk.Label(clock_frame, font=self.FONT_DATE,
                                   bg=BG, fg=GREEN_DIM)
        self.date_label.pack()

        # Шапка дней недели
        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(side="top", fill="x", padx=8, pady=(3, 0))

        days_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days_short):
            tk.Label(self.head_frame, text=d, font=self.FONT_HEAD,
                     bg=GREEN_DRK, fg=GREEN_BRT,
                     anchor="center", justify="center"
                     ).grid(row=0, column=i, sticky="nsew", padx=1, pady=2)
            self.head_frame.grid_columnconfigure(i, weight=1, uniform="days")

        # Сетка
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
        self.root.after(200, self.build_calendar)

    # ============ НАСТРОЙКИ ============
    def open_settings(self):
        SettingsWindow(self.root, self.config, self._after_settings_saved)

    def _after_settings_saved(self):
        """Перезагрузить всё после сохранения настроек."""
        self.load_settings()
        self.apply_fonts()

        # Обновить главное окно
        self.title_label.config(font=self.FONT_TITLE)
        self.time_label.config(font=self.FONT_CLOCK)
        self.date_label.config(font=self.FONT_DATE)
        for w in self.head_frame.winfo_children():
            w.config(font=self.FONT_HEAD)

        self.root.minsize(self.ui["min_width"], self.ui["min_height"])
        self.build_calendar()

        messagebox.showinfo("ГОТОВО", "Настройки сохранены и применены!")

    # ============ КЛАВИАТУРА ============
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
        self.root.after(200, self.build_calendar)
        return "break"

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.root.after(200, self.build_calendar)
        return "break"

    # ============ ЗАГРУЗКА ============
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
        self.FONT_NAME = tkfont.Font(family="Consolas", size=size, weight="normal")
        try:
            self.FONT_NAME.configure(linespace=max(0, size - 2))
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

    def open_config(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                save_config(DEFAULT_CONFIG)
            try:
                os.startfile(CONFIG_FILE)
                return
            except Exception:
                pass
            subprocess.Popen(["notepad.exe", CONFIG_FILE])
        except Exception as e:
            messagebox.showerror("ОШИБКА", f"Не удалось открыть файл:\n{e}")

    # ============ КАЛЕНДАРЬ ============
    def build_calendar(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.title_label.config(text=f"{MONTHS_RU_NOM[self.month-1]} {self.year}")

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
                    self._draw_day(row, col, cell_date, today, bw, True)
                elif idx < first_weekday + days_in_month:
                    cell_date = date(self.year, self.month, idx - first_weekday + 1)
                    self._draw_day(row, col, cell_date, today, bw, False)
                else:
                    cell_date = first_day + timedelta(days=idx - first_weekday)
                    self._draw_day(row, col, cell_date, today, bw, True)

    def _draw_day(self, row, col, cell_date, today, bw, is_other_month):
        hol_name = RU_HOLIDAYS.get(cell_date)
        team = self.get_team_for_date(cell_date)

        is_today = (cell_date == today) and not is_other_month
        bg = BG_CELL
        dim_factor = float(self.ui.get("other_month_dim", 0.55))
        vac_color = self.ui.get("vacation_color", VACATION)

        cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
        cell_border.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")

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

        tk.Label(head, text=str(cell_date.day), font=self.FONT_DAY,
                 bg=bg, fg=day_fg).grid(row=0, column=1)

        if hol_name:
            short = hol_name if len(hol_name) <= 16 else hol_name[:14] + "…"
            hol_fg = dim_hex(RED, dim_factor) if is_other_month else RED
            tk.Label(head, text=short, font=self.FONT_HOL,
                     bg=bg, fg=hol_fg, anchor="e"
                     ).grid(row=0, column=2, sticky="e", padx=(0, 4))

        if team:
            base_color = (dim_hex(team["color"], dim_factor)
                          if is_other_month else team["color"])
            vac_color_use = (dim_hex(vac_color, dim_factor)
                             if is_other_month else vac_color)

            if self.names_in_column:
                self._draw_names_text(inner, team["members"], cell_date,
                                      bg, base_color, vac_color_use)
            else:
                self._draw_names_inline(inner, team["members"], cell_date,
                                        bg, base_color, vac_color_use)

        if is_today:
            self._draw_today_frame(cell, bw)

    def _draw_names_text(self, parent, members, cell_date, bg,
                         base_color, vac_color):
        txt = tk.Text(parent, height=len(members), bg=bg, fg=base_color,
                      bd=0, highlightthickness=0, font=self.FONT_NAME,
                      wrap="none", cursor="arrow", padx=0, pady=0,
                      takefocus=0, spacing1=0, spacing2=0, spacing3=0)
        txt.pack(fill="x", anchor="n")
        txt.tag_configure("center", justify="center")
        txt.tag_configure("vac", overstrike=1, foreground=vac_color)

        for i, member in enumerate(members):
            if i > 0:
                txt.insert("end", "\n", "center")
            if self.is_on_vacation(member, cell_date):
                txt.insert("end", member, ("center", "vac"))
            else:
                txt.insert("end", member, "center")
        txt.config(state="disabled")

    def _draw_names_inline(self, parent, members, cell_date, bg,
                           base_color, vac_color):
        txt = tk.Text(parent, height=2, bg=bg, fg=base_color,
                      bd=0, highlightthickness=0, font=self.FONT_NAME,
                      wrap="word", cursor="arrow", padx=0, pady=0,
                      takefocus=0, spacing1=0, spacing2=0, spacing3=0)
        txt.pack(fill="x", anchor="n")
        txt.tag_configure("center", justify="center")
        txt.tag_configure("vac", overstrike=1, foreground=vac_color)

        for i, member in enumerate(members):
            if i > 0:
                txt.insert("end", ", ", "center")
            if self.is_on_vacation(member, cell_date):
                txt.insert("end", member, ("center", "vac"))
            else:
                txt.insert("end", member, "center")
        txt.config(state="disabled")

    def _draw_today_frame(self, parent, bw):
        tk.Frame(parent, bg=RED, height=bw).place(x=0, y=0, relwidth=1)
        tk.Frame(parent, bg=RED, height=bw).place(x=0, rely=1.0, y=-bw, relwidth=1)
        tk.Frame(parent, bg=RED, width=bw).place(x=0, y=0, relheight=1)
        tk.Frame(parent, bg=RED, width=bw).place(relx=1.0, x=-bw, y=0, relheight=1)

    # ============ ЧАСЫ ============
    def update_clock(self):
        now = datetime.now()
        today_now = now.date()

        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=f"{WEEKDAYS_RU[now.weekday()]}, {now.day} {MONTHS_RU_GEN[now.month-1]} {now.year}"
        )

        day_changed = (today_now != self.last_today)
        month_changed = (self.year, self.month) != (today_now.year, today_now.month)

        if day_changed or (self.follow_today and month_changed):
            if self.follow_today:
                self.year, self.month = today_now.year, today_now.month
            self.last_today = today_now
            self.build_calendar()

        self.root.after(1000, self.update_clock)

    # ============ НАВИГАЦИЯ ============
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
