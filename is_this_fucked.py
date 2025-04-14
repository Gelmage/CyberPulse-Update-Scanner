import sys
import subprocess
import re
import threading
import requests
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer
import pystray
from PIL import Image, ImageDraw

# === Analyze risk via web search ===
def analyze_kb_risk(kb_id):
    danger_keywords = ["bsod", "bootloop", "boot loop", "crash", "black screen", "exploit", "0-day"]
    risk_score = 0

    try:
        query_url = f"https://www.google.com/search?q={kb_id}+site:reddit.com+OR+site:bleepingcomputer.com"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(query_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text().lower()
            for keyword in danger_keywords:
                if keyword in text:
                    risk_score += 1
        if risk_score >= 3:
            return ("❌ Absolutely Fucked", "High-risk: multiple reports of serious issues.")
        elif risk_score in [1, 2]:
            return ("⚠️ Maybe Fucked", "Some users report issues—proceed with caution.")
        else:
            return ("✅ Safe", "No major complaints detected.")
    except Exception as e:
        return ("⚠️ Unknown", f"Error checking online: {e}")

# === Pull installed KB updates ===
def get_installed_kb_updates():
    try:
        cmd = [
            "powershell", "-Command",
            "Get-WmiObject -Query \"Select * from Win32_QuickFixEngineering\" | Select-Object -ExpandProperty HotFixID"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        updates_output = result.stdout
        kb_matches = re.findall(r'KB\d{7}', updates_output)
        return sorted(set(kb_matches))
    except Exception as e:
        return [f"Error fetching updates: {e}"]

# === GUI App ===
class UpdateCheckerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Is This Fucked?")
        self.setMinimumSize(700, 400)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        title = QLabel("Windows Update Risk Scanner")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        self.refresh_btn = QPushButton("Refresh Update List")
        self.refresh_btn.clicked.connect(self.populate_table)
        self.layout.addWidget(self.refresh_btn)

        self.populate_table()

    def populate_table(self):
        updates = get_installed_kb_updates()
        self.table.setRowCount(len(updates))
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Update ID", "Risk Rating", "Summary"])

        for row, kb in enumerate(updates):
            risk, summary = analyze_kb_risk(kb)
            self.table.setItem(row, 0, QTableWidgetItem(kb))
            self.table.setItem(row, 1, QTableWidgetItem(risk))
            self.table.setItem(row, 2, QTableWidgetItem(summary))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

# === Tray Mode Background Scan ===
def run_tray_scan():
    updates = get_installed_kb_updates()
    for kb in updates:
        risk, summary = analyze_kb_risk(kb)
        if "Fucked" in risk:
            show_popup(f"{kb} is flagged: {summary}")
            break  # Stop at first danger alert

def show_popup(message):
    app = QApplication([])
    msg = QMessageBox()
    msg.setWindowTitle("Update Warning!")
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.exec()

def create_tray_icon():
    # Generate a basic icon
    img = Image.new('RGB', (64, 64), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    draw.rectangle((8, 8, 56, 56), fill=(200, 50, 50))
    draw.text((18, 20), "ITF", fill=(255, 255, 255))

    def on_click(icon, item):
        app = QApplication(sys.argv)
        window = UpdateCheckerApp()
        window.show()
        app.exec()

    icon = pystray.Icon("IsThisFucked", img, "Is This Fucked?", menu=pystray.Menu(
        pystray.MenuItem("Open GUI", on_click),
        pystray.MenuItem("Exit", lambda icon, item: icon.stop())
    ))
    threading.Thread(target=run_tray_scan).start()
    icon.run()

# === Choose tray mode or GUI ===
if __name__ == "__main__":
    if "--tray" in sys.argv:
        create_tray_icon()
    else:
        app = QApplication(sys.argv)
        window = UpdateCheckerApp()
        window.show()
        sys.exit(app.exec())
