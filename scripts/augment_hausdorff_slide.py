"""补全第 15 页的 Hausdorff 维数覆盖图，并输出一个副本。"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Pt


SOURCE = Path("fractal_ppt_outline_template.pptx")
OUTPUT = Path("fractal_ppt_outline_template_hausdorff.pptx")

TEAL = RGBColor(0x00, 0x80, 0x80)
INK = RGBColor(0x18, 0x22, 0x31)
MUTED = RGBColor(0x5C, 0x66, 0x70)
MINT = RGBColor(0xE2, 0xF4, 0xF2)
GOLD = RGBColor(0xE2, 0xB2, 0x48)
PALE_GOLD = RGBColor(0xFC, 0xF4, 0xDC)


def set_text(shape, text, *, size, color=INK, bold=False, align=PP_ALIGN.LEFT):
    """设置单段文字，统一补充图解的排版。"""
    frame = shape.text_frame
    frame.clear()
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = text
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_label(slide, x, y, w, h, text, *, fill, color=INK, size=10, rounded=True):
    """新增说明标签，强调覆盖尺度与临界指数。"""
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if rounded else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    set_text(shape, text, size=size, color=color, bold=True, align=PP_ALIGN.CENTER)
    return shape


def main():
    presentation = Presentation(SOURCE)
    slide = presentation.slides[14]

    # 例子标题改为“覆盖数 + 成本”的阅读顺序，和上一页的定义直接衔接。
    set_text(slide.shapes[3], "例 1：线段的临界指数", size=13, color=TEAL, bold=True)
    set_text(slide.shapes[8], "把长度 1 的线段分成 4 段\n每段直径 r = 1/4", size=11, color=MUTED)
    set_text(slide.shapes[9], "4·(1/4)^s = 4^(1−s)\n临界 s = 1  →  H¹ 有限且非零", size=13, color=INK, bold=True, align=PP_ALIGN.CENTER)

    set_text(slide.shapes[10], "例 2：正方形的临界指数", size=13, color=TEAL, bold=True)
    set_text(slide.shapes[27], "边长 1 的正方形分成 4×4 格\n每格直径与 r = 1/4 同阶", size=11, color=MUTED)
    set_text(slide.shapes[28], "16·(1/4)^s = 4^(2−s)\n临界 s = 2  →  H² 有限且非零", size=13, color=INK, bold=True, align=PP_ALIGN.CENTER)

    # 右侧统一说明：小于临界值时成本发散，大于临界值时成本归零。
    set_text(slide.shapes[31], "固定尺度 r 后，把所有覆盖块的直径取 s 次方并相加。\n\ns < 临界值：成本趋于 ∞\ns = 临界值：成本稳定\ns > 临界值：成本趋于 0", size=10, color=MUTED)
    set_text(slide.shapes[32], "读法：覆盖数 N(r) 约为 r⁻ˢ 时，临界指数 s 就是经典几何维数。", size=13, color=INK, bold=True, align=PP_ALIGN.CENTER)

    # 两枚小标签让“图形分块”与“覆盖尺度”形成明确的视觉对应。
    add_label(slide, 868680, 1663704, 3474720, 182880, "用直径 ≤ r 的 4 个小段覆盖", fill=MINT, color=TEAL, size=9)
    add_label(slide, 4617720, 1737360, 2773680, 182880, "用直径约为 r 的 16 个小格覆盖", fill=PALE_GOLD, color=INK, size=9)

    # 关键数值提示；保留原图形以便读者从“数小块”过渡到“看指数”。
    add_label(slide, 1249680, 2042160, 1371600, 173736, "N(r)=4", fill=PALE_GOLD, color=INK, size=9)
    add_label(slide, 4953000, 3304032, 1371600, 173736, "N(r)=16", fill=MINT, color=TEAL, size=9)

    presentation.save(OUTPUT)


if __name__ == "__main__":
    main()
