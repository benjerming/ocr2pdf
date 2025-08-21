from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    """
    Arguments for the program.
    """

    input_img_path: Path
    output_img_path: Path
    dump: Path | None = None
    verbose: bool = False
    correct_word_rect: bool = False
    dump_boundary_adjustment_page: bool = False
    dump_boundary_adjustment_line: bool = False
    dump_ocr_word_rect: bool = False
    dump_ocr_line_rect: bool = False
    dump_move_horizontal: bool = False
    dump_delete_text: bool = False
    dump_insert_text: bool = False
    dump_edit_text: bool = False
    dump_layout_analysis: bool = False
    dump_delete_words_in_paragraph: bool = False
    dump_insert_words_in_paragraph: bool = False
    dump_edit_words_in_paragraph: bool = False

    def __post_init__(self):
        self.input_img_path = Path(self.input_img_path)
        self.output_img_path = Path(self.output_img_path)
        self.dump = Path(self.dump) if self.dump is not None else None


# 单例模式实现，保持向后兼容
_settings_instance: Settings | None = None


def init_settings(input_img_path: Path, output_img_path: Path, **args) -> Settings:
    """
    初始化全局参数实例 (为了向后兼容保留)
    """
    global _settings_instance
    _settings_instance = Settings(
        input_img_path=input_img_path,
        output_img_path=output_img_path,
        **args,
    )
    return _settings_instance


def get_settings() -> Settings:
    """
    获取全局参数实例 (为了向后兼容保留)
    """
    assert _settings_instance is not None
    return _settings_instance
