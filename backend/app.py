import os
import math
import base64
from io import BytesIO
import requests
import pandas as pd
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Find de præcise stier til dine CSV-datafiler i backend-mappen
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV1_PATH = os.path.join(BASE_DIR, 'den1.csv')
CSV2_PATH = os.path.join(BASE_DIR, 'den2.csv')
FRONTEND_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend', 'index.html'))

# Definition af dine metrics fra pizza.py
AVAILABLE_METRICS = {
    "Shooting": {
        "total goals_p90": "Goals",
        "xG_p90": "npxG",
        "total ontarget attempt_p90": "Shots\nOn Target",
    },
    "Passing": {
        "total assists_p90": "Assists",
        "xA_p90": "xA",
        "total att assist_p90": "Key Passes",
        "xT_pass_p90": "xT via\nLive Passes",
        "progressive_passes_p90": "Progressive\nPasses",   
    },
    "Possession": {
        "total won contest_p90": "Successful\nDribbles",
        "total contest_p90": "Dribble\nAttempts",
        "dribble_success_pct_p90": "Dribble\nSuccess %",
    },
    "Defending": {
        "tackle_success_pct_p90": "Tackles\nWon %",
        "aerial_success_pct_p90": "Aerials\nWon %",
    },
}

# Fladgør strukturen til opslag af tekst-labels
METRICS_MAPPING = {k: v for cat in AVAILABLE_METRICS.values() for k, v in cat.items()}

def load_data():
    """Indlæser og kombinerer dine specifikke liga-filer direkte"""
    df1 = pd.read_csv(CSV1_PATH)
    df2 = pd.read_csv(CSV2_PATH)
    return pd.concat([df1, df2], ignore_index=True)

# Datamodel til validering af POST-requests (Pizza setup)
class PizzaRequest(BaseModel):
    player: str
    position: str
    metrics: List[str]
    color: str = '#00FFD5'
@app.get("/", response_class=HTMLResponse)
def get_index():
    """Serverer din index.html fil direkte fra frontend-mappen"""
    if not os.path.exists(FRONTEND_PATH):
        raise HTTPException(status_code=404, detail="index.html blev ikke fundet i frontend mappen")
    with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/initial-data")
def get_initial_data():
    """Henter listen over unikke spillere og positioner til menuerne"""
    try:
        data = load_data()
        players = sorted(data['Player Name'].dropna().unique())
        pos_column = 'Pos.' if 'Pos.' in data.columns else ('Position' if 'Position' in data.columns else data.columns)
        positions = sorted(data[pos_column].dropna().unique())
        return {"players": players, "positions": positions, "metrics": AVAILABLE_METRICS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-pizza")
def generate_pizza(req_data: PizzaRequest):
    """Modtager parametre og genererer dit præcise HTML/SVG-diagram"""
    try:
        p1 = req_data.player
        selected_pos = req_data.position
        sel_keys = req_data.metrics
        selected_color = req_data.color

        if len(sel_keys) < 3:
            return {"html": "<p style='color:#e5e7eb; text-align:center;'>Vælg mindst 3 metrics for at generere diagrammet.</p>"}

        data = load_data()
        pos_column = 'Pos.' if 'Pos.' in data.columns else ('Position' if 'Position' in data.columns else data.columns)
        
        player_row = data[data['Player Name'] == p1].iloc[0]
        player_league = player_row['League']
        
        # Filtrer sammenligningsgruppen: samme liga OG samme valgte position
        filter_mask = (data['League'] == player_league) & (data[pos_column] == selected_pos)
        comparison_df = data[filter_mask].copy()
        
        if p1 not in comparison_df['Player Name'].values:
            comparison_df = pd.concat([comparison_df, data[data['Player Name'] == p1]], ignore_index=True)
        
        # Beregn percentil-ranks (0-100) dynamisk inden for gruppen
        for k in sel_keys:
            comparison_df[f'{k}_percentile'] = comparison_df[k].rank(pct=True, method='max') * 100.0

        r1 = comparison_df[comparison_df['Player Name'] == p1].iloc[0]
        # Hent klublogo via Opta API
        team_id = r1['contestantId']
        logo_base64 = ""
        try:
            url = f'https://opta.net{team_id}'
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                team_logo = Image.open(BytesIO(response.content))
                buffered = BytesIO()
                team_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_base64 = f"data:image/png;base64,{img_str}"
        except Exception:
            pass

        # Matematiske parametre for dit pizza-diagram
        CX, CY, MAX_R, N = 355, 252, 200, len(sel_keys)
        p1_display = p1 if len(p1) <= 35 else p1[:32] + "..."
        slice_width = 360.0 / N
        
        def get_slice_path(cx, cy, r, start_angle, end_angle):
            start_rad = math.radians(start_angle - 90)
            end_rad = math.radians(end_angle - 90)
            x1 = cx + r * math.cos(start_rad)
            y1 = cy + r * math.sin(start_rad)
            x2 = cx + r * math.cos(end_rad)
            y2 = cy + r * math.sin(end_rad)
            return f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 0 1 {x2} {y2} Z"

        pizza_slices, grid_lines, labels = "", "", ""
        
        # Generer diagramstykker, akser og dine tekst-labels
        for i, k in enumerate(sel_keys):
            start_ang = i * slice_width
            end_ang = start_ang + slice_width
            mid_ang = start_ang + (slice_width / 2.0)
            
            val = max(0.0, min(float(r1.get(f'{k}_percentile', 0)), 100.0))
            slice_r = (val / 100.0) * MAX_R
            
            if slice_r > 0:
                pizza_slices += f'<path d="{get_slice_path(CX, CY, slice_r, start_ang, end_ang)}" class="slice-b" />\n'
            
            rad_line = math.radians(start_ang - 90)
            lx2 = CX + MAX_R * math.cos(rad_line)
            ly2 = CY + MAX_R * math.sin(rad_line)
            grid_lines += f'<line class="grid-line" x1="{CX}" y1="{CY}" x2="{lx2:.1f}" y2="{ly2:.1f}" />\n'
            
            rad_mid = math.radians(mid_ang - 90)
            tx = CX + (MAX_R + 42) * math.cos(rad_mid)
            ty = CY + (MAX_R + 42) * math.sin(rad_mid)
            
            metric_lines = METRICS_MAPPING[k].split('\n')
            tspan_html = ""
            for idx, line in enumerate(metric_lines):
                dy_value = "-4" if idx == 0 else "1.1em"
                tspan_html += f'<tspan x="0" dy="{dy_value}">{line}</tspan>'
            
            label_text = f'<text class="ax-lbl" text-anchor="middle">{tspan_html}</text>'
            badge_y_offset = 20 if len(metric_lines) > 1 else 8
            
            # Det præcise skjold-badge-look under tekst-akserne
            val_badge = f"""
            <g transform="translate(-13, {badge_y_offset})">
                <path d="M 0 0 L 26 0 L 26 10 C 26 15, 13 20, 13 20 C 13 20, 0 15, 0 10 Z" class="bg-b" />
                <text class="tx-b" x="13" y="11" text-anchor="middle">{int(val)}</text>
            </g>"""
            labels += f'<g transform="translate({tx:.1f}, {ty:.1f})">{label_text}{val_badge}</g>\n'
        # Opbygning af den endelige HTML-streng med din præcise CSS-indpakning og download-skripter
        html_response = f"""
        <div class="wrap" id="report">
            <div class="chart-container" id="chart-only">
                <style>
                    @import url('https://googleapis.com');
                    
                    .wrap {{
                        width: 100%;
                        max-width: 710px;
                        margin: auto;
                        background: #0B1220;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                    }}
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
                    .header-card {{ 
                        position: relative; 
                        z-index: 2; 
                        width: 100%; 
                        max-width: 575px; 
                        margin: 15px auto 25px; 
                        padding: 20px 25px; 
                        background: transparent; 
                        border: 1px solid rgba(0, 240, 255, 0.08); 
                        border-radius: 16px; 
                        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); 
                        box-sizing: border-box; 
                    }}
                    .h-cnt {{ display: flex; gap: 20px; width: 100%; box-sizing: border-box; }}
                    .p-meta-right {{ display: flex; flex-direction: column; flex-grow: 1; }}
                    .p-nm {{ font-size: 27px; font-weight: 900; margin: 0 0 10px; text-transform: uppercase; letter-spacing: -.5px; color: #fff; }}
                    .tactic-line {{ width: 100%; height: 2px; margin-bottom: 12px; }}
                    .p-sub-bar {{ display: flex; align-items: center; gap: 14px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; flex-wrap: wrap; }}
                    .meta-item {{ display: flex; align-items: center; gap: 6px; color: #fff; }}
                    .meta-item svg {{ opacity: .6; fill: none; stroke: {selected_color}; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; width: 15px; height: 15px; }}
                    .logo-shape {{ display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: rgba(0,240,255,0.1); border: 1px solid {selected_color}; border-radius: 50%; padding: 2px; box-sizing: border-box; box-shadow: 0 0 6px rgba(0, 240, 255, 0.2); }}
                    .club-crest-small {{ width: 100%; height: 100%; object-fit: contain; }}
                    .data-val {{ color: #94a3b8; font-weight: 600; }}
                    .pipe-divider {{ color: rgba(0,240,255,.2); font-size: 14px; }}
                    svg {{ display: block; margin: auto; overflow: visible; max-width: 100%; height: auto; position: relative; z-index: 1; }}
                    .grid-circle {{ fill: none; stroke: rgba(255,255,255,.08); }}
                    .grid-line {{ stroke: rgba(255,255,255,.06); }}
                    .ax-lbl {{ font-size: 12px; fill: #94a3b8; font-weight: 700; letter-spacing: .5px; }}
                    .slice-b {{ fill: {selected_color}1a; stroke: {selected_color}; stroke-width: 1.75; stroke-linejoin: round; filter: drop-shadow(0 0 6px {selected_color}26); }}
                    .bg-b {{ fill: #0f172a; stroke: {selected_color}cc; }}
                    .tx-b {{ fill: {selected_color}; font-size: 12px; font-weight: 700; }}
                    .chart-footer, .chart-footer-source {{ text-align: center; width: 100%; font-size: 11px; font-weight: 300; color: #e5e7eb; letter-spacing: .4px; padding: 0 40px; box-sizing: border-box; position: relative; z-index: 2; }}
                    .chart-footer {{ margin-top: 1px; opacity: 0.75; }}
                    .chart-footer-source {{ margin-top: 6px; opacity: 0.5; }}
                    .download {{ margin-top: 20px; text-align: center; width: 100%; z-index: 10; position: relative; }}
                    .download button {{ padding: 8px 14px; border-radius: 8px; border: 1px solid #1f2a37; background: #0f172a; color: #e5e7eb; cursor: pointer; font-size: 13px; font-weight: 700; transition: background 0.2s; }}
                    .download button:hover {{ background: #1e293b; }}
                </style>
        
                <div class="header-card">
                    <div class="h-cnt">
                        <div class="p-meta-right">
                            <h2 class="p-nm">{p1_display}</h2>
                            <svg class="tactic-line" viewBox="0 0 100 2" preserveAspectRatio="none">
                                <defs>
                                    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stop-color="{selected_color}" stop-opacity="0.6" />
                                        <stop offset="70%" stop-color="{selected_color}" stop-opacity="0.3" />
                                        <stop offset="100%" stop-color="{selected_color}" stop-opacity="0" />
                                    </linearGradient>
                                </defs>
                                <rect width="100" height="2" fill="url(#lineGrad)" />
                            </svg>
        
                            <div class="p-sub-bar">
                                <div class="meta-item">
                                    <div class="logo-shape">{'<img class="club-crest-small" src="'+logo_base64+'" />' if logo_base64 else ''}</div>
                                    <span class="data-val">{r1.get('League', 'N/A')}</span>
                                </div>
                                <span class="pipe-divider">|</span>
                                <div class="meta-item">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20.38 3.46L16 2a4 4 0 0 0-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l1.08 5.4A2 2 0 0 0 5.3 12.5H7v7a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-7h1.7a2 2 0 0 0 1.94-1.41l1.08-5.4a2 2 0 0 0-1.34-2.23z"/></svg>
                                    <span class="data-val">{r1.get('Pos.', 'N/A')}</span>
                                </div>
                                <span class="pipe-divider">|</span>
                                <div class="meta-item">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                                    <span class="data-val">{int(r1.get('total mins played', 0)) if r1.get('total mins played') else 0} MIN.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <svg width="710" height="570" viewBox="0 0 710 570">
                    <circle cx="{CX}" cy="{CY}" r="50" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="100" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="150" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="{MAX_R}" class="grid-circle" style="stroke: rgba(255, 255, 255, .08);" />
                    {f'<image href="{logo_base64}" x="{CX-24}" y="{CY-24}" height="48" width="48"/>' if logo_base64 else ''}
                    {pizza_slices} {grid_lines} {labels}
                </svg>
        
                <div class="chart-footer">{p1}'s percentile rank vs. {player_league} {selected_pos}s</div>
                <div class="chart-footer-source">Generated via ://render.com</div>
            </div>
            
            <div class="download"><button onclick="downloadPNG()">Download as PNG</button></div>
        </div>
        """
        return {"html": html_response, "player_name": p1_display}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
