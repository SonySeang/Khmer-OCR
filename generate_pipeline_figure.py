"""
Generate Figure: Illustration of the Khmer OCR Pipeline
Run: python generate_pipeline_figure.py
Output: pipeline_figure.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(22, 9))
ax.set_xlim(0, 22)
ax.set_ylim(0, 9)
ax.axis('off')
fig.patch.set_facecolor('white')

# ── helpers ───────────────────────────────────────────────────────────────────

def rbox(ax, cx, cy, w, h, fc, ec, lw=2.2, r=0.35):
    ax.add_patch(FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3))

def arrow(ax, x1, y1, x2, y2, color='#333', lw=2.2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, mutation_scale=20), zorder=4)

def txt(ax, x, y, s, fs=10, color='#111', weight='normal',
        ha='center', va='center', style='normal'):
    ax.text(x, y, s, fontsize=fs, color=color, fontweight=weight,
            ha=ha, va=va, style=style, zorder=5)

# ── palette ───────────────────────────────────────────────────────────────────
C_IN   = '#FFF8E7'; C_OUT = '#F5F5F5'
C_P1   = '#E3F2FD'; C_P2  = '#FFF3E0'
C_P3   = '#E8F5E9'; C_P4  = '#F3E5F5'
BLU='#1565C0'; AMB='#BF360C'; GRN='#1B5E20'; PUR='#4A148C'; DRK='#212121'

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT constants
# ─────────────────────────────────────────────────────────────────────────────
PH_W   = 2.7    # phase-box width
PH_H   = 6.2    # phase-box height
PH_CY  = 4.0    # phase-box vertical centre

CARD_W = 2.25   # inner card width
CARD_H = 0.72   # inner card height
CARD_SP= 0.92   # vertical spacing between card centres

# x-centres of the 4 phase columns (evenly placed between inputs and outputs)
ph_x = [4.6, 7.9, 11.2, 14.5]
INPUT_X  = 1.45
OUTPUT_X = 18.3

# ─────────────────────────────────────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────────────────────────────────────
txt(ax, INPUT_X, 8.4, 'Input Sources', 13, DRK, 'bold')

def draw_input_card(ax, cx, cy, icon_fn, label):
    rbox(ax, cx, cy, 1.9, 1.25, C_IN, DRK, 1.8)
    icon_fn(ax, cx, cy + 0.18)
    txt(ax, cx, cy - 0.42, label, 8.5, DRK, 'bold')

def icon_pdf(ax, cx, cy):
    # page outline
    ax.plot([cx-.28, cx-.28, cx+.18, cx+.28, cx+.28, cx-.28],
            [cy+.32, cy-.22, cy-.22, cy-.12, cy+.32, cy+.32],
            color=DRK, lw=1.6, zorder=6)
    ax.plot([cx+.18, cx+.18, cx+.28], [cy-.22, cy-.12, cy-.12],
            color=DRK, lw=1.6, zorder=6)
    for dy in [.18, .05, -.08]:
        ax.plot([cx-.18, cx+.12], [cy+dy, cy+dy], color=DRK, lw=1.1, zorder=6)

def icon_image(ax, cx, cy):
    ax.add_patch(FancyBboxPatch((cx-.3, cy-.25), .6, .5,
        boxstyle="round,pad=0,rounding_size=0.05",
        facecolor='none', edgecolor=DRK, lw=1.6, zorder=6))
    ax.plot([cx-.3, cx-.08, cx+.1, cx+.3],
            [cy-.1, cy+.1, cy-.02, cy-.1], color=DRK, lw=1.4, zorder=6)
    ax.add_patch(plt.Circle((cx+.14, cy+.12), .07,
        color=DRK, fill=False, lw=1.4, zorder=6))

def icon_scanner(ax, cx, cy):
    ax.add_patch(mpatches.Rectangle(
        (cx-.35, cy-.1), .7, .25,
        facecolor='none', edgecolor=DRK, lw=1.6, zorder=6))
    ax.plot([cx-.42, cx+.42], [cy+.15, cy+.15], color=DRK, lw=1.6, zorder=6)
    for dx in [-.2, 0, .2]:
        ax.plot([cx+dx, cx+dx], [cy-.1, cy-.24], color=DRK, lw=1.2, zorder=6)

draw_input_card(ax, INPUT_X, 6.4, icon_pdf,     'PDF')
draw_input_card(ax, INPUT_X, 4.2, icon_image,   'Image / Photo')
draw_input_card(ax, INPUT_X, 2.0, icon_scanner, 'Scanned Document')

# arrows: inputs → phase 1
for src_y in [6.4, 4.2, 2.0]:
    arrow(ax, INPUT_X + 0.95, src_y, ph_x[0] - PH_W/2 - 0.05, src_y, DRK)

# ─────────────────────────────────────────────────────────────────────────────
# helper: draw one phase column
# ─────────────────────────────────────────────────────────────────────────────
def phase_col(ax, cx, cy, bg, ec,
              phase_num, title1, title2,
              cards,          # list of (bold_line, sub_line)
              phase_label):
    # outer box
    rbox(ax, cx, cy, PH_W, PH_H, bg, ec, 2.5)

    # phase label (italic, above box)
    txt(ax, cx, cy + PH_H/2 + 0.28, phase_label, 9.5, ec, 'normal', style='italic')

    # header text inside box
    txt(ax, cx, cy + PH_H/2 - 0.32, f'Phase {phase_num}', 10.5, ec, 'bold')
    txt(ax, cx, cy + PH_H/2 - 0.72, title1,  12,   ec, 'bold')
    txt(ax, cx, cy + PH_H/2 - 1.08, title2,  12,   ec, 'bold')

    # step cards
    card_top = cy + PH_H/2 - 1.60
    for i, (bold_line, sub_line) in enumerate(cards):
        card_cy = card_top - i * CARD_SP
        rbox(ax, cx, card_cy, CARD_W, CARD_H, 'white', ec, 1.3, 0.18)
        if sub_line:
            txt(ax, cx, card_cy + 0.14, bold_line,  9,   ec, 'bold')
            txt(ax, cx, card_cy - 0.16, sub_line,   8.5, '#555')
        else:
            txt(ax, cx, card_cy,        bold_line,  9.5, ec, 'bold')

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — Image Preprocessing
# ─────────────────────────────────────────────────────────────────────────────
phase_col(ax, ph_x[0], PH_CY, C_P1, BLU, 1,
          'Image', 'Preprocessing',
          [('Quality Detection',  'clean / scan / photo'),
           ('Denoise + CLAHE',    'bilateral / NLM'),
           ('Sharpen + Deskew',   'unsharp mask, Hough'),
           ('Binarize',           'Otsu / Adaptive')],
          'Preprocessing')

arrow(ax, ph_x[0]+PH_W/2+0.05, PH_CY, ph_x[1]-PH_W/2-0.05, PH_CY, AMB)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — Tesseract OCR
# ─────────────────────────────────────────────────────────────────────────────
phase_col(ax, ph_x[1], PH_CY, C_P2, AMB, 2,
          'Tesseract', 'OCR Engine',
          [('lang: khm+eng',      '--oem 1 --psm 4'),
           ('Word confidence',    'per-word scoring'),
           ('Timeout 25s',        'retry psm 3 fallback'),
           ('image_to_data',      'block / line / word')],
          'OCR Engine')

arrow(ax, ph_x[1]+PH_W/2+0.05, PH_CY, ph_x[2]-PH_W/2-0.05, PH_CY, GRN)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — Khmer Post-Processing
# ─────────────────────────────────────────────────────────────────────────────
phase_col(ax, ph_x[2], PH_CY, C_P3, GRN, 3,
          'Khmer', 'Post-Processing',
          [('Form Blank Cleanup', 'dots / dashes → ________'),
           ('Garbage Line',       'removal (Khmer ratio)'),
           ('Khmer Char',         'corrections (60+ rules)'),
           ('Symbol & Punct.',    'fix ។ misreads, stray |')],
          'Post-Process')

arrow(ax, ph_x[2]+PH_W/2+0.05, PH_CY, ph_x[3]-PH_W/2-0.05, PH_CY, PUR)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — AI Correction (Claude)
# ─────────────────────────────────────────────────────────────────────────────
phase_col(ax, ph_x[3], PH_CY, C_P4, PUR, 4,
          'AI', 'Correction',
          [('Claude Haiku',       'claude-haiku-4-5'),
           ('Context-aware',      'OCR error fixing'),
           ('Fix-only prompt',    '7 strict rules'),
           ('Retry + fallback',   'returns original if fail')],
          'AI Correction')

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
txt(ax, OUTPUT_X, 8.4, 'Output', 13, DRK, 'bold')

def draw_output_card(ax, cx, cy, icon_fn, label):
    rbox(ax, cx, cy, 2.0, 1.25, C_OUT, DRK, 1.8)
    icon_fn(ax, cx, cy + 0.18)
    txt(ax, cx, cy - 0.42, label, 8.5, DRK, 'bold')

def icon_txt(ax, cx, cy):
    ax.plot([cx-.28, cx-.28, cx+.18, cx+.28, cx+.28, cx-.28],
            [cy+.32, cy-.22, cy-.22, cy-.12, cy+.32, cy+.32],
            color=DRK, lw=1.6, zorder=6)
    ax.plot([cx+.18, cx+.18, cx+.28], [cy-.22, cy-.12, cy-.12],
            color=DRK, lw=1.6, zorder=6)
    txt(ax, cx, cy+.06, 'TXT', 10, DRK, 'bold')

def icon_docx(ax, cx, cy):
    ax.plot([cx-.28, cx-.28, cx+.18, cx+.28, cx+.28, cx-.28],
            [cy+.32, cy-.22, cy-.22, cy-.12, cy+.32, cy+.32],
            color=DRK, lw=1.6, zorder=6)
    ax.plot([cx+.18, cx+.18, cx+.28], [cy-.22, cy-.12, cy-.12],
            color=DRK, lw=1.6, zorder=6)
    for dy in [.15, .02, -.1]:
        ax.plot([cx-.18, cx+.12], [cy+dy, cy+dy], color=DRK, lw=1.1, zorder=6)

def icon_db(ax, cx, cy):
    ax.add_patch(mpatches.Ellipse((cx, cy+.22), .52, .16,
        facecolor='none', edgecolor=DRK, lw=1.6, zorder=6))
    ax.plot([cx-.26, cx-.26], [cy+.22, cy-.22], color=DRK, lw=1.6, zorder=6)
    ax.plot([cx+.26, cx+.26], [cy+.22, cy-.22], color=DRK, lw=1.6, zorder=6)
    ax.add_patch(mpatches.Ellipse((cx, cy-.22), .52, .16,
        facecolor='none', edgecolor=DRK, lw=1.6, zorder=6))

draw_output_card(ax, OUTPUT_X, 6.4, icon_txt,  'Plain Text (.txt)')
draw_output_card(ax, OUTPUT_X, 4.2, icon_docx, 'Document (.docx)')
draw_output_card(ax, OUTPUT_X, 2.0, icon_db,   'History DB (SQLite)')

# arrows: phase 4 → outputs
for tgt_y in [6.4, 4.2, 2.0]:
    arrow(ax, ph_x[3]+PH_W/2+0.05, tgt_y, OUTPUT_X-1.0-0.05, tgt_y, DRK)

# split arrow from phase4 right edge to output y-levels
# vertical connector
ax.plot([ph_x[3]+PH_W/2+0.52, ph_x[3]+PH_W/2+0.52], [2.0, 6.4],
        color=DRK, lw=2.2, zorder=4)

# ─────────────────────────────────────────────────────────────────────────────
# TITLE + CAPTION
# ─────────────────────────────────────────────────────────────────────────────
txt(ax, 11, 8.75,
    'Khmer OCR Post-Processing Pipeline — System Overview',
    15, DRK, 'bold')

txt(ax, 0.3, 0.22, "Source: Authors' design",
    9, '#666', style='italic', ha='left')

plt.tight_layout(pad=0.4)
plt.savefig('pipeline_figure.png', dpi=180, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print('Saved → pipeline_figure.png')
plt.show()
