# Integrare și rulare

## Fluxul activ

`chat_interface.py` → `BotAdvancedSystem.build_reply()` → `ChatPipeline` → răspuns local rapid / unealtă deterministă / Ollama.

Într-o tură obișnuită, botul actualizează starea și tonul, clasifică intenția, încarcă contextul și amintirile relevante, construiește promptul și trimite ultimul mesaj către Ollama prin `/api/chat`. Răspunsul, mesajele, snapshot-ul și episodul sunt salvate în SQLite. Extragerea regulată a faptelor explicite rulează în fundal.

## Pornire

Pornește serviciul Ollama și modelul local, apoi rulează din directorul proiectului:

```powershell
python chat_interface.py
```

Modelul implicit este `llama3`. Se poate alege alt model instalat și un alt URL local prin variabile de mediu:

```powershell
$env:MARIOARA_OLLAMA_MODEL = "llama3:latest"
$env:MARIOARA_OLLAMA_URL = "http://localhost:11434"
python chat_interface.py
```

Nu este folosit niciun serviciu cloud.

## Memorie

`chatbot_memory.db` este sursa activă pentru conversații, preferințe, fapte, episoade și snapshot-uri. `bot_memory.json` este doar sursă de import inițial, numai din directorul transmis botului; aplicația nu îl actualizează.

Comenzi disponibile în chat:

- `/memorie`
- `/uita <id>`
- `/corecteaza <id> <text>`
- `/export`
- `/sterge`, apoi `/sterge confirm`

## Teste

```powershell
python test_behavior_modules.py
```

Testele folosesc baze SQLite temporare și un generator Ollama simulat; ele nu verifică disponibilitatea modelului local.

## Limite cunoscute

Interfața Tkinter apelează generarea sincron. Nu există streaming în fereastră, anulare la mesaj nou sau voce/TTS. Recuperarea memoriei este lexicală, nu bazată pe embeddings.
