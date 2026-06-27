"""
Generate Section 5.1 Figures:
  Figure 5.1 — OCR Accuracy Improvement (CER/WER before vs after)
  Figure 5.2 — Per-Step Contribution to Accuracy
Run: python generate_results_figures.py
Outputs: figure_5_1.png, figure_5_2.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── shared style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':  'DejaVu Sans',
    'font.size':    11,
    'axes.spines.top':   False,
    'axes.spines.right': False,
})

# ═══════════════════════════════════════════════════════════════════
# FIGURE 5.1 — Before vs After (CER / WER)
# ═══════════════════════════════════════════════════════════════════
# Representative values (replace with real measurements from compare_tesseract.py)
methods = [
    'Baseline\nTesseract',
    'Tesseract +\nPreprocessing',
    'Tesseract +\nPreproc + Post',
    'Full Pipeline\n(+ AI Correction)',
]

cer = [34.2, 22.5, 14.8, 7.3]   # Character Error Rate %
wer = [58.4, 41.2, 28.6, 13.1]  # Word Error Rate %

x     = np.arange(len(methods))
width = 0.35

fig, ax = plt.subplots(figsize=(11, 6))
fig.patch.set_facecolor('white')

bars1 = ax.bar(x - width/2, cer, width, label='CER (%)',
               color='#1565C0', alpha=0.85, zorder=3)
bars2 = ax.bar(x + width/2, wer, width, label='WER (%)',
               color='#BF360C', alpha=0.85, zorder=3)

# value labels on bars
for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{bar.get_height():.1f}%', ha='center', va='bottom',
            fontsize=9.5, fontweight='bold', color='#1565C0')
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{bar.get_height():.1f}%', ha='center', va='bottom',
            fontsize=9.5, fontweight='bold', color='#BF360C')

# improvement annotation arrows
for i in range(len(methods) - 1):
    y_top = max(cer[i], wer[i]) + 5
    ax.annotate('', xy=(x[i+1] - width/2, cer[i+1] + 1),
                xytext=(x[i] - width/2, cer[i] - 1),
                arrowprops=dict(arrowstyle='->', color='#1565C0',
                                lw=1.2, linestyle='dashed'))

ax.set_xticks(x)
ax.set_xticklabels(methods, fontsize=10.5)
ax.set_ylabel('Error Rate (%)', fontsize=11)
ax.set_ylim(0, 68)
ax.set_title('Figure 5.1: OCR Accuracy Improvement\n'
             'Before vs. After Post-Processing (CER / WER)',
             fontsize=13, fontweight='bold', pad=14)
ax.legend(fontsize=10.5, framealpha=0.5)
ax.grid(axis='y', alpha=0.3, zorder=0)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))

# note
ax.text(0.5, -0.13,
        '* Lower is better.  Values are representative — replace with measurements from compare_tesseract.py.',
        ha='center', va='top', transform=ax.transAxes,
        fontsize=8.5, style='italic', color='#777')

plt.tight_layout()
plt.savefig('figure_5_1.png', dpi=180, bbox_inches='tight', facecolor='white')
print('Saved → figure_5_1.png')
plt.close()


# ═══════════════════════════════════════════════════════════════════
# FIGURE 5.2 — Per-Step Contribution to Accuracy
# ═══════════════════════════════════════════════════════════════════
steps = [
    'Step 0\nForm Blank Cleanup',
    'Step 1\nGarbage Line Removal',
    'Step 1.5\nInline Token Removal',
    'Step 2\nKhmer Char Corrections',
    'Step 3\nSymbol Cleanup',
    'Step 4\nPunctuation Fix',
    'Step 5\nBroken Word Repair',
]

# Cumulative CER after each step (starting from 22.5% after preprocessing)
# Each step reduces error further
cer_after_each = [20.8, 18.9, 17.4, 15.6, 15.1, 14.9, 14.8]
cer_start = 22.5

# CER reduction per step
reduction = []
prev = cer_start
for c in cer_after_each:
    reduction.append(round(prev - c, 1))
    prev = c

colors = ['#1565C0', '#1976D2', '#1E88E5', '#2E7D32',
          '#388E3C', '#BF360C', '#E64A19']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
fig.patch.set_facecolor('white')

# ── Left: CER reduction per step (horizontal bar) ──
y = np.arange(len(steps))
bars = ax1.barh(y, reduction, color=colors, alpha=0.88, zorder=3)
ax1.set_yticks(y)
ax1.set_yticklabels(steps, fontsize=9.5)
ax1.set_xlabel('CER Reduction (%)', fontsize=11)
ax1.set_title('CER Reduction per Post-Processing Step', fontsize=11.5,
              fontweight='bold')
ax1.grid(axis='x', alpha=0.3, zorder=0)
ax1.invert_yaxis()
for bar, val in zip(bars, reduction):
    ax1.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
             f'−{val}%', va='center', fontsize=9.5,
             fontweight='bold', color=bar.get_facecolor())

# ── Right: Cumulative CER after each step (line) ──
x_pts = list(range(len(steps) + 1))
y_pts = [cer_start] + cer_after_each
labels_x = ['Before\nPost-proc'] + [f'After\nStep {["0","1","1.5","2","3","4","5"][i]}'
                                      for i in range(len(steps))]

ax2.plot(x_pts, y_pts, 'o-', color='#1565C0', lw=2.2,
         markersize=8, markerfacecolor='white', markeredgewidth=2.2, zorder=4)
ax2.fill_between(x_pts, y_pts, alpha=0.12, color='#1565C0')

for xi, yi in zip(x_pts, y_pts):
    ax2.text(xi, yi + 0.35, f'{yi}%', ha='center', va='bottom',
             fontsize=9, fontweight='bold', color='#1565C0')

ax2.set_xticks(x_pts)
ax2.set_xticklabels(labels_x, fontsize=8.5)
ax2.set_ylabel('Cumulative CER (%)', fontsize=11)
ax2.set_ylim(12, 25)
ax2.set_title('Cumulative CER After Each Step', fontsize=11.5, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}%'))

fig.suptitle('Figure 5.2: Per-Step Contribution to Accuracy\n'
             'Relative Impact of Each Post-Processing Step on CER',
             fontsize=13, fontweight='bold', y=1.02)

plt.tight_layout()
plt.savefig('figure_5_2.png', dpi=180, bbox_inches='tight', facecolor='white')
print('Saved → figure_5_2.png')
plt.close()

print('\nDone. Replace values in this script once you run compare_tesseract.py with real data.')
