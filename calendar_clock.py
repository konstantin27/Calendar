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
    "start_date": "2026-01-01",
    "shift_days": 3,
    "names_in_column": True,
    "auto_return_seconds": 30,
    "weekend_header_color": "#cc0000",
    "weekend_header_brightness": 100,
    "today_border_color": "#ff3333",
    "today_border_brightness": 100,
    "holiday_gap": 12,
    "teams": [
        {"name": "Смена 1", "color": "#00ff41",
         "members": ["Иванов И.", "Петров П.", "Сидоров С.", "Морозов М."]},
        {"name": "Смена 2", "color": "#00bfff",
         "members": ["Кузнецов К.", "Смирнов С.", "Волков В.", "Соколов С."]}
    ],
    "vacations": {},
    "ui": {
        "window_width": 1100, "window_height": 900,
        "min_width": 800, "min_height": 650,
        "cell_min_height": 70,
        "font_day": 16, "font_holiday": 9, "font_names": 9,
        "font_clock": 26, "font_date": 11, "font_title": 16, "font_head": 10,
        "today_border_width": 3,
        "other_month_dim": 0.55,
        "fullscreen_on_start": False,
        "vacation_color": "#555555"
    }
}

DEFAULT_UI = DEFAULT_CONFIG["ui"]
DEFAULT_AUTO_RETURN = DEFAULT_CONFIG["auto_return_seconds"]
DEFAULT_HOLIDAY_GAP = DEFAULT_CONFIG["holiday_gap"]


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        changed = False
        for k, v in {
            "auto_return_seconds": DEFAULT_AUTO_RETURN,
            "names_in_column": True,
            "vacations": {},
            "weekend_header_color": "#cc0000",
            "weekend_header_brightness": 100,
            "today_border_color": "#ff3333",
            "today_border_brightness": 100,
            "holiday_gap": DEFAULT_HOLIDAY_GAP,
        }.items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        if changed:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg
    except Exception as e:
        print("Ошибка чтения:", e)
        return copy.deepcopy(DEFAULT_CONFIG)


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
    r = int(hex_color[0:2], 16); g = int(hex_color[2:4], 16); b = int(hex_color[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


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


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        self.cfg = copy.deepcopy(config)
        self.team_cards = []
        self.vac_rows = []

        self.title("НАСТРОЙКИ")
        self.configure(bg=BG)
        self.geometry("900x850")
        self.minsize(750, 650)
        self.transient(parent)
        self.grab_set()

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

        tk.Label(self, text="⚙  НАСТРОЙКИ", font=("Consolas", 16, "bold"),
                 bg=BG, fg=GREEN).pack(pady=(10, 5))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 5))

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

        tk.Label(f, text="Автовозврат к текущему месяцу после листания (секунд):",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(20, 3))
        self.e_auto = tk.Entry(f, font=("Consolas", 11),
                               bg=BG_PANEL, fg=GREEN_BRT,
                               insertbackground=GREEN, width=10)
        self.e_auto.pack(anchor="w", padx=20)
        self.e_auto.insert(0, str(self.cfg.get("auto_return_seconds",
                                                DEFAULT_AUTO_RETURN)))
        tk.Label(f, text="0 — не возвращать автоматически",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(2, 15))

        tk.Label(f, text="Фамилии в ячейке:",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(10, 3))
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

        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self.teams_frame = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=self.teams_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=5)
        scroll.pack(side="right", fill="y", padx=(0, 10), pady=5)
        self.teams_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._render_teams()

    def _render_teams(self):
        for w in self.teams_frame.winfo_children():
            w.destroy()
        self.team_cards = []
        for i, team in enumerate(self.cfg.get("teams", [])):
            self._render_one_team(i, team)

    def _render_one_team(self, idx, team):
        card = tk.Frame(self.teams_frame, bg=BG_PANEL,
                        highlightthickness=1, highlightbackground=GREEN_DIM)
        card.pack(fill="x", pady=5, padx=5)

        head = tk.Frame(card, bg=BG_PANEL)
        head.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(head, text=f"Смена #{idx + 1}", font=("Consolas", 10, "bold"),
                 bg=BG_PANEL, fg=GREEN).pack(side="left")
        tk.Button(head, text="🗑 Удалить", command=lambda i=idx: self._del_team(i),
                  font=("Consolas", 9), bg=BG_PANEL, fg=RED,
                  bd=0, relief="flat", activebackground=BG,
                  activeforeground="#ff8888", cursor="hand2"
                  ).pack(side="right")

        row1 = tk.Frame(card, bg=BG_PANEL)
        row1.pack(fill="x", padx=8, pady=3)
        tk.Label(row1, text="Название:", font=("Consolas", 10),
                 bg=BG_PANEL, fg=GREEN_BRT, width=11, anchor="w").pack(side="left")
        e_name = tk.Entry(row1, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN)
        e_name.pack(side="left", fill="x", expand=True)
        e_name.insert(0, team.get("name", ""))

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

        def _preview(ev=None, entry=e_color, prev=color_preview):
            try:
                prev.config(bg=entry.get().strip())
            except Exception:
                pass
        e_color.bind("<KeyRelease>", _preview)
        e_color.bind("<<Paste>>", lambda ev: self.after(50, _preview))
        e_color.bind("<FocusOut>", _preview)

        tk.Label(card, text="Работники:", font=("Consolas", 10),
                 bg=BG_PANEL, fg=GREEN_BRT, anchor="w"
                 ).pack(fill="x", padx=8, pady=(8, 2))

        members_frame = tk.Frame(card, bg=BG_PANEL)
        members_frame.pack(fill="x", padx=8, pady=2)
        member_entries = []
        for j, member in enumerate(team.get("members", [])):
            me = self._render_member(members_frame, idx, j, member)
            member_entries.append(me)

        tk.Button(card, text="+ Фамилия",
                  command=lambda i=idx: self._add_member(i),
                  font=("Consolas", 9, "bold"),
                  bg=BG, fg=GREEN_BRT, bd=1, relief="solid",
                  highlightthickness=1, highlightbackground=GREEN_DIM,
                  padx=8, pady=2, cursor="hand2"
                  ).pack(anchor="w", padx=8, pady=(3, 8))

        self.team_cards.append({
            "name_entry": e_name,
            "color_entry": e_color,
            "member_entries": member_entries,
        })

    def _render_member(self, parent, team_idx, member_idx, member):
        row = tk.Frame(parent, bg=BG_PANEL)
        row.pack(fill="x", pady=1)
        e = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                     insertbackground=GREEN)
        e.pack(side="left", fill="x", expand=True)
        e.insert(0, member)
        tk.Button(row, text="✖",
                  command=lambda t=team_idx, m=member_idx: self._del_member(t, m),
                  font=("Consolas", 10, "bold"),
                  bg=BG_PANEL, fg=RED, bd=0, relief="flat",
                  activebackground=BG, activeforeground="#ff8888",
                  padx=6, cursor="hand2"
                  ).pack(side="right")
        return e

    def _add_team(self):
        self._collect_teams_from_widgets()
        self.cfg.setdefault("teams", []).append({
            "name": f"Смена {len(self.cfg.get('teams', [])) + 1}",
            "color": "#ffcc00", "members": ["Новый работник"]})
        self._render_teams(); self._render_vacations()

    def _del_team(self, idx):
        self._collect_teams_from_widgets()
        if len(self.cfg.get("teams", [])) <= 1:
            messagebox.showwarning("ВНИМАНИЕ", "Нельзя удалить последнюю смену", parent=self)
            return
        if messagebox.askyesno("УДАЛИТЬ СМЕНУ",
                               f"Удалить «{self.cfg['teams'][idx].get('name', '')}»?",
                               parent=self):
            self.cfg["teams"].pop(idx)
            self._render_teams(); self._render_vacations()

    def _add_member(self, team_idx):
        self._collect_teams_from_widgets()
        self.cfg["teams"][team_idx].setdefault("members", []).append("Новый")
        self._render_teams(); self._render_vacations()

    def _del_member(self, team_idx, member_idx):
        self._collect_teams_from_widgets()
        self.cfg["teams"][team_idx]["members"].pop(member_idx)
        self._render_teams(); self._render_vacations()

    def _collect_teams_from_widgets(self):
        teams = []
        for card in self.team_cards:
            name = card["name_entry"].get().strip() or "Смена"
            color = card["color_entry"].get().strip() or "#00ff41"
            members = [e.get().strip() for e in card["member_entries"] if e.get().strip()]
            teams.append({"name": name, "color": color,
                          "members": members if members else ["Новый работник"]})
        if teams:
            self.cfg["teams"] = teams

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
        self.vac_frame.bind("<Configure>",
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self._render_vacations()

    def _get_all_members(self):
        self._collect_teams_from_widgets()
        result = []
        for t in self.cfg.get("teams", []):
            for m in t.get("members", []):
                if m and m not in result:
                    result.append(m)
        return result

    def _render_vacations(self):
        for w in self.vac_frame.winfo_children():
            w.destroy()
        self.vac_rows = []
        all_members = self._get_all_members()

        rows = []
        for name, periods in self.cfg.get("vacations", {}).items():
            for i, p in enumerate(periods):
                rows.append((name, i, p[0], p[1]))

        if not rows:
            tk.Label(self.vac_frame, text="Отпусков нет. Нажми «+ Добавить отпуск».",
                     font=("Consolas", 10), bg=BG, fg=GREEN_DIM
                     ).pack(anchor="w", pady=15, padx=5)
            return

        for (name, pidx, d1, d2) in rows:
            row = tk.Frame(self.vac_frame, bg=BG_PANEL,
                           highlightthickness=1, highlightbackground=GREEN_DIM)
            row.pack(fill="x", pady=3, padx=5)
            tk.Label(row, text="Работник:", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(8, 3), pady=6)
            combo = ttk.Combobox(row, values=all_members, state="readonly",
                                 font=("Consolas", 10), width=18)
            combo.pack(side="left", padx=3, pady=6)
            combo.set(name if name in all_members else (all_members[0] if all_members else ""))
            tk.Label(row, text="с", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(10, 3))
            e1 = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN, width=12)
            e1.pack(side="left", padx=3, pady=6); e1.insert(0, d1)
            tk.Label(row, text="по", font=("Consolas", 10),
                     bg=BG_PANEL, fg=GREEN_BRT).pack(side="left", padx=(8, 3))
            e2 = tk.Entry(row, font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                          insertbackground=GREEN, width=12)
            e2.pack(side="left", padx=3, pady=6); e2.insert(0, d2)
            tk.Button(row, text="🗑",
                      command=lambda n=name, pi=pidx: self._del_vacation(n, pi),
                      font=("Consolas", 10), bg=BG_PANEL, fg=RED,
                      bd=0, relief="flat", activebackground=BG,
                      activeforeground="#ff8888", padx=8, cursor="hand2"
                      ).pack(side="right", padx=5)
            self.vac_rows.append({"combo": combo, "e1": e1, "e2": e2})

    def _collect_vacations_from_widgets(self):
        vacations = {}
        for row in self.vac_rows:
            name = row["combo"].get().strip()
            d1 = row["e1"].get().strip()
            d2 = row["e2"].get().strip()
            if not name or not d1 or not d2:
                continue
            vacations.setdefault(name, []).append([d1, d2])
        self.cfg["vacations"] = vacations

    def _add_vacation(self):
        self._collect_vacations_from_widgets()
        all_members = self._get_all_members()
        if not all_members:
            messagebox.showwarning("ВНИМАНИЕ",
                                   "Сначала добавь работников на вкладке «Смены»",
                                   parent=self)
            return
        today = date.today()
        self.cfg.setdefault("vacations", {}).setdefault(all_members[0], []).append(
            [today.strftime("%Y-%m-%d"),
             (today + timedelta(days=13)).strftime("%Y-%m-%d")])
        self._render_vacations()

    def _del_vacation(self, name, period_idx):
        self._collect_vacations_from_widgets()
        v = self.cfg.get("vacations", {})
        if name in v and period_idx < len(v[name]):
            v[name].pop(period_idx)
            if not v[name]:
                del v[name]
            self._render_vacations()

    def _build_tab_ui(self):
        f = self.tab_ui
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        tk.Label(inner, text="Размеры окна и шрифтов:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(15, 10))

        grid = tk.Frame(inner, bg=BG)
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

        # ★ ОТСТУП МЕЖДУ ЧИСЛОМ И ПРАЗДНИКОМ
        tk.Label(inner, text="Отступ между числом и названием праздника:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(20, 5))

        gap_row = tk.Frame(inner, bg=BG)
        gap_row.pack(fill="x", padx=20, pady=3)
        tk.Label(gap_row, text="Пикселей:", font=("Consolas", 10),
                 bg=BG, fg=GREEN_BRT).pack(side="left")

        self.e_holiday_gap = tk.Entry(gap_row, font=("Consolas", 10),
                                       bg=BG_PANEL, fg=GREEN_BRT,
                                       insertbackground=GREEN, width=8)
        self.e_holiday_gap.pack(side="left", padx=5)
        self.e_holiday_gap.insert(
            0, str(self.cfg.get("holiday_gap", DEFAULT_HOLIDAY_GAP)))

        tk.Label(gap_row, text="(по умолчанию 12 — если буквы сливаются, увеличь до 16-20)",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(side="left", padx=5)

        # Рамка текущего дня
        tk.Label(inner, text="Рамка текущего дня (сегодня):",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(20, 5))

        tb_color_row = tk.Frame(inner, bg=BG)
        tb_color_row.pack(fill="x", padx=20, pady=3)

        tk.Label(tb_color_row, text="Цвет:", font=("Consolas", 10),
                 bg=BG, fg=GREEN_BRT).pack(side="left")

        self.e_today_border_color = tk.Entry(tb_color_row, font=("Consolas", 10),
                                              bg=BG_PANEL, fg=GREEN_BRT,
                                              insertbackground=GREEN, width=10)
        self.e_today_border_color.pack(side="left", padx=5)
        self.e_today_border_color.insert(
            0, str(self.cfg.get("today_border_color", "#ff3333")))

        self.tb_color_prev = tk.Label(tb_color_row, text="   ",
                                       bg=self.e_today_border_color.get())
        self.tb_color_prev.pack(side="left", padx=5)

        tk.Label(tb_color_row, text="(HEX, например #ff3333)",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(side="left", padx=5)

        def _upd_tb(e=None):
            try:
                self.tb_color_prev.config(bg=self.e_today_border_color.get())
            except Exception:
                pass
        self.e_today_border_color.bind("<KeyRelease>", _upd_tb)
        self.e_today_border_color.bind("<<Paste>>", lambda ev: self.after(50, _upd_tb))
        self.e_today_border_color.bind("<FocusOut>", _upd_tb)

        tk.Label(inner, text="Яркость рамки:",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(10, 3))

        cur_tb_bright = int(self.cfg.get("today_border_brightness", 100))
        cur_tb_bright = max(0, min(100, cur_tb_bright))
        self.v_tb_bright = tk.IntVar(value=cur_tb_bright)

        tb_bright_block = tk.Frame(inner, bg=BG)
        tb_bright_block.pack(fill="x", padx=20, pady=3)

        def _upd_tb_bright(val):
            try:
                self.tb_bright_label.config(text=f"{int(float(val))}%")
            except Exception:
                pass

        tb_scale = tk.Scale(tb_bright_block, from_=0, to=100,
                             orient="horizontal", variable=self.v_tb_bright,
                             showvalue=False, bg=BG, fg=GREEN_BRT,
                             troughcolor=BG_PANEL, highlightthickness=0, bd=0,
                             sliderrelief="flat", activebackground=GREEN,
                             length=420, command=_upd_tb_bright,
                             cursor="hand2", font=("Consolas", 9), width=18)
        tb_scale.pack(side="left", fill="x", expand=True)

        self.tb_bright_label = tk.Label(tb_bright_block, text=f"{cur_tb_bright}%",
                                         font=("Consolas", 14, "bold"),
                                         bg=BG, fg=GREEN, width=5)
        self.tb_bright_label.pack(side="right", padx=(10, 0))

        tk.Label(inner,
                 text="0% — чёрный        100% — максимально яркий",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(2, 15))

        # Приглушение
        tk.Label(inner, text="Приглушение дней соседних месяцев:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        cur_dim = float(self.cfg.get("ui", {}).get("other_month_dim", 0.55))
        cur_percent = max(0, min(100, int(round((1.0 - cur_dim) * 100))))
        self.v_dim = tk.IntVar(value=cur_percent)

        dim_block = tk.Frame(inner, bg=BG)
        dim_block.pack(fill="x", padx=20, pady=5)

        def _upd_dim_label(val):
            try:
                self.dim_label.config(text=f"{int(float(val))}%")
            except Exception:
                pass

        scale = tk.Scale(dim_block, from_=0, to=100, orient="horizontal",
                         variable=self.v_dim, showvalue=False,
                         bg=BG, fg=GREEN_BRT, troughcolor=BG_PANEL,
                         highlightthickness=0, bd=0, sliderrelief="flat",
                         activebackground=GREEN, length=420,
                         command=_upd_dim_label, cursor="hand2",
                         font=("Consolas", 9), width=18)
        scale.pack(side="left", fill="x", expand=True)

        self.dim_label = tk.Label(dim_block, text=f"{cur_percent}%",
                                  font=("Consolas", 14, "bold"),
                                  bg=BG, fg=GREEN, width=5)
        self.dim_label.pack(side="right", padx=(10, 0))

        tk.Label(inner,
                 text="0% — как обычные        100% — почти невидимы",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(2, 15))

        # Фон СБ/ВС
        tk.Label(inner, text="Фон СБ и ВС в шапке:",
                 font=("Consolas", 11, "bold"), bg=BG, fg=GREEN
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        wk_color_row = tk.Frame(inner, bg=BG)
        wk_color_row.pack(fill="x", padx=20, pady=3)

        tk.Label(wk_color_row, text="Цвет:", font=("Consolas", 10),
                 bg=BG, fg=GREEN_BRT).pack(side="left")

        self.e_weekend_color = tk.Entry(wk_color_row, font=("Consolas", 10),
                                        bg=BG_PANEL, fg=GREEN_BRT,
                                        insertbackground=GREEN, width=10)
        self.e_weekend_color.pack(side="left", padx=5)
        self.e_weekend_color.insert(
            0, str(self.cfg.get("weekend_header_color", "#cc0000")))

        self.wk_color_prev = tk.Label(wk_color_row, text="   ",
                                       bg=self.e_weekend_color.get())
        self.wk_color_prev.pack(side="left", padx=5)

        tk.Label(wk_color_row, text="(HEX, например #cc0000)",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(side="left", padx=5)

        def _upd_wk(e=None):
            try:
                self.wk_color_prev.config(bg=self.e_weekend_color.get())
            except Exception:
                pass
        self.e_weekend_color.bind("<KeyRelease>", _upd_wk)
        self.e_weekend_color.bind("<<Paste>>", lambda ev: self.after(50, _upd_wk))
        self.e_weekend_color.bind("<FocusOut>", _upd_wk)

        tk.Label(inner, text="Яркость фона:",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(10, 3))

        cur_wk_bright = int(self.cfg.get("weekend_header_brightness", 100))
        cur_wk_bright = max(0, min(100, cur_wk_bright))
        self.v_wk_bright = tk.IntVar(value=cur_wk_bright)

        wk_bright_block = tk.Frame(inner, bg=BG)
        wk_bright_block.pack(fill="x", padx=20, pady=3)

        def _upd_wk_bright(val):
            try:
                self.wk_bright_label.config(text=f"{int(float(val))}%")
            except Exception:
                pass

        wk_scale = tk.Scale(wk_bright_block, from_=0, to=100,
                             orient="horizontal", variable=self.v_wk_bright,
                             showvalue=False, bg=BG, fg=GREEN_BRT,
                             troughcolor=BG_PANEL, highlightthickness=0, bd=0,
                             sliderrelief="flat", activebackground=GREEN,
                             length=420, command=_upd_wk_bright,
                             cursor="hand2", font=("Consolas", 9), width=18)
        wk_scale.pack(side="left", fill="x", expand=True)

        self.wk_bright_label = tk.Label(wk_bright_block, text=f"{cur_wk_bright}%",
                                         font=("Consolas", 14, "bold"),
                                         bg=BG, fg=GREEN, width=5)
        self.wk_bright_label.pack(side="right", padx=(10, 0))

        tk.Label(inner,
                 text="0% — чёрный        100% — максимально яркий",
                 font=("Consolas", 9), bg=BG, fg=GREEN_DIM
                 ).pack(anchor="w", padx=20, pady=(2, 15))

        # Цвет отпуска
        tk.Label(inner, text="Цвет отпуска (HEX):",
                 font=("Consolas", 10), bg=BG, fg=GREEN_BRT
                 ).pack(anchor="w", padx=20, pady=(10, 3))
        color_row = tk.Frame(inner, bg=BG)
        color_row.pack(anchor="w", padx=20)
        self.e_vac_color = tk.Entry(color_row, font=("Consolas", 10),
                                    bg=BG_PANEL, fg=GREEN_BRT,
                                    insertbackground=GREEN, width=10)
        self.e_vac_color.pack(side="left")
        self.e_vac_color.insert(
            0, str(self.cfg.get("ui", {}).get("vacation_color", "#555555")))
        self.vac_color_prev = tk.Label(color_row, text="   ",
                                        bg=self.e_vac_color.get())
        self.vac_color_prev.pack(side="left", padx=5)

        def _upd_vac_color(e=None):
            try:
                self.vac_color_prev.config(bg=self.e_vac_color.get())
            except Exception:
                pass
        self.e_vac_color.bind("<KeyRelease>", _upd_vac_color)

        self.v_fs = tk.BooleanVar(
            value=bool(self.cfg.get("ui", {}).get("fullscreen_on_start", False)))
        tk.Checkbutton(inner, text="Запускать сразу в полноэкранном режиме",
                       variable=self.v_fs,
                       font=("Consolas", 10), bg=BG, fg=GREEN_BRT,
                       selectcolor=BG_PANEL, activebackground=BG,
                       activeforeground=GREEN_BRT
                       ).pack(anchor="w", padx=20, pady=(15, 20))

    def _save(self):
        self._collect_teams_from_widgets()
        self._collect_vacations_from_widgets()

        self.cfg["start_date"] = self.e_start.get().strip()
        try:
            self.cfg["shift_days"] = int(self.e_days.get().strip())
        except Exception:
            messagebox.showerror("ОШИБКА", "«Длина смены» должна быть числом", parent=self)
            return

        try:
            self.cfg["auto_return_seconds"] = int(self.e_auto.get().strip())
            if self.cfg["auto_return_seconds"] < 0:
                self.cfg["auto_return_seconds"] = 0
        except Exception:
            messagebox.showerror("ОШИБКА",
                                 "«Автовозврат» должен быть числом (секунды)",
                                 parent=self)
            return

        # ★ Отступ праздника
        try:
            gap = int(self.e_holiday_gap.get().strip())
            if gap < 0:
                gap = 0
            self.cfg["holiday_gap"] = gap
        except Exception:
            messagebox.showerror("ОШИБКА",
                                 "«Отступ праздника» должен быть числом",
                                 parent=self)
            return

        self.cfg["names_in_column"] = bool(self.v_col.get())

        wk_color = self.e_weekend_color.get().strip()
        if not wk_color.startswith("#") or len(wk_color) != 7:
            messagebox.showerror("ОШИБКА",
                                 f"Неверный цвет фона СБ/ВС:\n{wk_color}\n\n"
                                 f"Нужен HEX-код вида #cc0000", parent=self)
            return
        self.cfg["weekend_header_color"] = wk_color
        self.cfg["weekend_header_brightness"] = int(self.v_wk_bright.get())

        tb_color = self.e_today_border_color.get().strip()
        if not tb_color.startswith("#") or len(tb_color) != 7:
            messagebox.showerror("ОШИБКА",
                                 f"Неверный цвет рамки текущего дня:\n{tb_color}\n\n"
                                 f"Нужен HEX-код вида #ff3333", parent=self)
            return
        self.cfg["today_border_color"] = tb_color
        self.cfg["today_border_brightness"] = int(self.v_tb_bright.get())

        ui = self.cfg.setdefault("ui", {})
        for key, entry in self.ui_entries.items():
            val = entry.get().strip()
            if not val:
                continue
            try:
                ui[key] = int(val)
            except Exception:
                messagebox.showerror("ОШИБКА",
                                     f"Значение «{key}» должно быть числом", parent=self)
                return

        dim_percent = int(self.v_dim.get())
        ui["other_month_dim"] = max(0.0, min(1.0, 1.0 - dim_percent / 100.0))
        ui["vacation_color"] = self.e_vac_color.get().strip()
        ui["fullscreen_on_start"] = bool(self.v_fs.get())

        for name, periods in self.cfg.get("vacations", {}).items():
            for p in periods:
                try:
                    datetime.strptime(p[0], "%Y-%m-%d")
                    datetime.strptime(p[1], "%Y-%m-%d")
                except Exception:
                    messagebox.showerror(
                        "ОШИБКА",
                        f"Неверная дата у «{name}»:\n{p[0]} — {p[1]}\n\n"
                        f"Формат: ГГГГ-ММ-ДД", parent=self)
                    return

        try:
            datetime.strptime(self.cfg["start_date"], "%Y-%m-%d")
        except Exception:
            messagebox.showerror("ОШИБКА",
                                 "Дата начала цикла в формате ГГГГ-ММ-ДД", parent=self)
            return

        for t in self.cfg.get("teams", []):
            c = t.get("color", "").strip()
            if not c.startswith("#") or len(c) != 7:
                messagebox.showerror(
                    "ОШИБКА",
                    f"Неверный цвет у смены «{t.get('name', '')}»:\n{c}\n\n"
                    f"Нужен HEX-код вида #00ff41", parent=self)
                return

        if save_config(self.cfg):
            teams_info = ", ".join(
                f"{t['name']}({len(t['members'])}чел)" for t in self.cfg["teams"])
            vac_count = sum(len(v) for v in self.cfg.get("vacations", {}).values())
            auto = self.cfg["auto_return_seconds"]
            auto_txt = f"{auto} сек" if auto > 0 else "отключён"
            messagebox.showinfo(
                "СОХРАНЕНО",
                f"Файл: {CONFIG_FILE}\n\n"
                f"Смен: {len(self.cfg['teams'])} — {teams_info}\n"
                f"Периодов отпусков: {vac_count}\n"
                f"Отступ праздника: {gap} px\n"
                f"Приглушение соседних месяцев: {dim_percent}%\n"
                f"Автовозврат: {auto_txt}\n"
                f"Фон СБ/ВС: {wk_color} @ {self.cfg['weekend_header_brightness']}%\n"
                f"Рамка сегодня: {tb_color} @ {self.cfg['today_border_brightness']}%\n"
                f"Дата старта: {self.cfg['start_date']}\n"
                f"Длина смены: {self.cfg['shift_days']} дн.",
                parent=self)
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("ОШИБКА", "Не удалось сохранить файл", parent=self)


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
        self._auto_return_job = None
        self._building = False

        self.cells = []
        self.cells_created = False

        self.root.bind("<Left>",     self.key_prev_month)
        self.root.bind("<Right>",    self.key_next_month)
        self.root.bind("<Return>",   self.key_today)
        self.root.bind("<KP_Enter>", self.key_today)
        self.root.bind("<F11>",      self.toggle_fullscreen)
        self.root.bind("<Escape>",   self.exit_fullscreen)
        self.root.focus_set()

        now = datetime.now()
        self.year, self.month = now.year, now.month

        top = tk.Frame(root, bg=BG)
        top.pack(side="top", fill="x", padx=8, pady=(5, 2))

        nav_btn_style = {
            "font": ("Consolas", 12, "bold"),
            "bg": BG, "fg": GREEN,
            "bd": 0, "relief": "flat",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT,
            "width": 2, "padx": 2, "pady": 0,
        }
        btn_small = {
            "font": ("Consolas", 9, "bold"),
            "bg": BG, "fg": GREEN_DIM, "bd": 0, "relief": "flat",
            "highlightthickness": 1, "highlightbackground": GREEN_DIM,
            "padx": 8, "pady": 1, "cursor": "hand2",
            "activebackground": GREEN_DRK, "activeforeground": GREEN_BRT
        }

        tk.Button(top, text="◀", command=self.prev_month,
                  **nav_btn_style).pack(side="left")
        tk.Button(top, text="⚙ НАСТРОЙКИ", command=self.open_settings,
                  **btn_small).pack(side="left", padx=(3, 1))
        tk.Button(top, text="⛶", command=self.toggle_fullscreen,
                  **btn_small).pack(side="left", padx=(0, 3))

        tk.Button(top, text="▶", command=self.next_month,
                  **nav_btn_style).pack(side="right")
        tk.Button(top, text="СЕГОДНЯ", command=self.go_today,
                  **btn_small).pack(side="right", padx=(0, 3))

        self.title_label = tk.Label(top, font=self.FONT_TITLE, bg=BG, fg=GREEN)
        self.title_label.pack(side="left", expand=True)

        clock_frame = tk.Frame(root, bg=BG)
        clock_frame.pack(side="bottom", fill="x", pady=(4, 8))
        self.time_label = tk.Label(clock_frame, font=self.FONT_CLOCK, bg=BG, fg=GREEN)
        self.time_label.pack()
        self.date_label = tk.Label(clock_frame, font=self.FONT_DATE, bg=BG, fg=GREEN_DIM)
        self.date_label.pack()

        self.head_frame = tk.Frame(root, bg=GREEN_DRK)
        self.head_frame.pack(side="top", fill="x", padx=8, pady=(3, 0))
        self._build_header()

        self.grid_frame = tk.Frame(root, bg=BG_CELL)
        self.grid_frame.pack(side="top", fill="both", expand=True,
                             padx=8, pady=(0, 3))

        self._create_cells()
        self._update_all_cells()
        self.update_clock()

        if self.ui.get("fullscreen_on_start", False):
            self.root.after(200, self._initial_fullscreen)

    def _build_header(self):
        for w in self.head_frame.winfo_children():
            w.destroy()

        wk_color = self.config.get("weekend_header_color", "#cc0000")
        try:
            brightness = int(self.config.get("weekend_header_brightness", 100))
        except Exception:
            brightness = 100
        brightness = max(0, min(100, brightness))
        factor = brightness / 100.0
        try:
            weekend_bg = dim_hex(wk_color, factor) if factor < 1.0 else wk_color
        except Exception:
            weekend_bg = wk_color

        self.head_frame.configure(bg=GREEN_DRK)

        days_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days_short):
            is_weekend = i >= 5
            bg = weekend_bg if is_weekend else GREEN_DRK

            tk.Label(self.head_frame, text=d, font=self.FONT_HEAD,
                     bg=bg, fg=GREEN_BRT,
                     anchor="center", justify="center"
                     ).grid(row=0, column=i, sticky="nsew", padx=1, pady=2)
            self.head_frame.grid_columnconfigure(i, weight=1, uniform="days")

    def _get_today_color(self):
        color = self.config.get("today_border_color", "#ff3333")
        try:
            brightness = int(self.config.get("today_border_brightness", 100))
        except Exception:
            brightness = 100
        brightness = max(0, min(100, brightness))
        if brightness >= 100:
            return color
        return dim_hex(color, brightness / 100.0)

    def _initial_fullscreen(self):
        self.is_fullscreen = True
        self.root.attributes("-fullscreen", True)
        self.root.focus_set()
        self.root.after(200, self._update_all_cells)

    def open_settings(self):
        SettingsWindow(self.root, self.config, self._after_settings_saved)

    def _after_settings_saved(self):
        self.load_settings()
        self.apply_fonts()
        self.title_label.config(font=self.FONT_TITLE)
        self.time_label.config(font=self.FONT_CLOCK)
        self.date_label.config(font=self.FONT_DATE)
        self._build_header()
        self.root.minsize(self.ui["min_width"], self.ui["min_height"])
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.cells = []
        self.cells_created = False
        self._create_cells()
        self._update_all_cells()

    def _create_cells(self):
        if self.cells_created:
            return

        max_members = 4
        for t in self.teams:
            max_members = max(max_members, len(t.get("members", [])))

        for row in range(6):
            self.grid_frame.grid_rowconfigure(
                row, weight=1, minsize=self.ui["cell_min_height"])
            for col in range(7):
                self.grid_frame.grid_columnconfigure(
                    col, weight=1, uniform="days")

                cell_border = tk.Frame(self.grid_frame, bg=GREEN_DIM)
                cell_border.grid(row=row, column=col, sticky="nsew")

                cell = tk.Frame(cell_border, bg=BG_CELL)
                cell.pack(fill="both", expand=True, padx=1, pady=1)

                inner = tk.Frame(cell, bg=BG_CELL)
                inner.pack(fill="both", expand=True, padx=4, pady=4)

                head = tk.Frame(inner, bg=BG_CELL)
                head.pack(anchor="center")

                day_label = tk.Label(head, text="", font=self.FONT_DAY,
                                     bg=BG_CELL, fg=GREEN)
                day_label.pack(side="left")

                # ★ Праздник — с настраиваемым отступом
                hol_label = tk.Label(head, text="", font=self.FONT_HOL,
                                     bg=BG_CELL, fg=RED)

                names_text = tk.Text(inner, height=max_members,
                                     bg=BG_CELL, fg=GREEN,
                                     bd=0, highlightthickness=0,
                                     font=self.FONT_NAME,
                                     wrap="none", cursor="arrow",
                                     padx=0, pady=0, takefocus=0,
                                     spacing1=0, spacing2=0, spacing3=0)
                names_text.pack(fill="x", anchor="n")
                names_text.tag_configure("center", justify="center")
                names_text.tag_configure("vac", overstrike=1)
                names_text.config(state="disabled")

                today_top    = tk.Frame(cell, bg=RED)
                today_bottom = tk.Frame(cell, bg=RED)
                today_left   = tk.Frame(cell, bg=RED)
                today_right  = tk.Frame(cell, bg=RED)

                self.cells.append({
                    "border": cell_border,
                    "cell": cell,
                    "inner": inner,
                    "head": head,
                    "day_label": day_label,
                    "hol_label": hol_label,
                    "names": names_text,
                    "today_top": today_top,
                    "today_bottom": today_bottom,
                    "today_left": today_left,
                    "today_right": today_right,
                })

        self.cells_created = True

    def _update_all_cells(self):
        if not self.cells_created:
            return

        self.title_label.config(
            text=f"{MONTHS_RU_NOM[self.month-1]} {self.year}")

        today = date.today()
        first_day = date(self.year, self.month, 1)
        first_day_next = (date(self.year + 1, 1, 1) if self.month == 12
                          else date(self.year, self.month + 1, 1))
        days_in_month = (first_day_next - first_day).days
        first_weekday = first_day.weekday()

        for row in range(6):
            for col in range(7):
                idx = row * 7 + col
                if idx < first_weekday:
                    cell_date = first_day - timedelta(days=first_weekday - idx)
                    other = True
                elif idx < first_weekday + days_in_month:
                    cell_date = date(self.year, self.month,
                                     idx - first_weekday + 1)
                    other = False
                else:
                    cell_date = first_day + timedelta(days=idx - first_weekday)
                    other = True

                self._update_cell(idx, cell_date, today, other)

    def _update_cell(self, idx, cell_date, today, is_other_month):
        c = self.cells[idx]
        hol_name = RU_HOLIDAYS.get(cell_date)
        team = self.get_team_for_date(cell_date)
        is_today = (cell_date == today) and not is_other_month
        bg = BG_CELL
        dim_factor = float(self.ui.get("other_month_dim", 0.55))
        vac_color = self.ui.get("vacation_color", VACATION)
        bw = int(self.ui.get("today_border_width", 3))
        gap = int(self.config.get("holiday_gap", DEFAULT_HOLIDAY_GAP))

        today_color = self._get_today_color()

        border_color = today_color if is_today else GREEN_DIM
        c["border"].configure(bg=border_color)
        c["cell"].configure(bg=bg)
        c["inner"].configure(bg=bg)
        c["head"].configure(bg=bg)

        if is_other_month:
            if hol_name: day_fg = dim_hex(RED, dim_factor)
            elif team:   day_fg = dim_hex(team["color"], dim_factor)
            else:        day_fg = OTHER_MONTH
        else:
            if hol_name: day_fg = RED
            else:        day_fg = team["color"] if team else GREEN_DIM

        c["day_label"].configure(text=str(cell_date.day), fg=day_fg, bg=bg)

        # ★ Праздник — с отступом gap
        if hol_name:
            short = hol_name if len(hol_name) <= 20 else hol_name[:18] + "…"
            hol_fg = dim_hex(RED, dim_factor) if is_other_month else RED
            c["hol_label"].configure(text=short, fg=hol_fg, bg=bg)
            c["hol_label"].pack(side="left", padx=(gap, 0))   # ← отступ
        else:
            c["hol_label"].pack_forget()

        txt = c["names"]
        txt.configure(bg=bg)
        txt.config(state="normal")
        txt.delete("1.0", "end")

        if team:
            base_color = (dim_hex(team["color"], dim_factor)
                          if is_other_month else team["color"])
            vac_color_use = (dim_hex(vac_color, dim_factor)
                             if is_other_month else vac_color)

            txt.tag_configure("center", foreground=base_color, justify="center")
            txt.tag_configure("vac", overstrike=1, foreground=vac_color_use,
                              justify="center")

            for i, member in enumerate(team["members"]):
                if i > 0:
                    txt.insert("end", "\n", "center")
                if self.is_on_vacation(member, cell_date):
                    txt.insert("end", member, ("center", "vac"))
                else:
                    txt.insert("end", member, "center")
        txt.config(state="disabled")

        if is_today:
            c["today_top"].configure(bg=today_color, height=bw)
            c["today_bottom"].configure(bg=today_color, height=bw)
            c["today_left"].configure(bg=today_color, width=bw)
            c["today_right"].configure(bg=today_color, width=bw)

            c["today_top"].place(x=0, y=0, relwidth=1)
            c["today_bottom"].place(x=0, rely=1.0, y=-bw, relwidth=1)
            c["today_left"].place(x=0, y=0, relheight=1)
            c["today_right"].place(relx=1.0, x=-bw, y=0, relheight=1)
            c["today_top"].lift()
            c["today_bottom"].lift()
            c["today_left"].lift()
            c["today_right"].lift()
        else:
            c["today_top"].place_forget()
            c["today_bottom"].place_forget()
            c["today_left"].place_forget()
            c["today_right"].place_forget()

    def _get_auto_return_seconds(self):
        return int(self.config.get("auto_return_seconds", DEFAULT_AUTO_RETURN))

    def _schedule_auto_return(self):
        self._cancel_auto_return()
        sec = self._get_auto_return_seconds()
        if sec <= 0:
            return
        self._auto_return_job = self.root.after(sec * 1000, self._do_auto_return)

    def _cancel_auto_return(self):
        if self._auto_return_job is not None:
            try:
                self.root.after_cancel(self._auto_return_job)
            except Exception:
                pass
            self._auto_return_job = None

    def _do_auto_return(self):
        self._auto_return_job = None
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.follow_today = True
        self.last_today = now.date()
        self._update_all_cells()

    def key_prev_month(self, event=None): self.prev_month(); return "break"
    def key_next_month(self, event=None): self.next_month(); return "break"
    def key_today(self, event=None):      self.go_today();   return "break"

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        self.root.focus_set()
        self.root.after(200, self._update_all_cells)
        return "break"

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.root.after(200, self._update_all_cells)
        return "break"

    def load_settings(self):
        self.config = load_config()
        try:
            self.start_date = datetime.strptime(
                self.config["start_date"], "%Y-%m-%d").date()
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
        return self.teams[(delta % cycle) // self.shift_days]

    def is_on_vacation(self, name, target_date):
        for start, end in self.vacations.get(name, []):
            if start <= target_date <= end:
                return True
        return False

    def update_clock(self):
        now = datetime.now()
        today_now = now.date()
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(
            text=f"{WEEKDAYS_RU[now.weekday()]}, {now.day} "
                 f"{MONTHS_RU_GEN[now.month-1]} {now.year}")

        day_changed = (today_now != self.last_today)
        month_changed = (self.year, self.month) != (today_now.year, today_now.month)
        if day_changed or (self.follow_today and month_changed):
            if self.follow_today:
                self.year, self.month = today_now.year, today_now.month
            self.last_today = today_now
            self._update_all_cells()
        self.root.after(1000, self.update_clock)

    def prev_month(self):
        self.follow_today = False
        self.month -= 1
        if self.month < 1: self.month = 12; self.year -= 1
        self._update_all_cells()
        self._schedule_auto_return()

    def next_month(self):
        self.follow_today = False
        self.month += 1
        if self.month > 12: self.month = 1; self.year += 1
        self._update_all_cells()
        self._schedule_auto_return()

    def go_today(self):
        self._cancel_auto_return()
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.follow_today = True
        self.last_today = now.date()
        self._update_all_cells()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatrixShiftCalendar(root)
    root.mainloop()
