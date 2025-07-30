# 🎵 ani-themes  
A CLI tool to play anime openings using `ani-cli`, `mpv`, and other dependencies.
Working on library version...

## 📦 Features

- Search and stream anime openings easily from your terminal  
- Minimal, fast, and fully keyboard-driven  

---

## 🛠️ Requirements

This tool depends on:
- `mpv` (video player)
- `python` and relevant libraries (for CLI logic and controls)

---

## 🪟 Windows Setup (Using Scoop)

### 1. Install Scoop (if not already installed)

Open PowerShell as Administrator and run:

```powershell
Set-ExecutionPolicy RemoteSigned -scope CurrentUser
iwr -useb get.scoop.sh | iex
```

### 2. Add the Extras Bucket

```powershell
scoop bucket add extras
```

### 3. Install Dependencies

```powershell
scoop install mpv
```

---

## 🐍 Python Setup

Ensure you have a `requirements.txt` in your project directory with necessary libraries.

Then install the dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

```bash
python ani-themes.py
```

Pick an anime series and enjoy!

---

## 📁 Project Structure

```
ani-themes/
├── ani-themes.py
├── requirements.txt
└── README.md
```

---


---
