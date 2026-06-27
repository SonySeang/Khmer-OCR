"""
Generate Figure 3.2 as a clean three-column table — correct content for the report.
Run: python generate_architecture_table.py
Output: figure_3_2_architecture.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── colours (match Word doc style) ───────────────────────────────────
HDR_BLUE   = '#1565C0'
HDR_TEXT   = 'white'
COL1_BG    = '#DBEAFE'   # light blue
COL2_BG    = '#DCFCE7'   # light green
COL3_BG    = '#FEF9C3'   # light yellow
FOOTER_BG  = '#F8FAFC'
BORDER     = '#94A3B8'
DARK       = '#1E293B'
GREY       = '#64748B'

fig, ax = plt.subplots(figsize=(10, 3.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 3.6)
ax.axis('off')
fig.patch.set_facecolor('white')

# ── column x boundaries ───────────────────────────────────────────────
cols = [0.15, 3.48, 6.82, 9.85]

def cell(c, y_top, h, bg, content_lines, header=False):
    x0 = cols[c]
    x1 = cols[c + 1]
    w  = x1 - x0
    ax.add_patch(plt.Rectangle(
        (x0, y_top - h), w, h,
        facecolor=bg, edgecolor=BORDER, linewidth=1.0, zorder=2))
    cx = (x0 + x1) / 2
    mid_y = y_top - h / 2

    if header:
        ax.text(cx, mid_y, content_lines[0],
                ha='center', va='center', fontsize=9.5,
                fontweight='bold', color=HDR_TEXT, zorder=3)
    else:
        n = len(content_lines)
        step = min(0.28, (h - 0.12) / max(n, 1))
        start_y = mid_y + step * (n - 1) / 2
        for i, line in enumerate(content_lines):
            bold  = i == 0
            color = DARK if bold else GREY
            fs    = 8.5 if bold else 7.8
            ax.text(cx, start_y - i * step, line,
                    ha='center', va='center', fontsize=fs,
                    fontweight='bold' if bold else 'normal',
                    color=color, zorder=3)

# ── Header row ────────────────────────────────────────────────────────
H_TOP = 3.48
H_H   = 0.42
for c, title in enumerate(['FRONTEND  (Client)', 'BACKEND  (Server)', 'STORAGE & MODELS']):
    cell(c, H_TOP, H_H, HDR_BLUE, [title], header=True)

# ── Main content row ──────────────────────────────────────────────────
C_TOP = H_TOP - H_H
C_H   = 2.20

cell(0, C_TOP, C_H, COL1_BG, [
    'Web UI  (React SPA)',
    'Upload PDF / image',
    '— Display extracted text',
    '— Confidence highlighting',
    '— Edit & export',
    '— Batch processing',
    '— Processing history',
])

cell(1, C_TOP, C_H, COL2_BG, [
    'API Layer  (Flask)',
    '/upload  endpoint',
    '— /process  pipeline (SSE)',
    '— /download  endpoint',
    '— /correct  endpoint',
    '— /history  endpoint',
    '— /corrections  endpoint',
])

cell(2, C_TOP, C_H, COL3_BG, [
    'Tesseract OCR engine',
    'Claude API  (LLM)',
    '— claude-haiku-4-5',
    'User correction dictionary',
    '— corrections.json',
    'SQLite database',
    '— history.db',
])

# ── Footer row ────────────────────────────────────────────────────────
F_TOP = C_TOP - C_H
F_H   = 0.38

for c, label in enumerate(['⇌  HTTP / JSON  ⇌', '⇌  function calls  ⇌', '⇌  model inference  ⇌']):
    cell(c, F_TOP, F_H, FOOTER_BG, [label])
    ax.texts[-1].set_style('italic')
    ax.texts[-1].set_color(GREY)
    ax.texts[-1].set_fontsize(8)

# ── Caption ────────────────────────────────────────────────────────────
ax.text(5.0, 0.10,
        'Figure 3.2: Web Application Architecture — three-tier design with frontend client, backend API, and storage/model layer.',
        ha='center', va='center', fontsize=7.8,
        style='italic', color=GREY, zorder=3)

plt.tight_layout(pad=0.1)
plt.savefig('figure_3_2_architecture.png', dpi=180,
            bbox_inches='tight', facecolor='white')
print('Saved → figure_3_2_architecture.png')
plt.show()
