"""
Figure 3.2: Web Application Architecture
Three-tier design: Frontend Client | Backend API | Storage/Model Layer
Run: python generate_architecture_figure.py
Output: architecture_figure.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(18, 10))
ax.set_xlim(0, 18)
ax.set_ylim(0, 10)
ax.axis('off')
fig.patch.set_facecolor('white')

# ── helpers ───────────────────────────────────────────────────────────────────
def rbox(cx, cy, w, h, fc, ec, lw=1.8, r=0.25):
    ax.add_patch(FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3))

def txt(x, y, s, fs=9, color='#111', weight='normal',
        ha='center', va='center', style='normal'):
    ax.text(x, y, s, fontsize=fs, color=color, fontweight=weight,
            ha=ha, va=va, style=style, zorder=5,
            fontfamily='DejaVu Sans')

def harrow(x1, y, x2, color='#555', lw=1.8, label=''):
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, mutation_scale=16), zorder=4)
    if label:
        mx = (x1 + x2) / 2
        txt(mx, y + 0.18, label, 7.5, color, style='italic')

def varrow(x, y1, y2, color='#555', lw=1.8, label='', label_side='right'):
    ax.annotate('', xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, mutation_scale=16), zorder=4)
    if label:
        ox = 0.18 if label_side == 'right' else -0.18
        txt(x + ox, (y1 + y2) / 2, label, 7.5, color,
            ha='left' if label_side == 'right' else 'right', style='italic')

def dvarrow(x, y1, y2, color='#555', lw=1.6):
    """double-headed vertical arrow"""
    ax.annotate('', xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle='<->', color=color,
                                lw=lw, mutation_scale=16), zorder=4)

# ── palette ───────────────────────────────────────────────────────────────────
T1_BG  = '#E3F2FD'; T1_EC = '#1565C0'; T1_TXT = '#0D47A1'   # blue  – frontend
T2_BG  = '#E8F5E9'; T2_EC = '#2E7D32'; T2_TXT = '#1B5E20'   # green – backend
T3_BG  = '#FFF3E0'; T3_EC = '#BF360C'; T3_TXT = '#7F2700'   # orange – storage
CARD   = 'white'
DRK    = '#212121'
GREY   = '#757575'

# ═══════════════════════════════════════════════════════════════════
# TIER BACKGROUND BANDS
# ═══════════════════════════════════════════════════════════════════
tier_info = [
    (8.20, T1_BG, T1_EC, 'Tier 1 — Frontend Client (React SPA)'),
    (5.05, T2_BG, T2_EC, 'Tier 2 — Backend API (Flask, port 5001)'),
    (1.80, T3_BG, T3_EC, 'Tier 3 — Storage / Model Layer'),
]
tier_heights = [2.6, 2.8, 2.8]
for (cy, bg, ec, _), th in zip(tier_info, tier_heights):
    ax.add_patch(FancyBboxPatch(
        (0.3, cy - th/2), 17.4, th,
        boxstyle="round,pad=0,rounding_size=0.3",
        facecolor=bg, edgecolor=ec, linewidth=2.2,
        alpha=0.45, zorder=1))

# tier labels (left side)
for (cy, _, ec, label), th in zip(tier_info, tier_heights):
    txt(0.98, cy, label, 8.5, ec, 'bold',
        ha='center', va='center')
    ax.plot([1.55, 1.55], [cy - th/2 + 0.2, cy + th/2 - 0.2],
            color=ec, lw=1.2, alpha=0.5, zorder=2)

# ═══════════════════════════════════════════════════════════════════
# TIER 1 — FRONTEND  (y ≈ 8.2)
# ═══════════════════════════════════════════════════════════════════
T1Y = 8.20
COMP_W, COMP_H = 1.85, 0.72

components = [
    ('UploadSection',    'file picker / drag-drop'),
    ('SettingsSection',  'preset · AI toggle'),
    ('ProgressSection',  'SSE live updates'),
    ('ResultsSection',   'text · thumbnails'),
    ('HistorySection',   'past extractions'),
    ('BatchSection',     'multi-file queue'),
]
comp_xs = [2.4 + i * 2.35 for i in range(len(components))]

for cx, (name, sub) in zip(comp_xs, components):
    rbox(cx, T1Y, COMP_W, COMP_H, CARD, T1_EC, 1.5)
    txt(cx, T1Y + 0.14, name, 8.5, T1_TXT, 'bold')
    txt(cx, T1Y - 0.16, sub, 7.5, GREY)

# Browser wrapper label
rbox(9.0, T1Y, 15.0, 1.05, 'none', T1_EC, 1.2, 0.2)
txt(9.0, T1Y + 0.62, 'Browser  (React SPA — Vite + Tailwind)', 9, T1_TXT, 'bold')

# ═══════════════════════════════════════════════════════════════════
# TIER 2 — BACKEND API  (y ≈ 5.05)
# ═══════════════════════════════════════════════════════════════════
T2Y = 5.05

# --- Flask routes box ---
ROUTE_X = 4.0
rbox(ROUTE_X, T2Y, 3.5, 2.2, CARD, T2_EC, 1.5)
txt(ROUTE_X, T2Y + 0.88, 'Flask Routes', 9.5, T2_TXT, 'bold')
routes = [
    'POST  /upload',
    'POST  /process  (SSE)',
    'GET   /download/:id/txt|docx',
    'GET/POST  /history',
    'GET/POST  /corrections',
    'POST  /api/v1/extract',
]
for i, r in enumerate(routes):
    txt(ROUTE_X, T2Y + 0.52 - i * 0.30, r, 7.8, '#333',
        ha='center', va='center',
        weight='normal' if i > 0 else 'bold')

# --- OCR Pipeline box ---
PIPE_X = 10.5
rbox(PIPE_X, T2Y, 6.8, 2.2, CARD, T2_EC, 1.5)
txt(PIPE_X, T2Y + 0.88, 'OCR Pipeline  (ocr_preprocess.py)', 9.5, T2_TXT, 'bold')

pipe_steps = [
    ('pdf2image',        'PDF → PIL pages @300 DPI'),
    ('preprocess_for_ocr', 'quality detect → denoise → binarize → deskew'),
    ('run_ocr',          'Tesseract  khm+eng  --oem 1 --psm 4'),
    ('postprocess_khmer','7-step rule-based Khmer cleanup'),
    ('correct_with_ai',  'Claude Haiku  context-aware correction'),
]
for i, (fn, desc) in enumerate(pipe_steps):
    py = T2Y + 0.52 - i * 0.34
    txt(PIPE_X - 1.8, py, fn,   8,   T2_TXT, 'bold',   ha='left')
    txt(PIPE_X + 0.2, py, desc, 7.8, GREY,             ha='left')
    if i < len(pipe_steps) - 1:
        ax.annotate('', xy=(PIPE_X - 3.1, py - 0.20),
                    xytext=(PIPE_X - 3.1, py - 0.14),
                    arrowprops=dict(arrowstyle='->', color=T2_EC, lw=1.2,
                                    mutation_scale=10), zorder=4)

# arrow routes → pipeline
harrow(ROUTE_X + 1.75, T2Y, PIPE_X - 3.4, T2_EC, 1.8, 'orchestrate')

# ═══════════════════════════════════════════════════════════════════
# TIER 3 — STORAGE / MODEL  (y ≈ 1.8)
# ═══════════════════════════════════════════════════════════════════
T3Y = 1.80
ST_W, ST_H = 2.4, 1.7

stores = [
    (2.6,  'File System',   'uploads/\nauto-deleted after\nprocessing'),
    (5.4,  'SQLite DB',     'history.db\nper-job results\n& metadata'),
    (8.2,  'Corrections',   'corrections.json\nuser dictionary\n(editable via UI)'),
    (11.2, 'Tesseract',     'Engine v5\nkhm + eng\ntrained data'),
    (14.5, 'Claude API',    'claude-haiku-4-5\nAnthropic\ncloud API'),
]

for cx, title, body in stores:
    rbox(cx, T3Y, ST_W, ST_H, CARD, T3_EC, 1.5)
    txt(cx, T3Y + 0.56, title, 9.5, T3_TXT, 'bold')
    ax.plot([cx - ST_W/2 + 0.2, cx + ST_W/2 - 0.2],
            [T3Y + 0.36, T3Y + 0.36], color=T3_EC, lw=0.8, alpha=0.6, zorder=4)
    for j, line in enumerate(body.split('\n')):
        txt(cx, T3Y + 0.08 - j * 0.28, line, 8, '#444')

# ═══════════════════════════════════════════════════════════════════
# INTER-TIER ARROWS
# ═══════════════════════════════════════════════════════════════════

# T1 ↔ T2  (HTTP / SSE)
dvarrow(5.5, 7.68, 6.16, T1_EC, 1.8)
txt(5.78, 6.92, 'HTTP / JSON', 8, T1_EC, 'bold', ha='left')
dvarrow(8.5, 7.68, 6.16, T2_EC, 1.8)
txt(8.7,  6.92, 'SSE stream', 8, T2_EC, 'bold', ha='left')

# T2 → T3  (read/write)
varrow(2.6,  5.94, 2.82, T3_EC, 1.6, 'write', 'right')
varrow(5.4,  5.94, 2.82, T3_EC, 1.6, 'read/write', 'right')
varrow(8.2,  5.94, 2.82, T3_EC, 1.6, 'load/save', 'right')
varrow(11.2, 5.94, 2.82, T3_EC, 1.6, 'call', 'right')
varrow(14.5, 5.94, 2.82, T3_EC, 1.6, 'API call', 'right')

# ═══════════════════════════════════════════════════════════════════
# TITLE + CAPTION
# ═══════════════════════════════════════════════════════════════════
txt(9, 9.68,
    'Web Application Architecture — Three-Tier Design',
    15, DRK, 'bold')

txt(0.4, 0.18,
    "Figure 3.2: Web Application Architecture — three-tier design with frontend client, backend API, and storage/model layer.",
    8.5, GREY, style='italic', ha='left')

plt.tight_layout(pad=0.3)
plt.savefig('architecture_figure.png', dpi=180, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print('Saved → architecture_figure.png')
plt.show()
