import os
import sys
import time
import threading
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox

# ===== ДОБАВЛЕНО: библиотеки для трея =====
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

# ==================== Приложение (с треем) ====================
class TimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Таймер выключения")
        self.geometry("380x400")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Состояние
        self.timer_running = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.timer_thread = None
        self.stop_event = threading.Event()

        # ---- Иконка трея (создаётся позже, при первом сворачивании) ----
        self.tray_icon = None

        # ---- Переназначаем поведение при закрытии окна (крестик) ----
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # ===== Основной таймер =====
        self.timer_display = ctk.CTkLabel(
            self, text="00:00:00", font=("Segoe UI", 48, "bold"), text_color="#00d8ff"
        )
        self.timer_display.pack(pady=(15, 5))

        # ===== Выбор действия =====
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=30, pady=(5, 5))

        ctk.CTkLabel(action_frame, text="Действие:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))

        self.action_var = ctk.StringVar(value="shutdown")
        action_choices = [
            ("Выключить ПК", "shutdown"),
            ("Перезагрузить", "reboot"),
            ("Спящий режим", "hibernate"),
            ("Завершить сеанс", "lock"),
            ("Отключить интернет", "internet"),
            ("Выключить монитор", "monitor")
        ]
        self.action_combo = ctk.CTkComboBox(
            action_frame,
            values=[name for name, val in action_choices],
            variable=self.action_var,
            state="readonly",
            width=160
        )
        self.action_combo.pack(side="left", fill="x", expand=True)
        self.action_combo.set(action_choices[0][0])

        # ===== Режим и поле ввода =====
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=30, pady=(5, 5))

        self.mode_var = ctk.StringVar(value="countdown")
        ctk.CTkRadioButton(
            mode_frame, text="Обратный отсчёт", variable=self.mode_var,
            value="countdown", command=self.update_input_style
        ).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(
            mode_frame, text="В заданное время", variable=self.mode_var,
            value="exact", command=self.update_input_style
        ).pack(side="left")

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

        # ===== [ДОБАВЛЕНО] Кнопка "Свернуть в трей" =====
        self.tray_btn = ctk.CTkButton(
            self, text="— Свернуть в трей",
            command=self.hide_window,
            corner_radius=6, height=28,
            fg_color="#3a3a3a", hover_color="#4a4a4a",
            text_color="#cccccc", font=("Segoe UI", 10)
        )
        self.tray_btn.pack(fill="x", padx=30, pady=(0, 5))

        # ===== Зелёный лейбл "Осталось: X с" =====
        self.remaining_label = ctk.CTkLabel(
            self, text="Осталось: 0 с",
            font=("Segoe UI", 16, "bold"),
            text_color="#88ff88"
        )
        self.remaining_label.pack(pady=(5, 0))

        # ===== Статус и часы =====
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=30, pady=(5, 10))

        self.status_label = ctk.CTkLabel(
            bottom_frame, text="Готов", font=("Segoe UI", 10), text_color="#aaaaaa"
        )
        self.status_label.pack(side="left")

        self.clock_label = ctk.CTkLabel(
            bottom_frame, text="", font=("Segoe UI", 10), text_color="#888888"
        )
        self.clock_label.pack(side="right")
        self.update_clock()

        # Первоначальная настройка полей
        self.update_input_style()

    # ==================== Вспомогательные методы ====================
    def update_clock(self):
        now = datetime.now().strftime("%H:%M:%S  %d.%m.%Y")
        self.clock_label.configure(text=now)
        self.after(1000, self.update_clock)

    def update_input_style(self):
        if self.mode_var.get() == "countdown":
            self.input_label.configure(text="Секунд:")
            self.hint_label.configure(text="Пример: 3600 = 1 час")
            if not self.input_entry.get().strip():
                self.input_entry.delete(0, ctk.END)
                self.input_entry.insert(0, "3600")
        else:
            self.input_label.configure(text="Время (ЧЧ:ММ или ЧЧ:ММ:СС):")
            self.hint_label.configure(text="Пример: 11:15 или 11:15:30")
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
                messagebox.showerror("Ошибка", "Введите целое положительное число секунд.")
                return None
        else:  # точное время
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
                messagebox.showerror("Ошибка", "Введите время в формате ЧЧ:ММ или ЧЧ:ММ:СС (например, 11:15 или 11:15:30).")
                return None

    def update_timer_display(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        self.timer_display.configure(text=f"{hours:02d}:{minutes:02d}:{secs:02d}")

    # ==================== Управление таймером ====================
    def start_timer(self):
        if self.timer_running:
            return

        seconds = self.parse_time()
        if seconds is None:
            return

        if seconds == 0:
            # Выполняем действие сразу без подтверждения
            self.execute_action(ask_confirm=False)
            return

        self.timer_running = True
        self.remaining_seconds = seconds
        self.total_seconds = seconds
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Таймер запущен")
        self.remaining_label.configure(text=f"Осталось: {seconds} с")

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
        self.remaining_label.configure(text=f"Осталось: {self.remaining_seconds} с")
        self.status_label.configure(text=f"Осталось: {self.remaining_seconds} с")

    def _on_timer_finish(self):
        self.timer_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_timer_display(0)
        self.remaining_label.configure(text="Осталось: 0 с")
        self.status_label.configure(text="⏳ Выполняется действие...")
        # Выполняем действие без подтверждения
        self.execute_action(ask_confirm=False)

    def stop_timer(self):
        if self.timer_running:
            self.stop_event.set()
            self.timer_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.update_timer_display(0)
            self.remaining_label.configure(text="Осталось: 0 с")
            self.status_label.configure(text="⏹ Остановлено")

    # ==================== Выполнение действий ====================
    def execute_action(self, ask_confirm=True):
        action_name = self.action_combo.get()
        action_map = {
            "Выключить ПК": "shutdown",
            "Перезагрузить": "reboot",
            "Спящий режим": "hibernate",
            "Завершить сеанс": "lock",
            "Отключить интернет": "internet",
            "Выключить монитор": "monitor"
        }
        action_key = action_map.get(action_name, "shutdown")
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
            # Если требуется подтверждение и действие критичное
            if ask_confirm and action_key in ("shutdown", "reboot", "hibernate"):
                if not messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите {action_name.lower()}?"):
                    self.status_label.configure(text="Отменено")
                    self.remaining_label.configure(text="Отменено")
                    return
            try:
                func()
                self.status_label.configure(text=f"✅ {action_name} выполнено")
                self.remaining_label.configure(text="✅ Готово")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось выполнить действие:\n{e}")
                self.status_label.configure(text="❌ Ошибка")
                self.remaining_label.configure(text="❌ Ошибка")
        else:
            messagebox.showerror("Ошибка", "Неизвестное действие")

    def shutdown_now(self):
        # При ручном нажатии всегда спрашиваем
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите выключить компьютер сейчас?"):
            shutdown_pc()

    # ==================== Методы для работы с треем (ДОБАВЛЕНЫ) ====================
    def create_tray_icon(self):
        """Создаёт иконку в трее с контекстным меню."""
        # Генерируем простую иконку (круг с буквой T в цвете #00d8ff)
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill='#00d8ff')
        draw.text((20, 14), "T", fill='white', font=None, size=40)
        # Меню
        menu = pystray.Menu(
            pystray.MenuItem("Показать окно", self.show_window),
            pystray.MenuItem("Скрыть окно", self.hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выйти", self.quit_app)
        )
        self.tray_icon = pystray.Icon("timer_tray", image, "Таймер выключения", menu)

    def show_window(self, icon=None, item=None):
        """Показывает главное окно."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_window(self, icon=None, item=None):
        """Скрывает окно (сворачивает в трей)."""
        self.withdraw()
        # Если иконка ещё не запущена – запускаем
        if self.tray_icon is None:
            self.create_tray_icon()
        if not self.tray_icon._running:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def quit_app(self, icon=None, item=None):
        """Полный выход из приложения."""
        self.stop_timer()  # останавливаем таймер
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        sys.exit()

# ==================== Запуск ====================
if __name__ == "__main__":
    app = TimerApp()
    app.mainloop()
    
    
    
    
    
    
    
    
    
    
    
    
    
#####ByAsp710###