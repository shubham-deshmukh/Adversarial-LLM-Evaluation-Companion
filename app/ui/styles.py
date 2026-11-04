"""
Dark modern stylesheet (QSS) for the Adversarial LLM Evaluation Companion.
Designed for high legibility, professional aesthetics, and clear operational state cues.
"""

DARK_THEME_QSS = """
/* Global Window Styling */
QWidget {
    background-color: #121316;
    color: #e4e4e7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Status Banner */
QLabel#status_banner {
    background-color: #1e2025;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 13px;
    text-align: center;
}

/* Section Header Labels */
QLabel.section-header {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 4px;
    margin-bottom: 2px;
}

/* Preview / Edit Text Area */
QPlainTextEdit#preview_box {
    background-color: #18191e;
    color: #f1f5f9;
    border: 1px solid #2e333d;
    border-radius: 8px;
    padding: 10px;
    font-family: "Consolas", "Fira Code", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QPlainTextEdit#preview_box:focus {
    border: 1px solid #3b82f6;
}

/* Base Push Button */
QPushButton {
    background-color: #262930;
    color: #f8fafc;
    border: 1px solid #3b4252;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 600;
    font-size: 12px;
    min-height: 22px;
}

QPushButton:hover {
    background-color: #31353e;
    border-color: #4c566a;
}

QPushButton:pressed {
    background-color: #1e2127;
}

QPushButton:disabled {
    background-color: #18191d;
    color: #4b5563;
    border-color: #23272f;
}

/* Phase 1 Action: Generate Problem */
QPushButton#btn_gen_problem {
    background-color: #1d4ed8;
    border-color: #2563eb;
    color: #ffffff;
}

QPushButton#btn_gen_problem:hover {
    background-color: #2563eb;
    border-color: #3b82f6;
}

QPushButton#btn_gen_problem:pressed {
    background-color: #1e40af;
}

QPushButton#btn_gen_problem:disabled {
    background-color: #1a2234;
    color: #475569;
    border-color: #1e293b;
}

/* Typing Action Buttons */
QPushButton#btn_type_problem, QPushButton#btn_type_solution {
    background-color: #047857;
    border-color: #059669;
    color: #ffffff;
}

QPushButton#btn_type_problem:hover, QPushButton#btn_type_solution:hover {
    background-color: #059669;
    border-color: #10b981;
}

QPushButton#btn_type_problem:pressed, QPushButton#btn_type_solution:pressed {
    background-color: #065f46;
}

QPushButton#btn_type_problem:disabled, QPushButton#btn_type_solution:disabled {
    background-color: #132720;
    color: #335346;
    border-color: #19382c;
}

/* Phase 2 Evaluation Gate */
QPushButton#btn_model_defeated {
    background-color: #6366f1;
    border-color: #4f46e5;
    color: #ffffff;
}

QPushButton#btn_model_defeated:hover {
    background-color: #4f46e5;
    border-color: #4338ca;
}

QPushButton#btn_model_defeated:disabled {
    background-color: #1f213a;
    color: #474a6b;
    border-color: #272a48;
}

QPushButton#btn_model_succeeded {
    background-color: #334155;
    border-color: #475569;
    color: #f1f5f9;
}

QPushButton#btn_model_succeeded:hover {
    background-color: #475569;
    border-color: #64748b;
}

QPushButton#btn_model_succeeded:disabled {
    background-color: #1c222c;
    color: #475569;
    border-color: #232a36;
}

/* Emergency Stop Button - High Priority Crimson */
QPushButton#btn_emergency_stop {
    background-color: #dc2626;
    border: 2px solid #ef4444;
    color: #ffffff;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 10px 14px;
    min-height: 28px;
    border-radius: 8px;
}

QPushButton#btn_emergency_stop:hover {
    background-color: #ef4444;
    border-color: #f87171;
}

QPushButton#btn_emergency_stop:pressed {
    background-color: #991b1b;
    border-color: #b91c1c;
}

/* Subtle Scrollbar */
QScrollBar:vertical {
    background: #121316;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #2e333d;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

