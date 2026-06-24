from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "presentation"
PREVIEW_DIR = OUT_DIR / "previews"
PPTX_PATH = OUT_DIR / "HSL_Technical_Assessment_3DGS_Composition.pptx"

W, H = 1920, 1080
SLIDE_W_IN, SLIDE_H_IN = 13.333, 7.5

COLORS = {
    "paper": "F7F4EC",
    "ink": "111827",
    "muted": "5F6B73",
    "teal": "1F766F",
    "blue": "365E9D",
    "coral": "D7613D",
    "gold": "D9A441",
    "line": "C8C2B4",
    "soft": "EDE7DA",
    "white": "FFFFFF",
}


def rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def px_to_in(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    return (
        x / W * SLIDE_W_IN,
        y / H * SLIDE_H_IN,
        w / W * SLIDE_W_IN,
        h / H * SLIDE_H_IN,
    )


def add_text(
    slide,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: int,
    color: str = "ink",
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    font: str = "Aptos",
    line_spacing: float | None = None,
):
    left, top, width, height = [Inches(v) for v in px_to_in(x, y, w, h)]
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split("\n")
    for index, line in enumerate(lines):
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.text = line
        para.alignment = align
        if line_spacing is not None:
            para.line_spacing = line_spacing
        run = para.runs[0]
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = rgb(COLORS[color])
    return box


def add_rect(slide, x, y, w, h, fill, line=None):
    left, top, width, height = [Inches(v) for v in px_to_in(x, y, w, h)]
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(COLORS[fill])
    if line:
        shape.line.color.rgb = rgb(COLORS[line])
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_circle(slide, x, y, d, fill, transparency=0):
    left, top, width, height = [Inches(v) for v in px_to_in(x, y, d, d)]
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(COLORS[fill])
    shape.fill.transparency = transparency
    shape.line.fill.background()
    return shape


def add_line(slide, x1, y1, x2, y2, color="line", width=2):
    left, top, w, h = [Inches(v) for v in px_to_in(x1, y1, x2 - x1, y2 - y1)]
    line = slide.shapes.add_connector(1, left, top, left + w, top + h)
    line.line.color.rgb = rgb(COLORS[color])
    line.line.width = Pt(width)
    return line


def background(slide):
    add_rect(slide, 0, 0, W, H, "paper")


def pptx_splat_cloud(slide, origin_x, origin_y, scale=1.0):
    scene_points = [
        (0, 30, 20),
        (70, 0, 16),
        (145, 24, 22),
        (210, 3, 13),
        (285, 42, 18),
        (345, 16, 26),
        (420, 36, 15),
        (38, 118, 26),
        (115, 92, 18),
        (185, 135, 22),
        (255, 105, 14),
        (330, 130, 21),
        (400, 98, 17),
        (65, 215, 18),
        (140, 250, 26),
        (235, 220, 16),
        (310, 260, 23),
        (395, 230, 18),
        (100, 345, 22),
        (210, 360, 16),
        (325, 340, 24),
    ]
    asset_points = [
        (230, 155, 32),
        (275, 145, 22),
        (315, 175, 28),
        (250, 205, 24),
        (295, 225, 34),
        (345, 210, 20),
        (268, 272, 18),
        (325, 285, 23),
    ]
    for x, y, d in scene_points:
        add_circle(slide, origin_x + x * scale, origin_y + y * scale, d * scale, "blue", 24)
    for x, y, d in asset_points:
        add_circle(slide, origin_x + x * scale, origin_y + y * scale, d * scale, "coral", 8)


def slide_1(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background(slide)
    add_rect(slide, 0, 0, 34, H, "teal")
    add_text(slide, "Human Sensing Lab\nTechnical Assessment", 118, 92, 520, 80, 22, "muted")
    add_text(
        slide,
        "Composing\n3DGS Assets",
        116,
        210,
        650,
        260,
        74,
        "ink",
        bold=True,
        font="Aptos Display",
        line_spacing=0.85,
    )
    add_text(
        slide,
        "A reproducible baseline for inserting a separately trained foreground object into the Mip-NeRF 360 Bicycle scene.",
        122,
        514,
        660,
        120,
        26,
        "muted",
    )
    add_text(slide, "Bicycle scene + synthetic chair", 124, 798, 460, 42, 20, "teal", bold=True)
    add_text(slide, "June 2026", 124, 854, 240, 36, 18, "muted")
    pptx_splat_cloud(slide, 1040, 245, 1.45)
    add_text(slide, "one merged point_cloud.ply", 1060, 820, 520, 45, 24, "ink", bold=True)
    add_text(slide, "Render together to preserve splat depth and alpha ordering.", 1060, 864, 570, 48, 18, "muted")


def slide_2(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background(slide)
    add_text(slide, "Composition Method", 110, 82, 800, 78, 48, "ink", bold=True, font="Aptos Display")
    add_text(
        slide,
        "The foreground asset is transformed in 3DGS parameter space, then rasterized with the scene in one pass.",
        112,
        150,
        1000,
        56,
        22,
        "muted",
    )
    add_line(slide, 180, 370, 1640, 370, "line", 3)
    for x, color, label, caption in [
        (250, "blue", "Train", "Bicycle and chair\nas separate 3DGS models"),
        (790, "gold", "Transform", "p_scene = s R p_object + t\nlog-scale and quaternion updates"),
        (1330, "coral", "Merge", "write one point_cloud.ply\nrender with Bicycle cameras"),
    ]:
        add_circle(slide, x, 292, 150, color, 0)
        add_text(slide, label, x - 24, 342, 210, 38, 25, "white", bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, caption, x - 160, 520, 410, 98, 24, "ink", bold=True, align=PP_ALIGN.CENTER)
    add_text(
        slide,
        "3DGS-specific updates",
        110,
        755,
        410,
        40,
        24,
        "teal",
        bold=True,
    )
    add_text(
        slide,
        "scale_* += log(s)\nrot_* = q_place * q_asset\nopacity edited in sigmoid alpha space\nf_dc_* and f_rest_* support simple color matching",
        110,
        812,
        760,
        145,
        24,
        "ink",
    )
    add_text(
        slide,
        "Why this reduces conflicts",
        1010,
        755,
        430,
        40,
        24,
        "coral",
        bold=True,
    )
    add_text(
        slide,
        "No 2D paste step: scene and object Gaussians are depth-sorted and alpha-composited by the same rasterizer.",
        1010,
        812,
        720,
        92,
        24,
        "ink",
    )


def slide_3(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background(slide)
    add_text(slide, "What I Would Defend", 110, 82, 850, 78, 48, "ink", bold=True, font="Aptos Display")
    add_text(
        slide,
        "The hard part is not only training splats. It is choosing a defensible cross-dataset similarity transform.",
        112,
        150,
        1110,
        56,
        22,
        "muted",
    )
    add_line(slide, 118, 295, 118, 860, "line", 3)
    rows = [
        (
            270,
            "Scale ambiguity",
            "COLMAP and Blender cameras are internally calibrated,\nbut Bicycle and Chair do not share a metric ruler.",
            "teal",
        ),
        (
            455,
            "Practical baseline",
            "Use bounds, visual anchors, and an interactive placement loop;\nkeep every value in the JSON config.",
            "blue",
        ),
        (
            640,
            "Likely bottlenecks",
            "CUDA setup, floaters, splat intersections, and color mismatch\nbetween real outdoor imagery and synthetic lighting.",
            "coral",
        ),
        (
            825,
            "Extension idea",
            "Optimize a small asset-only SH/exposure correction while keeping geometry fixed.",
            "gold",
        ),
    ]
    for y, title, body, color in rows:
        add_circle(slide, 92, y - 9, 52, color, 0)
        add_text(slide, title, 172, y - 18, 470, 42, 29, "ink", bold=True)
        add_text(slide, body, 650, y - 18, 950, 64, 24, "muted")
    add_text(
        slide,
        "Submission assets: scripts, composer, placement UI, process notes, and this 3-slide deck.",
        110,
        960,
        1300,
        34,
        18,
        "muted",
    )


def build_pptx() -> None:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    slide_1(prs)
    slide_2(prs)
    slide_3(prs)
    prs.save(PPTX_PATH)


def load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/aptos.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_text(draw, xy, text, size, color="ink", bold=False, anchor=None, spacing=8):
    font = load_font(size, bold)
    draw.multiline_text(
        xy,
        text,
        fill="#" + COLORS[color],
        font=font,
        spacing=spacing,
        anchor=anchor,
        align="center" if anchor == "mm" else "left",
    )


def draw_cloud(draw, origin_x, origin_y, scale=1.0):
    scene_points = [
        (0, 30, 20), (70, 0, 16), (145, 24, 22), (210, 3, 13), (285, 42, 18),
        (345, 16, 26), (420, 36, 15), (38, 118, 26), (115, 92, 18),
        (185, 135, 22), (255, 105, 14), (330, 130, 21), (400, 98, 17),
        (65, 215, 18), (140, 250, 26), (235, 220, 16), (310, 260, 23),
        (395, 230, 18), (100, 345, 22), (210, 360, 16), (325, 340, 24),
    ]
    asset_points = [
        (230, 155, 32), (275, 145, 22), (315, 175, 28), (250, 205, 24),
        (295, 225, 34), (345, 210, 20), (268, 272, 18), (325, 285, 23),
    ]
    for x, y, d in scene_points:
        xx, yy, dd = origin_x + x * scale, origin_y + y * scale, d * scale
        draw.ellipse([xx, yy, xx + dd, yy + dd], fill="#365E9D")
    for x, y, d in asset_points:
        xx, yy, dd = origin_x + x * scale, origin_y + y * scale, d * scale
        draw.ellipse([xx, yy, xx + dd, yy + dd], fill="#D7613D")


def preview_slide_1(path: Path) -> None:
    img = Image.new("RGB", (W, H), "#" + COLORS["paper"])
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 34, H], fill="#" + COLORS["teal"])
    draw_text(draw, (118, 92), "Human Sensing Lab\nTechnical Assessment", 32, "muted")
    draw_text(draw, (116, 210), "Composing\n3DGS Assets", 92, "ink", True, spacing=0)
    draw_text(draw, (122, 514), "A reproducible baseline for inserting a separately trained\nforeground object into the Mip-NeRF 360 Bicycle scene.", 31, "muted")
    draw_text(draw, (124, 798), "Bicycle scene + synthetic chair", 28, "teal", True)
    draw_text(draw, (124, 854), "June 2026", 25, "muted")
    draw_cloud(draw, 1040, 245, 1.45)
    draw_text(draw, (1060, 820), "one merged point_cloud.ply", 34, "ink", True)
    draw_text(draw, (1060, 864), "Render together to preserve splat depth and alpha ordering.", 26, "muted")
    img.save(path)


def preview_slide_2(path: Path) -> None:
    img = Image.new("RGB", (W, H), "#" + COLORS["paper"])
    draw = ImageDraw.Draw(img)
    draw_text(draw, (110, 82), "Composition Method", 62, "ink", True)
    draw_text(draw, (112, 150), "The foreground asset is transformed in 3DGS parameter space, then rasterized with the scene in one pass.", 30, "muted")
    draw.line([180, 370, 1640, 370], fill="#" + COLORS["line"], width=5)
    for x, color, label, caption in [
        (250, "blue", "Train", "Bicycle and chair\nas separate 3DGS models"),
        (790, "gold", "Transform", "p_scene = s R p_object + t\nlog-scale and quaternion updates"),
        (1330, "coral", "Merge", "write one point_cloud.ply\nrender with Bicycle cameras"),
    ]:
        draw.ellipse([x, 292, x + 150, 442], fill="#" + COLORS[color])
        draw_text(draw, (x + 75, 367), label, 31, "white", True, anchor="mm")
        draw_text(draw, (x - 160, 520), caption, 31, "ink", True)
    draw_text(draw, (110, 755), "3DGS-specific updates", 32, "teal", True)
    draw_text(draw, (110, 812), "scale_* += log(s)\nrot_* = q_place * q_asset\nopacity edited in sigmoid alpha space\nf_dc_* and f_rest_* support simple color matching", 31, "ink")
    draw_text(draw, (1010, 755), "Why this reduces conflicts", 32, "coral", True)
    draw_text(draw, (1010, 812), "No 2D paste step: scene and object Gaussians are depth-sorted\nand alpha-composited by the same rasterizer.", 31, "ink")
    img.save(path)


def preview_slide_3(path: Path) -> None:
    img = Image.new("RGB", (W, H), "#" + COLORS["paper"])
    draw = ImageDraw.Draw(img)
    draw_text(draw, (110, 82), "What I Would Defend", 62, "ink", True)
    draw_text(draw, (112, 150), "The hard part is not only training splats. It is choosing a defensible cross-dataset similarity transform.", 30, "muted")
    draw.line([118, 295, 118, 860], fill="#" + COLORS["line"], width=5)
    rows = [
        (270, "Scale ambiguity", "COLMAP and Blender cameras are internally calibrated,\nbut Bicycle and Chair do not share a metric ruler.", "teal"),
        (455, "Practical baseline", "Use bounds, visual anchors, and an interactive placement loop;\nkeep every value in the JSON config.", "blue"),
        (640, "Likely bottlenecks", "CUDA setup, floaters, splat intersections, and color mismatch\nbetween real outdoor imagery and synthetic lighting.", "coral"),
        (825, "Extension idea", "Optimize a small asset-only SH/exposure correction while keeping geometry fixed.", "gold"),
    ]
    for y, title, body, color in rows:
        draw.ellipse([92, y - 9, 144, y + 43], fill="#" + COLORS[color])
        draw_text(draw, (172, y - 18), title, 38, "ink", True)
        draw_text(draw, (650, y - 18), body, 31, "muted")
    draw_text(draw, (110, 960), "Submission assets: scripts, composer, placement UI, process notes, and this 3-slide deck.", 25, "muted")
    img.save(path)


def build_previews() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    preview_fns = [preview_slide_1, preview_slide_2, preview_slide_3]
    paths = []
    for index, fn in enumerate(preview_fns, start=1):
        path = PREVIEW_DIR / f"slide_{index}.png"
        fn(path)
        paths.append(path)

    montage = Image.new("RGB", (W, H * 3), "#" + COLORS["paper"])
    for index, path in enumerate(paths):
        montage.paste(Image.open(path), (0, H * index))
    montage.save(PREVIEW_DIR / "montage.png")


def inspect_pptx_package() -> None:
    with ZipFile(PPTX_PATH) as zf:
        names = zf.namelist()
        slide_xml = [name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
        if len(slide_xml) != 3:
            raise RuntimeError(f"Expected 3 slides, found {len(slide_xml)}")
        for name in slide_xml:
            xml = zf.read(name).decode("utf-8", errors="ignore")
            if "Slide Number" in xml or "sldNum" in xml:
                raise RuntimeError(f"Unexpected slide-number placeholder in {name}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_pptx()
    build_previews()
    inspect_pptx_package()
    print(f"Wrote {PPTX_PATH}")
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
