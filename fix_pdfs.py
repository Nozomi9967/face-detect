"""
Fix PDFs by targeted text replacement using PyMuPDF.
Backup originals first.
"""
import os
import shutil
import fitz
from pathlib import Path

DOC_DIR = r"C:\Users\q1948\Desktop\Course\软开3\doc"
BACKUP_DIR = os.path.join(DOC_DIR, "_backup_pdf")
FONT_FILE = "C:/Windows/Fonts/simhei.ttf"

os.makedirs(BACKUP_DIR, exist_ok=True)

def backup(name):
    src = os.path.join(DOC_DIR, name)
    dst = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        print(f"  Backed up: {name}")


def replace_on_page(page, old, new, fontsize=10):
    """Replace all occurrences of old text with new text on a page."""
    text = page.get_text()
    if old not in text:
        return 0

    rects = page.search_for(old)
    if not rects:
        return 0

    count = len(rects)
    for r in rects:
        page.add_redact_annot(r, fill=(1, 1, 1))
    page.apply_redactions()

    # Re-insert at the first match position
    pt = rects[0].tl
    page.insert_text(
        pt, new,
        fontsize=fontsize,
        fontfile=FONT_FILE,
        color=(0, 0, 0)
    )
    return count


# ============================================================
# All replacements
# ============================================================

# Coord replacements - exact strings from PDF text extraction
COORD_REPLACEMENTS = [
    # master_driver JSON
    ('"x_range": [0.50, 1.00],\n      "y_range": [0.50, 1.00],\n      "label": "主驾"',
     '"x_range": [0.60, 1.00],\n      "y_range": [0.30, 0.55],\n      "label": "主驾"'),
    # co_driver JSON
    ('"x_range": [0.00, 0.50],\n      "y_range": [0.50, 1.00],\n      "label": "副驾"',
     '"x_range": [0.00, 0.40],\n      "y_range": [0.30, 0.55],\n      "label": "副驾"'),
    # posterior_left JSON
    ('"x_range": [0.00, 0.33],\n      "y_range": [0.00, 0.50],\n      "label": "后排左"',
     '"x_range": [0.25, 0.45],\n      "y_range": [0.25, 0.45],\n      "label": "后排左"'),
    # posterior_right JSON
    ('"x_range": [0.33, 0.66],\n      "y_range": [0.00, 0.50],\n      "label": "后排中"',
     '"x_range": [0.45, 0.65],\n      "y_range": [0.25, 0.45],\n      "label": "后排中"'),
    # after_the_middle JSON
    ('"x_range": [0.66, 1.00],\n      "y_range": [0.00, 0.50],\n      "label": "后排右"',
     '"x_range": [0.65, 0.90],\n      "y_range": [0.25, 0.50],\n      "label": "后排右"'),
]

# Table format coord replacements
COORD_TABLE = [
    ('0.00 ≤ nx ≤ 0.33\n0.00 ≤ ny ≤ 0.50\n后排左', '0.25 ≤ nx ≤ 0.45\n0.25 ≤ ny ≤ 0.45\n后排左'),
    ('0.33 < nx ≤ 0.66\n0.00 ≤ ny ≤ 0.50\n后排中', '0.45 ≤ nx ≤ 0.65\n0.25 ≤ ny ≤ 0.45\n后排中'),
    ('0.66 < nx ≤ 1.00\n0.00 ≤ ny ≤ 0.50\n后排右', '0.65 ≤ nx ≤ 0.90\n0.25 ≤ ny ≤ 0.50\n后排右'),
    ('0.00 ≤ nx ≤ 0.50\n0.50 < ny ≤ 1.00\n副驾', '0.00 ≤ nx ≤ 0.40\n0.30 < ny ≤ 0.55\n副驾'),
    ('0.50 < nx ≤ 1.00\n0.50 < ny ≤ 1.00\n主驾', '0.60 ≤ nx ≤ 1.00\n0.30 < ny ≤ 0.55\n主驾'),
]

# aggregate_stats removals/replacements
AGG_REPLACEMENTS = [
    ('"aggregate_stats": [\n    {\n      "person_id": 1,\n      "appearance_count": 3,\n      "primary_seat": "master_driver",\n      "primary_seat_label": "主驾"\n    }\n  ],',
     '/* aggregate_stats: 待实现 */'),
    ('返回包含逐图结果和聚合统计的 JSON',
     '返回包含逐图结果的 JSON'),
    ('统计报告生成的全链路自动化',
     '全链路自动化'),
    ('及统计报告生成',
     '功能扩展'),
    ('统计汇总五个环节',
     '可视化标注四个环节'),
    ('阶段四：聚合统计与响应组装',
     '阶段四：结果组装'),
    ('阶段四：聚合统计',
     '阶段四：结果组装'),
    ('按 person_id 分组，计算 appearance_count 和 primary_seat',
     '按 image_id 分组组装逐图结果'),
    ('统计结果组装为 aggregate_stats 数组',
     '结果组装为 JSON 响应'),
    ('和 aggregate_stats（聚合统计数组）',
     ''),
    ('统计报表',
     '统计信息'),
    ('aggregate_stats 正确',
     'results 正确'),
    ('aggregate_stats 非空',
     'results 非空'),
    ('包含 aggregate_stats',
     '包含 results'),
    ('检查 aggregate_stats',
     '检查 results'),
    ('aggregate_stats 数组',
     'results 数组'),
    ('聚合统计表（表头为"人员 ID"、"出现次数"、"主要座位"',
     '逐图统计信息（表头为"人员 ID"、"出现次数"'),
]

# classify method description
CLASSIFY_REPLACEMENTS = [
    ('按照预定义的五个矩形区域规则判定座位归属',
     '通过自适应算法判定座位归属（考虑Y坐标分布和框宽度）'),
    ('遍历 SEAT_ZONES 进行区域匹配',
     '通过自适应算法判断前后排'),
    ('依次检查归一化中心坐标是否落入各区域的 x_range 和 y_range 范围内，返回第一个匹配区域的 seat_id',
     '根据归一化中心坐标通过自适应算法判断前后排，再按 X 坐标映射'),
]

# Y coordinate descriptions
Y_DESC_REPLACEMENTS = [
    ('Y 轴上方（ny 值较小）代表车辆后排，Y 轴下方（ny 值较大）代表车辆前排',
     '前后排通过 Y 坐标分布和框宽度自适应判断'),
    ('Y 轴上方（ny 值较小）对应车辆后排，Y 轴下方（ny 值较大）对应车辆前排',
     '前后排通过 Y 坐标分布和框宽度自适应判断'),
]

ALL_REPLACEMENTS = []
ALL_REPLACEMENTS.extend([('coord', o, n) for o, n in COORD_REPLACEMENTS])
ALL_REPLACEMENTS.extend([('coord_tbl', o, n) for o, n in COORD_TABLE])
ALL_REPLACEMENTS.extend([('agg', o, n) for o, n in AGG_REPLACEMENTS])
ALL_REPLACEMENTS.extend([('classify', o, n) for o, n in CLASSIFY_REPLACEMENTS])
ALL_REPLACEMENTS.extend([('y_desc', o, n) for o, n in Y_DESC_REPLACEMENTS])


def process_pdf(pdf_name):
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_name}")
    print(f"{'='*60}")
    backup(pdf_name)

    path = os.path.join(DOC_DIR, pdf_name)
    doc = fitz.open(path)
    stats = {}

    for pi in range(len(doc)):
        page = doc[pi]
        for category, old, new in ALL_REPLACEMENTS:
            c = replace_on_page(page, old, new)
            if c > 0:
                stats[category] = stats.get(category, 0) + c
                print(f"  P{pi+1}: [{category}] '{old[:55]}...' ({c}x)")

    tmp_path = os.path.join(DOC_DIR, f"_tmp_{pdf_name}")
    output_path = os.path.join(DOC_DIR, pdf_name)
    doc.save(tmp_path)
    doc.close()
    # Overwrite original with modified version
    try:
        os.replace(tmp_path, output_path)
        print(f"  Saved successfully")
    except PermissionError:
        print(f"  WARNING: Could not overwrite {pdf_name} (file may be open)")
        print(f"  Modified version saved as: {tmp_path}")
        print(f"  Please close any PDF viewers and run: copy /Y \"{tmp_path}\" \"{output_path}\"")

    total = sum(stats.values())
    for cat, cnt in stats.items():
        print(f"  {cat}: {cnt} replacements")
    print(f"  Total: {total}")
    return total


# ============================================================
# Main
# ============================================================

pdfs = [
    "概要设计.pdf",
    "系统功能模块与数据流设计.pdf",
    "系统需求分析报告.pdf",
    "功能验收标准.pdf",
    "用户操作手册.pdf",
]

total = 0
for pdf_name in pdfs:
    try:
        total += process_pdf(pdf_name)
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*60}")
print(f"DONE: {total} total replacements")
print(f"Backups at: {BACKUP_DIR}")
print(f"{'='*60}")
