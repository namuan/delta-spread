APP_STYLE = "background-color: #FFFFFF; color: #333333;"

BUTTON_PRIMARY_STYLE = """
    QPushButton {
        background-color: #3B82F6;
        color: white;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #2563EB; }
    """

TIMELINE_FRAME_STYLE = "background-color: #EAEAEA; border-radius: 3px;"
HLINE_STYLE = "color: #BBB;"
MONTH_LABEL_STYLE = "color: #555; font-weight: bold; font-size: 12px;"

SYMBOL_INPUT_STYLE = (
    "border: 1px solid #CCC; border-radius: 3px; padding: 3px; font-weight: bold;"
)
PRICE_LABEL_STYLE = "font-size: 16px; font-weight: bold;"
CHANGE_LABEL_STYLE = "color: #22C55E; font-size: 11px; font-weight: bold;"
REALTIME_LABEL_STYLE = "color: #888;"
RT_HELP_STYLE = "border: 1px solid #AAA; border-radius: 7px; min-width: 14px; min-height: 14px; qproperty-alignment: AlignCenter; font-size: 10px; color: #555;"
EXP_LABEL_STYLE = "font-size: 12px;"

DAY_BTN_STYLE = "color: #333; font-size: 11px; font-weight: bold;"
DAY_BTN_SELECTED_STYLE = (
    "background-color: #5CACEE; color: white; border-radius: 2px; padding: 2px 5px;"
)

METRIC_TITLE_STYLE = "color: #666; font-size: 10px; font-weight: bold;"
METRIC_ICON_STYLE = "font-size: 12px;"
METRIC_SUBTEXT_STYLE = "color: #666; font-size: 10px;"

CHART_ARROW_STYLE = "color: #CCC; font-size: 20px;"

MENU_STYLE = "QMenu { background: white; border: 1px solid #CCC; }"
MENU_ROW_HOVER_STYLE = "QWidget:hover { background: #F5F5F5; }"

REFRESH_LABEL_STYLE = (
    "background: #CCC; border-radius: 8px; color: white; padding: 2px;"
)
AVERAGE_BUTTON_STYLE = "background: #777; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;"
IV_LABEL_STYLE = "font-size: 11px;"
MARKER_LABEL_STYLE = "color: #888; font-size: 9px;"

DATE_SLIDER_QSS = """
    QSlider::groove:horizontal { height: 6px; background: #DDD; border-radius: 3px; }
    QSlider::handle:horizontal { background: #888; width: 12px; margin: -3px 0; border-radius: 6px; }
    """

RANGE_SLIDER_QSS = """
    QSlider::groove:horizontal { height: 4px; background: #DDD; border-radius: 2px; }
    QSlider::handle:horizontal { background: #5CACEE; width: 6px; height: 15px; margin: -6px 0; border-radius: 0px; }
    QSlider::sub-page:horizontal { background: #5CACEE; }
    """
