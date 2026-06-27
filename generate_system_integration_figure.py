import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

fig, ax = plt.subplots(figsize=(12, 10))
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')

# ── Palette ────────────────────────────────────────────────────────────────────
C_CLIENT = "#D6EAF8"
C_FLASK  = "#D5F5E3"
C_OCR    = "#FEF9E7"
C_AI     = "#FADBD8"
C_PIPE   = "#FDF2E9"
C_BORDER = "#2C3E50"
C_ARROW  = "#2C3E50"

def box(ax, x, y, w, h, title, subtitle=None, color="#fff", fs=10, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                 facecolor=color, edgecolor=C_BORDER, linewidth=1.8, zorder=3))
    ty = y + h / 2 + (0.18 if subtitle else 0)
    ax.text(x + w/2, ty, title, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal",
            color=C_BORDER, zorder=4)
    if subtitle:
        ax.text(x + w/2, y + h/2 - 0.22, subtitle, ha="center", va="center",
                fontsize=8, color="#666", style="italic", zorder=4)

def region(ax, x, y, w, h, label, color, lc="#AAAAAA"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.18",
                 facecolor=color, edgecolor=lc, linewidth=1.2,
                 linestyle="--", zorder=1))
    ax.text(x + 0.2, y + h - 0.22, label, fontsize=8.5,
            fontweight="bold", color="#555", va="top", zorder=2)

def varrow(ax, x, y1, y2, label="", lx_off=0.22):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.8,
                                mutation_scale=18), zorder=5)
    if label:
        ax.text(x + lx_off, (y1 + y2) / 2, label, va="center",
                fontsize=8, color="#444", zorder=5)

def bivarrow(ax, x, y1, y2, label="", lx_off=0.22):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<|-|>", color=C_ARROW, lw=1.8,
                                mutation_scale=18), zorder=5)
    if label:
        ax.text(x + lx_off, (y1 + y2) / 2, label, va="center",
                fontsize=8, color="#444", zorder=5)

def curve_arrow(ax, x1, y1, x2, y2, label="", rad=0.3, label_off=(0, 0.2)):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.8,
                                mutation_scale=18,
                                connectionstyle=f"arc3,rad={rad}"), zorder=5)
    if label:
        mx = (x1 + x2) / 2 + label_off[0]
        my = (y1 + y2) / 2 + label_off[1]
        ax.text(mx, my, label, ha="center", fontsize=8, color="#444", zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT  (top → bottom)
#
#  ┌──────────────────────────────────────────────┐
#  │  Client Side                                 │
#  │  ┌────────────────────────────────────────┐  │
#  │  │         React Frontend                 │  │
#  │  └────────────────────────────────────────┘  │
#  └──────────────────┬───────────────────────────┘
#           HTTP / REST (↕)
#  ┌──────────────────▼───────────────────────────┐
#  │  Server Side (Flask Orchestration)           │
#  │  ┌────────────────────────────────────────┐  │
#  │  │          Flask Backend                 │  │
#  │  └──────────┬─────────────────┬───────────┘  │
#  │      Image  │            Text │              │
#  │      Upload │      Correction │              │
#  │  ┌──────────▼──────────┐  ┌──▼────────────┐  │
#  │  │  OCR Pipeline       │  │ Claude AI     │  │
#  │  │  ┌───────────────┐  │  │ Correction    │  │
#  │  │  │ Preprocessing │  │  │ Service       │  │
#  │  │  └───────┬───────┘  │  └───────────────┘  │
#  │  │          ↓          │                     │
#  │  │  ┌───────────────┐  │                     │
#  │  │  │ Tesseract OCR │  │                     │
#  │  │  └───────┬───────┘  │                     │
#  │  │          ↓          │                     │
#  │  │  ┌───────────────┐  │                     │
#  │  │  │Khmer Post-proc│  │                     │
#  │  │  └───────────────┘  │                     │
#  │  └─────────────────────┘                     │
#  └──────────────────────────────────────────────┘
# ══════════════════════════════════════════════════════════════════════════════

# ── Background regions ─────────────────────────────────────────────────────────
region(ax, 0.4, 8.1, 11.2, 1.5, "Client Side", "#EBF5FB", "#7FB3D3")
region(ax, 0.4, 0.3, 11.2, 7.6, "Server Side  (Flask Orchestration)", "#EAFAF1", "#76B7A3")
region(ax, 0.8, 0.7, 5.4, 5.2, "OCR Processing Pipeline", "#FFFDE7", "#C9A227")

# ── Boxes ──────────────────────────────────────────────────────────────────────
# React Frontend
box(ax, 2.5, 8.35, 7.0, 1.1, "React Frontend", "(Web Browser)", C_CLIENT, fs=11)

# Flask Backend
box(ax, 2.5, 6.3, 7.0, 1.2, "Flask Backend", "(REST API / Orchestrator)", C_FLASK, fs=11)

# OCR steps — stacked vertically
box(ax, 1.1, 4.8, 4.6, 0.9, "Image Preprocessing",  color=C_OCR, fs=9.5)
box(ax, 1.1, 3.5, 4.6, 0.9, "Tesseract OCR Engine",  color=C_OCR, fs=9.5)
box(ax, 1.1, 2.2, 4.6, 0.9, "Khmer Post-processing", color=C_OCR, fs=9.5)

# Claude AI
box(ax, 7.0, 3.5, 4.2, 1.6, "Claude AI\nCorrection Service", color=C_AI, fs=10.5)

# ── Arrows ─────────────────────────────────────────────────────────────────────
# React ↔ Flask (vertical center)
bivarrow(ax, 6.0, 7.45, 6.3 + 1.2, "HTTP / REST")  # top of flask = 6.3+1.2=7.5 → bottom react=8.35
# fix: y1 = bottom of react = 8.35, y2 = top of flask = 7.5
bivarrow(ax, 6.0, 8.35, 7.5, "  HTTP / REST")

# Flask → Image Preprocessing
curve_arrow(ax, 4.0, 6.3, 3.4, 5.7, "Image Upload", rad=0.0, label_off=(-0.9, 0))

# Internal OCR steps ↓
varrow(ax, 3.4, 4.8, 4.4, "")   # Preprocessing → Tesseract
varrow(ax, 3.4, 3.5, 3.1, "")   # Tesseract → Khmer

# Khmer Post-processing → Flask (return path, curved right)
curve_arrow(ax, 5.7, 2.65, 8.5, 6.3, "OCR Text", rad=-0.25, label_off=(1.1, 0))

# Flask ↔ Claude AI (vertical)
bivarrow(ax, 9.1, 5.1, 6.3, "  Text /\n  Correction")

# ── Title ──────────────────────────────────────────────────────────────────────
ax.text(6.0, 9.82, "Figure 5.6  System Integration Architecture",
        ha="center", va="center", fontsize=13, fontweight="bold", color=C_BORDER)

# ── Legend ─────────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=C_CLIENT, edgecolor=C_BORDER, label="Client Layer"),
    mpatches.Patch(facecolor=C_FLASK,  edgecolor=C_BORDER, label="Flask Backend"),
    mpatches.Patch(facecolor=C_OCR,    edgecolor=C_BORDER, label="OCR Pipeline"),
    mpatches.Patch(facecolor=C_AI,     edgecolor=C_BORDER, label="Claude AI Correction"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=9,
          framealpha=0.92, bbox_to_anchor=(0.99, 0.01))

plt.tight_layout(pad=0.3)
plt.savefig("figure_5_6_system_integration.png", dpi=200, bbox_inches="tight",
            facecolor="white")
print("Saved.")
