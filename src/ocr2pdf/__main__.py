from pathlib import Path

import fire

from ocr2pdf.ocr2pdf import ocr2pdf


def main(images: list[str], pdf: str):
    ocr2pdf([Path(_) for _ in images], Path(pdf))


if __name__ == "__main__":
    fire.Fire(main)
