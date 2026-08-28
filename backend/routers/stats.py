import base64
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
print("⚡ Indlæser data til stats-dashboard...")
try:
    df_den = pd.read_csv("den1.csv")
    df_tur = pd.read_csv("tur1.csv")
    df_global = pd.concat([df_den, df_tur], ignore_index=True)
    print("✅ Stats data er klar!")
except Exception as e:
    print(f"⚠️ Kunne ikke indlæse datafiler lokalt: {e}")
    df_global = pd.DataFrame()

# -----------------------
# HELPERS & METRICS DEFINITION
# -----------------------
def safe_int(x):
    try:
        return int(float(x))
    except:
        return 0

def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x)

def is_pct_metric(metric_name):
    return "pct" in metric_name.lower()

def pr_col(m):
    return m.replace("_p90", "_p90PR")

def get_tag(p):
    if p >= 85:
        return "Elite", "elite"
    elif p >= 65:
        return "Above Avg", "good"
    elif p >= 40:
        return "Average", "avg"
    elif p >= 20:
        return "Below Avg", "concern"
    else:
        return "Poor", "poor"

def get_metrics():
    return {
        "OUTPUT": [
            ("total goals_p90", "Goals"),
            ("xG_p90", "npxG"),
            ("total ontarget attempt_p90", "Shots On Target"),
            ("CreatedOwnShot_p90", "Created Own Shot"),
            ("total attempts ibox_p90", "Shots Inside Box"),
            ("total touches in opposition box_p90", "Touches In Opp. Box"),
        ],
        "PLAYMAKING": [
            ("total assists_p90", "Assists"),
            ("xA_p90", "xA"),
            ("total att assist_p90", "Key Passes"),
            ("xT_pass_p90", "xT via Live Passes"),
            ("progressive_passes_p90", "Progressive Passes"),
            ("passes_into_final_third_p90", "Passes Into Final 3rd"),
        ],
        "PASSING": [
            ("total accurate pass_p90", "Accurate Passes"),
            ("total accurate long balls_p90", "Accurate Long Balls"),
            ("total accurate cross_p90", "Accurate Crosses"),
            ("pass_success_pct_p90", "Pass Accuracy %"),
            ("long_balls_success_pct_p90", "Long Ball Accuracy %"),
            ("cross_success_pct_p90", "Cross Accuracy %"),
        ],
        "POSSESSION": [
            ("total won contest_p90", "Successful Dribbles"),
            ("total contest_p90", "Dribble Attempts"),
            ("dribble_success_pct_p90", "Dribble Success %"),
            ("Total Carries_p90", "Progressive Carries"),
            ("Total Carry xT_p90", "xT via Progressive Carries"),
            ("Total Final Third Carries_p90", "Carries Into Final ⅓"),
        ],
        "DEFENDING/DUELS": [
            ("tackle_success_pct_p90", "Tackles Won %"),
            ("aerial_success_pct_p90", "Aerials Won %"),
            ("duel_success_pct_p90", "Duels Won %"),
            ("total won tackle_p90", "Tackles Won"),
            ("total aerial won_p90", "Aerials Won"),
            ("total duels won_p90", "Duels Won"),
        ],
        "OTHER": [
            ("total interception_p90", "Interceptions"),
            ("total was fouled_p90", "Fouls Drawn"),
            ("total accurate fwd zone pass_p90", "Passes in Opp. Half"),
            ("forward_passes_p90", "Forward Passes"),
            ("total attempt_p90", "Total Shots"),
            ("attempt_success_pct_p90", "On Target %"),
        ],
    }

def metric_tile(label, value, percentile, metric_name):
    value = 0 if pd.isna(value) else value
    percentile = 0 if pd.isna(percentile) else float(percentile)
    percentile = max(0, min(100, percentile))
    tag_text, tag_class = get_tag(percentile)

    if is_pct_metric(metric_name):
        value_display = f"{value:.2f}%"
    else:
        value_display = f"{value:.2f}/90"

    return f"""
    <div class="metric">
        <div class="label-wrap">
            <div class="label">{label}</div>
        </div>
        <div class="bar">
            <div class="fill {tag_class}" style="width:{percentile}%"></div>
        </div>
        <div class="bottom">
            <div class="left">
                <span class="value">{value_display}</span>
                <span class="pct">({int(percentile)}%)</span>
            </div>
            <div class="right">
                <span class="tag {tag_class}">{tag_text}</span>
            </div>
        </div>
    </div>
    """

def vis_stats_page(selected_player_name, selected_cats):
    if df_global.empty:
        return HTMLResponse(content="<html><body>Data mangler</body></html>", status_code=500)
    
    # Sorterede lister til dropdowns
    all_players = sorted(df_global["Player Name"].dropna().unique())
    if not selected_player_name and all_players:
        selected_player_name = all_players[0]
        
    player_rows = df_global[df_global["Player Name"] == selected_player_name]
    if player_rows.empty:
        return HTMLResponse(content="<html><body>Spiller ikke fundet</body></html>", status_code=404)
        
    player = player_rows.iloc[0]
    metrics = get_metrics()
    
    if not selected_cats:
        selected_cats = list(metrics.keys())

    # Generer options til dropdown menuen
    p_opts = ""
    for p in all_players:
        sel = "selected" if p == selected_player_name else ""
        p_opts += f'<option value="{p}" {sel}>{p}</option>'

    # Opta Logo Fetching
    team_id = safe_str(player.get("contestantId"))
    logo_html = '<div class="logo"></div>'
    if team_id:
        try:
            url = f"https://opta.net{team_id}"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                logo_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
                logo_html = f'<img class="logo-img" src="{logo_url}" style="width:56px; height:56px; border-radius:8px; background:#111827;">'
        except:
            pass

    age = f"{safe_int(player.get('Age'))} y/o"
    mins = f"{safe_int(player.get('total mins played'))} min. played"

    # HTML Gengivelse med dobbelte curly brackets i stilarter
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PER 90 - Scouting Report</title>
        <link href="https://googleapis.com" rel="stylesheet">
        <style>
            body {{ margin: 0; font-family: 'Gabarito', sans-serif; background-color: #070B13; color: #e5e7eb; display: flex; min-height: 100vh; max-width: 100vw; overflow-x: hidden; }}
            aside {{ width: 260px; min-width: 260px; background: #0B1220; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 30px 20px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0; }}
            .sidebar-logo {{ font-size: 22px; font-weight: 900; color: #00FFD5; margin-bottom: 40px; text-decoration: none; }}
            nav {{ display: flex; flex-direction: column; gap: 10px; }}
            nav a {{ color: #94a3b8; text-decoration: none; padding: 12px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
            nav a:hover, nav a.active {{ background: rgba(0, 255, 213, 0.1); color: #00FFD5; }}
            
            main {{
                flex-grow: 1;
                padding: 40px;
                display: flex; 
                /* ÆNDRET: Sætter elementerne over hinanden i stedet for side om side */
                flex-direction: column; 
                gap: 30px;
                align-items: stretch; 
                width: calc(100% - 260px);
                max-width: 100%;
                box-sizing: border-box;
            }}

            /* KONTROLPANEL (NU I TOPPEN AF SIKRER FULD BREDDE) */

            .control-panel {{
                width: 100%;
                max-width: 100%; 
                background: #0B1220; 
                border: 1px solid rgba(255, 255, 255, 0.04); 
                padding: 24px; 
                border-radius: 16px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
                box-sizing: border-box;
                display: flex;
                flex-direction: row;
                gap: 50px;
                align-items: flex-start;
            }}
            
            #statsForm {{
                display: flex;
                flex-direction: row;
                gap: 50px;
                width: 100%;
                align-items: flex-start;
            }}

            /* FLOTTERE SPILLER SELECTOR */
            .control-panel .form-group:first-child {{
                width: 280px;
                min-width: 280px;
            }}

            select {{ 
                width: 100%; 
                background: #070B13; 
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-radius: 10px; 
                padding: 12px 16px; 
                color: #fff; 
                font-size: 14px; 
                font-family: inherit; 
                font-weight: 600;
                box-sizing: border-box; 
                outline: none; 
                cursor: pointer;
                transition: all 0.2s ease; 
                /* Skræddersyet designet pil i stedet for standardpil */
                appearance: none;
                -webkit-appearance: none;
                -moz-appearance: none;
                background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://w3.org' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>");
                background-repeat: no-repeat;
                background-position: right 12px center;
                background-size: 16px;
                padding-right: 40px;
            }}
            
            select:hover {{ 
                border-color: rgba(0, 255, 213, 0.4); 
                background-color: #0b1220;
            }}
            
            select:focus {{ 
                border-color: #00FFD5; 
                box-shadow: 0 0 0 2px rgba(0, 255, 213, 0.15);
            }}

            /* TVING METRICS TIL NØJAGTIG 3 PR RÆKKE */
            .cat-checkbox-list {{ 
                display: grid;
                grid-template-columns: repeat(3, minmax(160px, 1fr)); /* Præcis 3 lige store kolonner */
                gap: 14px 30px; 
                margin-top: 8px; 
                width: 100%;
                max-width: 650px; /* Holder pakken samlet */
            }}

            .check-item {{
                display: flex;
                align-items: center;
                color: #cbd5e1;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.3px;
                cursor: pointer;
                user-select: none;
                transition: color 0.15s ease;
            }}

            .check-item:hover {{
                color: #fff;
            }}

            .check-item input {{ display: none; }}
            .custom-box {{ width: 15px; height: 15px; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; margin-right: 10px; display: inline-block; position: relative; background: #0B1220; flex-shrink: 0; }}
            .check-item input:checked + .custom-box {{ background: #00FFD5; border-color: #00FFD5; }}
            .check-item input:checked + .custom-box::after {{ content: '✓'; position: absolute; color: #070B13; font-size: 11px; font-weight: 900; top: 50%; left: 50%; transform: translate(-50%, -50%); }}

            /* REPORT COMPONENT */
            .report-display {{ flex-grow: 1; min-width: 0; display: flex; flex-direction: column; }}
            .wrap {{ width: 100%; background: #0B1220; border: 1px solid rgba(255,255,255,0.04); border-radius: 24px; padding: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); box-sizing: border-box; }}
            
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 22px; padding-bottom: 14px; border-bottom: 1px solid #1f2a37; }}
            .left-header {{ display: flex; align-items: center; gap: 14px; }}
            .logo {{ width: 56px; height: 56px; border-radius: 8px; background: #111827; }}
            .name {{ font-size: 32px; font-weight: 800; color: #fff; }}
            .sub {{ color: #94a3b8; font-size: 13px; margin-top: 2px; }}
            .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; min-width: 260px; }}
            .pill {{ font-size: 11px; padding: 6px 10px; border-radius: 10px; border: 1px solid #1f2a37; background: rgba(255,255,255,0.02); text-align: center; color: #cbd5e1; font-weight: 700; }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }}
            .card {{ background: linear-gradient(180deg, #0f172a, #0b1220); border: 1px solid #1f2a37; border-radius: 14px; padding: 16px; }}
            .card-title {{ font-size: 12px; letter-spacing: 2px; text-transform: uppercase; color: #939DAB; margin-bottom: 14px; font-weight: 800; }}
            .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
            
            .metric {{ padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.02); border: 1px solid #111827; }}
            .label-wrap {{ display: flex; justify-content: center; margin-bottom: 8px; }}
            .label {{ font-size: 12px; color: #cbd5e1; text-align: center; font-weight: 600; }}
            .bar {{ height: 4px; background: #111727; border-radius: 999px; overflow: hidden; margin-bottom: 10px; }}
            .fill {{ height: 100%; border-radius: 999px; }}
            .fill.elite {{ background: #22c55e; }}
            .fill.good {{ background: #60a5fa; }}
            .fill.avg {{ background: #94a3b8; }}
            .fill.concern {{ background: #f59e0b; }}
            .fill.poor {{ background: #ef4444; }}
            
            .bottom {{ display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; font-weight: 700; }}
            .left {{ display: flex; gap: 4px; }}
            .value {{ color: #e5e7eb; }}
            .tag {{ font-size: 9px; padding: 2px 6px; border-radius: 5px; border: 1px solid; text-transform: uppercase; font-weight: 800; }}
            .tag.elite {{ color: #22c55e; border-color: #22c55e; }}
            .tag.good {{ color: #60a5fa; border-color: #60a5fa; }}
            .tag.avg {{ color: #94a3b8; border-color: #94a3b8; }}
            .tag.concern {{ color: #f59e0b; border-color: #f59e0b; }}
            .tag.poor {{ color: #ef4444; border-color: #ef4444; }}
            
            .download {{ margin-top: 18px; text-align: center; }}
            .download button {{ padding: 10px 18px; border-radius: 8px; border: 1px solid #1f2a37; background: #0f172a; color: #e5e7eb; cursor: pointer; font-weight: 700; font-size: 13px; transition: background 0.2s; }}
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
                <a href="/stats" class="active">🏃 Spilleranalyse</a>
                <a href="#">🏆 Leaderboard</a>
            </nav>
        </aside>
        
        <main>
            <!-- INDSTILLINGER / KONTROLPANEL -->
            <div class="control-panel">
                <form id="statsForm" action="/stats" method="get">
                    <div class="form-group">
                        <label class="form-title">Spiller</label>
                        <select name="player" class="live-input">{p_opts}</select>
                    </div>
                    
                    <div class="form-group" style="flex-grow: 1;">
                        <label class="form-title">Vælg Kategorier</label>
                        <div class="cat-checkbox-list">
    """
    
    for cat in metrics.keys():
        checked = "checked" if cat in selected_cats else ""
        html += f"""
                            <label class="check-item">
                                <input type="checkbox" name="cats" value="{cat}" class="live-input" {checked}>
                                <span class="custom-box"></span>
                                {cat}
                            </label>
        """

    html += f"""
                        </div>
                    </div>
                </form>
            </div>

            <!-- RAPPORT INDHOLD (HØJRE SIDE) -->
            <div class="report-display">
                <div class="wrap" id="report">
                    <div class="header">
                        <div class="left-header">
                            {logo_html}
                            <div>
                                <div class="name">{player['Player Name']}</div>
                                <div class="sub">Percentile rank vs. league's positional peers</div>
                            </div>
                        </div>
                        <div class="meta">
                            <div class="pill">{player.get('League', '')}</div>
                            <div class="pill">{player.get('Pos.', '')}</div>
                            <div class="pill">{age}</div>
                            <div class="pill">{mins}</div>
                        </div>
                    </div>

                    <div class="grid">
    """

    # Generering af paneler baseret på valgte kategorier
    for cat in selected_cats:
        if cat in metrics:
            html += f"""
                        <div class="card">
                            <div class="card-title">{cat}</div>
                            <div class="metrics-grid">
            """
            for metric, label in metrics[cat]:
                val = player.get(metric, 0)
                pct = player.get(pr_col(metric), 0)
                html += metric_tile(label, val, pct, metric)
            html += "</div></div>"

    html += """
                    </div>
                </div>
                
                <div class="download">
                    <button onclick="downloadPNG()">Download som PNG</button>
                </div>
            </div>
        </main>

        <script src="https://cloudflare.com"></script>
        <script>
            // Automatisk indsendelse ved ændring i inputs eller flueben
            document.querySelectorAll('.live-input').forEach(input => {{
                input.addEventListener('change', () => {{
                    document.getElementById('statsForm').submit();
                }});
            }});

            function downloadPNG() {{
                const el = document.getElementById("report");
                html2canvas(el, {{
                    scale: 3,
                    backgroundColor: "#0B1220",
                    useCORS: true
                }}).then(canvas => {{
                    const link = document.createElement("a");
                    link.download = "scouting_report_" + "{player['Player Name']}".toLowerCase().replace(/ /g, "_") + ".png";
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@router.get("/stats", response_class=HTMLResponse)
def get_stats_page(
    player: str = Query(None),
    cats: list[str] = Query([])
):
    return vis_stats_page(player, cats)
