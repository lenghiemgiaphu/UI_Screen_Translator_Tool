import re
import sys
import os
import json
from datetime import datetime
import keyboard
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QComboBox, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, 
                             QSizeGrip, QSystemTrayIcon, QMenu, QAction,
                             QCompleter, QLineEdit)
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QIcon, QPixmap
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
import pytesseract
from PIL import Image, ImageOps
from thefuzz import fuzz
from deep_translator import GoogleTranslator

# Path to Tesseract OCR executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Capture hotkey & history limit
HOTKEY_SNIP = 'f8'
MAX_HISTORY = 100
APP_SERVER_NAME = "ScreenTranslatorSingleInstance_v2"

LANG_MAP = {
    "English": {"db": "en", "gt": "en"},
    "Vietnamese": {"db": "vi", "gt": "vi"},
    "Chinese (Simplified)": {"db": "zh", "gt": "zh-CN"},
    "Chinese (Traditional)": {"db": "zh", "gt": "zh-TW"},
    "Japanese": {"db": "ja", "gt": "ja"},
    "Korean": {"db": "ko", "gt": "ko"},
    "French": {"db": "fr", "gt": "fr"},
    "German": {"db": "de", "gt": "de"},
    "Spanish": {"db": "es", "gt": "es"},
    "Russian": {"db": "ru", "gt": "ru"},
    "Thai": {"db": "th", "gt": "th"}
}

# Preferred Tesseract OCR language packs to load if installed locally
PREFERRED_OCR_LANGS = ['eng', 'vie', 'chi_sim', 'chi_tra', 'jpn', 'kor', 'fra', 'deu', 'rus', 'spa', 'tha']

# CJK Unicode ranges (Chinese, Japanese, Korean, and full-width punctuation)
CJK_CHAR_CLASS = r'\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u3000-\u303f\uff00-\uffef'


class TriggerSignal(QObject):
    snip_signal = pyqtSignal()


trigger = TriggerSignal()


def get_base_dir():
    return os.path.dirname(os.path.abspath(__file__))


def clean_cjk_spaces(text):
    """Remove spurious spaces inserted by Tesseract between CJK characters."""
    return re.sub(
        rf'(?<=[{CJK_CHAR_CLASS}])\s+(?=[{CJK_CHAR_CLASS}])',
        '',
        text
    )


def prepare_ocr_image(img, scale=2.0, pad=24):
    """Scale image and add background-matched padding so Tesseract does not clip edge characters."""
    rgb_img = img.convert("RGB")
    if scale != 1.0:
        new_w = max(1, int(rgb_img.width * scale))
        new_h = max(1, int(rgb_img.height * scale))
        rgb_img = rgb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    corner_color = rgb_img.getpixel((0, 0))
    return ImageOps.expand(rgb_img, border=pad, fill=corner_color)


def extract_ocr_lines(img, ocr_langs):
    """Multi-pass OCR extraction with automatic PSM and scale fallback for oversized/single-line text."""
    primary_scale = 2.0 if max(img.width, img.height) < 900 else 1.0
    prepared = prepare_ocr_image(img, scale=primary_scale, pad=24)

    for psm in ('--psm 6', '--psm 7', '--psm 11'):
        raw_text = pytesseract.image_to_string(prepared, lang=ocr_langs, config=psm).strip()
        if raw_text:
            return [clean_cjk_spaces(line.strip()) for line in raw_text.split('\n') if line.strip()]

    if img.height > 80:
        down_scale = min(80.0 / img.height, 0.5)
        shrunk = prepare_ocr_image(img, scale=down_scale, pad=24)
        for psm in ('--psm 7', '--psm 6'):
            raw_text = pytesseract.image_to_string(shrunk, lang=ocr_langs, config=psm).strip()
            if raw_text:
                return [clean_cjk_spaces(line.strip()) for line in raw_text.split('\n') if line.strip()]

    return []


def get_available_ocr_langs():
    try:
        installed = pytesseract.get_languages(config='')
        matched = [lang for lang in PREFERRED_OCR_LANGS if lang in installed]
        if matched:
            return '+'.join(matched)
    except Exception:
        pass
    return 'eng+vie'


def load_database():
    db_path = os.path.join(get_base_dir(), 'database.json')
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def load_history():
    hist_path = os.path.join(get_base_dir(), 'history.json')
    if os.path.exists(hist_path):
        try:
            with open(hist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def save_history_entry(target_lang, items):
    if not items:
        return
    history = load_history()
    entry = {
        "time": datetime.now().strftime("%d/%m %H:%M"),
        "target_lang": target_lang,
        "items": items
    }
    history.insert(0, entry)
    history = history[:MAX_HISTORY]

    hist_path = os.path.join(get_base_dir(), 'history.json')
    try:
        with open(hist_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_history_file():
    hist_path = os.path.join(get_base_dir(), 'history.json')
    try:
        with open(hist_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
    except Exception:
        pass


def translate_line(line_text, target_lang_name, db):
    line_text = clean_cjk_spaces(line_text.strip())
    if not line_text:
        return "", "N/A", ""

    lang_info = LANG_MAP.get(target_lang_name, {"db": "en", "gt": "en"})
    db_lang = lang_info["db"]
    gt_lang = lang_info["gt"]

    # Strip trailing keyboard shortcuts (e.g., "New tab Ctrl+T" -> "new tab") and ellipses for glossary lookup
    clean_query = re.sub(r'\s+(ctrl|alt|shift|f\d+)(\+[a-z0-9]+)*$', '', line_text, flags=re.IGNORECASE)
    clean_query = clean_query.rstrip('.…').strip().lower()

    has_cjk_input = bool(re.search(r'[\u4e00-\u9fff]', line_text))

    # 1. Local JSON glossary lookup (threshold 80 to prevent false-positive matches)
    if db and clean_query:
        best_match_score = 0
        best_match_target = None
        best_pinyin = ""

        for item_key, translations in db.items():
            if not isinstance(translations, dict):
                continue

            valid_values = [str(v) for k, v in translations.items() if isinstance(v, str) and k != "pinyin"]
            for val in valid_values:
                normalized_val = clean_cjk_spaces(val).lower()
                score = fuzz.ratio(clean_query, normalized_val)
                if score >= 80 and score > best_match_score:
                    if db_lang in translations:
                        best_match_score = score
                        best_match_target = translations[db_lang]
                        if db_lang == "zh" or has_cjk_input:
                            best_pinyin = translations.get("pinyin", "")
                        else:
                            best_pinyin = ""

        if best_match_target:
            return best_match_target, "Local DB", best_pinyin

    # 2. Online Google Translate fallback (preserves original line_text)
    src_lang = 'zh-CN' if (has_cjk_input and gt_lang not in ('zh-CN', 'zh-TW')) else 'auto'

    try:
        translated = GoogleTranslator(source=src_lang, target=gt_lang).translate(line_text)
        return (translated if translated else line_text), "Google", ""
    except Exception as e:
        return line_text, f"Error ({str(e)[:12]})", ""


class LineItemWidget(QWidget):
    def __init__(self, raw_text, translated_text, pinyin="", meta_tag=""):
        super().__init__()
        self.raw_text = raw_text
        self.translated_text = translated_text

        self.setObjectName("ResultCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(11, 8, 10, 8)
        card_layout.setSpacing(6)

        if meta_tag:
            meta_lbl = QLabel(meta_tag)
            meta_lbl.setStyleSheet("color: #6B7280; font-size: 8pt; background: transparent;")
            card_layout.addWidget(meta_lbl)

        # Attach Pinyin annotation to whichever line contains Chinese characters
        has_cjk_raw = bool(re.search(r'[\u4e00-\u9fff]', raw_text))
        has_cjk_trans = bool(re.search(r'[\u4e00-\u9fff]', translated_text))

        if pinyin and has_cjk_raw:
            display_raw = f"{raw_text}  ({pinyin})"
            display_trans = translated_text
        elif pinyin and has_cjk_trans:
            display_raw = raw_text
            display_trans = f"{translated_text}  ({pinyin})"
        else:
            display_raw = raw_text
            display_trans = translated_text

        # Row 1: Original text + Copy button
        raw_row = QHBoxLayout()
        raw_row.setContentsMargins(0, 0, 0, 0)
        raw_row.setSpacing(8)

        self.raw_label = QLabel(display_raw)
        self.raw_label.setFont(QFont("Segoe UI", 9))
        self.raw_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        self.raw_label.setWordWrap(True)
        self.raw_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.btn_copy_raw = QPushButton("Copy")
        self.btn_copy_raw.setObjectName("CopyRawBtn")
        self.btn_copy_raw.setFixedSize(46, 22)
        self.btn_copy_raw.setCursor(Qt.PointingHandCursor)
        self.btn_copy_raw.setToolTip("Copy original text")
        self.btn_copy_raw.clicked.connect(lambda: self.handle_copy(self.raw_text, self.btn_copy_raw))

        raw_row.addWidget(self.raw_label, stretch=1)
        raw_row.addWidget(self.btn_copy_raw, alignment=Qt.AlignTop)

        # Row 2: Translated text + Copy button
        trans_row = QHBoxLayout()
        trans_row.setContentsMargins(0, 0, 0, 0)
        trans_row.setSpacing(8)

        self.trans_label = QLabel(display_trans)
        self.trans_label.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.trans_label.setStyleSheet("color: #F3F4F6; background: transparent;")
        self.trans_label.setWordWrap(True)
        self.trans_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.btn_copy_trans = QPushButton("Copy")
        self.btn_copy_trans.setObjectName("CopyTransBtn")
        self.btn_copy_trans.setFixedSize(46, 23)
        self.btn_copy_trans.setCursor(Qt.PointingHandCursor)
        self.btn_copy_trans.setToolTip("Copy translation")
        self.btn_copy_trans.clicked.connect(lambda: self.handle_copy(self.translated_text, self.btn_copy_trans))

        trans_row.addWidget(self.trans_label, stretch=1)
        trans_row.addWidget(self.btn_copy_trans, alignment=Qt.AlignTop)

        card_layout.addLayout(raw_row)
        card_layout.addLayout(trans_row)

        self.setStyleSheet("""
            QWidget#ResultCard {
                background-color: #272930;
                border: 1px solid #353842;
                border-radius: 7px;
            }
            QWidget#ResultCard:hover {
                border: 1px solid #4B505E;
                background-color: #2B2E36;
            }
            QPushButton#CopyRawBtn {
                background-color: #2F323B;
                color: #9CA3AF;
                border: 1px solid #3E424E;
                border-radius: 4px;
                font-family: "Segoe UI";
                font-size: 8pt;
            }
            QPushButton#CopyRawBtn:hover {
                background-color: #3B3F4B;
                color: #E5E7EB;
            }
            QPushButton#CopyTransBtn {
                background-color: #373B47;
                color: #E5E7EB;
                border: 1px solid #4A4F5E;
                border-radius: 4px;
                font-family: "Segoe UI";
                font-size: 8pt;
                font-weight: 600;
            }
            QPushButton#CopyTransBtn:hover {
                background-color: #464B59;
                color: #FFFFFF;
            }
        """)

    def handle_copy(self, text, btn):
        QApplication.clipboard().setText(text)
        btn.setText("✓")
        btn.setStyleSheet("""
            background-color: #1E3A2F;
            color: #4ADE80;
            border: 1px solid #2E5A44;
            border-radius: 4px;
            font-size: 8.5pt;
            font-weight: bold;
        """)
        QTimer.singleShot(1000, lambda: self.reset_btn(btn))

    def reset_btn(self, btn):
        btn.setText("Copy")
        btn.setStyleSheet("")


class MultiLineOverlay(QWidget):
    def __init__(self, rect=None, lines_list=None, start_in_history=False):
        super().__init__()
        self.has_capture = rect is not None
        self.lines_list = [line for line in (lines_list or []) if line.strip()]
        self.db = load_database()
        self.old_pos = None
        self.history_mode = start_in_history

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        popup_width = 445
        base_rows = len(self.lines_list) if not start_in_history else 4
        popup_height = min(max(base_rows * 82 + 72, 160), 520)

        screen_geo = QApplication.primaryScreen().geometry()
        if rect is not None:
            pos_x = rect.x() + rect.width() + 12
            if pos_x + popup_width > screen_geo.width():
                pos_x = max(12, rect.x() - popup_width - 12)
            pos_y = min(rect.y(), max(12, screen_geo.height() - popup_height - 20))
        else:
            pos_x = (screen_geo.width() - popup_width) // 2
            pos_y = (screen_geo.height() - popup_height) // 2

        self.setGeometry(pos_x, pos_y, popup_width, popup_height)
        self.setMinimumSize(360, 140)

        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: #1D1E23;
                border: 1px solid #3A3D47;
                border-radius: 10px;
            }
            QLabel#HeaderTitle {
                color: #9CA3AF;
                font-family: "Segoe UI";
                font-size: 8.5pt;
                font-weight: 600;
            }
            QComboBox {
                background-color: #272930;
                color: #F3F4F6;
                border: 1px solid #3A3D47;
                border-radius: 5px;
                padding: 3px 8px;
                font-family: "Segoe UI";
                font-size: 9pt;
                min-width: 160px;
            }
            QComboBox:hover, QComboBox:focus {
                border-color: #5B6275;
            }
            QComboBox QLineEdit {
                background: transparent;
                color: #F3F4F6;
                border: none;
                selection-background-color: #2563EB;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #272930;
                color: #E5E7EB;
                border: 1px solid #454957;
                selection-background-color: #373B47;
                outline: none;
            }
            QLineEdit#HistorySearch {
                background-color: #272930;
                color: #F3F4F6;
                border: 1px solid #3A3D47;
                border-radius: 5px;
                padding: 5px 9px;
                font-family: "Segoe UI";
                font-size: 9pt;
            }
            QLineEdit#HistorySearch:focus {
                border-color: #5B6275;
            }
            QPushButton#HeaderBtn {
                background-color: #272930;
                color: #D1D5DB;
                border: 1px solid #3A3D47;
                border-radius: 5px;
                padding: 3px 9px;
                font-family: "Segoe UI";
                font-size: 8.5pt;
                font-weight: 600;
            }
            QPushButton#HeaderBtn:hover {
                background-color: #32353E;
                color: #FFFFFF;
            }
            QPushButton#HeaderBtn[active="true"] {
                background-color: #2563EB;
                border-color: #2563EB;
                color: #FFFFFF;
            }
            QPushButton#DangerBtn {
                background-color: #2E2326;
                color: #F87171;
                border: 1px solid #4B2E33;
                border-radius: 5px;
                padding: 4px 9px;
                font-size: 8.5pt;
            }
            QPushButton#DangerBtn:hover {
                background-color: #3F282C;
            }
            QPushButton#CloseBtn {
                background-color: transparent;
                color: #9CA3AF;
                border: none;
                border-radius: 5px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton#CloseBtn:hover {
                background-color: #DC2626;
                color: #FFFFFF;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: #3E424E;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(9)

        # Header bar: Target language selector + History button + Close button
        header = QHBoxLayout()
        header.setSpacing(7)

        self.title_lbl = QLabel("Translate to:")
        self.title_lbl.setObjectName("HeaderTitle")

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(LANG_MAP.keys()))
        self.lang_combo.setEditable(True)
        self.lang_combo.setInsertPolicy(QComboBox.NoInsert)
        self.lang_combo.lineEdit().setPlaceholderText("Search language...")

        completer = QCompleter(list(LANG_MAP.keys()), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.lang_combo.setCompleter(completer)
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)

        self.history_btn = QPushButton("History")
        self.history_btn.setObjectName("HeaderBtn")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.setToolTip("View last 100 translations")
        self.history_btn.clicked.connect(self.toggle_history_mode)

        close_btn = QPushButton("×")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close (Esc)")
        close_btn.clicked.connect(self.close)

        header.addWidget(self.title_lbl)
        header.addWidget(self.lang_combo)
        header.addStretch()
        header.addWidget(self.history_btn)
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # Search toolbar for History mode
        self.history_toolbar = QWidget()
        hist_bar_layout = QHBoxLayout(self.history_toolbar)
        hist_bar_layout.setContentsMargins(0, 0, 0, 0)
        hist_bar_layout.setSpacing(6)

        self.history_search = QLineEdit()
        self.history_search.setObjectName("HistorySearch")
        self.history_search.setPlaceholderText("Search translation history...")
        self.history_search.textChanged.connect(self.render_history)

        self.clear_hist_btn = QPushButton("Clear All")
        self.clear_hist_btn.setObjectName("DangerBtn")
        self.clear_hist_btn.setCursor(Qt.PointingHandCursor)
        self.clear_hist_btn.clicked.connect(self.handle_clear_history)

        hist_bar_layout.addWidget(self.history_search, stretch=1)
        hist_bar_layout.addWidget(self.clear_hist_btn)
        main_layout.addWidget(self.history_toolbar)

        # Card scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.viewport().setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")

        self.lines_layout = QVBoxLayout(self.scroll_content)
        self.lines_layout.setContentsMargins(0, 0, 2, 0)
        self.lines_layout.setSpacing(7)

        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("background: transparent;")

        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.container)

        self.update_view_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizegrip.move(self.width() - 16, self.height() - 16)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def clear_cards(self):
        while self.lines_layout.count():
            item = self.lines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_language_changed(self, text):
        if text in LANG_MAP and not self.history_mode:
            self.refresh_lines()

    def toggle_history_mode(self):
        self.history_mode = not self.history_mode
        self.update_view_state()

    def update_view_state(self):
        self.history_btn.setProperty("active", "true" if self.history_mode else "false")
        self.history_btn.style().unpolish(self.history_btn)
        self.history_btn.style().polish(self.history_btn)

        if self.history_mode:
            self.title_lbl.hide()
            self.lang_combo.hide()
            self.history_toolbar.show()
            self.history_btn.setText("Back")
            self.render_history()
        else:
            self.title_lbl.show()
            self.lang_combo.show()
            self.history_toolbar.hide()
            self.history_btn.setText("History")
            self.refresh_lines()

    def refresh_lines(self):
        self.clear_cards()
        target_lang = self.lang_combo.currentText()
        if target_lang not in LANG_MAP:
            target_lang = "English"

        if not self.lines_list:
            msg = (
                "No text detected in the captured area. Press F8 and try dragging a slightly wider selection."
                if self.has_capture
                else "No recent capture. Press F8 to select a screen area."
            )
            empty_lbl = QLabel(msg)
            empty_lbl.setStyleSheet("color: #8E95A5; font-size: 9pt; padding: 8px 2px;")
            empty_lbl.setWordWrap(True)
            self.lines_layout.addWidget(empty_lbl)
        else:
            saved_items = []
            for line in self.lines_list:
                translated, source_info, pinyin = translate_line(line, target_lang, self.db)
                row_widget = LineItemWidget(line, translated, pinyin=pinyin)
                self.lines_layout.addWidget(row_widget)
                saved_items.append({
                    "raw": line,
                    "translated": translated,
                    "pinyin": pinyin
                })
            save_history_entry(target_lang, saved_items)

        self.lines_layout.addStretch()

    def render_history(self):
        self.clear_cards()
        keyword = self.history_search.text().strip().lower()
        history_data = load_history()

        shown_count = 0
        for entry in history_data:
            time_str = entry.get("time", "")
            lang_str = entry.get("target_lang", "")
            for item in entry.get("items", []):
                raw = item.get("raw", "")
                trans = item.get("translated", "")
                pinyin = item.get("pinyin", "")

                if keyword and (keyword not in raw.lower() and keyword not in trans.lower()):
                    continue

                meta = f"{time_str}  •  → {lang_str}"
                card = LineItemWidget(raw, trans, pinyin=pinyin, meta_tag=meta)
                self.lines_layout.addWidget(card)
                shown_count += 1

        if shown_count == 0:
            msg = "No matching results found." if keyword else "History is empty (stores up to the 100 most recent translations)."
            empty_lbl = QLabel(msg)
            empty_lbl.setStyleSheet("color: #8E95A5; font-size: 9pt; padding: 8px 2px;")
            self.lines_layout.addWidget(empty_lbl)

        self.lines_layout.addStretch()

    def handle_clear_history(self):
        clear_history_file()
        self.render_history()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class SnippingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.screen_rect = QApplication.primaryScreen().geometry()
        self.setGeometry(self.screen_rect)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setCursor(Qt.CrossCursor)
        self.begin = None
        self.end = None
        self.full_screen_pixmap = None
        self.overlay = None
        self.ocr_langs = get_available_ocr_langs()

    def start_snip(self):
        if self.isVisible():
            return

        if self.overlay is not None:
            self.overlay.close()

        screen = QApplication.primaryScreen()
        self.screen_rect = screen.geometry()
        self.setGeometry(self.screen_rect)
        self.full_screen_pixmap = screen.grabWindow(0)

        self.begin = None
        self.end = None
        self.show()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.full_screen_pixmap:
            painter.drawPixmap(0, 0, self.full_screen_pixmap)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 115))

        if self.begin and self.end and self.full_screen_pixmap:
            rect = QRect(self.begin, self.end).normalized()
            painter.drawPixmap(rect, self.full_screen_pixmap, rect)

            pen = QPen(QColor(59, 130, 246), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.update()

    def mouseMoveEvent(self, event):
        if self.begin is not None:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None or self.end is None:
            self.hide()
            return

        rect = QRect(self.begin, self.end).normalized()
        self.begin = None
        self.end = None

        self.hide()
        QApplication.processEvents()

        if rect.width() < 10 or rect.height() < 10:
            return

        image_path = os.path.join(get_base_dir(), 'capture.png')
        cropped = self.full_screen_pixmap.copy(rect)
        cropped.save(image_path, 'png')

        with Image.open(image_path) as img:
            lines = extract_ocr_lines(img, self.ocr_langs)

        self.overlay = MultiLineOverlay(rect=rect, lines_list=lines, start_in_history=False)
        self.overlay.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.begin = None
            self.end = None
            self.hide()


class AppController:
    def __init__(self, app):
        self.app = app
        self.snipper = SnippingWidget()
        self.history_window = None

        trigger.snip_signal.connect(self.snipper.start_snip)
        keyboard.add_hotkey(HOTKEY_SNIP, lambda: trigger.snip_signal.emit())

        self.tray_icon = QSystemTrayIcon()
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#2563EB"))
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip(f"Screen Translator ({HOTKEY_SNIP.upper()})")

        tray_menu = QMenu()

        snip_action = QAction(f"Capture Screen to Translate ({HOTKEY_SNIP.upper()})", self.app)
        snip_action.triggered.connect(self.snipper.start_snip)

        history_action = QAction("Translation History (Last 100)", self.app)
        history_action.triggered.connect(self.open_history)

        open_db_action = QAction("Open database.json", self.app)
        open_db_action.triggered.connect(self.open_database)

        quit_action = QAction("Exit", self.app)
        quit_action.triggered.connect(self.app.quit)

        tray_menu.addAction(snip_action)
        tray_menu.addAction(history_action)
        tray_menu.addAction(open_db_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def open_history(self):
        if self.history_window is not None:
            self.history_window.close()
        self.history_window = MultiLineOverlay(rect=None, lines_list=[], start_in_history=True)
        self.history_window.show()

    def open_database(self):
        db_path = os.path.join(get_base_dir(), 'database.json')
        if os.path.exists(db_path):
            os.startfile(db_path)


def replace_existing_instance(app):
    """Terminate any existing background instance so duplicate overlays do not spawn."""
    socket = QLocalSocket()
    socket.connectToServer(APP_SERVER_NAME)
    if socket.waitForConnected(250):
        socket.write(b"QUIT")
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()

    QLocalServer.removeServer(APP_SERVER_NAME)
    server = QLocalServer(app)
    server.listen(APP_SERVER_NAME)

    def handle_new_connection():
        client = server.nextPendingConnection()
        if client and client.waitForReadyRead(250):
            if client.readAll().data() == b"QUIT":
                app.quit()

    server.newConnection.connect(handle_new_connection)
    return server


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    _server = replace_existing_instance(app)
    controller = AppController(app)

    print(f"-> Screen Translator is running in background (OCR: {controller.snipper.ocr_langs})")
    print(f"-> Press [{HOTKEY_SNIP.upper()}] to capture and translate.")
    sys.exit(app.exec_())
