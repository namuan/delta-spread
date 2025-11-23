COLOR_BG_WHITE = "#FFFFFF"
COLOR_TEXT_PRIMARY = "#333333"
COLOR_PRIMARY = "#3B82F6"
COLOR_PRIMARY_HOVER = "#2563EB"
COLOR_ACCENT_BLUE = "#5CACEE"
COLOR_SUCCESS_GREEN = "#22C55E"
COLOR_DANGER_RED = "#DC2626"
COLOR_GRAY_100 = "#EAEAEA"
COLOR_GRAY_200 = "#DDD"
COLOR_GRAY_300 = "#CCC"
COLOR_GRAY_400 = "#BBB"
COLOR_GRAY_500 = "#AAA"
COLOR_GRAY_600 = "#888"
COLOR_GRAY_700 = "#777"
COLOR_GRAY_800 = "#666"
COLOR_GRAY_900 = "#555"

APP_STYLE = f"background-color: {COLOR_BG_WHITE}; color: {COLOR_TEXT_PRIMARY};"

BUTTON_PRIMARY_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}
    """

TIMELINE_FRAME_STYLE = f"background-color: {COLOR_GRAY_100}; border-radius: 3px;"
HLINE_STYLE = f"color: {COLOR_GRAY_400};"
MONTH_LABEL_STYLE = f"color: {COLOR_GRAY_900}; font-weight: bold; font-size: 12px;"
MONTH_BAR_STYLE = (
    f"background: {COLOR_GRAY_200}; color: {COLOR_GRAY_900}; border-radius: 6px;"
    " padding: 2px 8px; font-weight: bold; font-size: 12px;"
)

SYMBOL_INPUT_STYLE = f"border: 1px solid {COLOR_GRAY_300}; border-radius: 3px; padding: 3px; font-weight: bold;"
PRICE_LABEL_STYLE = "font-size: 16px; font-weight: bold;"
CHANGE_LABEL_STYLE = (
    f"color: {COLOR_SUCCESS_GREEN}; font-size: 11px; font-weight: bold;"
)
REALTIME_LABEL_STYLE = f"color: {COLOR_GRAY_600};"
RT_HELP_STYLE = f"border: 1px solid {COLOR_GRAY_500}; border-radius: 7px; min-width: 14px; min-height: 14px; qproperty-alignment: AlignCenter; font-size: 10px; color: {COLOR_GRAY_900};"
EXP_LABEL_STYLE = "font-size: 12px;"

DAY_BTN_STYLE = f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: bold;"
DAY_BTN_SELECTED_STYLE = f"background-color: {COLOR_ACCENT_BLUE}; color: white; border-radius: 2px; padding: 2px 5px;"

METRIC_TITLE_STYLE = f"color: {COLOR_GRAY_800}; font-size: 10px; font-weight: bold;"
METRIC_ICON_STYLE = "font-size: 12px;"
METRIC_SUBTEXT_STYLE = f"color: {COLOR_GRAY_800}; font-size: 10px;"

CHART_ARROW_STYLE = f"color: {COLOR_GRAY_300}; font-size: 20px;"

MENU_STYLE = f"QMenu {{ background: white; border: 1px solid {COLOR_GRAY_300}; }}"
MENU_ROW_HOVER_STYLE = "QWidget:hover { background: #F5F5F5; }"

REFRESH_LABEL_STYLE = (
    f"background: {COLOR_GRAY_300}; border-radius: 8px; color: white; padding: 2px;"
)
AVERAGE_BUTTON_STYLE = f"background: {COLOR_GRAY_700}; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;"
IV_LABEL_STYLE = "font-size: 11px;"
MARKER_LABEL_STYLE = f"color: {COLOR_GRAY_600}; font-size: 9px;"

DATE_SLIDER_QSS = f"""
    QSlider::groove:horizontal {{ height: 6px; background: {COLOR_GRAY_200}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {COLOR_GRAY_600}; width: 12px; margin: -3px 0; border-radius: 6px; }}
    """

RANGE_SLIDER_QSS = f"""
    QSlider::groove:horizontal {{ height: 4px; background: {COLOR_GRAY_200}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {COLOR_ACCENT_BLUE}; width: 6px; height: 15px; margin: -6px 0; border-radius: 0px; }}
    QSlider::sub-page:horizontal {{ background: {COLOR_ACCENT_BLUE}; }}
    """
