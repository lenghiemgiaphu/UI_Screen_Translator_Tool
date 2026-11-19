<div align="center">

# 🖥️ Screen Translator

**Capture any area of your screen, extract the text with OCR, and translate it instantly — right where you are looking.**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-PyQt5-41CD52?logo=qt&logoColor=white)
![OCR](https://img.shields.io/badge/OCR-Tesseract-4B8BBE)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Local Glossary (`database.json`)](#-local-glossary-databasejson)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Privacy](#-privacy)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

**Screen Translator** is a lightweight Windows background utility that lives in your system tray. Press a single hotkey (**F8** by default), drag a rectangle over any text on your screen — a game, a PDF, a video, an app UI, an image — and a compact floating window appears next to your selection with the **original text and its translation**, line by line.

It is built for people who constantly read content in foreign languages and don't want to copy text by hand, switch windows, or open a browser tab just to translate a single line.

### Highlights

- ⚡ **One hotkey, zero friction** — press `F8`, drag, read.
- 🧠 **Hybrid translation engine** — a fast, offline, fuzzy-matched **local glossary** is checked first; **Google Translate** is used as a fallback.
- 🀄 **Chinese-aware** — automatic Pinyin annotation and cleanup of the stray spaces Tesseract inserts between CJK characters.
- 🕘 **Built-in searchable history** of your last 100 translations.
- 🪟 **Always-on-top, draggable, resizable** dark-themed result window.

---

## ✨ Features

| Feature | Description |
| --- | --- |
| **Global hotkey capture** | Trigger a screen snip from anywhere with `F8`, even when the app is minimized to the tray. |
| **Multi-pass OCR** | Automatically retries with different Tesseract page-segmentation modes (`--psm 6 → 7 → 11`) and image scaling to recover single-line, oversized, or small text. |
| **Smart image preprocessing** | Upscales small captures (2×) and adds background-matched padding so edge characters are not clipped. |
| **Multi-language OCR** | Auto-detects which installed Tesseract language packs are available and loads them together (`eng+vie+chi_sim+…`). |
| **Local glossary lookup** | Fuzzy-matches (≥ 80 % similarity) each line against `database.json` for consistent, curated translations of UI terms. |
| **Keyboard-shortcut aware** | Strips trailing shortcuts such as `Ctrl+T` or `Alt+F4` and trailing ellipses before glossary matching (e.g. `New tab Ctrl+T` → `new tab`). |
| **Google Translate fallback** | Uses [`deep-translator`](https://pypi.org/project/deep-translator/) for anything not in the glossary. |
| **Pinyin support** | Displays Pinyin next to Chinese text when the glossary provides it. |
| **Live language switching** | Change the target language from a searchable dropdown and the results re-translate instantly. |
| **One-click copy** | Copy either the original text or the translation per line, with visual confirmation. |
| **Translation history** | Browse, search, and clear the last 100 translations. |
| **Single-instance guard** | Launching the app again cleanly replaces the previous background instance. |
| **System tray integration** | Capture, open history, edit the glossary, or exit from the tray menu. |

### Supported Languages

Currently: English · Vietnamese · Chinese (Simplified) 
Future planes: Chinese (Traditional) · Japanese · Korean · French · German · Spanish · Russian · Thai

---

## ⚙️ How It Works

```text
   F8 hotkey
       │
       ▼
┌──────────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│  Fullscreen      │ ─► │  Tesseract OCR     │ ─► │  Line-by-line        │
│  region selector │    │  (multi-pass, PSM) │    │  translation         │
└──────────────────┘    └────────────────────┘    └──────────┬───────────┘
                                                             │
                              ┌──────────────────────────────┴───────┐
                              ▼                                      ▼
                    1. Local glossary (fuzzy ≥ 80%)        2. Google Translate
                       database.json  → source: "Local DB"    (fallback)
                              │                                      │
                              └──────────────────┬───────────────────┘
                                                 ▼
                                  Floating result window  +  history.json
```

1. **Capture** — A frozen screenshot of the primary display is shown with a dim overlay while you drag a selection.
2. **Recognize** — The cropped region is preprocessed and passed to Tesseract using every installed, supported language pack.
3. **Translate** — Each detected line is looked up in the local glossary first; if there is no confident match, it is sent to Google Translate.
4. **Display & store** — Results appear in a floating window next to your selection and are saved to `history.json`.

---

## 📋 Requirements

- **Operating system:** Windows 10 / 11
- **Python:** 3.9 or newer
- **Tesseract OCR:** installed locally (see below)
- **Internet connection:** only required for the Google Translate fallback

### Python dependencies

| Package | Purpose |
| --- | --- |
| `PyQt5` | GUI, system tray, screen capture |
| `pytesseract` | Python wrapper for Tesseract OCR |
| `Pillow` | Image processing |
| `deep-translator` | Google Translate client |
| `thefuzz` | Fuzzy string matching for the local glossary |
| `keyboard` | Global hotkey registration |

---

## 🚀 Installation

### 1. Install Tesseract OCR

Download and install Tesseract for Windows from the [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki).

During setup, **select the additional language data** you need (for example *Vietnamese*, *Chinese – Simplified*, *Japanese*, *Korean*, …). The app automatically detects and uses whichever of the following packs are installed:

```text
eng  vie  chi_sim  chi_tra  jpn  kor  fra  deu  rus  spa  tha
```

> By default the app expects Tesseract at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
> If you installed it elsewhere, see [Configuration](#-configuration).

### 2. Clone the repository

```bash
git clone [https://github.com/<your-username>/<your-repo>.git](https://github.com/lenghiemgiaphu/UI_Screen_Translator_Tool.git)
cd <your-repo>
```

### 3. Create a virtual environment (recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python snipping_tool.py
```

You should see:

```text
-> Screen Translator is running in background (OCR: eng+vie+chi_sim+...)
-> Press [F8] to capture and translate.
```

The app now runs in the system tray (blue square icon).

---

## 🎯 Usage

1. Press **`F8`** (or choose *Capture Screen to Translate* from the tray menu).
2. **Click and drag** to select the area containing text. Press `Esc` to cancel.
3. Release the mouse — a result window appears beside your selection.
4. Pick the **target language** from the dropdown (type to search). Results update instantly.
5. Use the **Copy** buttons to copy the original text or the translation.
6. Click **History** to browse and search past translations, or **Clear All** to wipe them.
7. Press `Esc` or click **×** to close the window.

### Tray menu

| Action | Description |
| --- | --- |
| **Capture Screen to Translate (F8)** | Starts a new snip. |
| **Translation History (Last 100)** | Opens the history viewer directly. |
| **Open database.json** | Opens the local glossary in your default editor. |
| **Exit** | Quits the application. |

### Result window

- **Drag** anywhere on the window to move it.
- **Resize** using the grip in the bottom-right corner.
- Each card shows the **original line**, the **translation**, and (for Chinese) the **Pinyin**.

---

## 📚 Local Glossary (`database.json`)

The glossary gives you full control over how specific terms are translated — ideal for **software UI strings, game terminology, or domain-specific vocabulary** where machine translation is inconsistent.

### Format

Each entry has a unique key and contains translations keyed by language code. An optional `pinyin` field provides the Pinyin reading for the Chinese text.

```json
{
  "UI_003": {
    "en": "Settings",
    "zh": "设置",
    "pinyin": "shè zhì",
    "vi": "Cài đặt"
  }
}
```

### Matching rules

- Every text value in an entry (except `pinyin`) is a searchable source term.
- Input is normalized (lower-cased, shortcuts like `Ctrl+T` and trailing `.` / `…` removed) and compared using fuzzy matching.
- A match requires a **similarity score of at least 80** and the entry must contain the **target language** code.
- Matches are labelled **`Local DB`** internally; everything else falls back to **`Google`**.

### Language codes

| Language | Code |
| --- | --- |
| English | `en` |
| Vietnamese | `vi` |
| Chinese (Simplified / Traditional) | `zh` |
| Japanese | `ja` |
| Korean | `ko` |
| French | `fr` |
| German | `de` |
| Spanish | `es` |
| Russian | `ru` |
| Thai | `th` |

> 💡 **Tip:** Add as many languages as you like to a single entry. Restart a capture (press `F8` again) after editing the file to load the latest version.

---

## 🛠️ Configuration

All settings are constants at the top of `snipping_tool.py`:

| Constant | Default | Description |
| --- | --- | --- |
| `pytesseract.pytesseract.tesseract_cmd` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Path to the Tesseract executable. |
| `HOTKEY_SNIP` | `'f8'` | Global hotkey that starts a capture (e.g. `'ctrl+shift+t'`). |
| `MAX_HISTORY` | `100` | Maximum number of history entries kept. |
| `LANG_MAP` | 11 languages | Maps display names to local-DB codes and Google Translate codes. Add new target languages here. |
| `PREFERRED_OCR_LANGS` | `eng, vie, chi_sim, …` | Tesseract language packs the app will try to load. |

### Adding a new target language

```python
LANG_MAP = {
    # ...
    "Italian": {"db": "it", "gt": "it"},
}
```

Then install the matching Tesseract language pack (`ita`) and append it to `PREFERRED_OCR_LANGS`.

---

## 🗂️ Project Structure

```text
.
├── snipping_tool.py    # Main application (capture, OCR, translation, UI)
├── database.json       # Local glossary (editable)
├── history.json        # Translation history (auto-managed)
├── requirements.txt    # Python dependencies
└── capture.png         # Last captured region (auto-generated, overwritten each time)
```

---

## 🩺 Troubleshooting

<details>
<summary><b><code>TesseractNotFoundError</code> or OCR returns nothing</b></summary>

Make sure Tesseract is installed and the path in `snipping_tool.py` points to the correct `tesseract.exe`.

</details>

<details>
<summary><b>"No text detected in the captured area"</b></summary>

- Drag a slightly larger selection with some margin around the text.
- Make sure the Tesseract language pack for the text you are capturing is installed (e.g. `chi_sim` for Simplified Chinese).
- Very low-contrast or highly stylized text may not be recognized.

</details>

<details>
<summary><b>The F8 hotkey does not respond</b></summary>

- Another application may be using the same key — change `HOTKEY_SNIP`.
- Some elevated (administrator) windows block global hotkeys from non-elevated apps. Try running the script from an elevated terminal.

</details>

<details>
<summary><b>Translation shows <code>Error (...)</code></b></summary>

The Google Translate fallback requires an internet connection. Terms found in your local glossary still work offline.

</details>

<details>
<summary><b>Chinese text has strange spacing or wrong characters</b></summary>

The app already removes spurious spaces between CJK characters. For better accuracy, install `chi_sim` / `chi_tra` and capture text at a reasonable size.

</details>

---

## 🔒 Privacy

- Screenshots are processed **locally** — OCR runs on your machine through Tesseract.
- Only the **extracted text** of lines that are *not* resolved by the local glossary is sent to Google Translate via `deep-translator`.
- History and glossary are stored as plain JSON files next to the script. Use **Clear All** in the History view to delete your history.

---

## 🗺️ Roadmap

- [ ] Multi-monitor support (currently the primary display only)
- [ ] User-configurable hotkey and settings UI
- [ ] Optional offline translation backend
- [ ] Packaged `.exe` release with a bundled installer
- [ ] Custom tray icon

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the project
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m "Add amazing feature"`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">

If you find this project useful, please consider giving it a ⭐

</div>
