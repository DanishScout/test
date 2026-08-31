# ==========================================
# ROUTERS/PIZZA.PY - DEL 1 AF 2
# ==========================================
import math
import base64
import requests
import pandas as pd
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

# Vi opretter routeren til pizzadiagrammet
router = APIRouter(prefix="/api/pizza", tags=["Pizza"])

class PizzaRequest(BaseModel):
    player: str
    position: str
    metrics: List[str]
    color: str = '#00FFD5'

def process_pizza_data(req: PizzaRequest, app_metrics: dict, df_loader):
    """ Håndterer opslag, filtrering og percentil-beregninger """
    p1, sel_keys = req.player, req.metrics
    metrics_mapping = {k: v for cat in app_metrics.values() for k, v in cat.items()}
    
    if len(sel_keys) < 3:
        return {
            "html": "<p style='color:#e5e7eb; text-align:center;'>Vælg mindst 3 metrics.</p>", 
            "player_name": p1, "position": req.position
        }, None, None, None, None

    df = df_loader()
    pos_col = 'Pos.' if 'Pos.' in df.columns else ('Position' if 'Position' in df.columns else df.columns)
    
    if p1 not in df['Player Name'].values:
        raise HTTPException(404, "Spilleren blev ikke fundet.")

    p_row = df[df['Player Name'] == p1].iloc[0]
    selected_pos = str(p_row[pos_col])
    
    # Filtrering mod liga og position
    comp_df = df[(df['League'] == p_row['League']) & (df[pos_col] == selected_pos)].copy()
    if p1 not in comp_df['Player Name'].values:
        comp_df = pd.concat([comp_df, df[df['Player Name'] == p1]], ignore_index=True)

    # Beregn percentiler effektivt
    for k in sel_keys:
        if k in comp_df.columns:
            comp_df[f'{k}_pct'] = comp_df[k].rank(pct=True, method='max') * 100.0
        else:
            comp_df[f'{k}_pct'] = 0.0

    r1 = comp_df[comp_df['Player Name'] == p1].iloc[0]
    
    # Hent klublogo via Opta API
    logo_base64 = ""
    if team_id := r1.get('contestantId'):
        try:
            res = requests.get(f'https://omo.akamai.opta.net/image.php?secure=true&h=omo.akamai.opta.net&sport=football&entity=team&description=badges&dimensions=150&id={team_id}', timeout=2)
            if res.status_code == 200:
                buf = BytesIO()
                Image.open(BytesIO(res.content)).save(buf, format="PNG")
                logo_base64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        except: 
            pass

    return None, r1, logo_base64, selected_pos, metrics_mapping
# ==========================================
# ROUTERS/PIZZA.PY - DEL 2 AF 2
# ==========================================

# ==========================================
# ROUTERS/PIZZA.PY - DEL 2A AF 2
# ==========================================

@router.post("/generate-pizza")
def generate_pizza(req: PizzaRequest, app_metrics: dict, df_loader):
    try:
        # Genbrug datalogi-funktionen fra Del 1
        err, r1, logo_base64, selected_pos, metrics_mapping = process_pizza_data(req, app_metrics, df_loader)
        if err: return err

        p1, sel_keys, selected_color = req.player, req.metrics, req.color
        CX, CY, MAX_R, N = 355, 310, 200, len(sel_keys)
        p1_display = p1 if len(p1) <= 35 else p1[:32] + "..."
        w = 360.0 / N

        def rad(deg): return math.radians(deg - 90)
        def slice_path(r, s, e):
            return f"M {CX} {CY} L {CX+r*math.cos(rad(s)):.1f} {CY+r*math.sin(rad(s)):.1f} A {r} {r} 0 0 1 {CX+r*math.cos(rad(e)):.1f} {CY+r*math.sin(rad(e)):.1f} Z"

        slices, lines, labels = "", "", ""
        for i, k in enumerate(sel_keys):
            s_ang, e_ang = i * w, (i + 1) * w
            m_ang = s_ang + (w / 2.0)
            
            val = max(0.0, min(float(r1.get(f'{k}_pct', 0)), 100.0))
            if (slice_r := (val / 100.0) * MAX_R) > 0:
                slices += f'<path d="{slice_path(slice_r, s_ang, e_ang)}" class="slice-b" />\n'
            
            lines += f'<line class="grid-line" x1="{CX}" y1="{CY}" x2="{CX+MAX_R*math.cos(rad(s_ang)):.1f}" y2="{CY+MAX_R*math.sin(rad(s_ang)):.1f}" />\n'
            
            tx, ty = CX + (MAX_R + 42) * math.cos(rad(m_ang)), CY + (MAX_R + 42) * math.sin(rad(m_ang))
            tspans = "".join([f'<tspan x="0" dy="{"-4" if idx==0 else "1.1em"}">{l}</tspan>' for idx, l in enumerate(metrics_mapping.get(k, k).split('\n'))])
            
            # RETTET AFSTAND: Øget markant for at stoppe overlap med metric-navnet
            badge_y_offset = 18 if '\n' in metrics_mapping.get(k, k) else 5
            
            labels += f"""<g transform="translate({tx:.1f}, {ty:.1f})">
                <text class="ax-lbl" text-anchor="middle">{tspans}</text>
                <g transform="translate(-13, {badge_y_offset})">
                    <path d="M 0 0 L 26 0 L 26 10 C 26 15, 13 20, 13 20 C 13 20, 0 15, 0 10 Z" class="bg-b" />
                    <text class="tx-b" x="13" y="11" text-anchor="middle">{int(val)}</text>
                </g>
            </g>\n"""

        logo_html = f'<img class="club-crest-small" src="{logo_base64}" />' if logo_base64 else ''
        team_val = str(r1.get('Team', r1.get('Team Name', 'N/A')))
        mins_val = "0" if pd.isna(r1.get('total mins played')) else str(int(r1.get('total mins played', 0)))

        # Fortsætter direkte i Del 2B under...
        # ==========================================
        # ROUTERS/PIZZA.PY - DEL 2B AF 2
        # ==========================================
        html_pizza = f"""
        <div class="wrap" id="report">
            <div class="chart-container" id="chart-only">
                <style>
                    @import url('https://googleapis.com');
                    .wrap {{ width: 100%; max-width: 710px; margin: auto; background: #0B1220; display: flex; flex-direction: column; align-items: center; }}
                    .chart-container {{ position: relative; padding: 15px 15px 35px; border-radius: 24px; width: 100%; max-width: 710px; border: 1px solid rgba(0,240,255,.08); box-shadow: 0 30px 60px -15px #000; box-sizing: border-box; background: #0B1220; display: flex; flex-direction: column; align-items: center; font-family: 'Gabarito', sans-serif; color: #e5e7eb; }}
                    .chart-container::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(#0f172a, #020617); z-index: 0; border-radius: 24px; }}
                    .header-card {{ position: relative; z-index: 2; width: 100%; max-width: 575px; margin: 15px auto 25px; padding: 20px 25px; border: 1px solid rgba(0, 240, 255, 0.08); border-radius: 16px; box-sizing: border-box; }}
                    .h-cnt {{ display: flex; gap: 20px; width: 100%; }}
                    .p-meta-right {{ display: flex; flex-direction: column; flex-grow: 1; }}
                    .p-nm {{ font-size: 27px; font-weight: 700; margin: 0 0 10px; text-transform: uppercase; color: #fff; }}
                    
                    /* Tvinger højden frem, så divider-linjen bliver synlig */
                    .tactic-line {{ width: 100%; height: 2px !important; margin-bottom: 12px; display: block; }}
                    
                    .p-sub-bar {{ display: flex; align-items: center; gap: 14px; font-size: 13px; font-weight: 700; text-transform: uppercase; flex-wrap: wrap; }}
                    .meta-item {{ display: flex; align-items: center; gap: 6px; color: #fff; }}
                    .meta-item svg {{ opacity: .6; fill: none; stroke: {selected_color}; stroke-width: 2.5; width: 15px; height: 15px; }}
                    .logo-shape {{ display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: rgba(0,240,255,0.1); border: 1px solid {selected_color}; border-radius: 50%; padding: 2px; box-sizing: border-box; }}
                    .club-crest-small {{ width: 100%; height: 100%; object-fit: contain; }}
                    .data-val {{ color: #94a3b8; }}
                    .pipe-divider {{ color: rgba(0,240,255,.2); }}
                    svg {{ display: block; margin: auto; overflow: visible; max-width: 100%; height: auto; position: relative; z-index: 1; }}
                    .grid-circle {{ fill: none; stroke: rgba(255,255,255,.08); }}
                    .grid-line {{ stroke: rgba(255,255,255,.06); }}
                    .ax-lbl {{ font-size: 12px; fill: #94a3b8; font-weight: 900; }}
                    .slice-b {{ fill: {selected_color}1a; stroke: {selected_color}; stroke-width: 1.75; stroke-linejoin: round; }}
                    .bg-b {{ fill: #0f172a; stroke: {selected_color}cc; }}
                    .tx-b {{ fill: {selected_color}; font-size: 12px; font-weight: 700; }}
                    .chart-footer, .chart-footer-source {{ text-align: center; width: 100%; font-size: 11px; color: #e5e7eb; position: relative; z-index: 2; }}
                    .chart-footer {{ margin-top: 1px; opacity: 0.75; }}
                    .chart-footer-source {{ margin-top: 6px; opacity: 0.5; }}
                    .download {{ margin-top: 20px; z-index: 10; position: relative; }}
                    .download button {{ padding: 8px 14px; border-radius: 8px; border: 1px solid #1f2a37; background: #0f172a; color: #e5e7eb; cursor: pointer; font-size: 13px; font-weight: 700; }}
                </style>
                <div class="header-card">
                    <div class="h-cnt">
                        <div class="p-meta-right">
                            <h2 class="p-nm">{p1_display}</h2>
                            <svg class="tactic-line" viewBox="0 0 100 2" preserveAspectRatio="none">
                                <defs>
                                    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stop-color="{selected_color}" stop-opacity="0.6" />
                                        <stop offset="100%" stop-color="{selected_color}" stop-opacity="0" />
                                    </linearGradient>
                                </defs>
                                <rect width="100" height="2" fill="url(#lineGrad)" />
                            </svg>
                            <div class="p-sub-bar">
                                <div class="meta-item"><div class="logo-shape">{logo_html}</div><span class="data-val">{team_val}</span></div>
                                <span class="pipe-divider">|</span>
                                <div class="meta-item">
                                    <svg viewBox="0 0 24 24"><path d="M20.38 3.46L16 2a4 4 0 0 0-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l1.08 5.4A2 2 0 0 0 5.3 12.5H7v7a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-7h1.7a2 2 0 0 0 1.94-1.41l1.08-5.4a2 2 0 0 0-1.34-2.23z"/></svg>
                                    <span class="data-val">{selected_pos}</span>
                                </div>
                                <span class="pipe-divider">|</span>
                                <div class="meta-item">
                                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                                    <span class="data-val">{mins_val} MIN.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <svg width="710" height="570" viewBox="0 0 710 570">
                    <circle cx="{CX}" cy="{CY}" r="50" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="100" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="150" class="grid-circle" />
                    <circle cx="{CX}" cy="{CY}" r="{MAX_R}" class="grid-circle" />
                    {slices} {lines} {labels}
                </svg>
                <div class="chart-footer">{p1_display}'s percentile rank vs. {r1.get('League', 'N/A')} {selected_pos}s</div>
                <div class="chart-footer-source">Generated via Render</div>
            </div>
            <div class="download"><button onclick="downloadPNG()">Download as PNG</button></div>
        </div>
        """
        return {"html": html_pizza, "player_name": p1_display, "position": selected_pos}
    except Exception as e: 
        raise HTTPException(500, str(e))
