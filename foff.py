import os
import sys
import time
import threading
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw

# ==================== Системные функции ====================
def shutdown_pc():
    if sys.platform == "win32":
        os.system("shutdown /s /t 0")
    else:
        os.system("shutdown -h now")

def reboot_pc():
    if sys.platform == "win32":
        os.system("shutdown /r /t 0")
    else:
        os.system("reboot")

def hibernate_pc():
    if sys.platform == "win32":
        os.system("shutdown /h")
    else:
        os.system("systemctl suspend")

def lock_pc():
    if sys.platform == "win32":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    else:
        os.system("gnome-screensaver-command -l")

def disconnect_internet():
    if sys.platform == "win32":
        os.system("netsh interface set interface name='Ethernet' admin=disable")
    else:
        os.system("nmcli networking off")

def monitor_off():
    if sys.platform == "win32":
        os.system("powershell -command \"(Add-Type '[DllImport(\\\"user32.dll\\\")]public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);' -Name a -Pas)::SendMessage(0xffff,0x0112,0xF170,2)\"")
    else:
        os.system("xset dpms force off")

# ==================== Словарь переводов (исправлены заполнители) ====================
TRANSLATIONS = {
    "ru": {
        "window_title": "Таймер выключения",
        "action_label": "Действие:",
        "shutdown": "Выключить ПК",
        "reboot": "Перезагрузить",
        "hibernate": "Спящий режим",
        "lock": "Завершить сеанс",
        "internet": "Отключить интернет",
        "monitor": "Выключить монитор",
        "mode_countdown": "Обратный отсчёт",
        "mode_exact": "В заданное время",
        "input_label_countdown": "Секунд:",
        "input_label_exact": "Время (ЧЧ:ММ или ЧЧ:ММ:СС):",
        "hint_countdown": "Пример: 3600 = 1 час",
        "hint_exact": "Пример: 11:15 или 11:15:30",
        "start_btn": "Запустить",
        "stop_btn": "Остановить",
        "shutdown_now_btn": "Выключить сейчас",
        "tray_btn": "— Свернуть в трей",
        "remaining_label": "Осталось: {seconds} с",
        "status_ready": "Готов",
        "status_running": "Таймер запущен",
        "status_executing": "⏳ Выполняется действие...",
        "status_stopped": "⏹ Остановлено",
        "status_canceled": "Отменено",
        "status_done": "✅ Готово",
        "status_error": "❌ Ошибка",
        "confirm_title": "Подтверждение",
        "confirm_message": "Вы уверены, что хотите {action}?",
        "error_title": "Ошибка",
        "error_parse_countdown": "Введите целое положительное число секунд.",
        "error_parse_exact": "Введите время в формате ЧЧ:ММ или ЧЧ:ММ:СС (например, 11:15 или 11:15:30).",
        "error_unknown": "Неизвестное действие",
        "error_execute": "Не удалось выполнить действие:\n{error}",
        "tray_title": "Таймер выключения",
        "tray_show": "Показать окно",
        "tray_hide": "Скрыть окно",
        "tray_quit": "Выйти"
    },
    "en": {
        "window_title": "Shutdown Timer",
        "action_label": "Action:",
        "shutdown": "Shut down PC",
        "reboot": "Reboot",
        "hibernate": "Hibernate",
        "lock": "Lock session",
        "internet": "Disconnect Internet",
        "monitor": "Turn off monitor",
        "mode_countdown": "Countdown",
        "mode_exact": "Scheduled time",
        "input_label_countdown": "Seconds:",
        "input_label_exact": "Time (HH:MM or HH:MM:SS):",
        "hint_countdown": "Example: 3600 = 1 hour",
        "hint_exact": "Example: 11:15 or 11:15:30",
        "start_btn": "Start",
        "stop_btn": "Stop",
        "shutdown_now_btn": "Shut down now",
        "tray_btn": "— Minimize to tray",
        "remaining_label": "Remaining: {seconds} s",
        "status_ready": "Ready",
        "status_running": "Timer running",
        "status_executing": "⏳ Executing action...",
        "status_stopped": "⏹ Stopped",
        "status_canceled": "Canceled",
        "status_done": "✅ Done",
        "status_error": "❌ Error",
        "confirm_title": "Confirmation",
        "confirm_message": "Are you sure you want to {action}?",
        "error_title": "Error",
        "error_parse_countdown": "Enter a positive integer number of seconds.",
        "error_parse_exact": "Enter time in HH:MM or HH:MM:SS format (e.g., 11:15 or 11:15:30).",
        "error_unknown": "Unknown action",
        "error_execute": "Failed to execute action:\n{error}",
        "tray_title": "Shutdown Timer",
        "tray_show": "Show window",
        "tray_hide": "Hide window",
        "tray_quit": "Quit"
    }
}

# ==================== Приложение ====================
class TimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lang = "ru"  # язык по умолчанию
        self.geometry("400x430")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Состояние
        self.timer_running = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.timer_thread = None
        self.stop_event = threading.Event()

        # ---- Иконка трея ----
        self.tray_icon = None
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # ---- Список действий (ключ, ru, en) ----
        self.action_choices = [
            ("shutdown", "Выключить ПК", "Shut down PC"),
            ("reboot", "Перезагрузить", "Reboot"),
            ("hibernate", "Спящий режим", "Hibernate"),
            ("lock", "Завершить сеанс", "Lock session"),
            ("internet", "Отключить интернет", "Disconnect Internet"),
            ("monitor", "Выключить монитор", "Turn off monitor")
        ]

        # ===== Основной таймер =====
        self.timer_display = ctk.CTkLabel(
            self, text="00:00:00", font=("Segoe UI", 48, "bold"), text_color="#00d8ff"
        )
        self.timer_display.pack(pady=(15, 5))

        # ===== Выбор действия =====
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=30, pady=(5, 5))

        self.action_label = ctk.CTkLabel(action_frame, text="Действие:", font=("Segoe UI", 11))
        self.action_label.pack(side="left", padx=(0, 8))

        self.action_var = ctk.StringVar(value="shutdown")
        self.action_combo = ctk.CTkComboBox(
            action_frame,
            values=[],
            variable=self.action_var,
            state="readonly",
            width=160
        )
        self.action_combo.pack(side="left", fill="x", expand=True)

        # ===== Режим и поле ввода =====
        self.mode_var = ctk.StringVar(value="countdown")

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=30, pady=(5, 5))

        self.radio_countdown = ctk.CTkRadioButton(
            mode_frame, text="Обратный отсчёт", variable=self.mode_var,
            value="countdown", command=self.update_input_style
        )
        self.radio_countdown.pack(side="left", padx=(0, 15))

        self.radio_exact = ctk.CTkRadioButton(
            mode_frame, text="В заданное время", variable=self.mode_var,
            value="exact", command=self.update_input_style
        )
        self.radio_exact.pack(side="left")

        # Поле ввода
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=30, pady=(5, 5))

        self.input_label = ctk.CTkLabel(input_frame, text="Секунд:", font=("Segoe UI", 11))
        self.input_label.pack(side="left", padx=(0, 8))

        self.input_entry = ctk.CTkEntry(input_frame, width=150, font=("Segoe UI", 11))
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.insert(0, "3600")
        self.input_entry.bind("<Return>", lambda e: self.start_timer())

        self.hint_label = ctk.CTkLabel(
            self, text="Пример: 3600 = 1 час", text_color="#888888", font=("Segoe UI", 10)
        )
        self.hint_label.pack(anchor="w", padx=30, pady=(0, 5))

        # ===== Кнопки управления =====
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(5, 5))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="Запустить", command=self.start_timer,
            corner_radius=6, height=30
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="Остановить", command=self.stop_timer,
            state="disabled", corner_radius=6, height=30
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # ===== Кнопка "Выключить сейчас" =====
        self.now_btn = ctk.CTkButton(
            self, text="Выключить сейчас", command=self.shutdown_now,
            corner_radius=6, height=30
        )
        self.now_btn.pack(fill="x", padx=30, pady=(5, 5))

        # ===== Кнопка "Свернуть в трей" =====
        self.tray_btn = ctk.CTkButton(
            self, text="— Свернуть в трей",
            command=self.hide_window,
            corner_radius=6, height=28,
            fg_color="#3a3a3a", hover_color="#4a4a4a",
            text_color="#cccccc", font=("Segoe UI", 10)
        )
        self.tray_btn.pack(fill="x", padx=30, pady=(0, 5))

        # ===== Зелёный лейбл "Осталось" =====
        self.remaining_label = ctk.CTkLabel(
            self, text="Осталось: 0 с",
            font=("Segoe UI", 16, "bold"),
            text_color="#88ff88"
        )
        self.remaining_label.pack(pady=(5, 0))

        # ===== Статус, часы и выбор языка =====
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=30, pady=(5, 10))

        self.status_label = ctk.CTkLabel(
            bottom_frame, text="Готов", font=("Segoe UI", 10), text_color="#aaaaaa"
        )
        self.status_label.pack(side="left")

        # ----- Выбор языка -----
        self.lang_combo = ctk.CTkComboBox(
            bottom_frame,
            values=["Русский", "English"],
            state="readonly",
            width=100,
            command=self.change_language
        )
        self.lang_combo.pack(side="right", padx=(0, 0))
        self.lang_combo.set("Русский")

        self.clock_label = ctk.CTkLabel(
            bottom_frame, text="", font=("Segoe UI", 10), text_color="#888888"
        )
        self.clock_label.pack(side="right", padx=(0, 10))

        self.update_clock()

        # Первоначальная настройка полей и языка
        self.update_input_style()
        self.refresh_language()

    # ==================== Методы перевода ====================
    def get_text(self, key, **kwargs):
        """Возвращает перевод по ключу с подстановкой параметров."""
        text = TRANSLATIONS[self.lang].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def refresh_language(self):
        """Обновляет все тексты интерфейса при смене языка."""
        self.title(self.get_text("window_title"))
        self.action_label.configure(text=self.get_text("action_label"))

        # ---- Сохраняем текущее действие по ключу ----
        current_display = self.action_var.get()
        current_key = None
        for key, ru, en in self.action_choices:
            display = ru if self.lang == "ru" else en
            if display == current_display:
                current_key = key
                break
        if current_key is None:
            current_key = "shutdown"

        # Обновляем список действий
        new_values = []
        for key, ru, en in self.action_choices:
            if self.lang == "ru":
                new_values.append(ru)
            else:
                new_values.append(en)
        self.action_combo.configure(values=new_values)

        # Восстанавливаем выбранное действие
        for key, ru, en in self.action_choices:
            if key == current_key:
                display = ru if self.lang == "ru" else en
                self.action_var.set(display)
                break

        # Радио-кнопки
        self.radio_countdown.configure(text=self.get_text("mode_countdown"))
        self.radio_exact.configure(text=self.get_text("mode_exact"))

        # Поле ввода
        self.update_input_style()

        # Кнопки
        self.start_btn.configure(text=self.get_text("start_btn"))
        self.stop_btn.configure(text=self.get_text("stop_btn"))
        self.now_btn.configure(text=self.get_text("shutdown_now_btn"))
        self.tray_btn.configure(text=self.get_text("tray_btn"))

        # Метка "Осталось"
        if self.timer_running:
            remaining_text = self.get_text("remaining_label", seconds=self.remaining_seconds)
        else:
            remaining_text = self.get_text("remaining_label", seconds=0)
        self.remaining_label.configure(text=remaining_text)

        # Статус (переводим только если он совпадает со стандартным)
        current_status = self.status_label.cget("text")
        status_map_ru = {
            "Готов": "status_ready",
            "Таймер запущен": "status_running",
            "⏳ Выполняется действие...": "status_executing",
            "⏹ Остановлено": "status_stopped",
            "Отменено": "status_canceled",
            "✅ Готово": "status_done",
            "❌ Ошибка": "status_error"
        }
        status_map_en = {
            "Ready": "status_ready",
            "Timer running": "status_running",
            "⏳ Executing action...": "status_executing",
            "⏹ Stopped": "status_stopped",
            "Canceled": "status_canceled",
            "✅ Done": "status_done",
            "❌ Error": "status_error"
        }
        status_map = status_map_ru if self.lang == "ru" else status_map_en
        if current_status in status_map:
            new_status = self.get_text(status_map[current_status])
            self.status_label.configure(text=new_status)

        # Удаляем старую иконку трея, чтобы при следующем сворачивании создать новую с переводом
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_icon = None

    def change_language(self, choice):
        if choice == "Русский":
            self.lang = "ru"
        else:
            self.lang = "en"
        self.refresh_language()

    # ==================== Остальные методы ====================
    def update_clock(self):
        now = datetime.now().strftime("%H:%M:%S  %d.%m.%Y")
        self.clock_label.configure(text=now)
        self.after(1000, self.update_clock)

    def update_input_style(self):
        if self.mode_var.get() == "countdown":
            self.input_label.configure(text=self.get_text("input_label_countdown"))
            self.hint_label.configure(text=self.get_text("hint_countdown"))
            if not self.input_entry.get().strip():
                self.input_entry.delete(0, ctk.END)
                self.input_entry.insert(0, "3600")
        else:
            self.input_label.configure(text=self.get_text("input_label_exact"))
            self.hint_label.configure(text=self.get_text("hint_exact"))
            if not self.input_entry.get().strip():
                self.input_entry.delete(0, ctk.END)
                self.input_entry.insert(0, "11:15")

    def parse_time(self):
        raw = self.input_entry.get().strip()
        if self.mode_var.get() == "countdown":
            try:
                sec = int(raw)
                if sec < 0:
                    raise ValueError
                return sec
            except:
                messagebox.showerror(
                    self.get_text("error_title"),
                    self.get_text("error_parse_countdown")
                )
                return None
        else:
            try:
                parts = raw.split(":")
                if len(parts) == 1:
                    h = int(parts[0])
                    m, s = 0, 0
                elif len(parts) == 2:
                    h = int(parts[0])
                    m = int(parts[1])
                    s = 0
                elif len(parts) == 3:
                    h, m, s = map(int, parts)
                else:
                    raise ValueError
                if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
                    raise ValueError
                now = datetime.now()
                target = datetime(now.year, now.month, now.day, h, m, s)
                if target <= now:
                    target += timedelta(days=1)
                delta = target - now
                return int(delta.total_seconds())
            except:
                messagebox.showerror(
                    self.get_text("error_title"),
                    self.get_text("error_parse_exact")
                )
                return None

    def update_timer_display(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        self.timer_display.configure(text=f"{hours:02d}:{minutes:02d}:{secs:02d}")

    def start_timer(self):
        if self.timer_running:
            return
        seconds = self.parse_time()
        if seconds is None:
            return
        if seconds == 0:
            self.execute_action(ask_confirm=False)
            return

        self.timer_running = True
        self.remaining_seconds = seconds
        self.total_seconds = seconds
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text=self.get_text("status_running"))
        self.remaining_label.configure(
            text=self.get_text("remaining_label", seconds=seconds)
        )

        self.stop_event.clear()
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _timer_loop(self):
        while self.remaining_seconds > 0 and not self.stop_event.is_set():
            time.sleep(1)
            self.remaining_seconds -= 1
            self.after(0, self._update_ui)

        if self.remaining_seconds <= 0 and not self.stop_event.is_set():
            self.after(0, self._on_timer_finish)

    def _update_ui(self):
        if not self.timer_running:
            return
        self.update_timer_display(self.remaining_seconds)
        self.remaining_label.configure(
            text=self.get_text("remaining_label", seconds=self.remaining_seconds)
        )
        self.status_label.configure(
            text=self.get_text("remaining_label", seconds=self.remaining_seconds)
        )

    def _on_timer_finish(self):
        self.timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_timer_display(0)
        self.remaining_label.configure(text=self.get_text("remaining_label", seconds=0))
        self.status_label.configure(text=self.get_text("status_executing"))
        self.execute_action(ask_confirm=False)

    def stop_timer(self):
        if self.timer_running:
            self.stop_event.set()
            self.timer_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.update_timer_display(0)
            self.remaining_label.configure(text=self.get_text("remaining_label", seconds=0))
            self.status_label.configure(text=self.get_text("status_stopped"))

    def execute_action(self, ask_confirm=True):
        action_display = self.action_var.get()
        action_key = None
        for key, ru, en in self.action_choices:
            display = ru if self.lang == "ru" else en
            if display == action_display:
                action_key = key
                break
        if action_key is None:
            messagebox.showerror(
                self.get_text("error_title"),
                self.get_text("error_unknown")
            )
            return

        actions = {
            "shutdown": shutdown_pc,
            "reboot": reboot_pc,
            "hibernate": hibernate_pc,
            "lock": lock_pc,
            "internet": disconnect_internet,
            "monitor": monitor_off
        }
        func = actions.get(action_key)
        if func:
            action_name = self.get_text(action_key)
            if ask_confirm and action_key in ("shutdown", "reboot", "hibernate"):
                if not messagebox.askyesno(
                    self.get_text("confirm_title"),
                    self.get_text("confirm_message", action=action_name.lower())
                ):
                    self.status_label.configure(text=self.get_text("status_canceled"))
                    self.remaining_label.configure(text=self.get_text("status_canceled"))
                    return
            try:
                func()
                if self.lang == "ru":
                    self.status_label.configure(text=f"✅ {action_name} выполнено")
                else:
                    self.status_label.configure(text=f"✅ {action_name} done")
                self.remaining_label.configure(text=self.get_text("status_done"))
            except Exception as e:
                messagebox.showerror(
                    self.get_text("error_title"),
                    self.get_text("error_execute", error=str(e))
                )
                self.status_label.configure(text=self.get_text("status_error"))
                self.remaining_label.configure(text=self.get_text("status_error"))
        else:
            messagebox.showerror(
                self.get_text("error_title"),
                self.get_text("error_unknown")
            )

    def shutdown_now(self):
        if messagebox.askyesno(
            self.get_text("confirm_title"),
            self.get_text("confirm_message", action=self.get_text("shutdown").lower())
        ):
            shutdown_pc()

    # ==================== Методы трея ====================
    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill='#00d8ff')
        draw.text((20, 14), "T", fill='white', font=None, size=40)
        menu = pystray.Menu(
            pystray.MenuItem(self.get_text("tray_show"), self.show_window),
            pystray.MenuItem(self.get_text("tray_hide"), self.hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.get_text("tray_quit"), self.quit_app)
        )
        self.tray_icon = pystray.Icon("timer_tray", image, self.get_text("tray_title"), menu)

    def show_window(self, icon=None, item=None):
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self, icon=None, item=None):
        self.withdraw()
        if self.tray_icon is None:
            self.create_tray_icon()
        if not self.tray_icon._running:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def quit_app(self, icon=None, item=None):
        self.stop_timer()
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        sys.exit()

# ==================== Запуск ====================
if __name__ == "__main__":
    app = TimerApp()
    app.mainloop()
    



#####by_asp710#####
