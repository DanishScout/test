import base64
import math
import requests
import pandas as pd
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

# -----------------------
# DATA INDLÆSNING (Sker kun én gang globalt ved opstart)
# -----------------------
print("⚡ Indlæser data til radar-sammenligning...")
try:
    df1 = pd.read_csv('aut1.csv')
    df2 = pd.read_csv('tur1.csv')
    data_global = pd.concat([df1, df2], ignore_index=True)
    print("✅ Radar data er klar!")
except Exception as e:
    print(f"⚠️ Kunne ikke indlæse datafiler lokalt: {e}")
    data_global = pd.DataFrame()

# -----------------------
# METRICS CONFIGURATION
# -----------------------
available_metrics = {
    "Shooting": {
        "total goals_p90PR": "Goals",
        "xG_p90PR": "npxG",
    },
    "Passing": {
        "total assists_p90PR": "Assists",
        "xA_p90PR": "xA",
    },
    "Possession": {
        "total won contest_p90PR": "Successful\nDribbles",
        "total contest_p90PR": "Dribble\nAttempts",
    },
    "Defending": {
        "tackle_success_pct_p90PR": "Tackles\nWon %",
        "aerial_success_pct_p90PR": "Aerials\nWon %",
    },
}

# Fladt opslagsværk til brug i HTML/SVG-genereringen bagefter
METRICS_MAP = {k: v for cat in available_metrics.values() for k, v in cat.items()}

def vis_radar_page(p1, p2, cat_shoot, cat_pass, cat_poss, cat_def):
    if data_global.empty:
        return HTMLResponse(content="<html><body>Data mangler</body></html>", status_code=500)
    
    p_list = sorted(data_global['Player Name'].dropna().unique())
    
    # Sæt standardspillere hvis ingen er angivet
    if not p1 and p_list: p1 = p_list[0]
    if not p2 and p_list: p2 = p_list[min(1, len(p_list)-1)]
    
    # Samler alle valgte metrics fra de fire sektioner
    sel_keys = cat_shoot + cat_pass + cat_poss + cat_def
    
    # Generer options til spiller-dropdowns
    p1_opts = "".join(f'<option value="{p}" {"selected" if p == p1 else ""}>{p}</option>' for p in p_list)
    p2_opts = "".join(f'<option value="{p}" {"selected" if p == p2 else ""}>{p}</option>' for p in p_list)
    
    # Hvis der er valgt under 3 metrics, viser vi en advarsel i stedet for diagrammet
    if len(sel_keys) < 3:
        chart_output_html = """
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; padding: 25px; border-radius: 12px; text-align: center; color: #f59e0b; font-weight: 700; margin: 40px auto; max-width: 500px;">
            ⚠️ Vælg mindst 3 metrics i kontrolpanelet for at generere radardiagrammet.
        </div>
        """
    else:
        # Hent datasæt-rækker for de to spillere
        r1_all = data_global[data_global['Player Name'] == p1]
        r2_all = data_global[data_global['Player Name'] == p2]
        
        if r1_all.empty or r2_all.empty:
            return HTMLResponse(content="<html><body>En eller flere spillere blev ikke fundet</body></html>", status_code=404)
            
        r1, r2 = r1_all.iloc[0], r2_all.iloc[0]
        
        # --- RADAR DIAGRAM MATEMATIK ---
        CX, CY, R, N = 355, 245, 180, len(sel_keys)
        
        p1_display = p1 if len(p1) <= 25 else p1[:22] + "..."
        p2_display = p2 if len(p2) <= 25 else p2[:22] + "..."
        
        # Beregn polygon-grids i baggrunden (20%, 40%, 60%, 80%, 100%)
        grid_polys = "".join(f'<polygon class="grid-poly" points="{" ".join(f"{CX+R*pct*math.cos(i*2*math.pi/N-math.pi/2):.1f},{CY+R*pct*math.sin(i*2*math.pi/N-math.pi/2):.1f}" for i in range(N))}" />\n' for pct in [0.2, 0.4, 0.6, 0.8, 1.0])
        
        b_pts, p_pts, spokes, labels = [], [], "", ""
        for i, k in enumerate(sel_keys):
            ang = (i * 2 * math.pi / N) - (math.pi / 2)
            cos_a, sin_a = math.cos(ang), math.sin(ang)
            
            # Skaler værdierne (percentiler) ind til radarens radius
            v1 = max(0.0, min(float(r1.get(k, 0))/100.0, 1.0))
            v2 = max(0.0, min(float(r2.get(k, 0))/100.0, 1.0))
            
            b_pts.append(f"{CX + v1 * R * cos_a:.1f},{CY + v1 * R * sin_a:.1f}")
            p_pts.append(f"{CX + v2 * R * cos_a:.1f},{CY + v2 * R * sin_a:.1f}")
            
            spokes += f'<line class="grid-line" x1="{CX}" y1="{CY}" x2="{CX+R*cos_a:.1f}" y2="{CY+R*sin_a:.1f}" />\n'
            
            # Tekst og metric badges placering uden om diagrammet
            lx, ly = CX + (R + 50) * cos_a, CY + (R + 50) * sin_a
            val1, val2 = int(float(r1.get(k,0))), int(float(r2.get(k,0)))
            
            label_text = f'<text class="ax-lbl" text-anchor="middle" dy="-4">{METRICS_MAP[k]}</text>'
            b_badge = f'<g transform="translate(-29, 10)"><rect class="bg-b" width="26" height="16" rx="4"/><text class="tx-b" x="13" y="12" text-anchor="middle">{val1}</text></g>'
            p_badge = f'<g transform="translate(3, 10)"><rect class="bg-p" width="26" height="16" rx="4"/><text class="tx-p" x="13" y="12" text-anchor="middle">{val2}</text></g>'
        
            labels += f'<g transform="translate({lx:.1f}, {ly:.1f})">{label_text}{b_badge}{p_badge}</g>\n'
        
        chart_output_html = f"""
        <div class="chart-container" id="chart-only">
            <div class="h-cnt">
                <div class="p-panel left">
                    <h2 class="p-nm b-tx">{p1_display}</h2>
                    <div class="p-row">
                        <span class="info-tag">{r1.get('Pos.', 'N/A')}</span>
                        <span class="info-tag">{int(float(r1.get('total mins played', 0))) if r1.get('total mins played') else '0'} MIN.</span>
                        <span class="info-tag">{r1.get('League', 'N/A')}</span>
                    </div>
                </div>
    
                <div class="h-divider"></div>
                
                <div class="p-panel right">
                    <h2 class="p-nm p-tx">{p2_display}</h2>
                    <div class="p-row">
                        <span class="info-tag">{r2.get('Pos.', 'N/A')}</span>
                        <span class="info-tag">{int(float(r2.get('total mins played', 0))) if r2.get('total mins played') else '0'} MIN.</span>
                        <span class="info-tag">{r2.get('League', 'N/A')}</span>
                    </div>
                </div>
            </div>
            
            <svg width="710" height="570" viewBox="0 0 710 570">
                {grid_polys}
                {spokes}
                <polygon class="pl-b" points="{" ".join(b_pts)}" />
                <polygon class="pl-p" points="{" ".join(p_pts)}" />
                {"".join(f'<circle class="n-b" cx="{pt.split(",")[0]}" cy="{pt.split(",")[1]}" r="6" />' for pt in b_pts)}
                {"".join(f'<circle class="n-p" cx="{pt.split(",")[0]}" cy="{pt.split(",")[1]}" r="6" />' for pt in p_pts)}
                {labels}
            </svg>
            
            <div class="chart-footer">
                Values represent percentile ranks in each metric compared to positional peers in the player's league
            </div>
        </div>
        """
    # HTML Output med dobbelte klammer til f-string CSS
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PER 90 - Player Comparison Radar</title>
        <link href="https://googleapis.com" rel="stylesheet">
        <style>
            body {{ margin: 0; font-family: 'Gabarito', sans-serif; background-color: #070B13; color: #e5e7eb; display: flex; min-height: 100vh; max-width: 100vw; overflow-x: hidden; }}
            aside {{ width: 260px; min-width: 260px; background: #0B1220; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 30px 20px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0; }}
            .sidebar-logo {{ font-size: 22px; font-weight: 900; color: #00FFD5; margin-bottom: 40px; text-decoration: none; }}
            nav {{ display: flex; flex-direction: column; gap: 10px; }}
            nav a {{ color: #94a3b8; text-decoration: none; padding: 12px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
            nav a:hover, nav a.active {{ background: rgba(0, 255, 213, 0.1); color: #00FFD5; }}
            
            main {{ flex-grow: 1; padding: 40px; display: flex; flex-direction: column; gap: 30px; align-items: stretch; width: calc(100% - 260px); max-width: 100%; box-sizing: border-box; }}
            
            /* TOP-PLACERET VANDRET KONTROLPANEL */
            .control-panel {{ width: 100%; max-width: 100%; background: #0B1220; border: 1px solid rgba(255, 255, 255, 0.04); padding: 24px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); box-sizing: border-box; }}
            #radarForm {{ display: flex; flex-direction: row; gap: 40px; width: 100%; align-items: flex-start; }}
            
            .players-section {{ display: flex; flex-direction: column; gap: 16px; width: 280px; min-width: 280px; }}
            .metrics-section {{ flex-grow: 1; }}
            
            .form-group {{ position: relative; width: 100%; }}
            label.form-title {{ display: block; font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }}
            
            /* FLOT DESIGNET SELECT MED DESIGNET PIL */
            select {{ 
                width: 100%; background: #070B13; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px 16px; color: #fff; font-size: 14px; font-family: inherit; font-weight: 600; box-sizing: border-box; outline: none; cursor: pointer; transition: all 0.2s ease; appearance: none; -webkit-appearance: none;
                background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://w3.org' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>");
                background-repeat: no-repeat; background-position: right 12px center; background-size: 16px; padding-right: 40px;
            }}
            select:hover {{ border-color: rgba(0, 255, 213, 0.4); background-color: #0b1220; }}
            select:focus {{ border-color: #00FFD5; box-shadow: 0 0 0 2px rgba(0, 255, 213, 0.15); }}
            
            /* METRICS GRID: PRÆCIS 3 COLUMNS VANDRET */
                        /* METRICS GRID: KATEGORIERNE VISES VANDRET */
            .metrics-grid-layout {{ 
                display: grid; 
                grid-template-columns: repeat(3, minmax(180px, 1fr)); 
                gap: 20px; 
                width: 100%; 
            }}
            .cat-block {{ display: flex; flex-direction: column; position: relative; }}
            
            /* DE NYE DROPDOWN MENUER MED FLUEBEN (FRA PIZZA.PY) */
            .custom-multiselect {{ position: relative; width: 100%; margin-top: 4px; }}
            .select-box {{ 
                display: flex; justify-content: space-between; align-items: center; 
                background: #070B13; border: 1px solid rgba(255,255,255,0.08); 
                border-radius: 8px; padding: 10px 14px; color: #fff; font-size: 13px; 
                font-weight: 600; cursor: pointer; user-select: none; box-sizing: border-box; 
            }}
            .select-box:hover {{ border-color: rgba(0, 255, 213, 0.5); }}
            .select-box .arrow {{ font-size: 9px; color: #64748b; transition: transform 0.2s; }}
            
            .checkboxes {{ 
                display: none; position: absolute; top: 100%; left: 0; right: 0; 
                background: #070B13; border: 1px solid #00FFD5; border-top: none; 
                border-radius: 0 0 8px 8px; max-height: 200px; overflow-y: auto; 
                z-index: 100; padding: 6px; box-shadow: 0 10px 25px rgba(0,0,0,0.6); 
            }}
            .custom-multiselect.open .checkboxes {{ display: block; }}
            .custom-multiselect.open .select-box {{ border-radius: 8px 8px 0 0; border-color: #00FFD5; }}
            .custom-multiselect.open .arrow {{ transform: rotate(180deg); color: #00FFD5; }}
            
            .check-item {{ 
                display: flex; align-items: center; padding: 8px 10px; color: #cbd5e1; 
                font-size: 13px; font-weight: 600; cursor: pointer; border-radius: 5px; 
                margin-bottom: 2px; transition: background 0.15s, color 0.15s; user-select: none; 
            }}
            .check-item:hover {{ background: rgba(255, 255, 255, 0.04); color: #fff; }}
            .check-item input {{ display: none; }}
            
            .custom-box {{ width: 15px; height: 15px; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; margin-right: 10px; display: inline-block; position: relative; background: #0B1220; flex-shrink: 0; }}
            .check-item input:checked + .custom-box {{ background: #00FFD5; border-color: #00FFD5; }}
            .check-item input:checked + .custom-box::after {{ content: '✓'; position: absolute; color: #070B13; font-size: 11px; font-weight: 900; top: 50%; left: 50%; transform: translate(-50%, -50%); }}


            /* RADAR RAPPORT VISUALISERING */
            .chart-display-wrapper {{ flex-grow: 1; display: flex; flex-direction: column; align-items: center; width: 100%; }}
            .chart-container {{ background: linear-gradient(180deg, #0f172a 0%, #020617 100%); padding: 30px; border-radius: 24px; width: 100%; max-width: 710px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); box-sizing: border-box; }}
            
            .h-cnt {{ position: relative; display: flex; flex-direction: row; height: 110px; margin-bottom: 35px; border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,0.06); background: rgba(15, 23, 42, 0.6); }}
            .p-panel {{ flex: 1; width: 50%; display: flex; flex-direction: column; justify-content: center; padding: 0 25px; z-index: 1; overflow: hidden; box-sizing: border-box; }}
            .p-panel.left {{ align-items: flex-start; background: linear-gradient(135deg, rgba(0,240,255,0.08) 0%, rgba(0,0,0,0) 80%); }}
            .p-panel.right {{ align-items: flex-end; text-align: right; background: linear-gradient(315deg, rgba(217,70,239,0.08) 0%, rgba(0,0,0,0) 80%); }}
            
            .h-divider {{ position: absolute; left: 50%; top: 10%; bottom: 10%; width: 1px; background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.35), transparent); transform: translateX(-50%); z-index: 2; }}
            .p-nm {{ font-size: 15px; font-weight: 600; margin: 0; text-transform: uppercase; letter-spacing: 2px; }}
            .b-tx {{ color: #00f0ff; text-shadow: 0 0 15px rgba(0,240,255,0.3); }} 
            .p-tx {{ color: #d946ef; text-shadow: 0 0 15px rgba(217,70,239,0.3); }}
            
            .p-row {{ display: flex; align-items: center; gap: 6px; margin-top: 6px; z-index: 2; }}
            .info-tag {{ font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.05); color: #f1f5f9; letter-spacing: 0.5px; text-transform: uppercase; }}
            .left .info-tag {{ border-left: 2px solid #00f0ff; }}
            .right .info-tag {{ border-right: 2px solid #d946ef; }}
            
            svg {{ display: block; margin: 0 auto; overflow: visible; width: 100%; height: auto; max-width: 710px; }}
            .grid-poly {{ fill: rgba(255,255,255,0.005); stroke: rgba(255,255,255,0.1); }}
            .grid-line {{ stroke: rgba(255,255,255,0.075); stroke-dasharray: 4,4; }}
            .ax-lbl {{ font-size: 12px; fill: #e2e8f0; font-weight: 600; letter-spacing: 0.3px; }}
            
            .pl-b {{ fill: rgba(0,240,255,0.07); stroke: #00f0ff; stroke-width: 2.5; stroke-linejoin: round; }}
            .pl-p {{ fill: rgba(217,70,239,0.07); stroke: #d946ef; stroke-width: 2.5; stroke-linejoin: round; }}
            .n-b {{ fill: #00f0ff; opacity: 0.8; stroke: none; }} 
            .n-p {{ fill: #d946ef; opacity: 0.8; stroke: none; }}
            
            .bg-b {{ fill: rgba(0, 240, 255, 0.12); stroke: rgba(0, 240, 255, 0.4); stroke-width: 1; }}
            .bg-p {{ fill: rgba(217, 70, 239, 0.12); stroke: rgba(217, 70, 239, 0.4); stroke-width: 1; }}
            
            .tx-b {{ fill: #00f0ff; font-size: 12px; font-weight: 600; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.9)); }}
            .tx-p {{ fill: #ffb6ff; font-size: 12px; font-weight: 600; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.9)); }}
    
            .chart-footer {{ text-align: center; width: 100%; margin-top: 15px; font-size: 11px; opacity: 0.4; color: #94a3b8; }}
            .download {{ margin-top: 20px; text-align: center; width: 100%; }}
            .download button {{ padding: 10px 18px; border-radius: 8px; border: 1px solid #1f2a37; background: #0f172a; color: #e5e7eb; cursor: pointer; font-size: 13px; font-weight: 700; transition: background 0.2s; }}
            .download button:hover {{ background: #1e293b; }}
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
                <a href="/radar" class="active">🕸️ Radarsammenligning</a>
                <a href="#">🏆 Leaderboard</a>
            </nav>
        </aside>
        
        <main>
            <!-- TOP KONTROLPANEL -->
            <div class="control-panel">
                <form id="radarForm" action="/radar" method="get">
                    <!-- VENSTRE SIDE: SPILLERVALG -->
                    <div class="players-section">
                        <div class="form-group">
                            <label class="form-title">Spiller 1 (Blå)</label>
                            <select name="p1" class="live-input">{p1_opts}</select>
                        </div>
                        <div class="form-group">
                            <label class="form-title">Spiller 2 (Lilla)</label>
                            <select name="p2" class="live-input">{p2_opts}</select>
                        </div>
                    </div>
                    
                    <!-- HØJRE SIDE: METRICS FILTER FORDelt I 3 KOLONNER -->
                    <div class="metrics-section">
                        <label class="form-title" style="margin-bottom: 12px;">Vælg Metrikker (Mindst 3)</label>
                        <div class="metrics-grid-layout">
    """

    # Gennemgår de 4 metrik-kategorier og fordeler dem i blokke til vores grid
        # Gennemgår de 4 metrik-kategorier og fordeler dem i dropdown-menuer
    for cat_name, cat_metrics in available_metrics.items():
        # Opretter id'er der matcher JavaScript-kaldene
        felt_id = "shoot" if cat_name == "Shooting" else "pass" if cat_name == "Passing" else "poss" if cat_name == "Possession" else "def"
        
        # Beregner dynamisk antallet af valgte metrics til tekst-visningen
        active_list = cat_shoot if cat_name == "Shooting" else cat_pass if cat_name == "Passing" else cat_poss if cat_name == "Possession" else cat_def
        count_text = f"Vælg metrics ({len(active_list)})"

        html += f"""
                            <div class="cat-block">
                                <div style="font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">{cat_name} METRICS</div>
                                <div class="custom-multiselect">
                                    <div class="select-box" onclick="toggleDropdown('{felt_id}')">
                                        <span>{count_text}</span>
                                        <span class="arrow">▼</span>
                                    </div>
                                    <div class="checkboxes" id="opts-{felt_id}">
        """
        for m_key, m_label in cat_metrics.items():
            is_checked = ""
            if cat_name == "Shooting" and m_key in cat_shoot: is_checked = "checked"
            elif cat_name == "Passing" and m_key in cat_pass: is_checked = "checked"
            elif cat_name == "Possession" and m_key in cat_poss: is_checked = "checked"
            elif cat_name == "Defending" and m_key in cat_def: is_checked = "checked"
            
            param_name = "cat_shoot" if cat_name == "Shooting" else "cat_pass" if cat_name == "Passing" else "cat_poss" if cat_name == "Possession" else "cat_def"
            
            html += f"""
                                        <label class="check-item">
                                            <input type="checkbox" name="{param_name}" value="{m_key}" class="live-input" {is_checked}>
                                            <span class="custom-box"></span>
                                            {m_label.replace('\n', ' ')}
                                        </label>
            """
        html += """
                                    </div>
                                </div>
                            </div>
        """

    html += f"""
                        </div>
                    </div>
                </form>
            </div>

            <!-- VISUALISERING AF RADAR -->
            <div class="chart-display-wrapper">
                <div id="report" style="width:100%; display:flex; flex-direction:column; align-items:center;">
                    {chart_output_html}
                </div>
                
                <div class="download">
                    <button onclick="downloadPNG()">Download som PNG</button>
                </div>
            </div>
        </main>
        
        <script src="https://cloudflare.com"></script>
        <script>
            // Åben og luk dropdown-menuerne ved at tilføje .open til den rigtige container
            function toggleDropdown(feltNavn) {{
                const el = document.getElementById('opts-' + feltNavn).closest('.custom-multiselect');
                const isOpen = el.classList.contains('open');
                
                // Luk alle andre åbne dropdowns for at undgå overlap
                document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                    dropdown.classList.remove('open');
                }});
                
                if (!isOpen) {{
                    el.classList.add('open');
                }}
            }}

            // Luk dropdown-menuerne, hvis der klikkes et tilfældigt sted udenfor
            document.addEventListener('click', function(e) {{
                if (!e.target.closest('.custom-multiselect')) {{
                    document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                        dropdown.classList.remove('open');
                    }});
                }}
            }});

            // Auto-update: Indsender automatisk formularen ved ændringer i inputs eller flueben
            document.querySelectorAll('.live-input').forEach(input => {{
                input.addEventListener('change', () => {{
                    document.getElementById('radarForm').submit();
                }});
            }});

            function downloadPNG() {{
                const el = document.getElementById("chart-only");
                html2canvas(el, {{
                    scale: 3,
                    backgroundColor: "#0B1220",
                    useCORS: true
                }}).then(canvas => {{
                    const link = document.createElement("a");
                    link.download = "radar_comparison.png";
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@router.get("/radar", response_class=HTMLResponse)
def get_radar_page(
    p1: str = Query(None),
    p2: str = Query(None),
    cat_shoot: list[str] = Query([]),
    cat_pass: list[str] = Query([]),
    cat_poss: list[str] = Query([]),
    cat_def: list[str] = Query([])
):
    return vis_radar_page(p1, p2, cat_shoot, cat_pass, cat_poss, cat_def)



