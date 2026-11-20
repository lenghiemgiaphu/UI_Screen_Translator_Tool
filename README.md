<div align="center">

# Screen Translator

**Press a hotkey, drag over any text on your screen, and read the translation right next to it — OCR and a curated local glossary first, Google Translate as fallback.**

Windows • Python • PyQt5 • Tesseract OCR

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-41CD52?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PyQt5/)
[![Tesseract](https://img.shields.io/badge/OCR-Tesseract-4B8BBE?style=flat-square)](https://github.com/UB-Mannheim/tesseract/wiki)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat-square&logo=windows&logoColor=white)](#5-installation)
[![Languages](https://img.shields.io/badge/Target%20Languages-11-F59E0B?style=flat-square)](#21-supported-languages)
[![License](https://img.shields.io/badge/License-MIT-16A34A?style=flat-square)](#11-license)

[✨ Features](#2-features) • [⚙️ How It Works](#3-how-it-works) • [🚀 Installation](#5-installation) • [📚 Glossary](#7-local-glossary-databasejson) • [⚠️ Limitations](#9-scope-limitations--caveats)

</div>

---

## 1. Overview

Screen Translator is a lightweight tray application for Windows. Press **F8**, drag a rectangle over text anywhere on the screen — a game, a PDF, a video, an application menu — and a compact, always-on-top window appears beside your selection showing each recognized line with its translation.

It is built for people who read foreign-language content all day and do not want to copy text by hand or switch to a browser to translate a single line.

**What makes it different**

1. **Hybrid translation.** Each line is matched against a user-editable **local glossary** first (fuzzy, ≥ 80 % similarity), so UI terms and domain vocabulary stay consistent and work offline. Only unmatched lines go to **Google Translate**.
2. **OCR built for short, awkward text.** Multi-pass Tesseract with automatic fallback page-segmentation modes, 2× upscaling and background-matched padding recovers single lines, menu items and small fonts that a single pass misses.
3. **Chinese-aware.** Removes the spurious spaces Tesseract inserts between CJK characters and shows **Pinyin** when the glossary provides it.
4. **Zero-friction workflow.** Global hotkey, live target-language switching, one-click copy, and a searchable history of the last 100 translations.

---

## 2. Features

| Feature | Description |
| :--- | :--- |
| **Global hotkey capture** | Start a snip from anywhere with `F8`, even while the app sits in the system tray. |
| **Multi-pass OCR** | Retries with Tesseract `--psm 6 → 7 → 11` and scaled images to recover text blocks, single lines and sparse text. |
| **Smart preprocessing** | Upscales small captures 2× and pads with the detected background color so edge characters are not clipped. |
| **Automatic language-pack detection** | Loads every installed pack from the supported list together (e.g. `eng+vie+chi_sim`). |
| **Local glossary** | Fuzzy matching against `database.json` with normalization of case, trailing ellipses and keyboard shortcuts (`New tab Ctrl+T` → `new tab`). |
| **Google Translate fallback** | Via [`deep-translator`](https://pypi.org/project/deep-translator/) for anything the glossary cannot resolve. |
| **Pinyin display** | Shown for Chinese text when the matching glossary entry has a `pinyin` field. |
| **Live language switching** | Searchable dropdown; results re-translate instantly. |
| **One-click copy** | Copy the original or the translation per line, with visual confirmation. |
| **History** | Browse, search and clear the last 100 translations. |
| **Single-instance guard** | Starting the app again cleanly replaces the previous background instance. |
| **Tray menu** | Capture, open history, open the glossary, or exit. |

### 2.1 Supported Languages

English · Vietnamese · Chinese (Simplified) · Chinese (Traditional) · Japanese · Korean · French · German · Spanish · Russian · Thai

---

## 3. How It Works

```text
   F8 hotkey / tray menu
            |
            v
+---------------------------+     +------------------------------+     +---------------------------+
| 1. Region selector        | --> | 2. Preprocess + Tesseract    | --> | 3. Line-by-line pipeline  |
|    frozen screenshot of   |     |    2x upscale, padding,      |     |    clean CJK spacing,     |
|    the primary display    |     |    PSM 6 -> 7 -> 11 retries  |     |    normalize text         |
+---------------------------+     +------------------------------+     +-------------+-------------+
                                                                                      |
                                              +---------------------------------------+------+
                                              v                                              v
                               +-----------------------------+              +--------------------------+
                               | 4a. Local glossary          |  no match    | 4b. Google Translate     |
                               |     fuzzy ratio >= 80       | -----------> |     (deep-translator)    |
                               |     source = "Local DB"     |              |     source = "Google"    |
                               +--------------+--------------+              +-------------+------------+
                                              |                                           |
                                              +---------------------+---------------------+
                                                                    v
                                              +------------------------------------------+
                                              | 5. Floating result window + history.json |
                                              +------------------------------------------+
```

1. **Capture** — a frozen screenshot of the primary display is shown under a dim overlay while you drag a selection (`Esc` cancels).
2. **Recognize** — the crop is preprocessed and passed to Tesseract using all installed, supported language packs.
3. **Translate** — each line is looked up in the glossary; if there is no confident match it is sent to Google Translate.
4. **Display & store** — results appear next to the selection and are appended to `history.json` (capped at 100 entries).

---

## 4. Requirements

| Component | Requirement |
| :--- | :--- |
| **OS** | Windows 10 / 11 |
| **Python** | 3.9 or newer |
| **Tesseract OCR** | Installed locally, with the language packs you need |
| **Internet** | Only for the Google Translate fallback; glossary hits work offline |

**Python packages**

| Package | Purpose |
| :--- | :--- |
| `PyQt5` | GUI, system tray, screen capture |
| `pytesseract` | Tesseract wrapper |
| `Pillow` | Image processing |
| `deep-translator` | Google Translate client |
| `thefuzz` | Fuzzy matching for the glossary |
| `keyboard` | Global hotkey |

> ⚠️ Make sure your `requirements.txt` lists **all six** packages (`keyboard` and `thefuzz` included), otherwise `pip install -r requirements.txt` produces an incomplete environment:
>
> ```text
> PyQt5>=5.15.9
> pytesseract>=0.3.10
> Pillow>=10.0.0
> deep-translator>=1.11.4
> thefuzz>=0.20.0
> keyboard>=0.13.5
> ```

---

## 5. Installation

**1. Install Tesseract OCR** from the [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki). During setup, tick the extra language data you need. The app uses whichever of these packs are installed:

```text
eng  vie  chi_sim  chi_tra  jpn  kor  fra  deu  rus  spa  tha
```

By default the app expects `C:\Program Files\Tesseract-OCR\tesseract.exe` (see [Configuration](#8-configuration) to change it).

**2. Clone and set up**

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Run**

```bash
python snipping_tool.py
```

Expected console output:

```text
-> Screen Translator is running in background (OCR: eng+vie+chi_sim+...)
-> Press [F8] to capture and translate.
```

The app now lives in the system tray.

---

## 6. Usage

1. Press **`F8`** or choose *Capture Screen to Translate* from the tray menu.
2. **Click and drag** over the text. `Esc` cancels.
3. Release — the result window opens beside your selection.
4. Choose a **target language** from the dropdown (type to search); results update instantly.
5. Use **Copy** to copy the original or the translation of any line.
6. Open **History** to browse and search past translations, or **Clear All** to delete them.
7. Move the window by dragging, resize it from the bottom-right grip, close it with `Esc` or **×**.

| Tray action | Effect |
| :--- | :--- |
| Capture Screen to Translate (F8) | Starts a new snip |
| Translation History (Last 100) | Opens the history viewer |
| Open database.json | Opens the glossary in your default editor |
| Exit | Quits the app |

---

## 7. Local Glossary (`database.json`)

The glossary gives you deterministic control over specific terms — ideal for **software UI strings, game terminology and domain vocabulary** where machine translation is inconsistent.

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

**Matching rules**

- Every text value of an entry (except `pinyin`) is a searchable source term; the entry must also contain the **target language** code to be used.
- Input is normalized (lower-case; trailing shortcuts such as `Ctrl+T` and trailing `.` / `…` removed) and compared with fuzzy matching. A score of **80 or higher** is a match and is labelled `Local DB`; everything else is `Google`.
- The glossary is re-read each time you start a capture, so edits apply on the next `F8`.

| Language | Code | Language | Code |
| :--- | :---: | :--- | :---: |
| English | `en` | Korean | `ko` |
| Vietnamese | `vi` | French | `fr` |
| Chinese | `zh` | German | `de` |
| Japanese | `ja` | Spanish | `es` |
| Russian | `ru` | Thai | `th` |

The bundled glossary contains 14 common browser-menu terms (Settings, History, Downloads, Extensions, …) in English, Chinese (with Pinyin) and Vietnamese, as a template for your own entries.

---

## 8. Configuration

Settings are constants near the top of `snipping_tool.py`:

| Constant | Default | Purpose |
| :--- | :--- | :--- |
| `pytesseract.pytesseract.tesseract_cmd` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Path to `tesseract.exe` |
| `HOTKEY_SNIP` | `'f8'` | Global capture hotkey (e.g. `'ctrl+shift+t'`) |
| `MAX_HISTORY` | `100` | Maximum stored history entries |
| `LANG_MAP` | 11 languages | Display name → glossary code and Google Translate code |
| `PREFERRED_OCR_LANGS` | `eng, vie, chi_sim, …` | Tesseract packs the app tries to load |

To add a target language, extend `LANG_MAP` (for example `"Italian": {"db": "it", "gt": "it"}`), install the matching Tesseract pack (`ita`) and append it to `PREFERRED_OCR_LANGS`.

---

## 9. Scope, Limitations & Caveats

1. **Windows only.** The app relies on Windows-specific calls (opening files with the default editor) and a Windows Tesseract path.
2. **Primary monitor only.** Capture uses the primary display; selections on secondary monitors are not supported.
3. **OCR quality varies.** Low-contrast, stylized, rotated or very small text may be misread. Each line is translated independently, so multi-line sentences lose context.
4. **Google Translate dependency.** `deep-translator` uses Google's web endpoint, which is unofficial for this use: it needs internet and may be rate-limited or change without notice. Glossary matches are unaffected.
5. **Hotkey constraints.** Global hotkeys may not reach elevated (administrator) windows unless the script is also run elevated; `F8` may conflict with other applications.
6. **Fixed configuration.** Hotkey and Tesseract path are edited in source; there is no settings UI yet.
7. **Plain-text storage.** History and glossary are plain JSON next to the script; `capture.png` is overwritten on every capture.

**Roadmap (proposed)**

- [ ] Multi-monitor support
- [ ] Settings UI (hotkey, Tesseract path, OCR languages)
- [ ] Optional offline translation backend
- [ ] Packaged `.exe` installer
- [ ] Cross-platform support (macOS / Linux)

---

## 10. Privacy

- Screenshots are processed **locally**; OCR runs on your machine through Tesseract.
- Only the recognized **text** of lines not resolved by the glossary is sent to Google Translate.
- History is stored locally in `history.json`; use **Clear All** to delete it.

---

## 11. Project Structure & Contributing

```text
.
├── snipping_tool.py    # Application: capture, OCR, translation, UI
├── database.json       # Editable local glossary
├── history.json        # Translation history (auto-managed)
├── requirements.txt    # Python dependencies
└── capture.png         # Last captured region (generated)
```

Contributions are welcome: fork the repo, create a branch (`git checkout -b feature/your-feature`), commit, push, and open a pull request. Add `capture.png` and `history.json` to `.gitignore`.

**License:** distributed under the **MIT License** — see [`LICENSE`](./LICENSE).

---

<div align="center">

If you find this project useful, please consider giving it a ⭐

</div>
