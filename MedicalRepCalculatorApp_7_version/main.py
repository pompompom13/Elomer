#!/usr/bin/env python3
"""
Калькулятор времени медицинского представителя
Десктопное приложение на PySide6
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui_main import MainWindow


def main():
    """Основная функция запуска приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("Medical Rep Calculator")
    app.setOrganizationName("MedCalc Inc.")

    # Устанавливаем стиль приложения
    app.setStyle("Fusion")

    # Создаем главное окно
    window = MainWindow()

    # Показываем окно
    window.show()
    window.showMaximized()  # Разворачиваем на весь экран

    # Запускаем главный цикл приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()