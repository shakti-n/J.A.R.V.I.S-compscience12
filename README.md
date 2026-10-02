# JARVIS CS Study Core v2

A Flask + SQLite Class 12 Computer Science study assistant with a futuristic JARVIS-inspired HUD and browser voice interaction.

## What changed in v2

- Full 17-chapter syllabus structure supplied for this project
- Four units stored in SQLite
- Chapter-aware knowledge retrieval
- Microphone input using the browser Web Speech API
- Spoken JARVIS responses using browser Speech Synthesis
- Listening/processing reactor animation
- Text and voice commands use the same backend
- Flashcards and study logs remain SQLite-backed

## Run on Windows

Open Command Prompt inside this folder, then:

    py -m pip install -r requirements.txt
    py app.py

Open:

    http://127.0.0.1:5000

For voice, use a browser with Web Speech support such as Chrome or Edge and allow microphone permission.

## Textbook content

The application does not bundle a copied textbook. Use your own notes, summaries, or material you are permitted to use through Knowledge Core.

## Future AI integration

The current retrieval layer is local and deterministic. An LLM provider can be connected later to make explanations and flashcards genuinely generative while preserving the Flask, SQLite and frontend architecture.
