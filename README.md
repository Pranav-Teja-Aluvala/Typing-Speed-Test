# TypingSpeedTest

> A terminal-based typing speed tester built with Python and Rich, inspired by Monkeytype.

<p align="left">
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python">
    <img src="https://img.shields.io/badge/Rich-Terminal-black?style=for-the-badge">
    <img src="https://img.shields.io/badge/License-MIT-success?style=for-the-badge">
</p>

---

## Overview

<p align="center">
    <img src="screenshots/infographic.png" width="100%">
</p>

TypingSpeedTest is a modern terminal-based typing speed tester designed for fast, distraction-free practice. It provides real-time performance metrics, persistent statistics, configurable settings, and a clean interface inspired by Monkeytype, all while running entirely inside the terminal.

---

## Demo

<p align="center">
    <img src="demo/demo.gif" width="100%">
</p>

**Full Video:** [demo/demo.mp4](demo/demo.mp4)

---

## Features

- Real-time WPM, Accuracy and Mistake Tracking
- Monkeytype-inspired Terminal Interface
- Easy, Medium, Hard and Quotes Modes
- Practice Mode
- Persistent Leaderboard
- Lifetime Statistics
- Configurable Settings
- Multiple Themes
- JSON-based Local Storage
- Cross-platform Keyboard Support

---

## Project Structure

```text
Typing-Speed-Test/
│
├── assets/
│   ├── easy.txt
│   ├── medium.txt
│   ├── hard.txt
│   └── quotes.txt
│
├── data/
│   ├── history.json
│   ├── leaderboard.json
│   └── settings.json
│
├── demo/
│   ├── demo.gif
│   └── demo.mp4
│
├── screenshots/
│   └── infographic.png
│
├── src/
│   ├── config.py
│   ├── constants.py
│   ├── game.py
│   ├── leaderboard.py
│   ├── paragraphs.py
│   ├── statistics.py
│   ├── typing.py
│   ├── ui.py
│   └── utils.py
│
├── main.py
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Installation

```bash
git clone https://github.com/Pranav-Teja-Aluvala/Typing-Speed-Test.git

cd Typing-Speed-Test

pip install -r requirements.txt

python main.py
```

---

## Technologies Used

- Python
- Rich
- JSON
- Dataclasses

---

## License

This project is licensed under the MIT License.
