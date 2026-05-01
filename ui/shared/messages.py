from __future__ import annotations

from PyQt5.QtWidgets import QMessageBox


def show_info(parent, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def show_warning(parent, title: str, message: str) -> None:
    QMessageBox.warning(parent, title, message)


def show_error(
    parent,
    title: str,
    message: str,
    details: str | None = None,
) -> None:
    if details:
        message = f"{message}\n\nDetails:\n{details}"

    QMessageBox.critical(parent, title, message)
