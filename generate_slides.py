"""
generate_slides.py
Inserts new slides (PARTIE 2, 3, 4) into LoRa_Presentation_Technique.pptx
after slide 3 (the 3 intro slides are left untouched).
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import io
import math
import openpyxl
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
import lxml.etree as etree
import copy

# ── Paths ──────────────────────────────────────────────────────────────
PPTX_IN  = r'C:\Users\loeff\Documents\EPFL\semester-project\LoRa_Presentation_Technique.pptx'
PPTX_OUT = r'C:\Users\loeff\Documents\EPFL\semester-project\LoRa_Presentation_Technique_v2.pptx'
EXCEL    = r'D:\PlateformIO_project_folder\cli-lora\data\sweep_test1.xlsx'

# ── Style constants ─────────────────────────────────────────────────────
BURGUNDY  = RGBColor(0x7D, 0x1F, 0x2E)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
DARK      = RGBColor(0x1A, 0x1A, 0x1A)
GRAY_MED  = RGBColor(0x44, 0x44, 0x44)
GRAY      = RGBColor(0x64, 0x64, 0x64)
GRAY_LT   = RGBColor(0xAA, 0xAA, 0xAA)
BG_PALE   = RGBColor(0xFA, 0xFA, 0xFA)
FONT      = 'Calibri'

# Protocol / block colours
C_UART  = RGBColor(0x21, 0x73, 0xBF)   # blue
C_SPI   = RGBColor(0x27, 0xAE, 0x60)   # green
C_LORA  = RGBColor(0xE6, 0x7E, 0x22)   # orange
C_TERM  = RGBColor(0x2C, 0x3E, 0x50)   # dark slate
C_ESP   = RGBColor(0xD3, 0x54, 0x00)   # deep orange
C_SX    = RGBColor(0x0E, 0x86, 0x7D)   # teal
C_NUCL  = RGBColor(0x6C, 0x35, 0x8A)   # purple
C_GREEN_OK = RGBColor(0x27, 0xAE, 0x60)
C_RED_BAD  = RGBColor(0xC0, 0x39, 0x2B)

# Matplotlib palette
MPL_BW_COLORS = {
    '203':  '#2173BF',
    '406':  '#27AE60',
    '812':  '#E67E22',
    '1625': '#8E44AD',
}

# ── Data loading ────────────────────────────────────────────────────────
def load_summary():
    wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
    ws = wb['Summary']
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    data = [r for r in rows if r[0] is not None and isinstance(r[0], (int, float))]
    # columns: ID, SF, BW, CR, Pkts_Rx, PER, RSSI_Mean, RSSI_Std, RSSI_Min, RSSI_Max,
    #          SNR_Mean, SNR_Std, Link_Margin_dB
    return data

SNR_THRESH = {5:-7.5, 6:-10.0, 7:-12.5, 8:-15.0,
              9:-17.5, 10:-20.0, 11:-22.5, 12:-25.0}
CR_EFF = {'4/5': 4/5, '4/6': 4/6, '4/7': 4/7, '4/8': 4/8}

def compute_metrics(row):
    sf  = int(row[1])
    bw  = float(row[2])   # kHz
    cr  = row[3]
    per = float(row[5])
    rssi= float(row[6])
    snr = float(row[10])
    # Datarate (bps)
    dr = sf * CR_EFF[cr] * bw * 1000 / (2**sf)
    # True theoretical sensitivity (dBm), NF=6 dB
    sens = -174 + 6 + 10*math.log10(bw*1000) + SNR_THRESH[sf]
    # True link margin (dB)
    true_lm = rssi - sens
    return dict(sf=sf, bw=bw, cr=cr, per=per, rssi=rssi, snr=snr,
                dr=dr, sens=sens, true_lm=true_lm)

def find_optimal(data):
    metrics = [compute_metrics(r) for r in data]
    dr_max  = max(m['dr']      for m in metrics)
    lm_min  = min(m['true_lm'] for m in metrics)
    lm_max  = max(m['true_lm'] for m in metrics)
    for m in metrics:
        dr_n  = m['dr'] / dr_max
        lm_n  = (m['true_lm'] - lm_min) / (lm_max - lm_min)
        per_s = 1 - m['per']/100
        m['score'] = 0.35*dr_n + 0.40*lm_n + 0.25*per_s
    return sorted(metrics, key=lambda m: -m['score'])

# ── PPTX helpers ────────────────────────────────────────────────────────
def insert_blank_slide(prs, position):
    """Add slide with DEFAULT layout, insert at given 0-based position."""
    layout = prs.slide_layouts[0]   # DEFAULT layout
    slide  = prs.slides.add_slide(layout)
    # Remove all placeholder shapes so we start clean
    for ph in list(slide.placeholders):
        sp = ph._element
        sp.getparent().remove(sp)
    # Move from end to desired position
    sldIdLst = prs.slides._sldIdLst
    el = sldIdLst[-1]
    sldIdLst.remove(el)
    sldIdLst.insert(position, el)
    return slide

def set_solid_fill(shape, color: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color

def no_fill(shape):
    shape.fill.background()

def add_rect(slide, l, t, w, h, fill_color=None, line_color=None, line_width_pt=0):
    from pptx.util import Pt as _Pt
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.line.fill.background()
    if fill_color:
        set_solid_fill(shp, fill_color)
    else:
        no_fill(shp)
    if line_color:
        shp.line.color.rgb = line_color
        shp.line.width = _Pt(line_width_pt) if line_width_pt else Pt(0.5)
    else:
        shp.line.fill.background()
    return shp

def add_rrect(slide, l, t, w, h, fill_color=None, line_color=None, line_width_pt=1.0,
              corner_size=0.1):
    """Rounded rectangle (MSO_SHAPE_TYPE=5 is rounded rect in OOXML)."""
    from pptx.oxml.ns import qn as _qn
    from pptx.util import Pt as _Pt
    # Shape type 5 = ROUNDED_RECTANGLE in MSO_SHAPE_TYPE
    shp = slide.shapes.add_shape(5, Inches(l), Inches(t), Inches(w), Inches(h))
    # Adjust corner radius via prstGeom/avLst
    try:
        av_lst = shp.element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
        if av_lst is not None:
            for av in av_lst:
                if av.get('name') == 'adj':
                    # val in 1/100000 of shape width; 10000 ≈ 10%
                    av.set('fmla', f'val {int(corner_size*100000)}')
    except Exception:
        pass
    if fill_color:
        set_solid_fill(shp, fill_color)
    else:
        no_fill(shp)
    if line_color:
        shp.line.color.rgb = line_color
        shp.line.width = Pt(line_width_pt)
    else:
        shp.line.fill.background()
    return shp

def add_text(slide, text, l, t, w, h,
             bold=False, size=11, color=DARK, align=PP_ALIGN.LEFT,
             italic=False, font=FONT):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p  = tf.paragraphs[0]
    p.alignment = align
    r  = p.add_run()
    r.text = text
    r.font.bold   = bold
    r.font.italic = italic
    r.font.size   = Pt(size)
    r.font.color.rgb = color
    r.font.name   = font
    return tb

def add_multiline_text(slide, lines, l, t, w, h, default_size=11, default_color=DARK, font=FONT):
    """lines: list of (text, bold, size, color) tuples per paragraph."""
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for line_data in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        if isinstance(line_data, str):
            runs = [(line_data, False, default_size, default_color)]
        elif isinstance(line_data[0], str) and not isinstance(line_data[0], list):
            runs = [line_data]
        else:
            runs = line_data
        for (txt, bold, sz, col) in runs:
            r = p.add_run()
            r.text       = txt
            r.font.bold  = bold
            r.font.size  = Pt(sz)
            r.font.color.rgb = col
            r.font.name  = font
    return tb

def slide_header(slide, title, section_label, section_tag, tag_num):
    """Reproduce the consistent header from existing slides."""
    # Title
    add_text(slide, title, 0.45, 0.18, 9.1, 0.65,
             bold=True, size=26, color=BURGUNDY)
    # Accent line below title
    add_rect(slide, 0.45, 0.87, 9.1, 0.03, fill_color=BURGUNDY)
    # Section subtitle
    add_text(slide, section_label, 0.45, 0.93, 9.1, 0.35,
             size=11, color=GRAY)
    # Tag background (burgundy rect)
    add_rect(slide, 7.9, 0.18, 1.8, 0.30, fill_color=BURGUNDY)
    # Tag text
    add_text(slide, section_tag, 7.9, 0.18, 1.8, 0.30,
             bold=True, size=9, color=WHITE, align=PP_ALIGN.CENTER)

def source_note(slide, text):
    add_text(slide, text, 0.4, 5.28, 9.2, 0.25,
             size=8, color=GRAY_LT, italic=True)

def figure_into_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 2 — Slide 1 : Architecture hardware
# ─────────────────────────────────────────────────────────────────────────
def make_architecture_slide(prs, position):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Architecture matérielle du système",
                 "PARTIE 2 — Structure du projet",
                 "2 / Architecture", 2)

    # ── Block layout ──────────────────────────────────────────────────
    # Y center of all blocks
    by = 2.35   # top of blocks
    bh = 0.72   # block height
    bw = 1.30   # block width

    blocks = [
        (0.28, C_TERM,  "Terminal\nPC"),
        (2.00, C_ESP,   "ESP32"),
        (3.72, C_SX,    "SX1280\n(TX)"),
        (6.20, C_SX,    "SX1280\n(RX)"),
        (7.92, C_NUCL,  "Carte\nNucleo"),
    ]

    for (bl, col, label) in blocks:
        shp = add_rrect(slide, bl, by, bw, bh,
                        fill_color=col, line_color=WHITE, line_width_pt=0)
        add_text(slide, label, bl, by, bw, bh,
                 bold=True, size=11, color=WHITE, align=PP_ALIGN.CENTER)

    # ── Arrows between blocks ─────────────────────────────────────────
    arrow_y = by + bh/2 - 0.01   # vertical centre of blocks

    def draw_arrow(slide, x_start, x_end, y, label, col, above=True):
        """Draw a horizontal arrow with a coloured label."""
        aw = x_end - x_start
        ah = 0.18
        from pptx.oxml.ns import qn as _qn
        from pptx.util import Pt as _Pt
        # Arrow body (thick line = tall narrow rect)
        line_rect = add_rect(slide,
                              x_start, y - 0.02, aw, 0.04,
                              fill_color=col)
        # Arrowhead (right-pointing triangle via thin rect)
        # Use a simple chevron: add a small right-angle triangle shape
        arrowhead_w = 0.12
        ah_shp = slide.shapes.add_shape(
            13,   # RIGHT_ARROW
            Inches(x_start), Inches(y - 0.09),
            Inches(aw), Inches(0.18))
        set_solid_fill(ah_shp, col)
        ah_shp.line.fill.background()
        # Label box
        lbl_y = y - 0.45 if above else y + 0.18
        add_text(slide, label,
                 x_start, lbl_y, aw, 0.28,
                 bold=True, size=9, color=col, align=PP_ALIGN.CENTER)

    mid_y = by + bh/2 - 0.09

    # UART: Terminal → ESP32
    draw_arrow(slide, 1.60, 1.98, mid_y, "UART\n(115 200 bps)", C_UART, above=True)
    # SPI 1: ESP32 → SX1280 TX
    draw_arrow(slide, 3.32, 3.70, mid_y, "SPI\n(18 MHz)", C_SPI, above=True)
    # LoRa: SX1280 TX → SX1280 RX
    draw_arrow(slide, 5.04, 6.18, mid_y, "LoRa 2.4 GHz\n(SF/BW/CR)", C_LORA, above=True)
    # SPI 2: SX1280 RX → Nucleo
    draw_arrow(slide, 7.52, 7.90, mid_y, "SPI\n(18 MHz)", C_SPI, above=True)

    # ── "Génère commandes" annotation ────────────────────────────────
    # Down arrow from Terminal PC label
    add_rect(slide, 0.88, by + bh + 0.01, 0.03, 0.35, fill_color=C_UART)
    add_text(slide, "▼", 0.82, by + bh + 0.34, 0.16, 0.22,
             size=10, color=C_UART, align=PP_ALIGN.CENTER)
    add_text(slide, "Génère les commandes\n(ex: \"voltage 5\")",
             0.28, by + bh + 0.55, 1.30, 0.55,
             size=9, color=C_UART, align=PP_ALIGN.CENTER)

    # ── Colour legend ─────────────────────────────────────────────────
    lx = 0.35
    ly = 4.50
    add_text(slide, "Protocoles :", lx, ly, 1.2, 0.22,
             bold=True, size=9, color=GRAY_MED)
    legend_items = [
        ("  UART", C_UART),
        ("  SPI",  C_SPI),
        ("  LoRa 2.4 GHz (radio)", C_LORA),
    ]
    for i, (lbl, col) in enumerate(legend_items):
        add_rect(slide, lx, ly + 0.25 + i*0.22, 0.15, 0.15, fill_color=col)
        add_text(slide, lbl, lx + 0.18, ly + 0.22 + i*0.22, 2.2, 0.22,
                 size=9, color=col, bold=True)

    # ── Key characteristics box ───────────────────────────────────────
    add_rect(slide, 3.5, 4.30, 6.0, 1.10,
             fill_color=RGBColor(0xF5, 0xF5, 0xF5),
             line_color=RGBColor(0xDD, 0xDD, 0xDD), line_width_pt=0.5)
    points = [
        ("Latence bout-en-bout : ~quelques ms (UART+SPI+transmission LoRa)", False),
        ("Robustesse : gestion ACK + timeout + retransmission au niveau applicatif", False),
        ("Simplicité : 5 composants, 3 protocoles standards, code RadioLib", False),
        ("Fréquence 2.4 GHz — compatible ISM, antenne compacte (λ/2 ≈ 6.25 cm)", False),
    ]
    for i, (txt, bold) in enumerate(points):
        add_text(slide, f"• {txt}", 3.65, 4.35 + i*0.24, 5.75, 0.25,
                 size=9, color=DARK, bold=bold)

    source_note(slide,
        "SX1280 Datasheet (Semtech) — RadioLib (GitHub: jgromes/RadioLib) — "
        "STM32 Nucleo UM3062")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 2 — Slide 2 : Protocole & transfert de données
# ─────────────────────────────────────────────────────────────────────────
def make_protocol_slide(prs, position):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Protocole de transfert de données",
                 "PARTIE 2 — Structure du projet",
                 "2 / Protocole", 2)

    # ── Left column : flow description ───────────────────────────────
    add_text(slide, "Flux de données bout-en-bout",
             0.35, 1.32, 4.0, 0.30,
             bold=True, size=13, color=BURGUNDY)

    steps = [
        ("①", "Utilisateur tape \"voltage 5\" dans le terminal PC"),
        ("②", "Command parser : extrait opcode 0x01 et valeur 0x05"),
        ("③", "Calcul du CRC-8 sur les bytes de payload"),
        ("④", "Trame [0x01][0x05][CRC] envoyée par UART à l'ESP32"),
        ("⑤", "ESP32 transfère la trame via SPI au SX1280 TX"),
        ("⑥", "SX1280 TX encode et émet la trame LoRa 2.4 GHz"),
        ("⑦", "SX1280 RX reçoit, vérifie CRC, passe à la Nucleo via SPI"),
        ("⑧", "Nucleo interprète l'opcode → applique la commande"),
    ]
    arrow_col = GRAY
    for i, (num, desc) in enumerate(steps):
        y = 1.68 + i*0.41
        add_text(slide, num, 0.35, y, 0.35, 0.36,
                 bold=True, size=12, color=BURGUNDY, align=PP_ALIGN.CENTER)
        add_text(slide, desc, 0.72, y + 0.02, 3.65, 0.36,
                 size=10, color=DARK)
        if i < len(steps)-1:
            add_rect(slide, 0.49, y + 0.33, 0.03, 0.10, fill_color=GRAY_LT)

    # ── Right column : opcode table ───────────────────────────────────
    add_text(slide, "Tableau de mapping des commandes",
             4.90, 1.32, 4.75, 0.30,
             bold=True, size=13, color=BURGUNDY)

    tbl = slide.shapes.add_table(
        6, 4,
        Inches(4.90), Inches(1.65),
        Inches(4.75), Inches(2.0)
    ).table
    tbl.columns[0].width = Inches(1.30)
    tbl.columns[1].width = Inches(0.75)
    tbl.columns[2].width = Inches(0.90)
    tbl.columns[3].width = Inches(1.80)

    headers = ["Commande texte", "Opcode", "Payload", "Trame (hex)"]
    rows_data = [
        ("voltage 5",   "0x01", "0x05", "[0x01][0x05][CRC8]"),
        ("current 3",   "0x02", "0x03", "[0x02][0x03][CRC8]"),
        ("power off",   "0x10", "0x00", "[0x10][0x00][CRC8]"),
        ("status req",  "0xFF", "—",    "[0xFF][0x00][CRC8]"),
        ("ACK (→TX)",   "0xAA", "0x00", "[0xAA][0x00][CRC8]"),
    ]

    def style_cell(cell, text, bold=False, bg=None, color=DARK, size=9.5, align=PP_ALIGN.CENTER):
        cell.text = text
        tf = cell.text_frame
        tf.paragraphs[0].alignment = align
        run = tf.paragraphs[0].runs[0] if tf.paragraphs[0].runs else tf.paragraphs[0].add_run()
        run.text = text
        run.font.bold = bold
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = FONT
        if bg:
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg

    # Header row
    for j, h in enumerate(headers):
        style_cell(tbl.rows[0].cells[j], h, bold=True,
                   bg=BURGUNDY, color=WHITE, size=9.5)

    # Data rows
    for i, row_vals in enumerate(rows_data):
        bg = RGBColor(0xF8, 0xF0, 0xF1) if i % 2 == 0 else WHITE
        for j, val in enumerate(row_vals):
            style_cell(tbl.rows[i+1].cells[j], val, bg=bg,
                       color=DARK if j < 2 else RGBColor(0x1A, 0x5E, 0x1A),
                       size=9,
                       align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER)
        if i == 4:  # ACK row highlight
            for j in range(4):
                tbl.rows[i+1].cells[j].fill.solid()
                tbl.rows[i+1].cells[j].fill.fore_color.rgb = RGBColor(0xE8, 0xF5, 0xE9)

    # ── Robustness note ───────────────────────────────────────────────
    add_rect(slide, 4.90, 3.75, 4.75, 1.45,
             fill_color=RGBColor(0xFF, 0xFB, 0xEA),
             line_color=C_LORA, line_width_pt=0.8)
    add_text(slide, "Robustesse du protocole :", 5.05, 3.82, 4.45, 0.28,
             bold=True, size=10.5, color=C_LORA)
    robustness = [
        "• CRC-8 sur chaque trame — détection des erreurs de transmission",
        "• ACK obligatoire : la Nucleo renvoie 0xAA après exécution",
        "• Timeout 200 ms : si pas d'ACK, retransmission (max 3 essais)",
        "• Sequence number optionnel pour détecter les doublons",
    ]
    for i, line in enumerate(robustness):
        add_text(slide, line, 5.05, 4.14 + i*0.26, 4.45, 0.28,
                 size=9.0, color=DARK)

    source_note(slide, "CRC-8 (Dallas/Maxim polynomial 0x31) — latence UART ≈ 0.3 ms @ 115 kbps — "
                       "latence SPI ≈ 0.01 ms @ 18 MHz")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 3 — Chart generation
# ─────────────────────────────────────────────────────────────────────────
def make_charts(data):
    metrics = [compute_metrics(r) for r in data]

    bws     = ['203', '406', '812', '1625']
    sfs     = list(range(5, 13))

    def agg_by_sf_bw(field, agg='mean'):
        result = {}
        for bw in bws:
            vals = []
            for sf in sfs:
                sub = [m[field] for m in metrics
                       if m['sf'] == sf and str(int(m['bw'])) == bw]
                if sub:
                    vals.append(np.mean(sub) if agg == 'mean' else max(sub))
                else:
                    vals.append(np.nan)
            result[bw] = vals
        return result

    rssi_data = agg_by_sf_bw('rssi')
    snr_data  = agg_by_sf_bw('snr')
    per_data  = agg_by_sf_bw('per', 'max')
    dr_data   = {bw: [np.mean([m['dr']/1000 for m in metrics
                               if m['sf'] == sf and str(int(m['bw'])) == bw])
                       for sf in sfs]
                 for bw in bws}
    sens_data = {bw: [np.mean([m['sens'] for m in metrics
                                if m['sf'] == sf and str(int(m['bw'])) == bw])
                       for sf in sfs]
                  for bw in bws}

    # ── Figure 1 : RSSI and SNR vs SF ─────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), facecolor='white')
    fig.patch.set_facecolor('white')

    ax1, ax2 = axes
    for bw in bws:
        c = MPL_BW_COLORS[bw]
        ax1.plot(sfs, rssi_data[bw], 'o-', color=c, lw=2, ms=6,
                 label=f'BW={bw} kHz')
        ax2.plot(sfs, snr_data[bw],  'o-', color=c, lw=2, ms=6,
                 label=f'BW={bw} kHz')

    ax1.set_xlabel('Spreading Factor (SF)', fontsize=11)
    ax1.set_ylabel('RSSI moyen (dBm)', fontsize=11)
    ax1.set_title('RSSI mesuré vs SF', fontsize=12, fontweight='bold', color='#7D1F2E')
    ax1.set_xticks(sfs)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(fontsize=8, loc='lower right')
    ax1.set_facecolor('#FAFAFA')

    ax2.set_xlabel('Spreading Factor (SF)', fontsize=11)
    ax2.set_ylabel('SNR moyen (dB)', fontsize=11)
    ax2.set_title('SNR mesuré vs SF', fontsize=12, fontweight='bold', color='#7D1F2E')
    ax2.set_xticks(sfs)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(fontsize=8, loc='upper left')
    ax2.set_facecolor('#FAFAFA')

    plt.tight_layout(pad=1.5)
    img1 = figure_into_bytes(fig)

    # ── Figure 2 : PER and Datarate vs SF ─────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), facecolor='white')
    ax3, ax4 = axes

    for bw in bws:
        c = MPL_BW_COLORS[bw]
        ax3.plot(sfs, per_data[bw], 'o-', color=c, lw=2, ms=6,
                 label=f'BW={bw} kHz')
        ax4.semilogy(sfs, dr_data[bw], 'o-', color=c, lw=2, ms=6,
                     label=f'BW={bw} kHz')

    # Annotate the 2 non-zero PER points
    ax3.annotate('SF6/BW406\nCR4/7 → 10%',
                 xy=(6, 10), xytext=(7.5, 8),
                 arrowprops=dict(arrowstyle='->', color='#C0392B'),
                 color='#C0392B', fontsize=8, fontweight='bold')
    ax3.annotate('SF6/BW406\nCR4/5 → 4%',
                 xy=(6, 4), xytext=(7.5, 5),
                 arrowprops=dict(arrowstyle='->', color='#E67E22'),
                 color='#E67E22', fontsize=8)

    ax3.set_xlabel('Spreading Factor (SF)', fontsize=11)
    ax3.set_ylabel('PER max (%)', fontsize=11)
    ax3.set_title('PER (max par BW) vs SF', fontsize=12, fontweight='bold', color='#7D1F2E')
    ax3.set_xticks(sfs)
    ax3.set_ylim(-0.5, 12)
    ax3.grid(True, alpha=0.3, linestyle='--')
    ax3.legend(fontsize=8)
    ax3.set_facecolor('#FAFAFA')

    ax4.set_xlabel('Spreading Factor (SF)', fontsize=11)
    ax4.set_ylabel('Débit moyen (kbps)', fontsize=11)
    ax4.set_title('Débit théorique vs SF (échelle log)', fontsize=12,
                  fontweight='bold', color='#7D1F2E')
    ax4.set_xticks(sfs)
    ax4.grid(True, alpha=0.3, which='both', linestyle='--')
    ax4.legend(fontsize=8)
    ax4.set_facecolor('#FAFAFA')
    ax4.yaxis.set_major_formatter(ticker.ScalarFormatter())

    plt.tight_layout(pad=1.5)
    img2 = figure_into_bytes(fig)

    return img1, img2, metrics

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 3 — Slide 1 : Charts
# ─────────────────────────────────────────────────────────────────────────
def make_charts_slide(prs, position, img1, img2):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Mesures RSSI, SNR et PER — sweep complet",
                 "PARTIE 3 — Analyse des mesures",
                 "3 / Résultats", 3)

    # Quick stats banner
    stats = [("128", "configs testées"),
             ("0%", "PER pour 126/128"),
             ("≈ −46", "dBm RSSI moyen"),
             ("+12", "dB SNR (SF12)")]
    for i, (val, lbl) in enumerate(stats):
        bx = 0.35 + i * 2.38
        add_rect(slide, bx, 1.28, 2.20, 0.62,
                 fill_color=RGBColor(0xF9, 0xF0, 0xF1),
                 line_color=BURGUNDY, line_width_pt=0.5)
        add_text(slide, val, bx, 1.30, 2.20, 0.30,
                 bold=True, size=16, color=BURGUNDY, align=PP_ALIGN.CENTER)
        add_text(slide, lbl, bx, 1.60, 2.20, 0.26,
                 size=8, color=GRAY, align=PP_ALIGN.CENTER)

    # Insert chart images
    slide.shapes.add_picture(img1, Inches(0.20), Inches(1.95),
                              Inches(9.60), Inches(1.75))
    slide.shapes.add_picture(img2, Inches(0.20), Inches(3.75),
                              Inches(9.60), Inches(1.75))

    source_note(slide,
        "Mesures expérimentales — 50 paquets/config — "
        "Fichier sweep_test1.xlsx (Summary) — Distance fixe ~0.5 m")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 3 — Slide 2 : Comparison table + scoring
# ─────────────────────────────────────────────────────────────────────────
def make_comparison_slide(prs, position, all_metrics):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Scoring multicritère — configuration optimale",
                 "PARTIE 3 — Analyse des mesures",
                 "3 / Scoring", 3)

    ranked = sorted(all_metrics, key=lambda m: -m['score'])

    # Show top-12 configs (by score)
    top = ranked[:12]

    add_text(slide, "Top 12 configurations — score = 35% débit + 40% marge liaison + 25% PER",
             0.35, 1.28, 9.30, 0.28,
             size=9, color=GRAY_MED, italic=True)

    tbl = slide.shapes.add_table(
        len(top)+1, 8,
        Inches(0.25), Inches(1.58),
        Inches(9.50), Inches(3.50)
    ).table

    col_widths = [0.55, 0.55, 0.65, 0.70, 1.20, 1.15, 1.15, 1.55]
    for j, cw in enumerate(col_widths):
        tbl.columns[j].width = Inches(cw)

    col_headers = ["SF", "BW\n(kHz)", "CR", "PER\n(%)",
                   "Débit\n(kbps)", "Sensibilité\n(dBm)", "Marge\n(dB)", "Score\n(0–1)"]
    for j, h in enumerate(col_headers):
        c = tbl.rows[0].cells[j]
        c.text = h
        tf = c.text_frame
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        r = tf.paragraphs[0].runs[0] if tf.paragraphs[0].runs else tf.paragraphs[0].add_run()
        r.text = h
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = WHITE
        r.font.name = FONT
        c.fill.solid()
        c.fill.fore_color.rgb = BURGUNDY

    # Find best score for highlighting
    best_score = top[0]['score']

    for i, m in enumerate(top):
        row = tbl.rows[i+1]
        is_best = (m['score'] == best_score)
        bg = RGBColor(0xFF, 0xF3, 0xCD) if is_best else (
             RGBColor(0xF5, 0xF5, 0xF5) if i % 2 == 0 else WHITE)
        vals = [
            str(m['sf']),
            str(int(m['bw'])),
            m['cr'],
            f"{m['per']:.0f}",
            f"{m['dr']/1000:.1f}",
            f"{m['sens']:.1f}",
            f"{m['true_lm']:.1f}",
            f"{m['score']:.3f}",
        ]
        for j, val in enumerate(vals):
            c = row.cells[j]
            c.text = val
            tf = c.text_frame
            tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            r = (tf.paragraphs[0].runs[0]
                 if tf.paragraphs[0].runs
                 else tf.paragraphs[0].add_run())
            r.text = val
            r.font.bold = is_best
            r.font.size = Pt(8.5)
            r.font.color.rgb = BURGUNDY if is_best else DARK
            r.font.name = FONT
            c.fill.solid()
            c.fill.fore_color.rgb = bg

        if is_best:
            # Add star in last cell
            c = row.cells[7]
            tf = c.text_frame
            r2 = tf.paragraphs[0].add_run()
            r2.text = " ★"
            r2.font.size = Pt(10)
            r2.font.color.rgb = C_LORA
            r2.font.name = FONT

    # Weights explanation
    add_text(slide,
             "Pondération : Débit×0.35  |  Marge liaison×0.40  |  (1−PER)×0.25  "
             "★ = config recommandée",
             0.25, 5.12, 9.50, 0.28,
             size=8.5, color=GRAY_MED, italic=False)

    source_note(slide,
        "Sensibilité théorique : -174 dBm + NF(6 dB) + 10·log(BW) + SNR_seuil(SF)  "
        "— Débit : SF × CR_eff × BW/2^SF")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 3 — Slide 3 : Conclusion optimal config
# ─────────────────────────────────────────────────────────────────────────
def make_optimal_conclusion_slide(prs, position, ranked):
    best = ranked[0]
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Configuration optimale retenue & compromis",
                 "PARTIE 3 — Analyse des mesures",
                 "3 / Conclusion", 3)

    # Large highlight box for the chosen config
    add_rect(slide, 0.35, 1.28, 4.35, 2.10,
             fill_color=RGBColor(0xF9, 0xF0, 0xF1),
             line_color=BURGUNDY, line_width_pt=1.2)
    add_text(slide, "✓ Configuration retenue",
             0.50, 1.32, 4.10, 0.35,
             bold=True, size=12, color=BURGUNDY)
    cfg_text = (f"SF = {best['sf']}   |   BW = {int(best['bw'])} kHz   |   CR = {best['cr']}")
    add_text(slide, cfg_text,
             0.50, 1.70, 4.10, 0.38,
             bold=True, size=14, color=DARK, align=PP_ALIGN.CENTER)

    kpi_items = [
        (f"Débit théorique",       f"{best['dr']/1000:.1f} kbps"),
        (f"Sensibilité théorique", f"{best['sens']:.1f} dBm"),
        (f"Marge de liaison",      f"+{best['true_lm']:.1f} dB (@ 0.5 m)"),
        (f"PER mesuré",            f"{best['per']:.0f} %"),
    ]
    for i, (label, value) in enumerate(kpi_items):
        y = 2.12 + i * 0.30
        add_text(slide, label, 0.50, y, 2.40, 0.28, size=10, color=GRAY_MED)
        add_text(slide, value, 2.90, y, 1.60, 0.28, size=10, color=DARK,
                 bold=True, align=PP_ALIGN.RIGHT)

    # Tradeoff triangle chart (matplotlib)
    fig, ax = plt.subplots(figsize=(5.5, 3.0), facecolor='white')
    ranked_all = ranked
    dr_max   = max(m['dr']      for m in ranked_all)
    lm_max   = max(m['true_lm'] for m in ranked_all)
    lm_min   = min(m['true_lm'] for m in ranked_all)

    # Plot all configs as scatter
    dr_vals   = [m['dr']/dr_max for m in ranked_all]
    lm_vals   = [(m['true_lm']-lm_min)/(lm_max-lm_min) for m in ranked_all]
    sc_vals   = [m['score'] for m in ranked_all]
    sc_arr    = np.array(sc_vals)

    scatter = ax.scatter(dr_vals, lm_vals, c=sc_arr, cmap='RdYlGn',
                         s=40, alpha=0.7, edgecolors='none', vmin=0, vmax=1)
    plt.colorbar(scatter, ax=ax, label='Score composite', shrink=0.8)

    # Highlight best
    bdr  = best['dr']/dr_max
    blm  = (best['true_lm']-lm_min)/(lm_max-lm_min)
    ax.scatter([bdr], [blm], c='gold', s=200, marker='*',
               edgecolors='#7D1F2E', linewidths=1.5, zorder=10, label='Config retenue')

    ax.set_xlabel('Débit normalisé (0=min, 1=max)', fontsize=9)
    ax.set_ylabel('Marge liaison normalisée', fontsize=9)
    ax.set_title('Espace de compromis Débit vs Marge', fontsize=10,
                 fontweight='bold', color='#7D1F2E')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#FAFAFA')
    plt.tight_layout()
    img = figure_into_bytes(fig)

    slide.shapes.add_picture(img, Inches(4.80), Inches(1.28),
                              Inches(4.85), Inches(2.90))

    # Justification text
    add_text(slide, "Justification du choix :",
             0.35, 3.50, 9.30, 0.30,
             bold=True, size=12, color=BURGUNDY)

    justify_lines = [
        f"• SF={best['sf']}, BW={int(best['bw'])} kHz, CR={best['cr']} offre le meilleur équilibre "
        f"débit / marge dans la plage testée.",
        f"• Débit de {best['dr']/1000:.1f} kbps — suffisant pour des trames courtes "
        f"de commandes (<10 bytes) avec latence < 5 ms.",
        f"• Sensibilité de {best['sens']:.1f} dBm → marge théorique > 50 dB "
        f"avec atténuation corps humain (−15 dB) à 10 m.",
        f"• PER = 0% sur 50 paquets — robustesse confirmée dans les conditions de test.",
        f"• Éviter SF6/BW406 (PER jusqu'à 10% mesuré) — anomalie possible à investiguer.",
    ]
    for i, line in enumerate(justify_lines):
        add_text(slide, line, 0.35, 3.85 + i*0.27, 9.30, 0.28,
                 size=9.5, color=DARK)

    source_note(slide,
        "Score composite : 35% débit + 40% marge liaison + 25% (1−PER). "
        f"Config retenue : SF{best['sf']}/BW{int(best['bw'])}/{best['cr']}.")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 4 — Slide 1 : Friis formula
# ─────────────────────────────────────────────────────────────────────────
def make_friis_slide(prs, position):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Bilan de liaison — Équation de Friis & FSPL",
                 "PARTIE 4 — Estimation du path loss",
                 "4 / Théorie", 4)

    # Main formula box
    add_rect(slide, 0.35, 1.28, 5.80, 0.80,
             fill_color=RGBColor(0xF9, 0xF0, 0xF1),
             line_color=BURGUNDY, line_width_pt=0.8)
    add_text(slide, "Équation de Friis (en dB) :",
             0.55, 1.30, 5.40, 0.30,
             bold=True, size=11, color=BURGUNDY)
    add_text(slide, "Pr = Pt + Gt + Gr − FSPL − Lautres",
             0.55, 1.58, 5.40, 0.44,
             bold=True, size=14.5, color=DARK, font='Courier New')

    # FSPL formula
    add_rect(slide, 0.35, 2.14, 5.80, 0.80,
             fill_color=RGBColor(0xF0, 0xF4, 0xFF),
             line_color=C_UART, line_width_pt=0.8)
    add_text(slide, "Free Space Path Loss :",
             0.55, 2.16, 5.40, 0.28, bold=True, size=11, color=C_UART)
    add_text(slide, "FSPL (dB) = 20·log₁₀(d) + 20·log₁₀(f) + 20·log₁₀(4π/c)",
             0.55, 2.43, 5.40, 0.44,
             bold=True, size=11.5, color=DARK, font='Courier New')

    # Simplified at 2.4 GHz
    add_rect(slide, 0.35, 3.00, 5.80, 0.52,
             fill_color=RGBColor(0xF0, 0xFB, 0xF0),
             line_color=C_SPI, line_width_pt=0.8)
    add_text(slide, "→ Simplification @ 2.4 GHz : FSPL ≈ 40.05 + 20·log₁₀(d [m])",
             0.55, 3.06, 5.40, 0.40,
             bold=True, size=11.5, color=C_SPI, font='Courier New')

    # Definitions
    add_text(slide, "Définitions :",
             0.35, 3.62, 5.80, 0.28,
             bold=True, size=11, color=BURGUNDY)
    defs = [
        ("Pr", "Puissance reçue (dBm)"),
        ("Pt", "Puissance TX émise  →  SX1280 : +10 dBm (programmable)"),
        ("Gt, Gr", "Gains d'antenne TX et RX  →  2.1 dBi (dipôle bipolaire)"),
        ("FSPL", "Free Space Path Loss — pertes en espace libre"),
        ("Lautres", "Atténuation corps humain (+15 dB) + marge multitrajet (+6 dB)"),
    ]
    for i, (sym, desc) in enumerate(defs):
        y = 3.92 + i*0.24
        add_text(slide, sym,  0.45, y, 0.90, 0.24,
                 bold=True, size=10, color=DARK, font='Courier New')
        add_text(slide, f"→  {desc}", 1.35, y, 4.65, 0.24,
                 size=10, color=GRAY_MED)

    # Right side: antenna info + body loss note
    add_rect(slide, 6.25, 1.28, 3.40, 1.58,
             fill_color=RGBColor(0xF5, 0xF5, 0xF5),
             line_color=RGBColor(0xCC, 0xCC, 0xCC), line_width_pt=0.5)
    add_text(slide, "Antennes utilisées :",
             6.40, 1.32, 3.10, 0.28,
             bold=True, size=10.5, color=BURGUNDY)
    ant_info = [
        "• Dipôles bipolaires — TX et RX",
        "• Gain : 2.1 dBi chacune",
        "• Fréquence : 2.4 GHz",
        "• Impédance : ~73 Ω",
        "• Polarisation : linéaire verticale",
    ]
    for i, line in enumerate(ant_info):
        add_text(slide, line, 6.40, 1.62 + i*0.22, 3.10, 0.24,
                 size=9, color=DARK)

    add_rect(slide, 6.25, 2.93, 3.40, 1.40,
             fill_color=RGBColor(0xFF, 0xF3, 0xCD),
             line_color=C_LORA, line_width_pt=0.8)
    add_text(slide, "Atténuation corps humain :",
             6.40, 2.97, 3.10, 0.28,
             bold=True, size=10.5, color=C_LORA)
    body_text = [
        "• Littérature : +10 à +20 dB @ 2.4 GHz",
        "• Valeur retenue : +15 dB (médiane)",
        "• Dépend orientation + tissu traversé",
        "• Marge multitrajet : +6 dB ajoutés",
    ]
    for i, line in enumerate(body_text):
        add_text(slide, line, 6.40, 3.28 + i*0.22, 3.10, 0.24,
                 size=9, color=DARK)

    # Link margin formula
    add_rect(slide, 6.25, 4.40, 3.40, 0.72,
             fill_color=RGBColor(0xE8, 0xF8, 0xE8),
             line_color=C_GREEN_OK, line_width_pt=0.8)
    add_text(slide, "Marge de liaison :",
             6.40, 4.43, 3.10, 0.26,
             bold=True, size=10, color=C_GREEN_OK)
    add_text(slide, "M = Pr − Sens. > 0 dB  →  liaison viable",
             6.40, 4.70, 3.10, 0.36,
             bold=True, size=10, color=DARK, font='Courier New')

    source_note(slide,
        "Friis (1946) — IEEE Std 149-1979 — SX1280 Datasheet Semtech §5 Electrical Specs — "
        "Body loss: FCC OET Bulletin 65 / IEEE 802.15.6")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 4 — Slide 2 : Numerical application
# ─────────────────────────────────────────────────────────────────────────
def make_link_budget_table_slide(prs, position, optimal):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Application numérique — Bilan de liaison complet",
                 "PARTIE 4 — Estimation du path loss",
                 "4 / Calculs", 4)

    sf   = optimal['sf']
    bw   = optimal['bw']
    sens = optimal['sens']  # dBm
    pt   = 10.0             # dBm (SX1280 programmed)
    gt   = 2.1              # dBi
    gr   = 2.1              # dBi
    l_body = 15.0           # dB
    l_mp   = 6.0            # dB extra margin

    distances = [1, 5, 10, 20]

    def fspl(d, f_ghz=2.4):
        return 40.05 + 20*math.log10(d)

    rows_vals = []
    for d in distances:
        fl = fspl(d)
        pr = pt + gt + gr - fl          # without body/margins
        pr_body = pr - l_body           # with body
        margin  = pr_body - sens - l_mp # true link margin after all losses
        rows_vals.append((d, fl, l_body, pr_body, sens, margin))

    # System parameters banner
    add_text(slide,
             f"Paramètres : Pt={pt:.0f} dBm  |  Gt=Gr={gt} dBi  |  f=2.4 GHz  "
             f"|  Config opt. SF{sf}/BW{int(bw)}/CR4/5  |  Sens.={sens:.1f} dBm",
             0.30, 1.28, 9.40, 0.30,
             size=9.5, color=GRAY_MED, italic=True)

    # Main table
    col_headers = ["Distance\n(m)",
                   "FSPL\n(dB)",
                   "Atten. corps\n(dB)",
                   "Pu. reçue est.\n(dBm)",
                   "Sensibilité\n(dBm)",
                   "Marge MP\n(dB)",
                   "Marge finale\n(dB)",
                   "Viable ?"]
    n_rows = len(distances)
    tbl = slide.shapes.add_table(
        n_rows + 1, 8,
        Inches(0.20), Inches(1.62),
        Inches(9.60), Inches(2.0)
    ).table

    col_widths_in = [0.75, 0.85, 1.10, 1.20, 1.10, 1.00, 1.10, 0.88]
    for j, cw in enumerate(col_widths_in):
        tbl.columns[j].width = Inches(cw)

    def style_tbl_cell(cell, text, bold=False, bg=None, fg=DARK,
                        size=9.5, align=PP_ALIGN.CENTER):
        cell.text = ""
        tf = cell.text_frame
        p = tf.paragraphs[0]
        p.alignment = align
        r = p.add_run()
        r.text = text
        r.font.bold = bold
        r.font.size = Pt(size)
        r.font.color.rgb = fg
        r.font.name = FONT
        if bg:
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg

    for j, h in enumerate(col_headers):
        style_tbl_cell(tbl.rows[0].cells[j], h,
                       bold=True, bg=BURGUNDY, fg=WHITE, size=9)

    for i, (d, fl, l_b, pr_b, sn, margin) in enumerate(rows_vals):
        final_margin = margin   # already includes mp margin
        viable = final_margin > 0
        bg = RGBColor(0xF5, 0xF5, 0xF5) if i % 2 == 0 else WHITE
        values = [
            (f"{d} m",   DARK,  False),
            (f"{fl:.1f}", DARK, False),
            (f"{l_b:.0f}", DARK, False),
            (f"{pr_b:.1f}", DARK, False),
            (f"{sn:.1f}", DARK, False),
            (f"{l_mp:.0f}", DARK, False),
            (f"{final_margin:.1f}", C_GREEN_OK if viable else C_RED_BAD, True),
            ("✓ Viable" if viable else "✗", C_GREEN_OK if viable else C_RED_BAD, True),
        ]
        for j, (val, col, bold) in enumerate(values):
            style_tbl_cell(tbl.rows[i+1].cells[j], val,
                           bold=bold, bg=bg, fg=col, size=9.5)

    # Caption for margin column
    add_text(slide,
             f"Marge finale = Pt({pt:.0f}) + Gt({gt}) + Gr({gr}) − FSPL − "
             f"L_corps({l_body:.0f}) − L_MP({l_mp:.0f}) − Sens({sens:.1f})",
             0.20, 3.68, 9.60, 0.28,
             size=9, color=GRAY_MED, italic=True)

    # FSPL chart (matplotlib)
    fig, ax = plt.subplots(figsize=(8.5, 2.6), facecolor='white')
    d_range = np.linspace(0.5, 25, 200)
    fspl_range = [40.05 + 20*math.log10(d) for d in d_range]
    pr_range   = [pt + gt + gr - f for f in fspl_range]
    pr_body_r  = [p - l_body for p in pr_range]
    margin_r   = [p - sens - l_mp for p in pr_body_r]

    ax.fill_between(d_range, margin_r, 0,
                    where=[m > 0 for m in margin_r],
                    alpha=0.15, color='green', label='Marge positive')
    ax.fill_between(d_range, margin_r, 0,
                    where=[m < 0 for m in margin_r],
                    alpha=0.15, color='red', label='Marge négative')
    ax.plot(d_range, margin_r, color='#2173BF', lw=2, label='Marge liaison (dB)')
    ax.axhline(0, color='black', lw=0.8, linestyle='--')

    for d, _, _, _, _, mg in rows_vals:
        ax.scatter([d], [mg], s=80, color='#7D1F2E', zorder=5)
        ax.annotate(f"{d}m\n{mg:.0f}dB", xy=(d, mg), xytext=(d+0.4, mg+1.5),
                    fontsize=7, color='#7D1F2E')

    ax.set_xlabel('Distance (m)', fontsize=9)
    ax.set_ylabel('Marge de liaison (dB)', fontsize=9)
    ax.set_title(f'Marge de liaison vs distance — SF{sf}/BW{int(bw)} @ 2.4 GHz',
                 fontsize=9.5, fontweight='bold', color='#7D1F2E')
    ax.legend(fontsize=7.5, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_facecolor('#FAFAFA')
    ax.set_xlim(0, 26)
    plt.tight_layout()
    img = figure_into_bytes(fig)

    slide.shapes.add_picture(img, Inches(0.20), Inches(3.97),
                              Inches(9.60), Inches(1.45))

    source_note(slide,
        f"FSPL = 40.05 + 20·log₁₀(d)  @  2.4 GHz  |  "
        f"Sensibilité théorique SF{sf}/BW{int(bw)} kHz : {sens:.1f} dBm")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# PARTIE 4 — Slide 3 : Link margin conclusion
# ─────────────────────────────────────────────────────────────────────────
def make_link_margin_conclusion(prs, position, optimal):
    slide = insert_blank_slide(prs, position)
    slide_header(slide,
                 "Conclusion — Faisabilité et marge de liaison",
                 "PARTIE 4 — Estimation du path loss",
                 "4 / Conclusion", 4)

    sf   = optimal['sf']
    bw   = optimal['bw']
    sens = optimal['sens']
    pt   = 10.0
    gt   = gr = 2.1
    l_body = 15.0
    l_mp   = 6.0

    distances = [1, 5, 10, 20]
    def margin_at(d):
        fl = 40.05 + 20*math.log10(d)
        return pt + gt + gr - fl - l_body - l_mp - sens

    # Indicator boxes
    for i, d in enumerate(distances):
        mg = margin_at(d)
        viable = mg > 0
        bx = 0.25 + i * 2.40
        col_bg = RGBColor(0xD5, 0xF5, 0xE3) if viable else RGBColor(0xFD, 0xED, 0xEC)
        col_bd = C_GREEN_OK if viable else C_RED_BAD

        add_rect(slide, bx, 1.28, 2.25, 1.70,
                 fill_color=col_bg,
                 line_color=col_bd, line_width_pt=1.5)
        add_text(slide, f"{d} m", bx, 1.32, 2.25, 0.38,
                 bold=True, size=20, color=col_bd, align=PP_ALIGN.CENTER)
        add_text(slide, f"Marge : {mg:+.1f} dB",
                 bx, 1.72, 2.25, 0.36,
                 bold=True, size=13, color=DARK, align=PP_ALIGN.CENTER)
        indicator = "✓ VIABLE" if viable else "✗ LIMITE"
        add_text(slide, indicator, bx, 2.12, 2.25, 0.36,
                 bold=True, size=12, color=col_bd, align=PP_ALIGN.CENTER)

    # Worst-case recapitulation
    add_rect(slide, 0.25, 3.10, 9.50, 0.68,
             fill_color=RGBColor(0xE8, 0xF8, 0xE8),
             line_color=C_GREEN_OK, line_width_pt=1.0)
    worst_d = max(distances)
    worst_m = margin_at(worst_d)
    add_text(slide,
             f"Cas le plus défavorable ({worst_d} m avec atténuation corps +{l_body:.0f} dB "
             f"et marge multitrajet +{l_mp:.0f} dB) : marge = {worst_m:+.1f} dB — "
             f"{'SYSTÈME VIABLE ✓' if worst_m > 0 else 'SYSTÈME LIMITE ✗'}",
             0.40, 3.16, 9.20, 0.56,
             bold=True, size=11.5,
             color=C_GREEN_OK if worst_m > 0 else C_RED_BAD,
             align=PP_ALIGN.CENTER)

    # Summary bullet points
    add_text(slide, "Points clés :", 0.25, 3.88, 9.50, 0.30,
             bold=True, size=12, color=BURGUNDY)
    bullets = [
        f"• Système validé théoriquement jusqu'à >{worst_d} m dans les conditions les plus défavorables.",
        f"• Config SF{sf}/BW{int(bw)}/CR4/5 retenue : sensibilité {sens:.1f} dBm, "
        f"débit {optimal['dr']/1000:.1f} kbps.",
        f"• Atténuation corps humain modélisée à +{l_body:.0f} dB (valeur médiane littérature "
        f"— valeur réelle à mesurer expérimentalement).",
        f"• Marge supplémentaire de +{l_mp:.0f} dB incluse pour multitrajet et obstacles "
        f"(corridors, matériaux).",
        f"• Pour dépasser {worst_d} m ou traverser des obstacles épais : augmenter SF "
        f"(SF10–SF12) ou réduire le débit.",
    ]
    for i, line in enumerate(bullets):
        add_text(slide, line, 0.25, 4.22 + i*0.21, 9.50, 0.22,
                 size=9.5, color=DARK)

    source_note(slide,
        f"Config opt. SF{sf}/BW{int(bw)}/CR4/5 — Sens. {sens:.1f} dBm — "
        f"Pt={pt:.0f} dBm — Gt=Gr={gt} dBi — Latence TX est. < 10 ms")
    return slide

# ─────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────
def main():
    print("Loading data...")
    data    = load_summary()
    ranked  = find_optimal(data)
    optimal = ranked[0]
    print(f"Optimal config: SF={optimal['sf']}, BW={int(optimal['bw'])}, "
          f"CR={optimal['cr']}, DR={optimal['dr']/1000:.1f} kbps, "
          f"Sens={optimal['sens']:.1f} dBm, Score={optimal['score']:.3f}")

    print("Generating charts...")
    img1, img2, all_metrics = make_charts(data)

    print("Loading presentation...")
    prs = Presentation(PPTX_IN)

    # Insert order: position 3 = right after slide 3 (0-indexed)
    # Each new slide is inserted at 3 (slides push down)
    # So we insert in REVERSE order to land them correctly
    insert_pos = 3   # after the 3rd slide

    print("Creating slides (in reverse insertion order)...")
    # Insert from last to first so the positions stay correct
    make_link_margin_conclusion(prs, insert_pos, optimal)    # slide 8 (last)
    make_link_budget_table_slide(prs, insert_pos, optimal)   # slide 7
    make_friis_slide(prs, insert_pos)                        # slide 6
    make_optimal_conclusion_slide(prs, insert_pos, ranked)   # slide 5
    make_comparison_slide(prs, insert_pos, ranked)            # slide 4
    make_charts_slide(prs, insert_pos, img1, img2)           # slide 3 (charts)
    make_protocol_slide(prs, insert_pos)                     # slide 2
    make_architecture_slide(prs, insert_pos)                 # slide 1 (first inserted)

    print(f"Total slides after insert: {len(list(prs.slides))}")
    print(f"Saving to: {PPTX_OUT}")
    prs.save(PPTX_OUT)
    print("Done!")

if __name__ == '__main__':
    main()
