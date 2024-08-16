import sqlite3
import os
import sys
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QTabBar, QMenu, QAction, QLineEdit, QStatusBar, QToolBar
from PyQt5.QtWebEngineWidgets import QWebEngineView

class FixedWidthTabBar(QTabBar):
    def __init__(self, parent=None):
        super(FixedWidthTabBar, self).__init__(parent)
        self.tab_width = 200
        self.parent = parent

    def tabSizeHint(self, index):
        size = super(FixedWidthTabBar, self).tabSizeHint(index)
        size.setWidth(self.tab_width)
        return size

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.tabBarClicked(event.pos())
        super(FixedWidthTabBar, self).mousePressEvent(event)

    def tabBarClicked(self, pos):
        index = self.tabAt(pos)
        if index != -1:
            menu = QMenu(self)
            close_action = QAction("Close", self)
            close_action.triggered.connect(lambda: self.parent.close_current_tab(index))
            menu.addAction(close_action)

            duplicate_action = QAction("Duplicate", self)
            duplicate_action.triggered.connect(lambda: self.parent.duplicate_tab(index))
            menu.addAction(duplicate_action)

            refresh_action = QAction("Refresh", self)
            refresh_action.triggered.connect(lambda: self.parent.refresh_tab(index))
            menu.addAction(refresh_action)

            mute_action = QAction("Mute/Unmute", self)
            mute_action.triggered.connect(lambda: self.parent.toggle_mute_tab(index))
            menu.addAction(mute_action)

            menu.exec_(self.mapToGlobal(pos))

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.tabs = QTabWidget()
        self.tabs.setTabBar(FixedWidthTabBar(self))
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        back_btn = QAction(QIcon('resources/icons/back.png'), 'Back', self)
        back_btn.setStatusTip("Back to previous page")
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(back_btn)

        forward_btn = QAction(QIcon('resources/icons/forward.png'), 'Forward', self)
        forward_btn.setStatusTip("Forward to next page")
        forward_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(forward_btn)

        reload_btn = QAction(QIcon('resources/icons/reload.png'), 'Reload', self)
        reload_btn.setStatusTip("Reload page")
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(reload_btn)

        home_btn = QAction(QIcon('resources/icons/home.png'), 'Home', self)
        home_btn.setStatusTip("Go home")
        home_btn.triggered.connect(self.navigate_home)
        navtb.addAction(home_btn)

        navtb.addSeparator()

        self.urlBar = QLineEdit()
        self.urlBar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlBar)

        stop_btn = QAction('Stop', self)
        stop_btn.setStatusTip("Stop loading current page")
        stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        navtb.addAction(stop_btn)

        menu_btn = QAction(QIcon('resources/icons/menu.png'), 'Menu', self)
        menu_btn.setStatusTip("Open menu")
        menu_btn.triggered.connect(self.show_menu)
        navtb.addAction(menu_btn)

        self.add_new_tab(QUrl.fromLocalFile(os.path.abspath('resources/okostartpage/index.html')), 'Home')
        self.show()
        self.setWindowTitle('Oko Browser')
        self.setWindowIcon(QIcon("resources/icons/main.png"))
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
            }
            QWidget {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QTabWidget {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QTabBar {
                background-color: #1C1C1C;
                color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: #1C1C1C;
                color: #FFFFFF;
                padding: 10px 20px;
                border: 1px solid #444;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
            }
            QTabBar::tab:hover {
                background-color: #333;
            }
            QTabBar::tab:selected {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border-bottom: 1px solid #2E2E2E;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QLineEdit {
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #555;
            }
        """)

    def add_new_tab(self, qurl=None, label="Blank"):
        if qurl is None:
            qurl = QUrl('http://www.google.com')

        browser = QWebEngineView()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.update_tab_icon(i, browser)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))
        browser.iconChanged.connect(lambda icon, i=i: self.update_tab_icon(i, browser))

        # Сохранение истории при каждом изменении URL
        browser.urlChanged.connect(lambda qurl: self.save_history(browser.page().title(), qurl))

        self.tabs.setTabIcon(i, browser.icon())
        browser.loadFinished.connect(lambda success: self.handle_load_finished(success))

    def update_favicon(self, page):
        # Обновляем иконку вкладки на основе favicon страницы
        icon = page.icon()
        if not icon.isNull():
            return icon
        return QIcon('resources/icons/blank.png')

    def update_tab_icon(self, index, browser):
        page = browser.page()
        icon = self.update_favicon(page)
        if page.isAudioMuted():
            icon = QIcon('resources/icons/mute.png')
        self.tabs.setTabIcon(index, icon)

    def save_history(self, title, url):
        db_path = 'resources/userdata/history.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO history (title, url) VALUES (?, ?)', (title, url.toString()))
        conn.commit()
        conn.close()

    def tab_open_doubleclick(self, i):
        if i == -1:
            self.add_new_tab()

    def current_tab_changed(self, i):
        qurl = self.tabs.currentWidget().url()
        self.update_urlbar(qurl, self.tabs.currentWidget())
        self.update_title(self.tabs.currentWidget())

    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(i)

    def duplicate_tab(self, i):
        browser = self.tabs.widget(i)
        self.add_new_tab(browser.url(), browser.page().title())

    def refresh_tab(self, i):
        self.tabs.widget(i).reload()

    def toggle_mute_tab(self, i):
        page = self.tabs.widget(i).page()
        is_muted = page.isAudioMuted()
        page.setAudioMuted(not is_muted)  # Используем isAudioMuted()

        self.update_tab_icon(i, self.tabs.widget(i))  # Обновляем иконку

    def handle_load_finished(self, success):
        if not success:
            self.tabs.currentWidget().setUrl(QUrl.fromLocalFile(os.path.abspath('resources/html/error.html')))

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl.fromLocalFile(os.path.abspath('resources/okostartpage/index.html')))

    def navigate_to_url(self):
        q = QUrl(self.urlBar.text())
        if q.scheme() == "":
            q.setScheme("http")
        self.tabs.currentWidget().setUrl(q)

    def update_urlbar(self, q, browser=None):
        if browser is None:
            browser = self.tabs.currentWidget()
        self.urlBar.setText(q.toString())
        self.urlBar.setCursorPosition(0)

    def update_title(self, browser):
        title = browser.page().title()
        self.setWindowTitle(title if title else 'Oko Browser')

    def show_menu(self):
        menu = QMenu(self)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        history_action = QAction("History", self)
        history_action.triggered.connect(self.open_history)
        menu.addAction(history_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

        menu.exec_(QCursor.pos())

    def open_settings(self):
        settings_url = QUrl.fromLocalFile(os.path.abspath('resources/html/settings.html'))
        self.add_new_tab(settings_url, 'Settings')

    def open_history(self):
        history_url = QUrl.fromLocalFile(os.path.abspath('resources/html/history.html'))
        self.add_new_tab(history_url, 'History')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec_()
