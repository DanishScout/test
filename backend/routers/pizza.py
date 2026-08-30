import os
import math
import base64
import requests
import pandas as pd
from io import BytesIO

# 📁 Indlæs data globalt ved app-opstart. 
# Den søger efter filerne i rodmappen eller backend-mappen afhængigt af hvor uvicorn startes.
try:
    sti_aut = "aut1.csv" if os.path.exists("aut1.csv") else "backend/aut1.csv"
    sti_tur = "tur1.csv" if os.path.exists("tur1.csv") else "backend/tur1.csv"
    
    df1 = pd.read_csv(sti_aut)
    df2 = pd.read_csv(sti_tur)
    DATA = pd.concat([df1, df2], ignore_index=True)
except Exception:
    DATA = pd.DataFrame()

# Mappings til pæne visuelle navne med linjeskift i SVG-diagrammet
METRICS_LABELS = {
    "total goals_p90": "Goals", 
    "xG_p90": "npxG",
    "total assists_p90": "Assists", 
    "xA_p90": "xA",
    "total won contest_p90": "Successful\nDribbles", 
    "total contest_p90": "Dribble\nAttempts",
    "tackle_success_pct_p90": "Tackles\nWon %", 
    "aerial_success_pct_p90": "Aerials\nWon %"
}

def get_slice_path(cx, cy, r, start_angle, end_angle):
    """Beregner den præcise SVG-sti (path) til en enkelt lagkageskive."""
    start_rad = math.radians(start_angle - 90)
    end_rad = math.radians(end_angle - 90)
    x1 = cx + r * math.cos(start_rad)
    y1 = cy + r * math.sin(start_rad)
    x2 = cx + r * math.cos(end_rad)
    y2 = cy + r * math.sin(end_rad)
    return f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 0 1 {x2} {y2} Z"
def vis_pizza_diagram(player: str, pos: str, shoot: list[str], p_ass: list[str], poss: list[str], defend: list[str], color: str = "#00FFD5"):
    if DATA.empty:
        return {"html": "<p style='color:#ef4444;text-align:center;'>Fejl: Kunne ikke indlæse datafiler (aut1.csv / tur1.csv).</p>", "player_slug": "error"}
        
    # Saml alle valgte metrikker fra query-arrays
    sel_keys = []
    if shoot: sel_keys.extend(shoot)
    if p_ass: sel_keys.extend(p_ass)
    if poss: sel_keys.extend(poss)
    if defend: sel_keys.extend(defend)
    
    if len(sel_keys) < 3:
        return {"html": "<p style='color:#f59e0b;text-align:center;padding:20px;'>Vælg mindst 3 metrikker i alt for at generere pizzadiagrammet.</p>", "player_slug": "unknown"}
        
    # Find spilleren i datagrundlaget
    if player not in DATA['Player Name'].values:
        return {"html": f"<p style='color:#ef4444;text-align:center;padding:20px;'>Spilleren '{player}' blev ikke fundet i systemet.</p>", "player_slug": "not_found"}
        
    pos_column = 'Pos.' if 'Pos.' in DATA.columns else ('Position' if 'Position' in DATA.columns else DATA.columns)
    player_row = DATA[DATA['Player Name'] == player].iloc[0]
    player_league = player_row.get('League', 'N/A')
    
    # Hvis en specifik sammenligningsposition ikke er valgt, bruges spillerens egen
    selected_pos = pos if pos else player_row[pos_column]
    
    # Filtrer sammenligningsgruppen ud fra Liga og Position
    comp_df = DATA[(DATA['League'] == player_league) & (DATA[pos_column] == selected_pos)].copy()
    
    # Sikr at spilleren selv er med i referencegruppen til percentil-beregningen
    if player not in comp_df['Player Name'].values:
        comp_df = pd.concat([comp_df, DATA[DATA['Player Name'] == player]], ignore_index=True)
        
    # Beregn percentil-rangering live for de valgte metrikker
    p_values = {}
    for k in sel_keys:
        if k in comp_df.columns:
            comp_df[f'{k}_pct'] = comp_df[k].rank(pct=True, method='max') * 100.0
            p_values[k] = float(comp_df[comp_df['Player Name'] == player][f'{k}_pct'].iloc[0])
        else:
            p_values[k] = 0.0

    # Hent Opta holdslogo live i Base64 via team_id / contestantId
    team_id = player_row.get('contestantId', '')
    logo_base64 = "data:image/svg+xml;utf8,<svg xmlns='http://w3.org' viewBox='0 0 24 24' fill='%2300FFD5'><circle cx='12' cy='12' r='10'/></svg>"
    if team_id:
        try:
            url = f'https://opta.net{team_id}'
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                logo_base64 = f"data:image/png;base64,{base64.b64encode(BytesIO(res.content).getvalue()).decode()}"
        except Exception:
            pass

    CX, CY, MAX_R = 355, 310, 200
    N = len(sel_keys)
    slice_width = 360.0 / N
    p1_display = player if len(player) <= 35 else player[:32] + "..."
    
    pizza_slices, grid_lines, labels = "", "", ""
    
    for i, k in enumerate(sel_keys):
        start_ang = i * slice_width
        end_ang = start_ang + slice_width
        mid_ang = start_ang + (slice_width / 2.0)
        
        # Hent percentil og find radius
        pct_val = max(0.0, min(p_values.get(k, 0.0), 100.0))
        slice_r = (pct_val / 100.0) * MAX_R
        
        # Generer lagkageskive
        if slice_r > 0:
            pizza_slices += f'<path d="{get_slice_path(CX, CY, slice_r, start_ang, end_ang)}" class="slice-b" />\n'
            
        # Generer adskillelseslinje
        rad_line = math.radians(start_ang - 90)
        lx = CX + MAX_R * math.cos(rad_line)
        ly = CY + MAX_R * math.sin(rad_line)
        grid_lines += f'<line class="grid-line" x1="{CX}" y1="{CY}" x2="{lx:.1f}" y2="{ly:.1f}" />\n'
        
        # Beregn placering til ydre tekst-labels
        rad_mid = math.radians(mid_ang - 90)
        tx = CX + (MAX_R + 42) * math.cos(rad_mid)
        ty = CY + (MAX_R + 42) * math.sin(rad_mid)
        
        # Split metriknavnet op ved linjeskift for pæn formatering i SVG
        metric_display = METRICS_LABELS.get(k, k)
        metric_lines = metric_display.split('\n')
        tspan_html = "".join([f'<tspan x="0" dy="{ "0" if idx == 0 else "1.2em" }">{line}</tspan>' for idx, line in enumerate(metric_lines)])
        
        label_text = f'<text class="ax-lbl" text-anchor="middle">{tspan_html}</text>'
        badge_y = 22 if len(metric_lines) > 1 else 10
        val_badge = f'<g transform="translate(-14, {badge_y})"><rect class="bg-b" width="28" height="16" rx="4"/><text class="tx-b" x="14" y="12" text-anchor="middle">{int(pct_val)}</text></g>'
        
        labels += f'<g transform="translate({tx:.1f}, {ty:.1f})">{label_text}{val_badge}</g>\n'

    mins_played = int(player_row.get('total mins played', 0)) if pd.notna(player_row.get('total mins played')) else 0

    # Præcis integration af din styling, HTML-struktur og kilde-footer
    html_output = f"""
    <div class="chart-container" id="chart-only">
        <style>
            @import url('https://googleapis.com');
            .chart-container {{ 
                position: relative; 
                padding: 15px 15px 35px; 
                border-radius: 24px; 
                width: 100%; 
                max-width: 710px; 
                border: 1px solid rgba(0,240,255,.08); 
                box-shadow: 0 30px 60px -15px #000, inset 0 1px 0 rgba(255,255,255,.05); 
                box-sizing: border-box; 
                opacity: .85; 
                overflow: hidden;
                background: #0B1220;
                display: flex;
                flex-direction: column;
                align-items: center;
                font-family: 'Gabarito', sans-serif;
                color: #e5e7eb;
            }}
            .chart-container::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(#0f172a, #020617); z-index: 0; border-radius: 24px; }}
            .header-card {{ position: relative; z-index: 2; width: 100%; max-width: 575px; margin: 15px auto 25px; padding: 20px 25px; background: transparent; border: 1px solid rgba(0, 240, 255, 0.08); border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); box-sizing: border-box; }}
            .h-cnt {{ display: flex; gap: 20px; width: 100%; box-sizing: border-box; }}
            .p-meta-right {{ display: flex; flex-direction: column; flex-grow: 1; }}
            .p-nm {{ font-size: 27px; font-weight: 900; margin: 0 0 10px; text-transform: uppercase; letter-spacing: -.5px; color: #fff; -webkit-text-fill-color: #fff; }}
            .tactic-line {{ width: 100%; height: 2px; margin-bottom: 12px; }}
            .p-sub-bar {{ display: flex; align-items: center; gap: 14px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; flex-wrap: wrap; }}
            .meta-item {{ display: flex; align-items: center; gap: 6px; color: #fff; }}
            .meta-item svg {{ opacity: .6; fill: none; stroke: {color}; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; width: 15px; height: 15px; }}
            .logo-shape {{ display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: rgba(0,240,255,0.1); border: 1px solid {color}; border-radius: 50%; padding: 2px; box-sizing: border-box; box-shadow: 0 0 6px rgba(0, 240, 255, 0.2); }}
            .club-crest-small {{ width: 100%; height: 100%; object-fit: contain; }}
            .data-val {{ color: #94a3b8; font-weight: 600; }}
            .pipe-divider {{ color: rgba(0,240,255,.2); font-size: 14px; }}
            svg {{ display: block; margin: auto; overflow: visible; max-width: 100%; height: auto; position: relative; z-index: 1; }}
            .grid-circle {{ fill: none; stroke: rgba(255,255,255,.08); }}
            .grid-line {{ stroke: rgba(255,255,255,.06); }}
            .ax-lbl {{ font-size: 12px; fill: #94a3b8; font-weight: 700; letter-spacing: .5px; }}
            .slice-b {{ fill: {color}1a; stroke: {color}; stroke-width: 1.75; stroke-linejoin: round; filter: drop-shadow(0 0 6px {color}26); }}
            .bg-b {{ fill: #0f172a; stroke: {color}cc; }}
            .tx-b {{ fill: {color}; font-size: 12px; font-weight: 700; }}
            .chart-footer, .chart-footer-source {{ text-align: center; width: 100%; font-size: 11px; font-weight: 300; color: #e5e7eb; letter-spacing: .4px; padding: 0 40px; box-sizing: border-box; position: relative; z-index: 2; }}
            .chart-footer {{ margin-top: 1px; opacity: 0.75; }}
            .chart-footer-source {{ margin-top: 6px; opacity: 0.5; }}
        </style>
        
        <div class="header-card">
            <div class="h-cnt">
                <div class="p-meta-right">
                    <h2 class="p-nm">{p1_display}</h2>
                    <svg class="tactic-line" viewBox="0 0 100 2" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="{color}" stop-opacity="0.6" />
                                <stop offset="70%" stop-color="{color}" stop-opacity="0.3" />
                                <stop offset="100%" stop-color="{color}" stop-opacity="0" />
                            </linearGradient>
                        </defs>
                        <rect width="100" height="2" fill="url(#lineGrad)" />
                    </svg>
                    <div class="p-sub-bar">
                        <div class="meta-item"><div class="logo-shape"><img class="club-crest-small" src="{logo_base64}" /></div><span class="data-val">{player_league}</span></div>
                        <span class="pipe-divider">|</span>
                        <div class="meta-item"><svg viewBox="0 0 24 24"><path d="M20.38 3.46L16 2a4 4 0 0 0-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l1.08 5.4A2 2 0 0 0 5.3 12.5H7v7a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-7h1.7a2 2 0 0 0 1.94-1.41l1.08-5.4a2 2 0 0 0-1.34-2.23z"/></svg><span class="data-val">{selected_pos}</span></div>
                        <span class="pipe-divider">|</span>
                        <div class="meta-item"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg><span class="data-val">{mins_played} MIN.</span></div>
                    </div>
                </div>
            </div>
        </div>
        <svg width="710" height="620" viewBox="0 0 710 620">
            <circle cx="{CX}" cy="{CY}" r="50" class="grid-circle" />
            <circle cx="{CX}" cy="{CY}" r="100" class="grid-circle" />
            <circle cx="{CX}" cy="{CY}" r="150" class="grid-circle" />
            <circle cx="{CX}" cy="{CY}" r="{MAX_R}" class="grid-circle" style="stroke: rgba(255, 255, 255, .08);" />
            {pizza_slices} {grid_lines} {labels}
        </svg>
        <div class="chart-footer">{player}'s percentile rank vs. {player_league} {selected_pos}s</div>
        <div class="chart-footer-source">Generated via per-90.streamlit.app</div>
    </div>
    """
    return {"html": html_output, "player_slug": player.lower().replace(" ", "_")}

def hent_filtre():
    """Henter alle unikke spillere og positioner til frontend-menuerne."""
    if DATA.empty: 
        return {"players": [], "positions": []}
    pos_col = 'Pos.' if 'Pos.' in DATA.columns else ('Position' if 'Position' in DATA.columns else DATA.columns)
    return {
        "players": sorted(DATA['Player Name'].dropna().unique().tolist()), 
        "positions": sorted(DATA[pos_col].dropna().unique().tolist())
    }
