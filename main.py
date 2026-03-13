import sys
import os, json, re, time, math, requests, ssl, socket, subprocess, shutil
import PyQt5
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork, QtSvg
from time import sleep
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

script_dir = os.path.dirname(os.path.abspath(__file__))
pydir = script_dir
#pydir = os.path.dirname(script_dir)
#pydir = pydir+"/Resources"

blox_name = "bloxv333"


#-------------------- Worker --------------------#
class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    text = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.func(self.signals, *self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

#-------------------- Custom Widgets --------------------#
class ClickableSVGWidget(QtSvg.QSvgWidget):
    clicked=pyqtSignal()

    def mousePressEvent(self, ev):
        self.clicked.emit()

class LineNumberArea(QWidget):
    """Small gutter widget to paint line numbers."""
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return self.codeEditor.lineNumberAreaSize()

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CustomTextEdit(QPlainTextEdit):
    def __init__(self, *args, caret_color="#ff4b8b", blink_speed=1000, **kwargs):
        super().__init__(*args, **kwargs)

        self.caret_color = QColor(caret_color)
        self.start_time = time.time()
        self._blink_speed = blink_speed
        self._typing_pause = False
        self._last_input_time = time.time()
        self._save_path = f"{pydir}/Bin/socks5.txt"

        # Caret animation timer
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._update_blink)
        self._blink_timer.start(16)

        # Line number area
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.textChanged.connect(self._on_text_changed)

        # Style
        self.setStyleSheet("""
            QPlainTextEdit {
                background: #9580ad;
                color: #29242f;
                border-right: 2px solid #372e42;
                outline: none;
                border-bottom-left-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12pt;
            }
        """)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        # Load text from file
        if os.path.exists(self._save_path):
            with open(self._save_path, "r", encoding="utf-8", errors="ignore") as f:
                self.setPlainText(f.read())

    # ---------- Line Number Area Logic ----------
    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        fm = self.fontMetrics()
        return 10 + fm.horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#7d6997"))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        fm = self.fontMetrics()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#292231"))
                painter.drawText(0, top, self.lineNumberArea.width() - 4, fm.height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    # ---------- Save & Caret ----------
    def _on_text_changed(self):
        self._typing_pause = True
        self._last_input_time = time.time()
        self._save_text_to_file()

    def _save_text_to_file(self):
        try:
            with open(self._save_path, "w", encoding="utf-8") as f:
                f.write(self.toPlainText())
        except Exception as e:
            print("[Alstolfo-TextEdit]: Save failed:", e)

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#a48cbf")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def _update_blink(self):
        now = time.time()
        if self._typing_pause and now - self._last_input_time > 1.2:
            self._typing_pause = False
            self.start_time = now
        if self.hasFocus():
            self.viewport().update(self.cursorRect())

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasFocus():
            return

        painter = QPainter(self.viewport())
        if self._typing_pause:
            alpha = 255
        else:
            elapsed = (time.time() - self.start_time) * 1000
            alpha = 100 + int((math.sin(2 * math.pi * elapsed / self._blink_speed) + 1) / 2 * (255 - 100))

        color = QColor(self.caret_color)
        color.setAlpha(alpha)
        rect = self.cursorRect()
        rect.setWidth(3)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 1.5, 1.5)
        painter.end()

class SteuerQComboBox(QComboBox):
    def showPopup(self):
        super().showPopup()
        popup = self.findChild(QFrame)
        if not popup:
            return
        popup.move(self.mapToGlobal(QPoint(0, self.height())))
        popup.resize(self.width(), popup.height())
        popup.setStyleSheet("""
            QFrame {
                border-top: 1px solid #29242f;
            }
        """)

#-------------------- Window --------------------#
class Window(QWidget):
    def __init__(self, parent=None):
       super(Window, self).__init__(parent)
       self.setWindowFlags(Qt.FramelessWindowHint)
       self.setAttribute(Qt.WA_TranslucentBackground)
       screen = QApplication.primaryScreen()
       size = screen.size()
       self.w= size.width()/2
       self.h= size.height()/2
       self.setFixedWidth(800)
       self.setFixedHeight(550)
       self.move(self.w-800/2,self.h-550/2)

       cornerCurve = "6"

       #Back Frame/ Bottom Frame
       self.backFrame = BackFrame(self)
       self.backFrame.setFixedWidth(800); self.backFrame.setFixedHeight(500)
       self.backFrame.setStyleSheet("QFrame{border-image: url("+pydir+"/Bin/mybg.png) 0 0 0 0 stretch stretch; background:#6e607e; border-bottom-left-radius:"+cornerCurve+"px; border-bottom-right-radius:"+cornerCurve+"px;}")
       self.backFrame.move(0,50)

       #Top Frame
       self.topFrame = TopFrame(self)
       self.topFrame.setObjectName("objTopFrame")
       self.topFrame.setStyleSheet("QFrame{background:#6e607e; border-top-left-radius:"+cornerCurve+"px; border-top-right-radius:"+cornerCurve+"px; border-bottom:2px solid #372e42}")
       self.topFrame.setFixedWidth(800); self.topFrame.setFixedHeight(50)

       #Vars for Minimizing and Restoring Window
       self._RestoreCounter = 0
       self._Minimized = False
       self.winX = 0
       self.winY = 0

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() == Qt.WindowMinimized:
                print("[DEBUG]: Window Minimized")
                self._Minimized = True
                return

            if self.windowState() == Qt.WindowNoState:
                if self._RestoreCounter == 2:
                    print("[DEBUG]: Window Restored")
                    self._RestoreCounter = 0
                    return
                else:
                    self._RestoreCounter += 1

            elif self._Minimized == True:
                self.showNormal()
                self.setWindowState(Qt.WindowNoState)
                QApplication.processEvents()
                self.setWindowFlag(Qt.FramelessWindowHint, True)
                QApplication.processEvents()
                self.window().move(self.winX,self.winY)
                QApplication.processEvents()
                self._Minimized = False
                QApplication.processEvents()
                return

    def minimizeWindow(self):
        self.winX = self.window().x()
        self.winY = self.window().y()

        self.setWindowFlag(Qt.FramelessWindowHint, False)
        self.showMinimized()
        self.setWindowState(Qt.WindowMinimized)
        QApplication.processEvents()

#-------------------- Main Window --------------------#
class TopFrame(QFrame):
    def __init__(self,parent=None):
        super(TopFrame, self).__init__(parent)
        #---    Close Button     ---#
        self.closeBtn = ClickableSVGWidget(f"{pydir}/Bin/x.svg", self)
        self.closeBtn.setFixedWidth(30); self.closeBtn.setFixedHeight(30)
        self.closeBtn.move(760,10)

        #---    Minimize Button     ---#
        self.minimizeBtn = ClickableSVGWidget(f"{pydir}/Bin/minus.svg", self)
        self.minimizeBtn.setFixedWidth(30); self.minimizeBtn.setFixedHeight(30)
        self.minimizeBtn.move(720,10)

        #Close and Minimize button functions
        self.closeBtn.clicked.connect(lambda: sys.exit())
        self.minimizeBtn.clicked.connect(lambda: self.parent().minimizeWindow())

        #Fix for minimizing without moving window
        self.initial_pos = None

        #---    Window Title     ---#
        self.wTitle = QLabel("Alstolfo Launcher v1.0",self)
        self.wTitle.move(10,5)
        self.wTitle.setStyleSheet("color:#dbe3dc; font-size:30px;border:none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_pos = event.pos()
        super().mousePressEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.initial_pos is not None:
            delta = event.pos() - self.initial_pos
            self.window().move(self.window().x() + delta.x(), self.window().y() + delta.y())
        super().mouseMoveEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.initial_pos = None
        super().mouseReleaseEvent(event)
        event.accept()

class BackFrame(QFrame):
    def __init__(self,parent=None):
        super(BackFrame, self).__init__(parent)
        #---------- Settings ----------#
        self.SETTINGS_PATH = f"{pydir}/Bin/settings.json"
        self.DEFAULT_SETTINGS = {
            "AUTO_UPDATE": False,
            "DEFAULT_TO_AUTO": True,
            "CLOSE_ON_LAUNCH": True
        }
        self.settings = {}
        self.load_settings()

        self.validate_file()

        self._PROXY = "Auto"

        #---------- Styling ----------#
        self.button_style = """
            QPushButton {
                color:#29242f;
                font-size:16px;
                border-radius:8px;
                background:#997db9;
            }
            QPushButton:hover{
                background:#ad97c7;
            }
            QPushButton:pressed{
                background: #7a6494;
            }
        """

        self.checkbox_style = """
            QCheckBox:indicator{
                background-color:#997db9;
            }
            QCheckBox:indicator:checked{
                border-image: url("""+pydir+"""/Bin/check.svg) 0 0 0 0 stretch stretch;
            }
            QCheckBox{
                color:#29242f;
                font-size:16px;border-radius:8px;
            }
        """

        self.comboBox_style = """
            QComboBox {
                color: #29242f;
                padding-left:6px;
                background: #997db9;
                border-radius: 6px;
                combobox-popup: 0;
                border-style:none;
            }
            QComboBox::drop-down {
                width: 15px;
                image: url("""+pydir+"""/Bin/down-arrow.svg);
                border-left-width: 1px;
                border-left-color: #29242f;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QAbstractItemView {
                border-top: solid 2px #29242f;
                selection-background-color:#b8a4ce;
                background:#997db9;
                color:#29242f;
                border-bottom-left-radius:6px;
                border-bottom-right-radius:6px;
            }
            QComboBox:on{
                border-bottom-left-radius:0px;
                border-bottom-right-radius:0px;
            }
        """

        #---------- Buttons & Stuff ----------#
        self.startBtn = QPushButton("Start",self)
        self.startBtn.setFixedWidth(150); self.startBtn.setFixedHeight(50)
        self.startBtn.move(50,50)
        self.startBtn.setStyleSheet(self.button_style)
        self.startBtn.clicked.connect(self.start_roblox)
        self.add_shadow(self.startBtn)

        self.updateBtn = QPushButton("Update/Re-Install",self)
        self.updateBtn.setFixedWidth(150); self.updateBtn.setFixedHeight(50)
        self.updateBtn.move(50,125)
        self.updateBtn.setStyleSheet(self.button_style)
        self.add_shadow(self.updateBtn)
        self.updateBtn.clicked.connect(self.update_roblox)

        self.manageProxiesBtn = QPushButton("Manage Proxies",self)
        self.manageProxiesBtn.setFixedWidth(150); self.manageProxiesBtn.setFixedHeight(50)
        self.manageProxiesBtn.move(50,200)
        self.manageProxiesBtn.setStyleSheet(self.button_style)
        self.manageProxiesBtn.clicked.connect(self.manage_proxies_popup)
        self.add_shadow(self.manageProxiesBtn)

        self.autoUpdateChkbx = QCheckBox("Auto Update",self)
        self.autoUpdateChkbx.setFixedWidth(200); self.autoUpdateChkbx.setFixedHeight(50)
        self.autoUpdateChkbx.move(50,350)
        self.autoUpdateChkbx.setStyleSheet(self.checkbox_style)
        self.autoUpdateChkbx.setChecked(self.settings["AUTO_UPDATE"])
        self.autoUpdateChkbx.stateChanged.connect(lambda _: self.change_setting("AUTO_UPDATE", self.autoUpdateChkbx.isChecked()))

        self.defaultToAutoChkbx = QCheckBox("Default To Auto",self)
        self.defaultToAutoChkbx.setFixedWidth(200); self.defaultToAutoChkbx.setFixedHeight(50)
        self.defaultToAutoChkbx.move(50,400)
        self.defaultToAutoChkbx.setStyleSheet(self.checkbox_style)
        self.defaultToAutoChkbx.setChecked(self.settings["DEFAULT_TO_AUTO"])
        self.defaultToAutoChkbx.stateChanged.connect(lambda _: self.change_setting("AUTO_GET_PROXIES", self.defaultToAutoChkbx.isChecked()))

        self.closeOnLaunchChkbx = QCheckBox("Close On Launch",self)
        self.closeOnLaunchChkbx.setFixedWidth(200); self.closeOnLaunchChkbx.setFixedHeight(50)
        self.closeOnLaunchChkbx.move(50,450)
        self.closeOnLaunchChkbx.setStyleSheet(self.checkbox_style)
        self.closeOnLaunchChkbx.setChecked(self.settings["CLOSE_ON_LAUNCH"])
        self.closeOnLaunchChkbx.stateChanged.connect(lambda _: self.change_setting("CLOSE_ON_LAUNCH", self.closeOnLaunchChkbx.isChecked()))

    def add_shadow(self, widget, blur_radius=16, x_offset=0, y_offset=2, color=QColor(0, 0, 0, 80)):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(x_offset)
        shadow.setYOffset(y_offset)
        shadow.setColor(color)
        widget.setGraphicsEffect(shadow)

    #---------- Settings Fucntions ----------#
    def load_settings(self):
        if not os.path.exists(self.SETTINGS_PATH):
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings()
            return

        try:
            with open(self.SETTINGS_PATH, "r") as f:
                data = json.load(f)
            for k, v in self.DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            self.settings = data
        except (json.JSONDecodeError, FileNotFoundError):
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings()

    def save_settings(self):
        with open(self.SETTINGS_PATH, "w") as f:
            json.dump(self.settings, f, indent=4)

    def change_setting(self, item, value):
        if item not in self.settings:
            return
        self.settings[item] = bool(value)
        self.save_settings()

    #---------- Proxy Functions ----------#

    def validate_file(self):
        if not os.path.exists(f"{pydir}/Bin/socks5.txt"):
            print("[Alstolfo-File]: socks5.txt Not Found - Creating File")
            with open(f"{pydir}/Bin/socks5.txt","w+") as file:
                pass
            file.close()
        with open(f"{pydir}/Bin/socks5.txt", "r+") as file:
            lines = file.readlines()
        valid_lines = [line for line in lines if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}:\d+", line.strip())]
        file.close()
        with open(f"{pydir}/Bin/socks5.txt", "w+") as file:
            file.writelines(valid_lines)
        file.close()

    def manage_proxies_popup(self):
        self.popup = ProxyMenu(backframe=self)
        self.popup.show()

    #---------- The actual Stuff ----------#

    def update_roblox(self):
        self.UPDpopup = Launcher(backframe=self,what="Download")
        self.UPDpopup.show()

    def start_roblox(self):
        self.UPDpopup = Launcher(backframe=self,what="Launch")
        self.UPDpopup.show()

#-------------------- unoptomized popups --------------------#
class TopBar(QFrame):
    def __init__(self, parent=None, title="Window", width=0,killall=False,backframe=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.dragPos = None
        self.initial_pos = None
        self.killall = killall
        self.backframe = backframe
        # Window title
        self.label = QLabel(title, self)
        self.label.setStyleSheet("color:#dbe3dc; font-size:30px;border:none;")
        self.label.move(10, 5)

        # Close button
        self.closeBtn = ClickableSVGWidget(f"{pydir}/Bin/x.svg", self)
        self.closeBtn.setStyleSheet("background: transparent; color:white;")
        self.closeBtn.setFixedSize(30, 30)
        self.closeBtn.move(width-40, 10)
        self.closeBtn.clicked.connect(self.closePopup)

    def closePopup(self):
        if self.killall:
            self.backframe.parent().close()
            self.parent().close()
        else:
            self.parent().close()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_pos = event.pos()
        super().mousePressEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.initial_pos is not None:
            delta = event.pos() - self.initial_pos
            self.window().move(self.window().x() + delta.x(), self.window().y() + delta.y())
        super().mouseMoveEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.initial_pos = None
        super().mouseReleaseEvent(event)
        event.accept()

class ProxyMenu(QWidget):
    def __init__(self, width=800, height=400, backframe=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().size()
        self.move((screen.width() - width)//2, (screen.height() - height)//2)
        p = backframe
        self.lazyAF = p

        #----- Top Bar -----#
        self.topBar = TopBar(self, "Manage Proxies",width)
        self.topBar.setFixedWidth(800); self.topBar.setFixedHeight(50)
        self.topBar.setStyleSheet("QFrame {background: #6e607e; border-top-left-radius:6px; border-top-right-radius:6px; border-bottom:2px solid #372e42; outline:0;}")

        #----- Main Frame -----#
        self.content = QFrame(self)
        self.content.setFixedWidth(800);self.content.setFixedHeight(400)
        self.content.move(0,50)
        self.content.setStyleSheet("QFrame {background:#8a789e; border-bottom-left-radius:6px; border-bottom-right-radius:6px;border:0; outline:0;}")

        p.validate_file()
        with open(f"{pydir}/Bin/socks5.txt","r+") as file:
            lines = file.readlines()

        self.editBox = CustomTextEdit(self)
        self.editBox.setPlainText("".join(lines))
        self.editBox.setFixedWidth(550);self.editBox.setFixedHeight(400)
        self.editBox.move(0,50)

        self.refreshBtn = QPushButton("Refresh",self)
        self.refreshBtn.setFixedWidth(150); self.refreshBtn.setFixedHeight(50)
        self.refreshBtn.move(600,75)
        self.refreshBtn.setStyleSheet(p.button_style)
        self.refreshBtn.clicked.connect(self.reload_file)
        p.add_shadow(self.refreshBtn)

        self.getProxiesBtn = QPushButton("Get Proxies",self)
        self.getProxiesBtn.setFixedWidth(150); self.getProxiesBtn.setFixedHeight(50)
        self.getProxiesBtn.move(600,150)
        self.getProxiesBtn.setStyleSheet(p.button_style)
        self.getProxiesBtn.clicked.connect(lambda: self.get_proxies_popup(p,"Get"))
        p.add_shadow(self.getProxiesBtn)

        self.testProxiesBtn = QPushButton("Test Proxies",self)
        self.testProxiesBtn.setFixedWidth(150); self.testProxiesBtn.setFixedHeight(50)
        self.testProxiesBtn.move(600,225)
        self.testProxiesBtn.setStyleSheet(p.button_style)
        self.testProxiesBtn.clicked.connect(lambda: self.get_proxies_popup(p,"Test"))
        p.add_shadow(self.testProxiesBtn)

        self.unsetProxyBtn = QPushButton("Get & Test",self)
        self.unsetProxyBtn.setFixedWidth(150); self.unsetProxyBtn.setFixedHeight(50)
        self.unsetProxyBtn.move(600,300)
        self.unsetProxyBtn.setStyleSheet(p.button_style)
        self.unsetProxyBtn.clicked.connect(lambda: self.get_proxies_popup(p,"Get and Test"))
        p.add_shadow(self.unsetProxyBtn)

        self.selectProxyCB = SteuerQComboBox(self)
        self.selectProxyCB.setFixedWidth(150); self.selectProxyCB.setFixedHeight(25)
        self.selectProxyCB.move(600,375)
        self.selectProxyCB.setStyleSheet(p.comboBox_style)
        self.selectProxyCB.currentTextChanged.connect(self.selected_proxy)
        p.add_shadow(self.selectProxyCB)
        self.pop_proxies()

        view_window = self.selectProxyCB.view().window()
        view_window.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        view_window.setAttribute(Qt.WA_TranslucentBackground)

    def selected_proxy(self,value):
        if self.lazyAF._PROXY == value:
            return
        else:
            self.lazyAF._PROXY = value

    def pop_proxies(self):
        # Determine which proxy should be active
        bruh = self.lazyAF._PROXY if self.lazyAF._PROXY not in ("", None) else "Auto"

        self.selectProxyCB.blockSignals(True)
        self.selectProxyCB.clear()

        # Always add "Auto" first
        self.selectProxyCB.addItem("Auto")

        # Load proxies from file
        with open(f"{pydir}/Bin/socks5.txt", "r+", encoding="utf-8") as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]
            self.selectProxyCB.addItems(lines)

        # If current proxy isn't in file, add it (for custom/temporary proxies)
        if bruh not in lines and bruh != "Auto":
            self.selectProxyCB.addItem(bruh)

        # Restore selection
        self.selectProxyCB.setCurrentText(bruh)
        self.lazyAF._PROXY = bruh

        self.selectProxyCB.blockSignals(False)



    def get_proxies_popup(self, bf, wt):
        self.popup = ManageProxies(backframe=bf,what=wt)
        self.popup.show()

    def reload_file(self):
        with open(f"{pydir}/Bin/socks5.txt","r+") as file:
            lines = file.readlines()
            self.editBox.setPlainText("".join(lines))
        file.close()
        self.pop_proxies()

class ManageProxies(QWidget):
    def __init__(self, width=600, height=200, backframe=None, what=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().size()
        self.move((screen.width() - width)//2, (screen.height() - height)//2)
        p = backframe
        self.threadpool = QThreadPool()

        #----- Top Bar -----#
        self.topBar = TopBar(self, "Manage Proxies",width)
        self.topBar.setFixedWidth(600); self.topBar.setFixedHeight(50)
        self.topBar.setStyleSheet("QFrame {background: #6e607e; border-top-left-radius:6px; border-top-right-radius:6px; border-bottom:2px solid #372e42; outline:0;}")

        #----- Main Frame -----#
        self.content = QFrame(self)
        self.content.setFixedWidth(600);self.content.setFixedHeight(200)
        self.content.move(0,50)
        self.content.setStyleSheet("QFrame {background:#8a789e; border-bottom-left-radius:6px; border-bottom-right-radius:6px;border:0; outline:0;}")

        if hasattr(p, "validate_file"):
            p.validate_file()

        #img = QLabel(self.content)
        #pixmap = QPixmap('./image.png').scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        #img.setPixmap(pixmap)
        #img.move(25, 25)

        img = QLabel(self.content)
        movie = QMovie(f'{pydir}/Bin/hm.gif')
        movie.setScaledSize(QSize(150, 150))  # scale the animation
        img.setMovie(movie)
        img.move(25, 25)
        movie.start()

        self.whatLabel = QLabel("Loading Script...", self.content)
        self.whatLabel.setGeometry(200, 75, 350, 50)
        self.whatLabel.setStyleSheet("font-size:20px;")

        self.progress = QProgressBar(self.content)
        self.progress.setGeometry(200, 100, 350, 50)

        self.SOCKS5_SOURCES = [
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/socks5_checked.txt",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/socks5/data.txt"
        ]

        self.OUTPUT_FILE = f"{pydir}/Bin/socks5.txt"
        self._MODE = 1
        self._TIMEOUT = 1.0
        self._MAX_WORKERS = 20
        self._MAX_MS = 1500
        self._Bruh = what

        QTimer.singleShot(200, self.what_am_i_doing)

    # ---------- Flow Control ---------- #
    def what_am_i_doing(self):
        if self._Bruh == "Get":
            self.start_scrape()
        elif self._Bruh == "Test":
            self.start_test()
        elif self._Bruh == "Get and Test":
            self.start_scrape(then_test=True)

    # ---------- Helper ---------- #
    def clean_proxy_line(self, line):
        if not line:
            return ""
        s = line.strip()
        s = re.sub(r'^(?:socks5?h?|https?|http)://', '', s, flags=re.I)
        if "@" in s:
            s = s.split("@", 1)[1]
        s = s.strip().rstrip("/")
        if re.fullmatch(r"[A-Za-z0-9\.\-]+:\d{1,5}", s):
            try:
                port = int(s.split(":")[-1])
                if 1 <= port <= 65535:
                    return s
            except Exception:
                return ""
        return ""

    # ---------- Scrape ---------- #
    def start_scrape(self, then_test=False):
        self.whatLabel.setText("Fetching New Proxies...")
        self.progress.setRange(0, len(self.SOCKS5_SOURCES))
        self.progress.setValue(0)

        worker = Worker(self.scrape_socks5, then_test)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.text.connect(self.whatLabel.setText)
        worker.signals.finished.connect(
            lambda: self.start_test() if then_test else self.whatLabel.setText("Done")
        )
        self.threadpool.start(worker)

    def scrape_socks5(self, signals, then_test):
        proxies = set()
        for i, url in enumerate(self.SOCKS5_SOURCES, 1):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                for ln in r.text.splitlines():
                    p = self.clean_proxy_line(ln)
                    if p:
                        proxies.add(p)
                signals.progress.emit(i)
            except Exception:
                signals.progress.emit(i)
                continue

        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, "r") as f:
                for ln in f:
                    c = self.clean_proxy_line(ln)
                    if c:
                        proxies.add(c)

        with open(self.OUTPUT_FILE, "w") as f:
            f.write("\n".join(sorted(proxies)))

        signals.text.emit(f"[Alstolfo-Proxy]: Saved {len(proxies)} proxies")
        signals.finished.emit()

    # ---------- Test ---------- #
    def start_test(self):
        if not os.path.isfile(self.OUTPUT_FILE):
            self.whatLabel.setText("No proxy file found!")
            return

        with open(self.OUTPUT_FILE, "r", encoding="utf-8") as f:
            proxies = [p.strip() for p in f if p.strip()]

        self.whatLabel.setText("Testing Proxies...")
        self.progress.setRange(0, len(proxies))
        self.progress.setValue(0)

        worker = Worker(self.check_proxies_concurrent, proxies)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.text.connect(self.whatLabel.setText)
        worker.signals.finished.connect(lambda: self.whatLabel.setText("Finished"))
        self.threadpool.start(worker)

    def check_proxies_concurrent(self, signals, proxies):
        results = []
        total = len(proxies)

        def check(proxy):
            proxies_cfg = {"http": f"socks5h://{proxy}", "https": f"socks5h://{proxy}"}
            url = "https://clientsettingscdn.roblox.com/v2/client-version/MacPlayer"
            try:
                start = time.time()
                r = requests.get(url, proxies=proxies_cfg, timeout=self._TIMEOUT, verify=True)
                if r.status_code == 200:
                    ms = int((time.time() - start) * 1000)
                    if ms < self._MAX_MS:  # Only include proxies faster than max_ms
                        return proxy, ms
            except Exception:
                pass
            return None, None

        with ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as ex:
            for idx, fut in enumerate(as_completed([ex.submit(check, p) for p in proxies]), 1):
                proxy, ms = fut.result()
                if proxy and ms is not None:
                    results.append((proxy, ms))
                    print(f"[+] {proxy} -> {ms}ms")
                signals.progress.emit(idx)

        # Sort proxies by latency (lowest ms first)
        results.sort(key=lambda x: x[1])

        # Save only the proxy addresses (no ms or comments)
        with open(self.OUTPUT_FILE, "w") as f:
            f.write("\n".join(proxy for proxy, _ in results))

        print(f"\n[Alstolfo-Proxy]: {len(results)} working SOCKS5 proxies under {self._MAX_MS}ms\n")
        signals.text.emit(f"[Alstolfo-Proxy]: Done - {len(results)} proxies saved.")
        signals.finished.emit()

#Reskin of ManageProxies and could easily be one class but whatever
class Launcher(QWidget):
    def __init__(self, width=600, height=200, backframe=None, what=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().size()
        self.move((screen.width() - width)//2, (screen.height() - height)//2)
        self.bf = backframe
        self.pluhh = what
        self.threadpool = QThreadPool()

        #----- Top Bar -----#
        self.topBar = TopBar(self, "Downloader/Launcher",width,killall=True,backframe=self.bf)
        self.topBar.setFixedWidth(600); self.topBar.setFixedHeight(50)
        self.topBar.setStyleSheet("QFrame {background: #6e607e; border-top-left-radius:6px; border-top-right-radius:6px; border-bottom:2px solid #372e42; outline:0;}")

        #----- Main Frame -----#
        self.content = QFrame(self)
        self.content.setFixedWidth(600);self.content.setFixedHeight(200)
        self.content.move(0,50)
        self.content.setStyleSheet("QFrame {background:#8a789e; border-bottom-left-radius:6px; border-bottom-right-radius:6px;border:0; outline:0;}")

        img = QLabel(self.content)
        movie = QMovie(f'{pydir}/Bin/hm.gif')
        movie.setScaledSize(QSize(150, 150))  # scale the animation
        img.setMovie(movie)
        img.move(25, 25)
        movie.start()

        self.whatLabel = QLabel("Loading Script...", self.content)
        self.whatLabel.setGeometry(200, 50, 350, 50)
        self.whatLabel.setStyleSheet("font-size:20px;")

        self.progress = QProgressBar(self.content)
        self.progress.setGeometry(200, 75, 350, 50)

        self.switchToAutoBtn = QPushButton("Switch To Auto",self)
        self.switchToAutoBtn.setGeometry(200, 175, 150, 50)
        self.switchToAutoBtn.setStyleSheet(self.bf.button_style)
        self.switchToAutoBtn.clicked.connect(self.switch_to_auto)
        self.bf.add_shadow(self.switchToAutoBtn)
        self.switchToAutoBtn.hide()

        self.returnBtn = QPushButton("Return",self)
        self.returnBtn.setGeometry(400, 175, 150, 50)
        self.returnBtn.setStyleSheet(self.bf.button_style)
        self.returnBtn.clicked.connect(self.go_back)
        self.bf.add_shadow(self.returnBtn)

        self.pList = []
        self.active = None
        self.auto = False
        self.loop = QEventLoop()

        #QTimer.singleShot(200, self.what_doing)
        self.what_doing()

    def go_back(self):
        self.bf.parent().show()
        self.close()
    def switch_to_auto(self):
        self.active = self.pList[0]
        self.auto = True
        self.loop.quit()
        self.whatLabel.setText("Continuing Task...")

    def what_doing(self):
        if self.bf.settings["CLOSE_ON_LAUNCH"]:
            self.bf.parent().hide()
        self.load_proxies()
        sleep(0.2)
        self.show()
        QApplication.processEvents()
        if self.pluhh == "Download":
            print("Download")
            self.download()
        elif self.pluhh == "Launch":
            print("Launch")
            print("setQuitOnLastWindowClosed: False")
            QApplication.setQuitOnLastWindowClosed(True)
            self.launch()
        elif self.pluhh == "Download and Launch":
            pass

    def load_proxies(self):
        with open(f"{pydir}/Bin/socks5.txt") as f:
            proxies = f.readlines()
            proxies = [x.strip() for x in proxies]
            self.pList = proxies
        if self.bf._PROXY == "Auto":
            self.active = self.pList[0]
            print(f"set active to[Auto]: {self.pList[0]} altRef: {self.active}")
            self.auto = True
        else:
            self.active = self.bf._PROXY
            print(f"set active to[NoAuto]: {self.active}")

    def download(self):
        def task(signals):
            version = None
            most_likely_valid = None

            def run(cmd):
                return subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            def fetchVersion(x):
                proxies_cfg = {"http": f"socks5h://{x.strip()}", "https": f"socks5h://{x.strip()}"}
                try:
                    r = requests.get("https://clientsettingscdn.roblox.com/v2/client-version/MacPlayer", proxies=proxies_cfg, timeout=1.5, verify=True)
                    if r.status_code == 200:
                        data = r.json()
                        version = data.get("clientVersionUpload")
                        most_likely_valid = x.strip()
                        return version, most_likely_valid
                except Exception:
                    return None, None

            def fetchDownload(url, proxy):
                #self.whatLabel.setText("Connecting/Downloading...")
                proxies_cfg = {"http": f"socks5h://{proxy}", "https": f"socks5h://{proxy}"}
                local_filename = url.split("/")[-1]
                try:
                    with requests.get(url, proxies=proxies_cfg, stream=True, timeout=10) as r:
                        r.raise_for_status()
                        total_length = int(r.headers.get("Content-Length", 0))
                        downloaded = 0
                        with open(f"{pydir}/Game/{local_filename}", "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_length > 0:
                                    percent = int(downloaded * 100 / total_length)
                                    signals.progress.emit(percent)
                    signals.progress.emit(100)
                    return True
                except Exception as e:
                    signals.error.emit(str(e))
                    print(e)
                    return False

            self.whatLabel.setText("Fetching Roblox Version...")
            while len(self.pList) > 0:
                version, most_likely_valid = fetchVersion(self.active)
                if version and most_likely_valid:
                    break
                else:
                    if self.auto or self.bf.settings["DEFAULT_TO_AUTO"]:
                        self.pList.remove(self.active)
                        if not self.pList:
                            self.whatLabel.setText("No proxies left, Try Getting/Testing")
                            return
                        self.active = self.pList[0]
                        self.auto = True
                    else:
                        self.whatLabel.setText("Proxy Failed, Either Switch to Auto or Return")
                        self.pList.remove(self.active)
                        self.loop.exec_()

            if not version or not most_likely_valid:
                self.whatLabel.setText("Failed to fetch version. (You May Close/Return Now)")
                return

            self.whatLabel.setText(f"Downloading RobloxPlayer...")
            print(f"Downloading RobloxPlayer - ClientVersion {version}")
            url = f"https://setup.rbxcdn.com/mac/arm64/{version}-RobloxPlayer.zip"

            ok = fetchDownload(url, most_likely_valid)
            if not ok:
                self.whatLabel.setText("Download failed. Proxy got version but couldn't download.")
                return

            self.whatLabel.setText("Reconfiguring... (Close/Ignore Popup(s))")
            subprocess.run(["unzip", "-o",f"{pydir}/Game/{version}-RobloxPlayer.zip","-d",f"{pydir}/Game"], check=True)

            os.system(f"{pydir}/Game/RobloxPlayer.app/Contents/MacOS/RobloxPlayer")
            if os.path.exists(f"{pydir}/Game/{blox_name}.app"):
                shutil.rmtree(f"{pydir}/Game/{blox_name}.app")
            # Move new app into place
            shutil.move(f"{pydir}/Game/RobloxPlayer.app",
                        f"{pydir}/Game/{blox_name}.app")
            # Rename executable inside
            os.rename(f"{pydir}/Game/{blox_name}.app/Contents/MacOS/RobloxPlayer",
                      f"{pydir}/Game/{blox_name}.app/Contents/MacOS/{blox_name}")
            os.system(f"{pydir}/Game/{blox_name}.app/Contents/MacOS/{blox_name}")
            if self.pluhh == "Download and Launch":
                self.launch()
            else:
                self.whatLabel.setText("Finished Update. (Close Roblox If Opened)")

        # Create worker and connect signals
        worker = Worker(task)
        worker.signals.text.connect(self.whatLabel.setText)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.error.connect(lambda e: self.whatLabel.setText(f"Error: {e}"))
        worker.signals.finished.connect(lambda: print("Worker finished."))

        self.threadpool.start(worker)

    def launch(self):
        import shutil
        from pathlib import Path

        self.whatLabel.setText("Launching...")

        app_path = f"{pydir}/Game/{blox_name}.app/Contents/MacOS/{blox_name}"
        app_dir = os.path.dirname(app_path)

        # Deletes everything inside ~/Library/Logs/Roblox (recursive)
        def wipe_roblox_logs():
            logs_dir = Path.home() / "Library" / "Logs" / "Roblox"
            if not logs_dir.exists():
                return
            for item in logs_dir.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"Failed deleting {item}: {e}")

        # Try to codesign and kill any existing {blox_name} instances
        def prep_process(name=f"{blox_name}"):
            try:
                subprocess.run(
                    ["codesign", "--force", "--deep", "--sign", "-", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=app_dir
                )
            except Exception:
                pass
            try:
                subprocess.run(
                    f"pkill -9 -x {name}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

        # Worker that will run under QThreadPool
        def worker_func(signals, proxy):
            wipe_roblox_logs()
            prep_process(f"{blox_name}")

            try:
                os.chdir(app_dir)
            except Exception:
                pass

            # Environment with proxy applied
            env = os.environ.copy()
            env["all_proxy"] = f"socks5h://{proxy}"

            # ----------------------------------------------------------
            # Launch Roblox (REAL FIX: no wrapper, read stdout directly)
            # ----------------------------------------------------------
            process = subprocess.Popen(
                [app_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid,     # start new session so Python closing doesn't kill child
                text=True,
                bufsize=1
            )

            # Wait for "hello world"
            start = time.time()

            for line in process.stdout:
                line_str = line.strip()
                signals.text.emit(line_str)

                if "hello world :3" in line_str.lower():
                    # Close pipe & detach
                    try:
                        process.stdout.close()
                    except:
                        pass

                    # Start Roblox again in the background, WITHOUT pipes
                    subprocess.Popen(
                        [app_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid,
                        env=env
                    )

                    # Kill the monitored instance (the one we attached to stdout)
                    try:
                        process.terminate()
                    except:
                        pass

                    signals.progress.emit(1)
                    return


                # Timeout
                if time.time() - start > 5:
                    try:
                        prep_process()
                        process.terminate()
                    except Exception:
                        pass
                    signals.progress.emit(0)
                    return

            # If stdout loop ends without hello world
            try:
                process.terminate()
            except Exception:
                pass
            signals.progress.emit(0)
            return

        # attempt kickoff using Worker
        def attempt(proxy):
            worker = Worker(worker_func, proxy)
            worker.signals.text.connect(lambda t: print("OUT:", t))
            worker.signals.progress.connect(lambda result: handle_result(result, proxy))
            worker.signals.error.connect(lambda e: self.whatLabel.setText(f"Error: {e}"))
            self.threadpool.start(worker)

        # handle worker result (runs on main thread)
        def handle_result(result, proxy):
            if result == 1:
                self.whatLabel.setText("Successfully Launched")
                return

            if not self.auto and not self.bf.settings.get("DEFAULT_TO_AUTO", False):
                self.switchToAutoBtn.show()

            if self.auto or self.bf.settings.get("DEFAULT_TO_AUTO", False):
                if proxy in self.pList:
                    self.pList.remove(proxy)

                if not self.pList:
                    self.whatLabel.setText("No proxies left, Try Getting/Testing")
                    return

                self.active = self.pList[0]
                attempt(self.active)
            else:
                self.whatLabel.setText("Proxy Failed, Either Switch to Auto or Return")
                if proxy in self.pList:
                    self.pList.remove(proxy)
                self.loop.exec_()
                attempt(self.active)

        # start first attempt
        attempt(self.active)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    m = Window()
    m.show()
    app.exec_()
