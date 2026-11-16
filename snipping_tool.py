# Screen Translator - chụp màn hình rồi dịch chữ
# Bấm F8 để khoanh vùng, chương trình sẽ đọc chữ rồi dịch
#
# Cài thư viện: pip install PyQt5 keyboard pytesseract Pillow thefuzz deep-translator
# Cần cài thêm Tesseract OCR (nhớ chọn thêm các ngôn ngữ Vietnamese, Chinese Simplified, French, German)

import sys
import os
import json
import keyboard
import pytesseract
from PIL import Image
from thefuzz import fuzz
from deep_translator import GoogleTranslator
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QComboBox,
                             QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
                             QSizeGrip, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QIcon, QPixmap


# ============================================================
# Phần cài đặt - muốn đổi gì thì sửa ở đây
# ============================================================

# đường dẫn tới tesseract (cài ở đâu thì sửa lại cho đúng)
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# phím tắt để chụp màn hình
HOTKEY = 'f8'

# điểm giống nhau tối thiểu (%) thì mới lấy kết quả trong database
NGUONG_KHOP = 60

# db = tên ngôn ngữ trong database.json, gt = mã của google translate
LANG_MAP = {
    "Tiếng Việt": {"db": "vi", "gt": "vi"},
    "Tiếng Anh": {"db": "en", "gt": "en"},
    "Tiếng Trung (Simplified)": {"db": "zh", "gt": "zh-CN"},
    "Tiếng Pháp": {"db": "fr", "gt": "fr"},
    "Tiếng Đức": {"db": "de", "gt": "de"}
}

# các ngôn ngữ cho tesseract đọc chữ
OCR_LANG = 'eng+vie+chi_sim+fra+deu'

# lưu mấy câu đã dịch rồi để lần sau khỏi gọi google nữa
cache = {}


# phím tắt chạy ở luồng khác nên phải dùng signal để mở giao diện
class TriggerSignal(QObject):
    snip_signal = pyqtSignal()


trigger = TriggerSignal()


# ============================================================
# Phần xử lý dịch
# ============================================================

def load_database():
    # lấy đường dẫn thư mục chứa file này
    thu_muc = os.path.dirname(os.path.abspath(__file__))
    duong_dan = os.path.join(thu_muc, 'database.json')

    if not os.path.exists(duong_dan):
        print("Không tìm thấy database.json")
        return {}

    try:
        with open(duong_dan, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print("Lỗi đọc database:", e)
        return {}


def co_chu_trung(text):
    # kiểm tra trong chữ có ký tự tiếng Trung không
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            return True
    return False


def tim_trong_db(text, db, db_lang):
    # tìm xem chữ này có giống cái nào trong database không
    diem_cao_nhat = 0
    ket_qua = None

    # chữ ngắn (như Edit với Exit) rất dễ nhầm nên bắt khớp chặt hơn
    nguong = NGUONG_KHOP
    if len(text) <= 5:
        nguong = 90

    for key in db:
        muc = db[key]

        # bỏ qua nếu dữ liệu bị sai định dạng
        if not isinstance(muc, dict):
            continue
        # mục này không có ngôn ngữ cần dịch thì bỏ qua luôn
        if db_lang not in muc:
            continue

        # so với tất cả ngôn ngữ của mục này (en, zh, pinyin, vi...)
        for ngon_ngu in muc:
            gia_tri = muc[ngon_ngu]
            if not isinstance(gia_tri, str):
                continue

            diem = fuzz.ratio(text.lower(), gia_tri.lower())
            if diem >= nguong and diem > diem_cao_nhat:
                diem_cao_nhat = diem
                ket_qua = muc[db_lang]

    return ket_qua, diem_cao_nhat


def dich_dong(text, ten_ngon_ngu, db):
    text = text.strip()
    if text == "":
        return "", "N/A"

    # dịch rồi thì lấy luôn trong cache
    key_cache = (text, ten_ngon_ngu)
    if key_cache in cache:
        return cache[key_cache]

    thong_tin = LANG_MAP.get(ten_ngon_ngu, {"db": "vi", "gt": "vi"})
    db_lang = thong_tin["db"]
    gt_lang = thong_tin["gt"]

    # cách 1: tra trong database trước
    if db:
        ket_qua, diem = tim_trong_db(text, db, db_lang)
        if ket_qua:
            kq = (ket_qua, "DB (" + str(diem) + "%)")
            cache[key_cache] = kq
            return kq

    # cách 2: không có thì nhờ google dịch
    try:
        dich = GoogleTranslator(source='auto', target=gt_lang).translate(text)
        if not dich:
            dich = text
        kq = (dich, "Google")
        cache[key_cache] = kq
        return kq
    except Exception as e:
        # lỗi mạng thì trả lại chữ gốc, không lưu cache
        print("Lỗi google:", e)
        return text, "Lỗi Google"


# ============================================================
# Một dòng kết quả (chữ gốc -> chữ đã dịch)
# ============================================================
class LineItemWidget(QWidget):
    def __init__(self, raw_text, translated_text, nguon):
        super().__init__()
        self.raw_text = raw_text
        self.translated_text = translated_text

        layout = QHBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # chữ gốc
        self.raw_label = QLabel(raw_text)
        self.raw_label.setFont(QFont("Segoe UI", 9))
        self.raw_label.setStyleSheet("color: #89B4FA; font-weight: bold;")
        self.raw_label.setWordWrap(True)

        btn_copy_raw = QPushButton("📋")
        btn_copy_raw.setFixedSize(22, 22)
        btn_copy_raw.setToolTip("Copy từ gốc")
        btn_copy_raw.clicked.connect(self.copy_raw)

        mui_ten = QLabel("➔")
        mui_ten.setStyleSheet("color: #6C7086; border: none;")

        # chữ đã dịch
        self.trans_label = QLabel(translated_text)
        self.trans_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.trans_label.setStyleSheet("color: #A6E3A1;")
        self.trans_label.setWordWrap(True)
        self.trans_label.setToolTip("Nguồn: " + nguon)  # rê chuột vào để xem dịch từ đâu

        btn_copy_trans = QPushButton("📋")
        btn_copy_trans.setFixedSize(22, 22)
        btn_copy_trans.setToolTip("Copy từ đã dịch")
        btn_copy_trans.clicked.connect(self.copy_trans)

        layout.addWidget(self.raw_label, stretch=4)
        layout.addWidget(btn_copy_raw)
        layout.addWidget(mui_ten)
        layout.addWidget(self.trans_label, stretch=5)
        layout.addWidget(btn_copy_trans)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #313244;
                border-radius: 6px;
                border: 1px solid #45475A;
            }
            QLabel { border: none; }
            QPushButton {
                background-color: #45475A;
                border: none;
                border-radius: 3px;
                color: #CDD6F4;
            }
            QPushButton:hover { background-color: #585B70; }
        """)

    def copy_raw(self):
        QApplication.clipboard().setText(self.raw_text)

    def copy_trans(self):
        QApplication.clipboard().setText(self.translated_text)


# ============================================================
# Cửa sổ popup hiện kết quả dịch
# ============================================================
class MultiLineOverlay(QWidget):
    def __init__(self, rect, lines_list):
        super().__init__()
        self.lines_list = []
        for line in lines_list:
            if line.strip():
                self.lines_list.append(line)

        self.db = load_database()  # load lại mỗi lần để sửa database xong khỏi cần mở lại app
        self.old_pos = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # tính kích thước popup theo số dòng
        popup_width = 440
        popup_height = len(self.lines_list) * 52 + 70
        if popup_height < 140:
            popup_height = 140
        if popup_height > 520:
            popup_height = 520

        # đặt popup bên phải vùng đã chụp, hết chỗ thì qua bên trái
        screen_width = QApplication.primaryScreen().geometry().width()
        pos_x = rect.x() + rect.width() + 10
        if pos_x + popup_width > screen_width:
            pos_x = max(10, rect.x() - popup_width - 10)

        self.setGeometry(pos_x, rect.y(), popup_width, popup_height)
        self.setMinimumSize(320, 120)

        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: #1E1E2E;
                border: 2px solid #89B4FA;
                border-radius: 10px;
            }
            QComboBox {
                background-color: #313244;
                color: #89B4FA;
                border: 1px solid #45475A;
                border-radius: 5px;
                padding: 3px 8px;
                font-weight: bold;
            }
            QPushButton#CloseBtn {
                background-color: #F38BA8;
                color: #11111B;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(10, 8, 10, 8)

        # phần trên cùng: chọn ngôn ngữ + nút đóng
        header = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(LANG_MAP.keys()))
        # phải connect SAU khi addItems, không là nó chạy refresh_lines khi chưa tạo xong layout
        self.lang_combo.currentTextChanged.connect(self.refresh_lines)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.close)

        header.addWidget(self.lang_combo)
        header.addStretch()
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # phần danh sách các dòng (có thanh cuộn)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.lines_layout = QVBoxLayout(self.scroll_content)
        self.lines_layout.setContentsMargins(0, 0, 0, 0)
        self.lines_layout.setSpacing(6)

        self.scroll.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll)

        # góc kéo để đổi kích thước
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("background: transparent;")

        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.container)

        self.refresh_lines()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizegrip.move(self.width() - 16, self.height() - 16)

    # 3 hàm dưới để kéo popup đi chỗ khác bằng chuột
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

    def refresh_lines(self):
        # xóa hết các dòng cũ
        while self.lines_layout.count():
            item = self.lines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # dịch lại từng dòng theo ngôn ngữ đang chọn
        target_lang = self.lang_combo.currentText()
        for line in self.lines_list:
            translated, nguon = dich_dong(line, target_lang, self.db)
            row = LineItemWidget(line, translated, nguon)
            self.lines_layout.addWidget(row)

        self.lines_layout.addStretch()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


# ============================================================
# Lớp phủ toàn màn hình để khoanh vùng chụp
# ============================================================
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

    def start_snip(self):
        # đóng popup cũ nếu còn mở
        if self.overlay is not None:
            self.overlay.close()

        # chụp cả màn hình trước rồi mới hiện lớp phủ lên
        screen = QApplication.primaryScreen()
        self.full_screen_pixmap = screen.grabWindow(0)

        self.begin = None
        self.end = None
        self.show()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event):
        painter = QPainter(self)

        if self.full_screen_pixmap:
            painter.drawPixmap(0, 0, self.full_screen_pixmap)

        # phủ màu đen mờ lên cho tối màn hình
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        # vùng đang chọn thì vẽ lại ảnh sáng + viền xanh
        if self.begin and self.end and self.full_screen_pixmap:
            rect = QRect(self.begin, self.end).normalized()
            painter.drawPixmap(rect, self.full_screen_pixmap, rect)

            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.begin is None:
            return

        rect = QRect(self.begin, self.end).normalized()

        # ẩn lớp phủ đi để dùng chuột bình thường lại
        self.hide()

        # vùng chọn quá nhỏ (bấm nhầm) thì bỏ qua
        if rect.width() < 10 or rect.height() < 10:
            return

        lines = self.doc_chu(rect)
        print("Đọc được", len(lines), "dòng")

        if len(lines) == 0:
            print("Không đọc được chữ nào")
            return

        self.overlay = MultiLineOverlay(rect, lines)
        self.overlay.show()

    def doc_chu(self, rect):
        # cắt vùng đã chọn rồi lưu thành file ảnh
        thu_muc = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(thu_muc, 'capture.png')

        cropped = self.full_screen_pixmap.copy(rect)
        cropped.save(image_path, 'png')

        # phóng to ảnh gấp 2 cho tesseract đọc chính xác hơn
        img = Image.open(image_path)
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

        try:
            text = pytesseract.image_to_string(img, lang=OCR_LANG)
        except Exception as e:
            # có thể do chưa cài đủ ngôn ngữ, thử lại với anh + việt thôi
            print("Lỗi OCR:", e)
            try:
                text = pytesseract.image_to_string(img, lang='eng+vie')
            except Exception as e2:
                print("Vẫn lỗi:", e2)
                return []

        # tách thành từng dòng
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line == "":
                continue
            # tesseract hay chèn dấu cách giữa các chữ Hán nên xóa đi
            if co_chu_trung(line):
                line = line.replace(" ", "")
            lines.append(line)

        return lines

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()


# ============================================================
# Điều khiển chung: phím tắt + icon dưới khay hệ thống
# ============================================================
class AppController:
    def __init__(self, app):
        self.app = app
        self.snipper = SnippingWidget()

        trigger.snip_signal.connect(self.snipper.start_snip)
        keyboard.add_hotkey(HOTKEY, self.bam_phim_tat)

        # icon tray (tạm tô màu xanh cho đơn giản)
        self.tray_icon = QSystemTrayIcon()
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#89B4FA"))
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Screen Translator (" + HOTKEY.upper() + ")")

        tray_menu = QMenu()

        snip_action = QAction("✂ Chụp màn hình (Dịch)", self.app)
        snip_action.triggered.connect(self.snipper.start_snip)

        open_db_action = QAction("📂 Mở file database.json", self.app)
        open_db_action.triggered.connect(self.open_database)

        quit_action = QAction("✕ Thoát hẳn", self.app)
        quit_action.triggered.connect(self.app.quit)

        tray_menu.addAction(snip_action)
        tray_menu.addAction(open_db_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def bam_phim_tat(self):
        trigger.snip_signal.emit()

    def open_database(self):
        thu_muc = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(thu_muc, 'database.json')
        if os.path.exists(db_path):
            os.startfile(db_path)  # chỉ chạy trên Windows


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # kiểm tra tesseract có chưa
    if not os.path.exists(TESSERACT_PATH):
        print("Cảnh báo: không thấy Tesseract ở", TESSERACT_PATH)
        print("Sửa lại TESSERACT_PATH ở đầu file nhé")

    controller = AppController(app)

    print("-> Ứng dụng đã chạy ngầm!")
    print("-> Bấm phím [" + HOTKEY.upper() + "] để khoanh vùng dịch.")
    sys.exit(app.exec_())
