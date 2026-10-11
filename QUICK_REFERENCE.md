# Referință rapidă

## Pornire

1. Pornește Ollama și asigură-te că modelul ales este instalat.
2. Din PowerShell, în directorul proiectului, rulează:

```powershell
python chat_interface.py
```

Configurarea opțională a modelului și URL-ului:

```powershell
$env:MARIOARA_OLLAMA_MODEL = "llama3:latest"
$env:MARIOARA_OLLAMA_URL = "http://localhost:11434"
```

## Traseul unui mesaj

- `BotAdvancedSystem.build_reply()` actualizează profilul, emoțiile, tonul și ghidajul de comportament.
- `ChatPipeline` face verificările de siguranță, clasifică intenția și topicul, apoi încearcă răspuns rapid sau unealtă locală.
- Întrebările obișnuite ajung la Ollama prin `/api/chat` cu context, preferințe relevante și amintiri SQLite.
- Mesajele și episoadele sunt persistate în SQLite; snapshot-ul păstrează contextul pentru repornire.

## Comenzi de memorie

- `/memorie` listează amintirile salvate.
- `/uita <id>` șterge o amintire.
- `/corecteaza <id> <text>` corectează o amintire.
- `/export` exportă baza de memorie.
- `/sterge` cere confirmare; `/sterge confirm` șterge memoria activă.

## Verificare

```powershell
python test_behavior_modules.py
```

Testele backend nu au nevoie de Ollama pornit. Pentru verificarea modelului real, folosește Ollama separat; performanța depinde de model și GPU.

## Nu este inclus

Vocea/TTS, streamingul în UI, barge-in, embeddings pentru memorie și schedulerul de remindere sunt încă în afara implementării. UI-ul rămâne Tkinter și nu trebuie pornit dintr-un al doilea launcher.
