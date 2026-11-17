# UI Screen Translator

A lightweight Windows desktop utility built with **Python** and **PyQt5** that captures any screen region via a global hotkey, extracts text using multi-language OCR, and displays instant translations in a floating, draggable overlay.

Designed specifically for translating software interfaces, error messages, and foreign-language UI elements without interrupting workflow.

---

## Demo

> **[Watch Full Demo Video (60s)](#)** *(Replace `#` with your YouTube / Google Drive demo link)*

<!-- Uncomment the line below once you add your demo GIF to the repository -->
<!-- ![UI Screen Translator Demo](assets/demo.gif) -->

---

## Key Features

- **Instant Region Capture (`F8`):** Runs silently in the Windows System Tray with single-instance protection (`QLocalServer`) to prevent duplicate background processes.
- **Auto-Detected Multi-Language OCR:** Automatically scans locally installed Tesseract language packs (`eng`, `vie`, `chi_sim`, `chi_tra`, `jpn`, `kor`, `fra`, `deu`, `rus`, `spa`, `tha`) and applies **2x Lanczos upscaling** prior to recognition for sharper accuracy on small UI fonts.
- **Two-Tier Hybrid Translation Engine:**
  1. **Local UI Glossary (`database.json`):** Uses fuzzy string matching (`thefuzz`, 60% similarity threshold) to match domain-specific interface terms with high accuracy, including **Pinyin** annotations for Simplified Chinese.
  2. **Online Fallback:** Automatically falls back to Google Translate (`deep-translator`) across 11 target languages when a phrase is not found in the local glossary.
- **Clean Floating Overlay:** Frameless, resizable dark-mode pop-up with stacked original/translated cards, text selection, and **dual one-click Copy buttons** (with visual confirmation) for both source and target text.
- **Searchable Language Selector & History:** Type directly inside the target language dropdown to filter languages, or switch to the built-in **History** tab to search and revisit the **100 most recent translations** (`history.json`).

---

## Architecture & Workflow

```text
[Press F8] ──► [Screen Snipping Overlay] ──► [2x Lanczos Image Upscaling]
                                                          │
                                                          ▼
[Floating PyQt5 Pop-up] ◄── [Hybrid Lookup] ◄── [Tesseract Multi-Lang OCR]
         │                    ├─ 1. Local JSON Fuzzy Match (+ Pinyin)
         │                    └─ 2. Google Translate Fallback
         ▼
[Auto-Save to history.json (Latest 100 Entries)]
```

---

## Project Structure

```text
UI_Screen_Translator_Tool/
├── snipping_tool.py    # Main application: tray controller, screen snipper, OCR & PyQt5 overlay
├── database.json       # Local multilingual UI glossary with Pinyin annotations
├── history.json        # Auto-generated at runtime (stores up to 100 recent translations)
├── capture.png         # Auto-generated temporary buffer for the latest screen snip
└── README.md
```

---

## Installation & Setup (Windows)

### 1. Prerequisites
- **Python 3.8+**
- **Tesseract-OCR for Windows:** Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). During installation, select additional language data packs (e.g., Vietnamese, Chinese, Japanese) as needed.
  - Default expected path: `C:\Program Files\Tesseract-OCR\tesseract.exe` *(update `pytesseract.pytesseract.tesseract_cmd` in `snipping_tool.py` if installed elsewhere)*.

### 2. Install Dependencies
```bash
git clone https://github.com/lenghiemgiaphu/UI_Screen_Translator_Tool.git
cd UI_Screen_Translator_Tool
pip install PyQt5 pytesseract Pillow keyboard thefuzz python-Levenshtein deep-translator
```

### 3. Run the Application
```bash
python snipping_tool.py
```
- The app starts minimized in the **Windows System Tray** (blue icon).
- Press **`F8`** anywhere on your screen, drag to select text, and view the translation pop-up.
- Press **`Esc`** to cancel snipping or close the pop-up.

---

## Customizing the Local Glossary (`database.json`)

You can add domain-specific terms or software UI labels to `database.json` for instant offline lookup:

```json
{
  "UI_001": {
    "en": "task manager",
    "zh": "任务管理器",
    "pinyin": "rèn wu guǎn lǐ qì",
    "vi": "Trình quản lý tác vụ"
  }
}
```

---

## License

This project was developed as an independent personal utility for educational and portfolio demonstration purposes.