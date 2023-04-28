# -*- coding:UTF-8  -*-
"""
console颜色
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from enum import Enum, unique
from typing import Optional, Self


@unique
class FontStyle(Enum):
    NORMAL: int = 0
    BOLD: int = 1
    FAINT: int = 2
    ITALICS: int = 3
    UNDERLINED: int = 4


@unique
class BackgroudColor(Enum):
    BLACK: int = 40
    RED: int = 41
    GREEN: int = 42
    YELLOW: int = 43
    BLUE: int = 44
    MAGENTA: int = 45
    CYAN: int = 46
    LIGHT_GRAY: int = 47
    GRAY: int = 100
    LIGHT_RED: int = 101
    LIGHT_GREEN: int = 102
    LIGHT_YELLOW: int = 103
    LIGHT_BLUE: int = 104
    LIGHT_MAGENTA: int = 105
    LIGHT_CYAN: int = 106
    WHITE: int = 107


@unique
class ForegroundColor(Enum):
    BLACK: int = 30
    RED: int = 31
    GREEN: int = 32
    YELLOW: int = 33
    BLUE: int = 34
    MAGENTA: int = 35
    CYAN: int = 36
    LIGHT_GRAY: int = 37
    GRAY: int = 90
    LIGHT_RED: int = 91
    LIGHT_GREEN: int = 92
    LIGHT_YELLOW: int = 93
    LIGHT_BLUE: int = 94
    LIGHT_MAGENTA: int = 95
    LIGHT_CYAN: int = 96
    WHITE: int = 97


class ColorFormat:
    def __init__(self, font_style: FontStyle = FontStyle.NORMAL, foreground_color: Optional[ForegroundColor] = None, backgoud_color: Optional[BackgroudColor] = None) -> None:
        self.font_style: FontStyle = font_style
        self.foreground_color: Optional[ForegroundColor] = foreground_color
        self.backgoud_color: Optional[BackgroudColor] = backgoud_color

    def set_font_style(self, font_style: FontStyle = FontStyle.NORMAL) -> Self:
        self.font_style = font_style
        return self

    def set_foreground_color(self, foreground_color: Optional[ForegroundColor] = None) -> Self:
        self.foreground_color = foreground_color
        return self

    def set_backgoud_color(self, backgoud_color: Optional[BackgroudColor] = None) -> Self:
        self.backgoud_color = backgoud_color
        return self

    def fomat(self, message: str) -> str:
        return color(message, font_style=self.font_style, foreground_color=self.foreground_color, backgoud_color=self.backgoud_color)


def color(message: str, font_style: FontStyle = FontStyle.NORMAL, foreground_color: Optional[ForegroundColor] = None, backgoud_color: Optional[BackgroudColor] = None) -> str:
    return "\033[%s;%s%sm%s\033[0m" % (font_style.value,
                                       "" if foreground_color is None else (";" + str(foreground_color.value)),
                                       "" if backgoud_color is None else (";" + str(backgoud_color.value) + "m"),
                                       message)
