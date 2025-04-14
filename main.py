import tkinter as tk
import pyautogui
import pytesseract
import keyboard
from deep_translator import GoogleTranslator
import configparser
import os
import threading
import time
from pynput import mouse  # Add this import for mouse button detection

# Konfiguracja ścieżki do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# Domyślne ustawienia
config = {
    'Settings': {
        'source_language': 'english',
        'target_language': 'pl',
        'text_color': '#FFFFFF',
        'background_color': '#333333',
        'opacity': '0.85',
        'font_size': '13',
        'hotkey': 'mouse4',
        'screenshot_hotkey': 'alt+w',
        'display_time': '10'
    }
}


# Ładowanie/tworzenie pliku konfiguracyjnego
def load_config():
    config_file = 'translator_config.ini'
    config_parser = configparser.ConfigParser()

    if os.path.exists(config_file):
        config_parser.read(config_file)

        # Jeśli w istniejącym pliku nie ma parametru display_time, dodaj go
        if 'display_time' not in config_parser['Settings']:
            config_parser['Settings']['display_time'] = '5'
    else:
        config_parser['Settings'] = config['Settings']
        with open(config_file, 'w') as f:
            config_parser.write(f)

    return config_parser


# Zapis konfiguracji
def save_config(config_parser):
    with open('translator_config.ini', 'w') as f:
        config_parser.write(f)


class OverlayTranslator:
    def __init__(self, root):
        self.root = root
        self.config = load_config()

        # Ustawienia okna głównego
        self.root.title("Visual Novel Translator")
        self.root.geometry("500x200+100+100")
        self.root.attributes("-topmost", True)

        # Ustawienia tłumacza
        self.source_language = self.config['Settings']['source_language']
        self.target_language = self.config['Settings']['target_language']
        self.translator = GoogleTranslator(source=self.source_language, target=self.target_language)

        # Zmienne do śledzenia pozycji myszy dla przesuwania okna
        self.x = 0
        self.y = 0

        # Timer do automatycznego ukrywania
        self.hide_timer = None
        self.display_time = int(self.config['Settings']['display_time'])

        # Utworzenie interfejsu
        self.create_main_window()

        # Utworzenie nakładki
        self.create_overlay()

        # Konfiguracja skrótów klawiszowych
        self.setup_hotkeys()

        # Konfiguracja nasłuchiwania myszy
        self.setup_mouse_listener()

    def setup_mouse_listener(self):
        # Inicjalizacja nasłuchiwania myszy w oddzielnym wątku
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.mouse_listener.daemon = True  # Wątek będzie zakończony razem z głównym programem
        self.mouse_listener.start()

    def on_mouse_click(self, x, y, button, pressed):
        # Sprawdź czy to naciśnięcie (nie puszczenie) przycisku
        if pressed:
            # Sprawdź czy to przycisk mouse4 (zwykle xbutton1)
            if button == mouse.Button.x1 and self.config['Settings']['hotkey'] == 'mouse4':
                self.capture_and_translate()
            # Możesz też obsłużyć mouse5 (zwykle xbutton2) jeśli potrzeba
            elif button == mouse.Button.x2 and self.config['Settings']['hotkey'] == 'mouse5':
                self.capture_and_translate()

    def create_main_window(self):
        # Ramka główna
        main_frame = tk.Frame(self.root, bg="#F0F0F0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tytuł
        title_label = tk.Label(main_frame, text="Visual Novel Translator", font=("Arial", 16, "bold"), bg="#F0F0F0")
        title_label.pack(pady=5)

        # Informacje o skrótach
        hotkey_frame = tk.Frame(main_frame, bg="#F0F0F0")
        hotkey_frame.pack(fill=tk.X, pady=5)

        hotkey_label = tk.Label(hotkey_frame, text=f"Skrót do tłumaczenia: {self.config['Settings']['hotkey']}",
                                bg="#F0F0F0", font=("Arial", 10))
        hotkey_label.pack(side=tk.LEFT)

        screenshot_label = tk.Label(hotkey_frame,
                                    text=f"Skrót do zrzutu ekranu: {self.config['Settings']['screenshot_hotkey']}",
                                    bg="#F0F0F0", font=("Arial", 10))
        screenshot_label.pack(side=tk.RIGHT)

        # Dodatkowa informacja o czasie wyświetlania
        auto_hide_label = tk.Label(main_frame,
                                   text=f"Nakładka zniknie automatycznie po {self.config['Settings']['display_time']} sekundach",
                                   bg="#F0F0F0", font=("Arial", 10))
        auto_hide_label.pack(pady=2)

        # Przyciski kontrolne
        button_frame = tk.Frame(main_frame, bg="#F0F0F0")
        button_frame.pack(fill=tk.X, pady=10)

        translate_button = tk.Button(button_frame, text="Tłumacz teraz", command=self.capture_and_translate,
                                     bg="#4CAF50", fg="white", font=("Arial", 10), padx=10)
        translate_button.pack(side=tk.LEFT, padx=5)

        settings_button = tk.Button(button_frame, text="Ustawienia", command=self.open_settings,
                                    bg="#2196F3", fg="white", font=("Arial", 10), padx=10)
        settings_button.pack(side=tk.LEFT, padx=5)

        toggle_overlay_button = tk.Button(button_frame, text="Pokaż/Ukryj nakładkę", command=self.toggle_overlay,
                                          bg="#FF9800", fg="white", font=("Arial", 10), padx=10)
        toggle_overlay_button.pack(side=tk.LEFT, padx=5)

        exit_button = tk.Button(button_frame, text="Wyjście", command=self.root.quit,
                                bg="#F44336", fg="white", font=("Arial", 10), padx=10)
        exit_button.pack(side=tk.RIGHT, padx=5)

        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Gotowy")
        status_label = tk.Label(main_frame, textvariable=self.status_var, bg="#F0F0F0",
                                font=("Arial", 10), fg="#666666")
        status_label.pack(pady=5)

    def create_overlay(self):
        # Utworzenie okna nakładki
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Tłumaczenie")
        self.overlay.geometry("600x200+200+300")
        self.overlay.overrideredirect(True)  # Ukrycie ramki okna
        self.overlay.attributes("-topmost", True)  # Zawsze na wierzchu

        # Ustawienie przezroczystości
        self.overlay.attributes("-alpha", float(self.config['Settings']['opacity']))

        # Ramka dla kontrolek manipulacji oknem
        control_frame = tk.Frame(self.overlay, bg=self.config['Settings']['background_color'])
        control_frame.pack(fill=tk.X)

        # Przycisk zamknięcia
        close_button = tk.Button(control_frame, text="X", command=self.hide_overlay,
                                 bg="#F44336", fg="white", width=2, height=1)
        close_button.pack(side=tk.RIGHT)

        # Obszar do przeciągania
        drag_label = tk.Label(control_frame, text="≡ Tłumaczenie", bg=self.config['Settings']['background_color'],
                              fg=self.config['Settings']['text_color'])
        drag_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        drag_label.bind("<ButtonPress-1>", self.start_drag)
        drag_label.bind("<ButtonRelease-1>", self.stop_drag)
        drag_label.bind("<B1-Motion>", self.on_drag)

        # Pole tekstowe na tłumaczenie
        self.translation_text = tk.Text(self.overlay, wrap=tk.WORD, bg=self.config['Settings']['background_color'],
                                        fg=self.config['Settings']['text_color'],
                                        font=("Arial", int(self.config['Settings']['font_size'])))
        self.translation_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Licznik czasu - pokazujący ile sekund pozostało do zniknięcia nakładki
        self.timer_var = tk.StringVar()
        self.timer_label = tk.Label(self.overlay, textvariable=self.timer_var,
                                    bg=self.config['Settings']['background_color'],
                                    fg=self.config['Settings']['text_color'])
        self.timer_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Domyślnie ukryjemy nakładkę
        self.overlay.withdraw()

    def setup_hotkeys(self):
        # Ustawienie skrótów klawiszowych (tylko dla standardowych klawiszy, nie myszy)
        if self.config['Settings']['hotkey'] not in ['mouse4', 'mouse5']:
            keyboard.add_hotkey(self.config['Settings']['hotkey'], self.capture_and_translate)

        keyboard.add_hotkey(self.config['Settings']['screenshot_hotkey'], self.take_screenshot)

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y
        # Zatrzymaj timer podczas przeciągania
        self.cancel_auto_hide()

    def stop_drag(self, event):
        self.x = None
        self.y = None
        # Wznów timer po zakończeniu przeciągania
        self.start_auto_hide()

    def on_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.overlay.winfo_x() + deltax
        y = self.overlay.winfo_y() + deltay
        self.overlay.geometry(f"+{x}+{y}")

    def capture_and_translate(self):
        self.status_var.set("Tłumaczenie w toku...")
        self.root.update()

        try:
            # Zrzut ekranu
            screenshot = pyautogui.screenshot()

            # Rozpoznawanie tekstu
            text = pytesseract.image_to_string(screenshot)

            if not text.strip():
                self.status_var.set("Nie wykryto tekstu!")
                return

            # Tłumaczenie
            translated_text = self.translator.translate(text)

            # Aktualizacja pola tekstowego w nakładce
            self.translation_text.delete("1.0", tk.END)
            self.translation_text.insert(tk.END, translated_text)

            # Pokazanie nakładki jeśli jest ukryta
            self.show_overlay()

            self.status_var.set("Przetłumaczono pomyślnie")
        except Exception as e:
            self.status_var.set(f"Błąd: {str(e)}")

    def take_screenshot(self):
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save("vn_screenshot.png")
            self.status_var.set("Zapisano zrzut ekranu jako vn_screenshot.png")
        except Exception as e:
            self.status_var.set(f"Błąd zrzutu ekranu: {str(e)}")

    def toggle_overlay(self):
        if self.overlay.winfo_viewable():
            self.hide_overlay()
        else:
            self.show_overlay()

    def show_overlay(self):
        self.overlay.deiconify()
        # Uruchom timer do automatycznego ukrycia nakładki
        self.start_auto_hide()

    def hide_overlay(self):
        self.overlay.withdraw()
        # Anuluj aktywny timer jeśli istnieje
        self.cancel_auto_hide()

    def start_auto_hide(self):
        # Anuluj istniejący timer jeśli istnieje
        self.cancel_auto_hide()

        # Zainicjuj nowy timer
        self.seconds_left = int(self.config['Settings']['display_time'])
        self.update_timer_display()

        # Uruchom timer w oddzielnym wątku
        self.hide_timer = threading.Thread(target=self.auto_hide_countdown)
        self.hide_timer.daemon = True  # Wątek będzie zakończony razem z głównym programem
        self.hide_timer.start()

    def auto_hide_countdown(self):
        while self.seconds_left > 0:
            time.sleep(1)
            # Sprawdź czy nakładka jest nadal widoczna
            if not self.overlay.winfo_viewable():
                return

            self.seconds_left -= 1
            # Aktualizuj wyświetlany licznik
            self.root.after(0, self.update_timer_display)

        # Ukryj nakładkę po upływie czasu
        self.root.after(0, self.hide_overlay)

    def update_timer_display(self):
        if self.seconds_left > 0:
            self.timer_var.set(f"Automatyczne ukrycie za: {self.seconds_left}s")
        else:
            self.timer_var.set("")

    def cancel_auto_hide(self):
        # Anuluj licznik czasu (nie anuluje wątku, ale przestanie wyświetlać licznik)
        self.seconds_left = 0
        self.timer_var.set("")

    def open_settings(self):
        # Okno ustawień
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Ustawienia")
        settings_window.geometry("400x500")  # Zwiększony rozmiar dla dodatkowego ustawienia
        settings_window.attributes("-topmost", True)

        settings_frame = tk.Frame(settings_window, padx=20, pady=20)
        settings_frame.pack(fill=tk.BOTH, expand=True)

        # Języki
        language_frame = tk.LabelFrame(settings_frame, text="Języki", padx=10, pady=10)
        language_frame.pack(fill=tk.X, pady=5)

        # Źródłowy język
        source_label = tk.Label(language_frame, text="Język źródłowy:")
        source_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        source_var = tk.StringVar(value=self.config['Settings']['source_language'])
        source_entry = tk.Entry(language_frame, textvariable=source_var)
        source_entry.grid(row=0, column=1, sticky=tk.W + tk.E, pady=5)

        # Docelowy język
        target_label = tk.Label(language_frame, text="Język docelowy:")
        target_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        target_var = tk.StringVar(value=self.config['Settings']['target_language'])
        target_entry = tk.Entry(language_frame, textvariable=target_var)
        target_entry.grid(row=1, column=1, sticky=tk.W + tk.E, pady=5)

        # Wygląd
        appearance_frame = tk.LabelFrame(settings_frame, text="Wygląd", padx=10, pady=10)
        appearance_frame.pack(fill=tk.X, pady=5)

        # Kolor tekstu
        text_color_label = tk.Label(appearance_frame, text="Kolor tekstu:")
        text_color_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        text_color_var = tk.StringVar(value=self.config['Settings']['text_color'])
        text_color_entry = tk.Entry(appearance_frame, textvariable=text_color_var)
        text_color_entry.grid(row=0, column=1, sticky=tk.W + tk.E, pady=5)

        # Kolor tła
        bg_color_label = tk.Label(appearance_frame, text="Kolor tła:")
        bg_color_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        bg_color_var = tk.StringVar(value=self.config['Settings']['background_color'])
        bg_color_entry = tk.Entry(appearance_frame, textvariable=bg_color_var)
        bg_color_entry.grid(row=1, column=1, sticky=tk.W + tk.E, pady=5)

        # Przezroczystość
        opacity_label = tk.Label(appearance_frame, text="Przezroczystość (0.1-1.0):")
        opacity_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        opacity_var = tk.StringVar(value=self.config['Settings']['opacity'])
        opacity_entry = tk.Entry(appearance_frame, textvariable=opacity_var)
        opacity_entry.grid(row=2, column=1, sticky=tk.W + tk.E, pady=5)

        # Rozmiar czcionki
        font_size_label = tk.Label(appearance_frame, text="Rozmiar czcionki:")
        font_size_label.grid(row=3, column=0, sticky=tk.W, pady=5)

        font_size_var = tk.StringVar(value=self.config['Settings']['font_size'])
        font_size_entry = tk.Entry(appearance_frame, textvariable=font_size_var)
        font_size_entry.grid(row=3, column=1, sticky=tk.W + tk.E, pady=5)

        # Czas wyświetlania
        display_time_label = tk.Label(appearance_frame, text="Czas wyświetlania (sek):")
        display_time_label.grid(row=4, column=0, sticky=tk.W, pady=5)

        display_time_var = tk.StringVar(value=self.config['Settings']['display_time'])
        display_time_entry = tk.Entry(appearance_frame, textvariable=display_time_var)
        display_time_entry.grid(row=4, column=1, sticky=tk.W + tk.E, pady=5)

        # Skróty klawiszowe
        hotkeys_frame = tk.LabelFrame(settings_frame, text="Skróty klawiszowe", padx=10, pady=10)
        hotkeys_frame.pack(fill=tk.X, pady=5)

        translate_hotkey_label = tk.Label(hotkeys_frame, text="Skrót do tłumaczenia:")
        translate_hotkey_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        # Lista możliwych przycisków myszy
        mouse_buttons = ['', 'mouse4', 'mouse5']
        all_hotkeys = [''] + mouse_buttons + ['alt+a', 'alt+b', 'alt+c', 'alt+d', 'ctrl+a', 'ctrl+b', 'ctrl+c', 'ctrl+d']

        translate_hotkey_var = tk.StringVar(value=self.config['Settings']['hotkey'])
        translate_hotkey_combo = tk.OptionMenu(hotkeys_frame, translate_hotkey_var, *all_hotkeys)
        translate_hotkey_combo.grid(row=0, column=1, sticky=tk.W + tk.E, pady=5)

        screenshot_hotkey_label = tk.Label(hotkeys_frame, text="Skrót do zrzutu ekranu:")
        screenshot_hotkey_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        screenshot_hotkey_var = tk.StringVar(value=self.config['Settings']['screenshot_hotkey'])
        screenshot_hotkey_combo = tk.OptionMenu(hotkeys_frame, screenshot_hotkey_var, *all_hotkeys)
        screenshot_hotkey_combo.grid(row=1, column=1, sticky=tk.W + tk.E, pady=5)

        # Informacja o przyciskach myszy
        mouse_info_label = tk.Label(hotkeys_frame, text="mouse4/5 to dodatkowe przyciski myszy", fg="#666666")
        mouse_info_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        button_frame = tk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, pady=10)

        def save_settings():
            self.config['Settings']['source_language'] = source_var.get()
            self.config['Settings']['target_language'] = target_var.get()
            self.config['Settings']['text_color'] = text_color_var.get()
            self.config['Settings']['background_color'] = bg_color_var.get()
            self.config['Settings']['opacity'] = opacity_var.get()
            self.config['Settings']['font_size'] = font_size_var.get()
            self.config['Settings']['display_time'] = display_time_var.get()  # Zapisz czas wyświetlania

            self.display_time = int(self.config['Settings']['display_time'])

            # Usuń wszystkie skróty klawiaturowe
            try:
                if self.config['Settings']['hotkey'] not in ['mouse4', 'mouse5']:
                    keyboard.remove_hotkey(self.config['Settings']['hotkey'])

                keyboard.remove_hotkey(self.config['Settings']['screenshot_hotkey'])
            except Exception:
                pass  # Ignorujemy błędy, gdyż skrót mógł nie istnieć

            # Zapisz nowe skróty
            old_hotkey = self.config['Settings']['hotkey']
            new_hotkey = translate_hotkey_var.get()

            self.config['Settings']['hotkey'] = new_hotkey
            self.config['Settings']['screenshot_hotkey'] = screenshot_hotkey_var.get()

            # Dodaj nowe skróty klawiaturowe (tylko dla standardowych klawiszy)
            if new_hotkey not in ['mouse4', 'mouse5']:
                keyboard.add_hotkey(new_hotkey, self.capture_and_translate)

            keyboard.add_hotkey(self.config['Settings']['screenshot_hotkey'], self.take_screenshot)

            # Zrestartuj nasłuchiwacz myszy jeśli zmieniły się skróty myszy
            if (old_hotkey in ['mouse4', 'mouse5'] and new_hotkey not in ['mouse4', 'mouse5']) or \
                    (old_hotkey not in ['mouse4', 'mouse5'] and new_hotkey in ['mouse4', 'mouse5']):
                try:
                    self.mouse_listener.stop()
                    self.setup_mouse_listener()
                except Exception:
                    pass

            save_config(self.config)

            self.translator = GoogleTranslator(source=self.config['Settings']['source_language'],
                                               target=self.config['Settings']['target_language'])

            self.translation_text.config(bg=self.config['Settings']['background_color'],
                                         fg=self.config['Settings']['text_color'],
                                         font=("Arial", int(self.config['Settings']['font_size'])))

            self.overlay.attributes("-alpha", float(self.config['Settings']['opacity']))

            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and "zniknie automatycznie" in child.cget("text"):
                            child.config(
                                text=f"Nakładka zniknie automatycznie po {self.config['Settings']['display_time']} sekundach")

            settings_window.destroy()

            self.status_var.set("Zapisano ustawienia")

        save_button = tk.Button(button_frame, text="Zapisz", command=save_settings,
                                bg="#4CAF50", fg="white", padx=20)
        save_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Anuluj", command=settings_window.destroy,
                                  bg="#F44336", fg="white", padx=20)
        cancel_button.pack(side=tk.RIGHT, padx=5)

def main():
    root = tk.Tk()
    app = OverlayTranslator(root)
    root.mainloop()


if __name__ == "__main__":
    main()