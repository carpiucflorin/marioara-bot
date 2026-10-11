# Funcții

## Active

- Interfață Tkinter pornită din `chat_interface.py`.
- Un singur flux conversațional: `BotAdvancedSystem` → `ChatPipeline` → Ollama `/api/chat`.
- Clasificare de intenție și ton, instrucțiuni de comportament și răspunsuri locale pentru mesaje simple.
- Memorie SQLite pentru conversații, preferințe, fapte, episoade și snapshot-uri de context.
- Import o singură dată din `bot_memory.json`, doar din directorul indicat; fișierul vechi nu mai este destinație de scriere.
- Recuperare lexicală a amintirilor după topic, relevanță, importanță și recență.
- Extragere asincronă, bazată pe reguli, a informațiilor declarate explicit.
- Protecție de bază pentru mesaje de criză și tentative de jailbreak, cu jurnalizare SQLite.
- Calculator și dată/oră locale; comenzile de memorie `/memorie`, `/uita`, `/corecteaza`, `/export`, `/sterge confirm`.
- Teste backend: `python test_behavior_modules.py`.

## Limite actuale

- Vocea/TTS și modificările UI sunt amânate.
- UI-ul folosește apel Ollama sincron; nu există streaming în fereastră sau barge-in.
- Recuperarea memoriei nu folosește embeddings; consolidarea semantică și schedulerul de remindere nu sunt implementate.
- Viteza a fost măsurată cu `llama3` pe RTX 3060 12 GB; rezultatele nu reprezintă RTX 3050 și nu verifică singure calitatea răspunsurilor.
