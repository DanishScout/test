import base64
import math
import requests
import pandas as pd
import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

# -----------------------
# DATA INDLÆSNING (Sker kun én gang globalt ved opstart i hukommelsen)
# -----------------------
print("⚡ Indlæser Superliga & Premier League data til HTML-Scatter...")
try:
    files = ['den1.csv', 'eng1.csv']
    df_list = []
    for f in files:
        try:
            temp_df = pd.read_csv(f)
            df_list.append(temp_df)
        except Exception as file_err:
            print(f"⚠️ Kunne ikke læse filen {f}: {file_err}")
            
    if df_list:
        df_global = pd.concat(df_list, ignore_index=True)
        print(f"✅ Scatter-data er klar! Indlæste {len(df_global)} spillere fra Danmark og England.")
    else:
        df_global = pd.DataFrame()
except Exception as e:
    print(f"⚠️ Kritisk fejl under indlæsning af data: {e}")
    df_global = pd.DataFrame()

# Globale parametre til udelukkelse af tekst-kolonner
exclude_cols = {
    "Team", "contestantId", "playerId", "Short Name", "Player Name", "Age", 
    "Position_x", "Nationality", "Position_y", "total mins played", "Pos.", "League"
}

def get_custom_titles(suffix):
    return {
        f"total goals{suffix}": "Goals",
        "G/A": "G+A",
        f"xG{suffix}": "npxG",
        f"total ontarget attempt{suffix}": "Shots On Target"
    }

def vis_scatter_page(stat_type, x_axis_label, y_axis_label, sel_leagues, sel_positions, min_age, max_age, min_mins, max_mins, top10_x, top10_y, u21, u19, highlight_players, highlight_teams):
    if df_global.empty:
        return "<div style='color:white; padding:20px;'>Ingen data tilgængelig. Kontroller CSV-filerne.</div>"

    # Lav en kopi af det globale datasæt til filtrering
    df = df_global.copy()

    # 1. Definer suffiks baseret på stat_type
    suffix = "_p90" if stat_type == "Per 90" else "_Total"
    stat_label = "p90" if stat_type == "Per 90" else "Total"

    # 2. Beregn kombinerede metrikker og hent ordbog
    df['G/A'] = df[f'total goals{suffix}'] + df[f'total assists{suffix}']
    custom_titles = get_custom_titles(suffix)

    # Find gyldige metrikker baseret på dine krav
    metric_candidates = [f"total goals{suffix}", f"xG{suffix}", f"total ontarget attempt{suffix}", "G/A"]
    metric_candidates = [col for col in metric_candidates if col in df.columns]

    def clean_label(metric):
        return custom_titles.get(metric, metric.replace(suffix, "").capitalize())

    metric_labels_dict = {metric: clean_label(metric) for metric in metric_candidates}
    label_to_metric = {v: k for k, v in metric_labels_dict.items()}

    x_col = label_to_metric.get(x_axis_label, f"xG{suffix}")
    y_col = label_to_metric.get(y_axis_label, f"total goals{suffix}")

    # 3. Anvend dropdown- og numeriske filtre
    if "All" not in sel_leagues and sel_leagues:
        df = df[df["League"].isin(sel_leagues)]
    if sel_positions:
        df = df[df["Pos."].isin(sel_positions)]

    df = df[(df["Age"] >= min_age) & (df["Age"] <= max_age)]
    df = df[(df["total mins played"] >= min_mins) & (df["total mins played"] <= max_mins)]

    if df.empty:
        return "<div style='color:#f59e0b; background:rgba(245,158,11,0.1); padding:20px; border-radius:12px; text-align:center; font-weight:700;'>⚠️ Ingen spillere matcher de valgte filtre. Juster dine indstillinger.</div>"

    # Konverter kolonner til float for at undgå fejl under sortering
    df[x_col] = df[x_col].astype(float).fillna(0.0)
    df[y_col] = df[y_col].astype(float).fillna(0.0)

    # 4. Beregn Highlighting (Top 10, U21, U19 og specifikke valg)
    top_players = []
    if top10_x:
        top_players += df.groupby("Short Name")[x_col].max().nlargest(10).index.tolist()
    if top10_y:
        top_players += df.groupby("Short Name")[y_col].max().nlargest(10).index.tolist()

    age_players = []
    if u21:
        age_players += df[df["Age"] <= 21]["Short Name"].tolist()
    if u19:
        age_players += df[df["Age"] <= 19]["Short Name"].tolist()

    combined_highlight = set(top_players + age_players + highlight_players)

    def is_highlighted(row):
        if row["Short Name"] in combined_highlight:
            return True
        if highlight_teams and row["Team"] in highlight_teams:
            return True
        return False

    df["highlight"] = df.apply(is_highlighted, axis=1)

    # Sorter datasættet, så de vigtige spillere renderes øverst på SVG-kortet
    df = df.sort_values(by="highlight", ascending=True)
def vis_scatter_page(stat_type, x_axis_label, y_axis_label, sel_leagues, sel_positions, min_age, max_age, min_mins, max_mins, top10_x, top10_y, u21, u19, highlight_players, highlight_teams):
    if df_global.empty:
        return "<div style='color:white; padding:20px;'>Ingen data tilgængelig. Kontroller CSV-filerne.</div>"

    # Lav en kopi af det globale datasæt til filtrering
    df = df_global.copy()

    # 1. Definer suffiks baseret på stat_type
    suffix = "_p90" if stat_type == "Per 90" else "_Total"
    stat_label = "p90" if stat_type == "Per 90" else "Total"

    # 2. Beregn kombinerede metrikker og hent ordbog
    df['G/A'] = df[f'total goals{suffix}'] + df[f'total assists{suffix}']
    custom_titles = get_custom_titles(suffix)

    # Find gyldige metrikker baseret på dine krav
    metric_candidates = [f"total goals{suffix}", f"xG{suffix}", f"total ontarget attempt{suffix}", "G/A"]
    metric_candidates = [col for col in metric_candidates if col in df.columns]

    def clean_label(metric):
        return custom_titles.get(metric, metric.replace(suffix, "").capitalize())

    metric_labels_dict = {metric: clean_label(metric) for metric in metric_candidates}
    label_to_metric = {v: k for k, v in metric_labels_dict.items()}

    x_col = label_to_metric.get(x_axis_label, f"xG{suffix}")
    y_col = label_to_metric.get(y_axis_label, f"total goals{suffix}")

    # 3. Anvend dropdown- og numeriske filtre
    if "All" not in sel_leagues and sel_leagues:
        df = df[df["League"].isin(sel_leagues)]
    if sel_positions:
        df = df[df["Pos."].isin(sel_positions)]

    df = df[(df["Age"] >= min_age) & (df["Age"] <= max_age)]
    df = df[(df["total mins played"] >= min_mins) & (df["total mins played"] <= max_mins)]

    if df.empty:
        return "<div style='color:#f59e0b; background:rgba(245,158,11,0.1); padding:20px; border-radius:12px; text-align:center; font-weight:700;'>⚠️ Ingen spillere matcher de valgte filtre. Juster dine indstillinger.</div>"

    # Konverter kolonner til float for at undgå fejl under sortering
    df[x_col] = df[x_col].astype(float).fillna(0.0)
    df[y_col] = df[y_col].astype(float).fillna(0.0)

    # 4. Beregn Highlighting (Top 10, U21, U19 og specifikke valg)
    top_players = []
    if top10_x:
        top_players += df.groupby("Short Name")[x_col].max().nlargest(10).index.tolist()
    if top10_y:
        top_players += df.groupby("Short Name")[y_col].max().nlargest(10).index.tolist()

    age_players = []
    if u21:
        age_players += df[df["Age"] <= 21]["Short Name"].tolist()
    if u19:
        age_players += df[df["Age"] <= 19]["Short Name"].tolist()

    combined_highlight = set(top_players + age_players + highlight_players)

    def is_highlighted(row):
        if row["Short Name"] in combined_highlight:
            return True
        if highlight_teams and row["Team"] in highlight_teams:
            return True
        return False

    df["highlight"] = df.apply(is_highlighted, axis=1)

    # Sorter datasættet, så de vigtige spillere renderes øverst på SVG-kortet
    df = df.sort_values(by="highlight", ascending=True)
    # --- INTELLIGENT AKSE-AFRUNDING LOGIK ---
    def beregn_smukt_interval(max_val):
        if max_val <= 0:
            return 0.25, 1.0
        # Find den bedste trinstørrelse baseret på tallenes størrelse
        if max_val <= 1.2:
            trin = 0.25
        elif max_val <= 2.5:
            trin = 0.50
        elif max_val <= 6.0:
            trin = 1.0
        elif max_val <= 12.0:
            trin = 2.0
        elif max_val <= 25.0:
            trin = 5.0
        else:
            trin = 10.0
        
        # Rund op til det næste hele trin for at sikre en pæn slutværdi
        afrundet_max = math.ceil(max_val / trin) * trin
        return trin, afrundet_max

    # Find de rå maksværdier fra datasættet
    raw_x_max = df[x_col].max()
    raw_y_max = df[y_col].max()

    # Beregn de smukke trin og maksværdier (Vi starter altid fra 0.00)
    x_trin, x_max_smuk = beregn_smukt_interval(raw_x_max)
    y_trin, y_max_smuk = beregn_smukt_interval(raw_y_max)
    x_min_smuk, y_min_smuk = 0.0, 0.0

    # Dimensioner og marginer til SVG-kortet
    padding_l, padding_r, padding_t, padding_b = 75, 45, 75, 65
    svg_w, svg_h = 850, 560
    chart_w = svg_w - padding_l - padding_r
    chart_h = svg_h - padding_t - padding_b

    def get_cx(val):
        return padding_l + ((float(val) - x_min_smuk) / x_max_smuk) * chart_w

    def get_cy(val):
        return padding_t + chart_h - ((float(val) - y_min_smuk) / y_max_smuk) * chart_h

    # Generer grid-linjer og aksetal baseret på de faste, afrundede intervaller
    grid_lines_html = ""
    axis_labels_html = ""

    # X-aksens værdier (Fra 0.00 til max med fast intervaltrin)
    x_vals = np.arange(x_min_smuk, x_max_smuk + (x_trin / 2), x_trin)
    for x_v in x_vals:
        cx = get_cx(x_v)
        if cx <= svg_w - padding_r:
            grid_lines_html += f'<line class="sc-grid" x1="{cx:.1f}" y1="{padding_t}" x2="{cx:.1f}" y2="{padding_t + chart_h}" />'
            axis_labels_html += f'<text class="sc-axis-num" x="{cx:.1f}" y="{padding_t + chart_h + 20}" text-anchor="middle">{x_v:.2f}</text>'

    # Y-aksens værdier (Fra 0.00 til max med fast intervaltrin)
    y_vals = np.arange(y_min_smuk, y_max_smuk + (y_trin / 2), y_trin)
    for y_v in y_vals:
        cy = get_cy(y_v)
        if cy >= padding_t:
            grid_lines_html += f'<line class="sc-grid" x1="{padding_l}" y1="{cy:.1f}" x2="{svg_w - padding_r}" y2="{cy:.1f}" />'
            axis_labels_html += f'<text class="sc-axis-num" x="{padding_l - 12}" y="{cy:.1f}" text-anchor="end" alignment-baseline="middle">{y_v:.2f}</text>'
    # Generer spiller-punkter og navne-labels på SVG'en
    scatter_dots_html = ""
    for _, row in df.iterrows():
        cx = get_cx(row[x_col])
        cy = get_cy(row[y_col])
        
        # Bestem visuel styling baseret på om spilleren er fremhævet
        if row["highlight"]:
            dot_color = "#00FFD5"
            dot_radius = "7"
            dot_stroke = "rgba(0, 255, 213, 0.4)"
            stroke_w = "5"
            # Vis altid navnetekst på kortet for fremhævede spillere
            label_text = f'<text class="sc-dot-lbl" x="{cx:.1f}" y="{cy - 12:.1f}" text-anchor="middle">{row["Short Name"]}</text>'
        else:
            dot_color = "rgba(148, 163, 184, 0.3)"
            dot_radius = "5.5"
            dot_stroke = "rgba(255, 255, 255, 0.05)"
            stroke_w = "1"
            label_text = ""

        # Opbyg en detaljeret, skjult CSS-infoboks til hover-effekt
        tooltip_content = f"""
            <strong>{row['Player Name']}</strong><br>
            Hold: {row['Team']}<br>
            Alder: {int(row['Age'])} år<br>
            Minutter: {int(row['total mins played'])}<br>
            {x_axis_label}: {row[x_col]:.2f}<br>
            {y_axis_label}: {row[y_col]:.2f}
        """

        scatter_dots_html += f"""
        <g class="sc-dot-group">
            <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{dot_radius}" fill="{dot_color}" stroke="{dot_stroke}" stroke-width="{stroke_w}" />
            {label_text}
            <foreignObject x="{cx + 10:.1f}" y="{cy - 40:.1f}" width="180" height="110" class="sc-tip">
                <div class="sc-tip-box">{tooltip_content}</div>
            </foreignObject>
        </g>
        """

    # --- NY FLOT IMPLEMENTERING AF AKTIVE FILTRE UNDER PLOTTET ---
    # Behandl tekstlister til visning som brikker (tags)
    disp_leagues = sorted(df_global["League"].dropna().unique().tolist()) if ("All" in sel_leagues or not sel_leagues) else sel_leagues
    disp_positions = sorted(df_global["Pos."].dropna().unique().tolist()) if not sel_positions else sel_positions

    # Generer små brikker (tags) i HTML til det mørke infopanel
    league_tags = "".join(f'<span class="filter-tag tag-lg">{l}</span>' for l in disp_leagues)
    pos_tags = "".join(f'<span class="filter-tag tag-pos">{p}</span>' for p in disp_positions)

    active_filters_html = f"""
    <div class="active-filters-container">
        <div class="filter-info-section">
            <div class="info-section-title">Aktiv Spilleranalyse-Konfiguration</div>
            <div class="info-grid-row">
                <div class="info-cell">
                    <span class="info-cell-label">Målestok (Stat Type):</span>
                    <span class="info-cell-val font-highlight">{stat_type}</span>
                </div>
                <div class="info-cell">
                    <span class="info-cell-label">Aldersinterval:</span>
                    <span class="info-cell-val">{min_age} - {max_age} år</span>
                </div>
                <div class="info-cell">
                    <span class="info-cell-label">Spillede minutter:</span>
                    <span class="info-cell-val">{min_mins} - {max_mins} min.</span>
                </div>
            </div>
        </div>
        
        <div class="filter-tags-section">
            <div class="tags-group">
                <div class="tags-group-label">Valgte Ligaer ({len(disp_leagues)}):</div>
                <div class="tags-wrapper">{league_tags}</div>
            </div>
            <div class="tags-group">
                <div class="tags-group-label">Aktive Positioner ({len(disp_positions)}):</div>
                <div class="tags-wrapper">{pos_tags}</div>
            </div>
        </div>
    </div>
    """
    # Hent unikke lister til filtervalg (kun baseret på den1 og eng1)
    all_leagues = ["All"] + sorted(df_global["League"].dropna().unique().tolist())
    all_positions = sorted(df_global["Pos."].dropna().unique().tolist())
    all_teams = sorted(df_global["Team"].dropna().unique().tolist())
    all_short_names = sorted(df_global["Short Name"].unique().tolist())

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PER 90 - HTML Scatter Plot</title>
        <link href="https://googleapis.com" rel="stylesheet">
        <style>
            body {{ margin: 0; font-family: 'Gabarito', sans-serif; background-color: #070B13; color: #e5e7eb; display: flex; min-height: 100vh; max-width: 100vw; overflow-x: hidden; }}
            aside {{ width: 260px; min-width: 260px; background: #0B1220; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 30px 20px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0; }}
            .sidebar-logo {{ font-size: 22px; font-weight: 900; color: #00FFD5; margin-bottom: 40px; text-decoration: none; }}
            nav {{ display: flex; flex-direction: column; gap: 10px; }}
            nav a {{ color: #94a3b8; text-decoration: none; padding: 12px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
            nav a:hover, nav a.active {{ background: rgba(0, 255, 213, 0.1); color: #00FFD5; }}
            
            main {{ flex-grow: 1; padding: 40px; display: flex; flex-direction: column; gap: 30px; align-items: stretch; width: calc(100% - 260px); max-width: 100%; box-sizing: border-box; }}
            
            /* FILTER PANEL DESIGN */
            .control-panel {{ width: 100%; max-width: 100%; background: #0B1220; border: 1px solid rgba(255, 255, 255, 0.04); padding: 24px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); box-sizing: border-box; display: flex; flex-direction: column; gap: 20px; }}
            .filter-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; width: 100%; }}
            
            .form-group {{ position: relative; width: 100%; box-sizing: border-box; }}
            label.form-title {{ display: block; font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }}
            
            select, input[type="number"] {{ 
                width: 100%; background: #070B13; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px 16px; color: #fff; font-size: 14px; font-family: inherit; font-weight: 600; box-sizing: border-box; outline: none; transition: all 0.2s ease;
            }}
            select {{ appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://w3.org' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>"); background-repeat: no-repeat; background-position: right 12px center; background-size: 16px; padding-right: 40px; cursor: pointer; }}
            select:hover, input:hover {{ border-color: rgba(0, 255, 213, 0.4); }}
            select:focus, input:focus {{ border-color: #00FFD5; box-shadow: 0 0 0 2px rgba(0, 255, 213, 0.15); }}
            
            /* COMPACT DROPDOWNS */
            .custom-multiselect {{ position: relative; width: 100%; }}
            .select-box {{ display: flex; justify-content: space-between; align-items: center; background: #070B13; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px 16px; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; user-select: none; box-sizing: border-box; }}
            .select-box:hover {{ border-color: rgba(0, 255, 213, 0.5); }}
            .select-box .arrow {{ font-size: 9px; color: #64748b; transition: transform 0.2s; }}
            
            .checkboxes {{ display: none; position: absolute; top: 100%; left: 0; right: 0; background: #070B13; border: 1px solid #00FFD5; border-top: none; border-radius: 0 0 10px 10px; max-height: 220px; overflow-y: auto; z-index: 100; padding: 6px; box-shadow: 0 10px 25px rgba(0,0,0,0.6); }}
            .custom-multiselect.open .checkboxes {{ display: block; }}
            .custom-multiselect.open .select-box {{ border-radius: 10px 10px 0 0; border-color: #00FFD5; }}
            .custom-multiselect.open .arrow {{ transform: rotate(180deg); color: #00FFD5; }}
            
            .check-item {{ display: flex; align-items: center; padding: 8px 10px; color: #cbd5e1; font-size: 13px; font-weight: 600; cursor: pointer; border-radius: 5px; margin-bottom: 2px; transition: background 0.15s, color 0.15s; user-select: none; }}
            .check-item:hover {{ background: rgba(255, 255, 255, 0.04); color: #fff; }}
            .check-item input {{ display: none; }}
            .custom-box {{ width: 15px; height: 15px; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; margin-right: 10px; display: inline-block; position: relative; background: #0B1220; flex-shrink: 0; }}
            .check-item input:checked + .custom-box {{ background: #00FFD5; border-color: #00FFD5; }}
            .check-item input:checked + .custom-box::after {{ content: '✓'; position: absolute; color: #070B13; font-size: 11px; font-weight: 900; top: 50%; left: 50%; transform: translate(-50%, -50%); }}
            
            .highlight-checks {{ display: flex; flex-wrap: wrap; gap: 24px; padding: 5px 0; }}
            
            /* SVG PLOT STYLING */
            .chart-display-wrapper {{ background: #0B1220; border: 1px solid rgba(255,255,255,0.05); padding: 30px; border-radius: 24px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); display: flex; flex-direction: column; align-items: center; width: 100%; box-sizing: border-box; }}
            .sc-main-svg {{ background-color: #0f172a; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: inset 0 4px 20px rgba(0,0,0,0.4); }}
            .sc-grid {{ stroke: rgba(255, 255, 255, 0.04); stroke-width: 1; stroke-dasharray: 4,4; }}
            .sc-axis {{ stroke: rgba(255, 255, 255, 0.15); stroke-width: 1.5; }}
            .sc-axis-title {{ fill: #94a3b8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }}
            .sc-axis-num {{ fill: #64748b; font-size: 11px; font-weight: 700; }}
            .sc-main-title {{ fill: #ffffff; font-size: 26px; font-weight: 900; letter-spacing: -0.5px; }}
            
            .sc-dot-group {{ cursor: pointer; }}
            .sc-dot-group:hover circle {{ fill: #00FFD5 !important; stroke: #00FFD5; stroke-width: 4; }}
            .sc-dot-lbl {{ fill: #fff; font-size: 11px; font-weight: 700; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.9)); pointer-events: none; }}
            
            /* CSS HOVER TOOLTIPS */
            .sc-tip {{ display: none; pointer-events: none; z-index: 200; }}
            .sc-dot-group:hover .sc-tip {{ display: block; }}
            .sc-tip-box {{ background: #070B13; border: 1px solid #00FFD5; border-radius: 8px; padding: 10px 12px; color: #e5e7eb; font-size: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.7); line-height: 1.5; }}
            
            /* SKELETON TIL AKTIVE FILTRE UNDER PLOTTET */
            .active-filters-container {{ width: 100%; max-width: 850px; background: #0b1220; border: 1px solid rgba(255,255,255,0.04); border-radius: 16px; padding: 20px; margin-top: 25px; box-sizing: border-box; display: flex; flex-direction: column; gap: 16px; }}
            .filter-info-section {{ border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 14px; }}
            .info-section-title {{ font-size: 12px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
            .info-grid-row {{ display: flex; flex-wrap: wrap; gap: 40px; }}
            .info-cell {{ display: flex; flex-direction: column; gap: 4px; }}
            .info-cell-label {{ font-size: 11px; color: #475569; font-weight: 700; }}
            .info-cell-val {{ font-size: 14px; color: #cbd5e1; font-weight: 700; }}
            .font-highlight {{ color: #00FFD5; }}
            
            .filter-tags-section {{ display: flex; flex-direction: column; gap: 14px; }}
            .tags-group {{ display: flex; flex-direction: column; gap: 6px; }}
            .tags-group-label {{ font-size: 11px; color: #475569; font-weight: 700; }}
            .tags-wrapper {{ display: flex; flex-wrap: wrap; gap: 6px; }}
            .filter-tag {{ font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.3px; }}
            .tag-lg {{ background: rgba(0, 255, 213, 0.08); color: #00FFD5; border: 1px solid rgba(0, 255, 213, 0.15); }}
            .tag-pos {{ background: rgba(96, 165, 250, 0.08); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.15); }}
        </style>
    </head>

    <body>
        <!-- SIDEBAR -->
        <aside>
            <div class="sidebar-logo">⚽ PER 90</div>
            <nav>
                <a href="/">🏠 Startside</a>
                <a href="/pizza">📊 Pizza Diagram</a>
                <a href="/stats">🏃 Spilleranalyse</a>
                <a href="/radar">🕸️ Radarsammenligning</a>
                <a href="/scatter" class="active">📈 Scatter Plot</a>
                <a href="#">🏆 Leaderboard</a>
            </nav>
        </aside>
        
        <main>
            <!-- FILTER PANEL -->
            <div class="control-panel">
                <form id="scatterForm" action="/scatter" method="get">
                    
                    <!-- RÆKKE 1: STAT TYPE OG METRICS -->
                    <div class="filter-row">
                        <div class="form-group">
                            <label class="form-title">Choose Stat Type</label>
                            <select name="stat_type" class="live-input">
                                <option value="Per 90" {"selected" if stat_type == "Per 90" else ""}>Per 90</option>
                                <option value="Total" {"selected" if stat_type == "Total" else ""}>Total</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-title">X Axis Metric</label>
                            <select name="x_axis_label" class="live-input">
                                {"".join(f'<option value="{lbl}" {"selected" if lbl == x_axis_label else ""}>{lbl}</option>' for lbl in sorted(metric_labels_dict.values()))}
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-title">Y Axis Metric</label>
                            <select name="y_axis_label" class="live-input">
                                {"".join(f'<option value="{lbl}" {"selected" if lbl == y_axis_label else ""}>{lbl}</option>' for lbl in sorted(metric_labels_dict.values()))}
                            </select>
                        </div>
                    </div>
                    
                    <!-- RÆKKE 2: LIGA OG POSITION DROPDOWNS -->
                    <div class="filter-row">
                        <div class="form-group">
                            <label class="form-title">Leagues</label>
                            <div class="custom-multiselect">
                                <div class="select-box" onclick="toggleDropdown('leagues')">
                                    <span>{"All" if "All" in sel_leagues or not sel_leagues else f"({len(sel_leagues)} valgt)"}</span>
                                    <span class="arrow">▼</span>
                                </div>
                                <div class="checkboxes" id="opts-leagues">
                                    {"".join(f'<label class="check-item"><input type="checkbox" name="sel_leagues" value="{lg}" class="live-input" {"checked" if lg in sel_leagues else "" if sel_leagues or lg != "All" else "checked"}><span class="custom-box"></span>{lg}</label>' for lg in all_leagues)}
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-title">Positions</label>
                            <div class="custom-multiselect">
                                <div class="select-box" onclick="toggleDropdown('positions')">
                                    <span>{f"({len(sel_positions)} valgt)" if sel_positions else "Vælg..."}</span>
                                    <span class="arrow">▼</span>
                                </div>
                                <div class="checkboxes" id="opts-positions">
                                    {"".join(f'<label class="check-item"><input type="checkbox" name="sel_positions" value="{pos}" class="live-input" {"checked" if pos in sel_positions else ""}><span class="custom-box"></span>{pos}</label>' for pos in all_positions)}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- RÆKKE 3: ALDER OG MINUTTER -->
                    <div class="filter-row">
                        <div class="form-group" style="display: flex; gap: 10px;">
                            <div style="flex: 1;">
                                <label class="form-title">Min. age</label>
                                <input type="number" name="min_age" value="{min_age}" class="live-input">
                            </div>
                            <div style="flex: 1;">
                                <label class="form-title">Max. age</label>
                                <input type="number" name="max_age" value="{max_age}" class="live-input">
                            </div>
                        </div>
                        
                        <div class="form-group" style="display: flex; gap: 10px;">
                            <div style="flex: 1;">
                                <label class="form-title">Min. minutes</label>
                                <input type="number" name="min_mins" value="{min_mins}" class="live-input">
                            </div>
                            <div style="flex: 1;">
                                <label class="form-title">Max. minutes</label>
                                <input type="number" name="max_mins" value="{max_mins}" class="live-input">
                            </div>
                        </div>
                    </div>
                    
                    <!-- RÆKKE 4: HIGHLIGHTING FILTRE (START) -->
                    <div style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px;">
                        <label class="form-title" style="margin-bottom: 12px;">Highlighting Options</label>
                        
                        <div class="highlight-checks">
                            <label class="check-item"><input type="checkbox" name="top10_x" value="true" class="live-input" {"checked" if top10_x else ""}><span class="custom-box"></span>Top 10, X Axis</label>
                            <label class="check-item"><input type="checkbox" name="top10_y" value="true" class="live-input" {"checked" if top10_y else ""}><span class="custom-box"></span>Top 10, Y Axis</label>
                            <label class="check-item"><input type="checkbox" name="u21" value="true" class="live-input" {"checked" if u21 else ""}><span class="custom-box"></span>U21 Players</label>
                            <label class="check-item"><input type="checkbox" name="u19" value="true" class="live-input" {"checked" if u19 else ""}><span class="custom-box"></span>U19 Players</label>
                        </div>
                        
                        <div class="filter-row" style="margin-top: 15px;">
                            <div class="form-group">
                                <label class="form-title">Highlight Player(s)</label>
                                <div class="custom-multiselect">
                                    <div class="select-box" onclick="toggleDropdown('high_players')">
                                        <span>{f"({len(highlight_players)} valgt)" if highlight_players else "Søg / vælg..."}</span>
                                        <span class="arrow">▼</span>
                                    </div>
                                    <div class="checkboxes" id="opts-high_players">
                                        {"".join(f'<label class="check-item"><input type="checkbox" name="highlight_players" value="{name}" class="live-input" {"checked" if name in highlight_players else ""}><span class="custom-box"></span>{name}</label>' for name in all_short_names)}
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-title">Highlight Team(s)</label>
                                <div class="custom-multiselect">
                                    <div class="select-box" onclick="toggleDropdown('high_teams')">
                                        <span>{f"({len(highlight_teams)} valgt)" if highlight_teams else "Vælg..."}</span>
                                        <span class="arrow">▼</span>
                                    </div>
                                    <div class="checkboxes" id="opts-high_teams">
                                        {"".join(f'<label class="check-item"><input type="checkbox" name="highlight_teams" value="{tm}" class="live-input" {"checked" if tm in highlight_teams else ""}><span class="custom-box"></span>{tm}</label>' for tm in all_teams)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
            </div>

            <!-- CHART VISUALISERING MED SKRÆDDERSYET RESPONSIV SVG -->
            <div class="chart-display-wrapper">
                <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" class="sc-main-svg">
                    <!-- Baggrunds-grid og akser -->
                    {grid_lines_html}
                    <line class="sc-axis" x1="{padding_l}" y1="{padding_t}" x2="{padding_l}" y2="{padding_t + chart_h}" />
                    <line class="sc-axis" x1="{padding_l}" y1="{padding_t + chart_h}" x2="{svg_w - padding_r}" y2="{padding_t + chart_h}" />
                    
                    <!-- TITEL OG AKSETEKSTER -->
                    <text class="sc-main-title" x="{padding_l}" y="{padding_t - 24}">Scatter plot</text>
                    <text class="sc-axis-title" x="{padding_l + chart_w / 2}" y="{svg_h - 15}" text-anchor="middle">{x_axis_label}</text>
                    <text class="sc-axis-title" x="22" y="{padding_t + chart_h / 2}" text-anchor="middle" transform="rotate(-90, 22, {padding_t + chart_h / 2})">{y_axis_label}</text>
                    
                    <!-- Aksernes tal-labels og alle spiller-punkterne -->
                    {axis_labels_html}
                    {scatter_dots_html}
                </svg>
                
                <!-- NY FLOT FILTRERINGSHALVDEL IMPLEMENTERET DIREKTE UNDER PLOTTET -->
                {active_filters_html}
            </div>
        </main>

        <script>
            // Åben og luk dropdown-menuerne korrekt ved klik
            function toggleDropdown(feltNavn) {{
                const el = document.getElementById('opts-' + feltNavn).closest('.custom-multiselect');
                const isOpen = el.classList.contains('open');
                
                document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                    dropdown.classList.remove('open');
                }});
                
                if (!isOpen) {{
                    el.classList.add('open');
                }}
            }}

            // Luk menuer hvis brugeren klikker uden for
            document.addEventListener('click', function(e) {{
                if (!e.target.closest('.custom-multiselect')) {{
                    document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                        dropdown.classList.remove('open');
                    }});
                }}
            }});

            // Auto-update: Indsend formularen når et input ændres eller flueben sættes
            document.querySelectorAll('.live-input').forEach(input => {{
                input.addEventListener('change', () => {{
                    document.getElementById('scatterForm').submit();
                }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@router.get("/scatter", response_class=HTMLResponse)
def get_scatter_page(
    stat_type: str = Query("Per 90"),
    x_axis_label: str = Query("Goals"),
    y_axis_label: str = Query("Assists"),
    sel_leagues: list[str] = Query([]),
    sel_positions: list[str] = Query([]),
    min_age: int = Query(16),
    max_age: int = Query(45),
    min_mins: int = Query(0),
    max_mins: int = Query(5000),
    top10_x: bool = Query(False),
    top10_y: bool = Query(False),
    u21: bool = Query(False),
    u19: bool = Query(False),
    highlight_players: list[str] = Query([]),
    highlight_teams: list[str] = Query([])
):
    if not sel_positions and not df_global.empty:
        sel_positions = sorted(df_global["Pos."].dropna().unique().tolist())
        
    return vis_scatter_page(stat_type, x_axis_label, y_axis_label, sel_leagues, sel_positions, min_age, max_age, min_mins, max_mins, top10_x, top10_y, u21, u19, highlight_players, highlight_teams)
