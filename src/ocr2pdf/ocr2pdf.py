import argparse
import time
from pathlib import Path
from fontmod.picker import fz_encode_character_with_system_font
from fontmod.context import FontContext

from PIL import Image
import pypdf
from pypdf import mupdf

from ocr2pdf.common import settings
from ocr2pdf.ocr.ms.page import Page as OCRPage


_format_g = pypdf.format_g

font_ctx = FontContext()


def pick_font(text: str):
    font = None
    for c in text:
        result = fz_encode_character_with_system_font(
            font_ctx, font, ord(c), False, False, False
        )
        if result is None:
            continue
        font, _ = result
    return font


def escapt_font_name(name: str) -> str:
    return name.replace(" ", "_")


def auto_detect_font(text: str) -> tuple[str, str]:
    font = pick_font(text)

    if font is None:
        name, file = "helv", None
    else:
        name, file = escapt_font_name(font.name), str(font.path)
    return name, file


def shape_insert_single_line_text(
    self,
    rect: tuple,
    text: str,
    *,
    fontname: str = "helv",
    fontfile: str | None = None,
    fontsize: float = 11,
    set_simple: int = 0,
    encoding: int = 0,
    color: tuple | None = None,
    fill: tuple | None = None,
    align: int = 0,
    render_mode: int = 0,
    rotate: int = 0,
    morph: tuple | None = None,
    stroke_opacity: float = 1,
    fill_opacity: float = 1,
    oc: int = 0,
) -> dict:
    """Insert a single line of text into a rectangle with adaptive character spacing.

    Args:
        rect -- the rectangle to fill with text
        text -- single line text to be inserted (newlines will be replaced with spaces)
        fontname -- a Base-14 font, font name or '/name'
        fontfile -- name of a font file
        fontsize -- font size
        set_simple -- whether to treat font as simple
        encoding -- font encoding
        color -- RGB stroke color triple
        fill -- RGB fill color triple
        align -- 0=left, 1=center, 2=right
        render_mode -- text rendering control
        rotate -- 0, 90, 180, or 270 degrees
        morph -- morph box with a matrix and a fixpoint
        stroke_opacity -- stroke opacity (0-1)
        fill_opacity -- fill opacity (0-1)
        oc -- optional content reference
        min_char_spacing -- minimum character spacing (negative values make text tighter)
    Returns:
        dict with keys: 'success' (bool), 'char_spacing' (float), 'text_width' (float), 'rect_width' (float)
    """
    rect = pypdf.Rect(rect)
    if rect.is_empty or rect.is_infinite:
        raise ValueError("text box must be finite and not empty")

    # 将多行文本转换为单行（替换换行符为空格）
    text = str(text).replace("\n", " ").replace("\r", " ")
    if not text.strip():
        return {
            "success": False,
            "char_spacing": 0,
            "text_width": 0,
            "rect_width": rect.width,
        }

    # 颜色处理
    color_str = pypdf.ColorCode(color, "c")
    fill_str = pypdf.ColorCode(fill, "f")
    if fill is None and render_mode == 0:  # ensure fill color for 0 Tr
        fill = color
        fill_str = pypdf.ColorCode(color, "f")

    # 可选内容处理
    optcont = self.page._get_optional_content(oc)
    if optcont is not None:
        bdc = "/OC /%s BDC\n" % optcont
        emc = "EMC\n"
    else:
        bdc = emc = ""

    # 透明度处理
    alpha = self.page._set_opacity(CA=stroke_opacity, ca=fill_opacity)
    if alpha is None:
        alpha = ""
    else:
        alpha = "/%s gs\n" % alpha

    # 旋转角度验证
    if rotate % 90 != 0:
        raise ValueError("rotate must be multiple of 90")

    rot = rotate
    while rot < 0:
        rot += 360
    rot = rot % 360

    # 旋转变换矩阵
    cmp90 = "0 1 -1 0 0 0 cm\n"  # rotates counter-clockwise
    cmm90 = "0 -1 1 0 0 0 cm\n"  # rotates clockwise
    cm180 = "-1 0 0 -1 0 0 cm\n"  # rotates by 180 deg.
    height = self.height

    # 字体处理
    fname = fontname
    if fname.startswith("/"):
        fname = fname[1:]

    if fontname == "auto":
        font = auto_detect_font(text)
        pdf = pypdf._as_pdf_document(self.doc)
        font_obj = mupdf.pdf_add_simple_font(pdf, font, encoding)
        xref = mupdf.pdf_to_num(font_obj)
        fontdict = {}  # TODO:
        self.doc.get_char_widths(xref, fontdict=fontdict)
    else:
        xref = self.page.insert_font(
            fontname=fname, fontfile=fontfile, encoding=encoding, set_simple=set_simple
        )

    fontinfo = pypdf.CheckFontInfo(self.doc, xref)

    fontdict = fontinfo[1]
    ordering = fontdict["ordering"]
    simple = fontdict["simple"]
    glyphs = fontdict["glyphs"]
    bfname = fontdict["name"]
    ascender = fontdict["ascender"]
    descender = fontdict["descender"]

    # 处理字符编码限制
    maxcode = max([ord(c) for c in text])
    if simple and maxcode > 255:
        text = "".join([c if ord(c) < 256 else "?" for c in text])

    # 获取字符宽度信息
    glyphs = self.doc.get_char_widths(xref, maxcode + 1)
    if simple and bfname not in ("Symbol", "ZapfDingbats"):
        tj_glyphs = None
    else:
        tj_glyphs = glyphs

    # 计算文本像素长度的函数
    def pixlen(x, char_spacing=0):
        """计算字符串的像素长度，包含字符间距"""
        if ordering < 0:
            base_width = sum([glyphs[ord(c)][1] for c in x]) * fontsize
            # 字符间距 = (字符数 - 1) * char_spacing * fontsize
            spacing_width = (len(x) - 1) * char_spacing * fontsize if len(x) > 1 else 0
            return base_width + spacing_width
        else:
            base_width = len(x) * fontsize
            spacing_width = (len(x) - 1) * char_spacing * fontsize if len(x) > 1 else 0
            return base_width + spacing_width

    # def pixlen(x):
    #     """Calculate pixel length of x."""
    #     if ordering < 0:
    #         return sum([glyphs[ord(c)][1] for c in x]) * fontsize
    #     else:
    #         return len(x) * fontsize

    # 形变处理
    if pypdf.CheckMorph(morph):
        m1 = pypdf.Matrix(
            1, 0, 0, 1, morph[0].x + self.x, self.height - morph[0].y - self.y
        )
        mat = ~m1 * morph[1] * m1
        cm = _format_g(pypdf.JM_TUPLE(mat)) + " cm\n"
    else:
        cm = ""

    # 根据旋转调整坐标和可用宽度
    if rot == 0:  # normal orientation
        point = rect.tl + pypdf.Point(0, fontsize * ascender)
        maxwidth = rect.width
    elif rot == 90:  # rotate counter clockwise
        point = rect.bl + pypdf.Point(fontsize * ascender, 0)
        maxwidth = rect.height
        cm += cmp90
    elif rot == 180:  # text upside down
        point = rect.br + pypdf.Point(0, -fontsize * ascender)
        maxwidth = rect.width
        cm += cm180
    else:  # rotate clockwise (270 or -90)
        point = rect.tr + pypdf.Point(-fontsize * ascender, 0)
        maxwidth = rect.height
        cm += cmm90

    # 计算基础文本宽度（无字符间距）
    base_text_width = pixlen(text)

    # 计算所需的字符间距
    char_spacing = 0.0
    if len(text) > 1:
        dw = maxwidth - base_text_width
        char_spacing = dw / (len(text) - 1)

    # 重新计算实际文本宽度
    actual_text_width = pixlen(text, char_spacing)

    # # 根据对齐方式调整起始位置
    # if align == 1:  # center
    #     offset = (maxwidth - actual_text_width) / 2
    # elif align == 2:  # right
    #     offset = maxwidth - actual_text_width
    # else:  # left align
    #     offset = 0
    offset = 0

    # 调整起始点位置
    if rot == 0:
        point.x += offset
    elif rot == 90:
        point.y -= offset
    elif rot == 180:
        point.x -= offset
    else:  # 270
        point.y += offset

    # 计算PDF坐标系中的位置
    if rot == 90:
        left = height - point.y - self.y
        top = -point.x - self.x
    elif rot == 270:
        left = -height + point.y + self.y
        top = point.x + self.x
    elif rot == 180:
        left = -point.x - self.x
        top = -height + point.y + self.y
    else:
        left = point.x + self.x
        top = height - point.y - self.y

    # 生成PDF内容流
    nres = "\nq\n%s%sBT\n" % (bdc, alpha) + cm
    nres += f"1 0 0 1 {_format_g((left, top))} Tm /{fname} {_format_g(fontsize)} Tf "

    # 设置渲染模式
    if render_mode > 0:
        nres += "%i Tr " % render_mode

    # 设置字符间距（如果需要）
    if abs(char_spacing) > 1e-6:  # 只有当字符间距显著时才设置
        nres += _format_g(char_spacing) + " Tc "

    # 设置颜色
    if color is not None:
        nres += color_str
    if fill is not None:
        nres += fill_str

    # 输出文本
    nres += "%sTJ\n" % pypdf.getTJstr(text, tj_glyphs, simple, ordering)
    nres += "ET\n%sQ\n" % emc

    # 更新形状内容
    self.text_cont += nres
    self.updateRect(rect)

    # 返回结果信息
    result = {
        "success": True,
        "char_spacing": char_spacing,
        "text_width": actual_text_width,
        "rect_width": maxwidth,
        "text_fits": actual_text_width <= maxwidth,
    }

    return result


# ... existing code ...


def insert_single_line_text(
    page: pypdf.Page,
    rect: tuple,
    text: str,
    *,
    fontname: str = "auto",
    fontfile: str | None = None,
    fontsize: float = 11,
    set_simple: int = 0,
    encoding: int = 0,
    color: tuple | None = None,
    fill: tuple | None = None,
    align: int = 0,
    render_mode: int = 0,
    rotate: int = 0,
    morph: tuple | None = None,
    stroke_opacity: float = 1,
    fill_opacity: float = 1,
    oc: int = 0,
    overlay: bool = True,
) -> float:
    """Insert single line text into a given rectangle.

    Notes:
        Creates a Shape object, uses its same-named method and commits it.
    Parameters:
        rect: (rect-like) area to use for text.
        buffer: text to be inserted
        fontname: a Base-14 font, font name or '/name'
        fontfile: name of a font file
        fontsize: font size
        lineheight: overwrite the font property
        color: RGB color triple
        expandtabs: handles tabulators with string function
        align: left, center, right, justified
        rotate: 0, 90, 180, or 270 degrees
        morph: morph box with a matrix and a fixpoint
        overlay: put text in foreground or background
    Returns:
        unused or deficit rectangle area (float)
    """
    img = pypdf.utils.Shape(page)
    rc = img.insert_single_line_text(
        rect,
        text,
        fontname=fontname,
        fontfile=fontfile,
        fontsize=fontsize,
        set_simple=set_simple,
        encoding=encoding,
        color=color,
        fill=fill,
        align=align,
        render_mode=render_mode,
        rotate=rotate,
        morph=morph,
        stroke_opacity=stroke_opacity,
        fill_opacity=fill_opacity,
        oc=oc,
    )
    if rc["success"]:
        img.commit(overlay)
    return rc


pypdf.utils.Shape.insert_single_line_text = shape_insert_single_line_text
pypdf.utils.insert_single_line_text = insert_single_line_text


def ocr2pdf(img_paths: list[Path], pdf_path: Path):
    total_start = time.perf_counter()
    print(f"开始处理 {len(img_paths)} 个图片文件...")

    with pypdf.open() as doc:
        for i, img_path in enumerate(img_paths, 1):
            img_start = time.perf_counter()
            print(f"\n[{i}/{len(img_paths)}] 处理图片: {img_path.name}")

            ocr_path = img_path.with_suffix(".ms.json")
            if not ocr_path.exists():
                print(f"  跳过 - OCR文件不存在: {ocr_path.name}")
                continue

            # OCR结果加载计时
            ocr_load_start = time.perf_counter()
            settings.init_settings(
                input_img_path=img_path,
                output_img_path=img_path.with_suffix(".unused.png"),
            )

            with open(ocr_path, "r", encoding="utf-8") as f:
                ocr_pages = OCRPage.load(f)

            ocr_load_time = time.perf_counter() - ocr_load_start
            print(f"  OCR数据加载耗时: {ocr_load_time:.3f}秒")

            # OCR处理计时
            ocr_process_start = time.perf_counter()
            for ocr_page in ocr_pages:
                ocr_page.dump()

            editor_pages = ocr_pages  # [Page(p) for p in ocr_pages]
            # for page in editor_pages:
            #     page.correct_rect()

            with Image.open(str(settings.get_settings().input_img_path)) as img:
                width, height = img.size
            ocr_process_time = time.perf_counter() - ocr_process_start
            print(f"  OCR数据处理耗时: {ocr_process_time:.3f}秒")

            # PDF生成计时
            pdf_gen_start = time.perf_counter()
            for editor_page in editor_pages:
                page = pypdf.utils.new_page(
                    doc=doc,
                    pno=-1,
                    width=width,
                    height=height,
                )

                # page.insert_font(fontname="msyh", fontfile=fontfile)
                # word_count = 0

                for line in editor_page.lines:
                    text = line.words[0].text
                    for word in line.words[1:]:
                        if len(word.text) > 1:
                            text += " "
                        text += word.text
                        # word_count += 1

                    font_name, font_file = auto_detect_font(text)
                    page.insert_font(fontname=font_name, fontfile=font_file)

                    pypdf.utils.insert_single_line_text(
                        page=page,
                        rect=list(iter(line.rect)),
                        text=text,
                        fontname=font_name,
                        fontsize=line.rect.h / 1.32,
                        align=pypdf.TEXT_ALIGN_JUSTIFY,
                    )

                    # pypdf.utils.draw_rect(
                    #     page=page,
                    #     rect=list(iter(line.rect)),
                    #     stroke_opacity=0.2,
                    # )

                    # for word in line.words:
                    #     pypdf.mupdf.fz_encode_character_with_fallback(None, word.text, 0, 0, )

                    #     rect = word.rect.resize(y0=line.rect.y0, y1=line.rect.y1)
                    #     pypdf.utils.insert_single_line_text(
                    #         page=page,
                    #         rect=list(iter(rect)),
                    #         text=word.text,
                    #         fontname="msyh",
                    #         fontsize=word.rect.h / 1.32,
                    #     )

                    #     pypdf.utils.draw_rect(
                    #         page=page,
                    #         rect=list(iter(rect)),
                    #         stroke_opacity=0.2,
                    #     )

                    #     pypdf.utils.insert_text(
                    #         page=page,
                    #         point=(word.rect.x0, word.rect.y0),
                    #         text=word.text,
                    #         fontsize=word.rect.h * 0.8,
                    #         fontname="msyh",
                    #     )

                    #     word_count += 1
                    #     print(
                    #         f"insert origin={word.rect.p0}, size={word.rect.h * 0.8:2.2f}, text={word.text}"
                    #     )

                # print(f"  插入了 {word_count} 个文字")

            pdf_gen_time = time.perf_counter() - pdf_gen_start
            print(f"  PDF生成耗时: {pdf_gen_time:.3f}秒")

            img_total_time = time.perf_counter() - img_start
            print(f"  图片总耗时: {img_total_time:.3f}秒")

        if doc.page_count == 0:
            print("  没有生成PDF")
            return -1

        # PDF保存计时
        save_start = time.perf_counter()
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(pdf_path))
        save_time = time.perf_counter() - save_start
        print(f"\nPDF保存耗时: {save_time:.3f}秒")

    total_time = time.perf_counter() - total_start
    print(f"\n总耗时: {total_time:.3f}秒")
    print(f"平均每张图片耗时: {total_time / len(img_paths):.3f}秒")
    return 0


if __name__ == "__main__":
    main_start = time.perf_counter()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("input"),
        help="input dir contains .png or an exact input .png",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="output .pdf",
    )
    args = parser.parse_args()

    # 文件查找计时
    file_search_start = time.perf_counter()
    if args.input.is_dir():
        img_paths = [
            _ for _ in args.input.rglob("*.png") if _.with_suffix(".ms.json").exists()
        ]
    elif args.input.with_suffix(".ms.json").exists():
        img_paths = [args.input]
    else:
        raise ValueError(f"input {args.input} is not a valid input")

    file_search_time = time.perf_counter() - file_search_start
    print(f"文件查找耗时: {file_search_time:.3f}秒")
    print(f"找到 {len(img_paths)} 个有效图片文件")

    ocr2pdf(img_paths, args.output)

    main_total_time = time.perf_counter() - main_start
    print(f"\n程序总运行时间: {main_total_time:.3f}秒")
