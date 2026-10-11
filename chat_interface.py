import tkinter as tk

from advanced_bot_system import BotAdvancedSystem
from voice import VoiceEngine


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marioara - Personal Companion")
        self.root.geometry("760x560")
        self.root.minsize(560, 420)

        self.bot = BotAdvancedSystem(bot_name="Marioara")
        self.voice = VoiceEngine()
        self.voice_enabled = self.voice.is_available()

        top = tk.Frame(self.root, bg="#fffafc")
        top.pack(fill=tk.X, padx=12, pady=(10, 0))

        title = tk.Label(top, text="Marioara", font=("Segoe UI", 14, "bold"), fg="#7a1f70", bg="#fffafc")
        title.pack(side=tk.LEFT)

        self.voice_btn = tk.Button(
            top,
            text="🔊 Voce: Pornită" if self.voice_enabled else "🔇 Voce: Oprită",
            command=self.toggle_voice,
            font=("Segoe UI", 9),
            width=16,
        )
        self.voice_btn.pack(side=tk.RIGHT)

        self.chat = tk.Text(self.root, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 11), bg="#fffafc", height=20)
        self.chat.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 8))

        label = tk.Label(self.root, text="MESAJ", font=("Segoe UI", 9, "bold"), fg="#7a1f70")
        label.pack(anchor="w", padx=12)

        bottom = tk.Frame(self.root, bg="#f5f1f4", padx=8, pady=8)
        bottom.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.entry = tk.Entry(bottom, font=("Segoe UI", 12), width=60, relief=tk.SOLID, borderwidth=2)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.entry.bind("<Return>", self.send_message_event)

        send_btn = tk.Button(bottom, text="Trimite", command=self.send_message, font=("Segoe UI", 10, "bold"), width=12)
        send_btn.pack(side=tk.RIGHT, padx=(8, 0))

        greeting = "Hei, dragă. Mă bucur că ești aici. Țin cont de context, de ce îți place și de tonul conversației. Ce ai în cap azi?"
        self.append_message(greeting, "bot")
        self.entry.focus_set()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        if self.voice_enabled:
            self.voice.speak(greeting)

    def append_message(self, text, sender):
        self.chat.configure(state=tk.NORMAL)
        prefix = "Tu: " if sender == "user" else "Marioara: "
        self.chat.insert(tk.END, prefix + text + "\n\n")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def send_message(self):
        message = self.entry.get().strip()
        if not message:
            return

        self.entry.delete(0, tk.END)
        self.append_message(message, "user")

        response = self.bot.build_reply(message)
        self.append_message(response, "bot")
        if self.voice_enabled:
            self.voice.speak(response)

    def send_message_event(self, event=None):
        self.send_message()
        return "break"

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        self.voice_btn.config(
            text="🔊 Voce: Pornită" if self.voice_enabled else "🔇 Voce: Oprită"
        )
        if not self.voice_enabled:
            self.voice.stop()

    def on_close(self):
        self.voice.cleanup()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
