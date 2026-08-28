import math, requests, base64
from io import BytesIO
from PIL import Image
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

def vis_pizza_diagram(player: str, pos: str, shoot: list[str], p_ass: list[str], poss: list[str], defend: list[str], color: str):
    try:
        # 1. Indlæs og kombiner dine to CSV-filer
        df1, df2 = pd.read_csv('den1.csv'), pd.read_csv('tur1.csv')
        data = pd.concat([df1, df2], ignore_index=True)
        
        available_metrics = {
            "Shooting": {"total goals_p90": "Goals", "xG_p90": "npxG"},
            "Passing": {"total assists_p90": "Assists", "xA_p90": "xA"},
            "Possession": {"total won contest_p90": "Successful Dribbles", "total contest_p90": "Dribble Attempts"},
            "Defending": {"tackle_success_pct_p90": "Tackles Won %", "aerial_success_pct_p90": "Aerials Won %"},
        }
        METRICS = {k: v for cat in available_metrics.values() for k, v in cat.items()}
        
        p_list = sorted(data['Player Name'].dropna().unique())
        pos_column = 'Pos.' if 'Pos.' in data.columns else ('Position' if 'Position' in data.columns else data.columns)
        pos_list = sorted(data[pos_column].dropna().unique())
        
        if not player and p_list: player = p_list[0]
        p_row = data[data['Player Name'] == player].iloc[0]
        if not pos: pos = p_row[pos_column]
        
        # Saml alle valgte metrics fra tjekboksene
        sel_keys = shoot + p_ass + poss + defend
        if not sel_keys:
            sel_keys = ["total goals_p90", "total assists_p90", "total won contest_p90", "tackle_success_pct_p90"]
            shoot, p_ass, poss, defend = ["total goals_p90"], ["total assists_p90"], ["total won contest_p90"], ["tackle_success_pct_p90"]

        # 2. Filtrer sammenligningsgruppen dynamisk
        comp_df = data[(data['League'] == p_row['League']) & (data[pos_column] == pos)].copy()
        if player not in comp_df['Player Name'].values:
            comp_df = pd.concat([comp_df, data[data['Player Name'] == player]], ignore_index=True)
            
        # 3. Beregn percentiler for ALLE valgte metrics
        for k in sel_keys:
            comp_df[f'{k}_pct'] = comp_df[k].rank(pct=True, method='max') * 100.0
            
        r1 = comp_df[comp_df['Player Name'] == player].iloc[0]
        
        # 4. Hent holdets logo via Opta API
        try:
            logo_url = f"https://opta.net{r1['contestantId']}"
            img_b = base64.b64encode(BytesIO(requests.get(logo_url, timeout=3).content).getvalue()).decode()
            logo_html = f'<img src="data:image/png;base64,{img_b}" style="width:22px;height:22px;object-fit:contain;"/>'
        except:
            logo_html = ""
        
        # 5. Avanceret Matematik til SVG Pizza-diagrammet
        CX, CY, MAX_R, N = 355, 252, 200, len(sel_keys)
        pizza_slices, grid_lines, labels = "", "", ""
        width = 360.0 / N
        
        for i, k in enumerate(sel_keys):
            start_ang, end_ang = i * width, (i + 1) * width
            mid_ang = start_ang + (width / 2.0)
            val = max(0.0, min(float(r1.get(f'{k}_pct', 0)), 100.0))
            r = (val / 100.0) * MAX_R
            
            r_start, r_end = math.radians(start_ang - 90), math.radians(end_ang - 90)
            if r > 0:
                pizza_slices += f'<path d="M {CX} {CY} L {CX + r * math.cos(r_start)} {CY + r * math.sin(r_start)} A {r} {r} 0 0 1 {CX + r * math.cos(r_end)} {CY + r * math.sin(r_end)} Z" class="slice-b" />\n'
            grid_lines += f'<line class="grid-line" x1="{CX}" y1="{CY}" x2="{CX + MAX_R * math.cos(r_start)}" y2="{CY + MAX_R * math.sin(r_start)}" />\n'
            
            r_mid = math.radians(mid_ang - 90)
            tx, ty = CX + (MAX_R + 42) * math.cos(r_mid), CY + (MAX_R + 42) * math.sin(r_mid)
            m_lines = METRICS[k].split('\n')
            tspan_html = "".join([f'<tspan x="0" dy="{"-4" if idx==0 else "1.1em"}">{line}</tspan>' for idx, line in enumerate(m_lines)])
            labels += f'<g transform="translate({tx:.1f},{ty:.1f})"><text class="ax-lbl" text-anchor="middle">{tspan_html}</text><g transform="translate(-13, {20 if len(m_lines) > 1 else 8})"><rect class="bg-b" width="26" height="16" rx="4"/><text class="tx-b" x="13" y="12" text-anchor="middle">{int(val)}</text></g></g>\n'

        # 6. Dynamisk dropdown HTML-generering for spillere og positioner
        p_opts = "".join([f'<option value="{p}" {"selected" if p == player else ""}>{p}</option>' for p in p_list])
        pos_opts = "".join([f'<option value="{x}" {"selected" if x == pos else ""}>{x}</option>' for x in pos_list])

        # Generering af de nye tilpassede dropdowns med tjekbokse
        def lav_multiselect(kategori: str, felt_navn: str, valgte_verdier: list):
            html_indhold = f"""
            <div class="custom-multiselect">
                <div class="select-box" onclick="toggleDropdown('{felt_navn}')">
                    <span id="label-{felt_navn}">Vælg metrics ({len(valgte_verdier)})</span>
                    <span class="arrow">▼</span>
                </div>
                <div class="checkboxes" id="opts-{felt_navn}">
            """
            for k, v in available_metrics[kategori].items():
                checked = "checked" if k in valgte_verdier else ""
                html_indhold += f"""
                    <label class="check-item">
                        <input type="checkbox" name="{felt_navn}" value="{k}" class="live-input" {checked}>
                        <span class="custom-box"></span>
                        {v}
                    </label>
                """
            html_indhold += "</div></div>"
            return html_indhold

        shoot_html = lav_multiselect("Shooting", "shoot", shoot)
        pass_html = lav_multiselect("Passing", "p_ass", p_ass)
        poss_html = lav_multiselect("Possession", "poss", poss)
        def_html = lav_multiselect("Defending", "defend", defend)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PER 90 - Live Pizza Diagram</title>
            <link href="https://googleapis.com" rel="stylesheet">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <style>
                body {{ margin: 0; font-family: 'Gabarito', sans-serif; background-color: #070B13; color: #e5e7eb; display: flex; min-height: 100vh; max-width: 100vw; overflow-x: hidden; }}
                aside {{ width: 260px; min-width: 260px; background: #0B1220; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 30px 20px; display: flex; flex-direction: column; box-sizing: border-box; flex-shrink: 0; }}
                .logo {{ font-size: 22px; font-weight: 900; color: #00FFD5; margin-bottom: 40px; }}
                nav {{ display: flex; flex-direction: column; gap: 10px; }}
                nav a {{ color: #94a3b8; text-decoration: none; padding: 12px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
                nav a:hover, nav a.active {{ background: rgba(0, 255, 213, 0.1); color: #00FFD5; }}
                main {{
                    flex-grow: 1;
                    padding: 40px;
                    display: flex; 
                    gap: 30px;
                    /* ÆNDRET FRA 'start' TIL 'stretch' - dette tvinger boksene til samme højde */
                    align-items: stretch; 
                    width: calc(100% - 260px);
                    max-width: 100%;
                    box-sizing: border-box;
                    }}

                /* KONTROLPANEL (VENSTRE SIDE INDE I MAIN) */
                .control-panel {{
                    width: 250px;
                    min-width: 250px;
                    background: #0B1220; 
                    border: 1px solid rgba(255, 255, 255, 0.04); 
                    padding: 22px; 
                    border-radius: 16px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5); 
                    box-sizing: border-box;
                    
                    /* TILFØJ DISSE TO LINJER: */
                    display: flex;
                    flex-direction: column;
                }}

                .form-group {{ margin-bottom: 16px; position: relative; }}
                label.form-title {{ display: block; font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }}
                
                select, input[type="color"] {{ width: 100%; background: #070B13; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; color: #fff; font-size: 13px; font-family: inherit; box-sizing: border-box; outline: none; transition: border 0.2s; }}
                select:focus {{ border: 1px solid #00FFD5; }}
                
                /* DE NYE DROPDOWN MENUER MED FLUEBEN */
                .custom-multiselect {{ position: relative; width: 100%; }}
                .select-box {{ display: flex; justify-content: space-between; align-items: center; background: #070B13; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px; color: #fff; font-size: 13px; cursor: pointer; user-select: none; box-sizing: border-box; }}
                .select-box:hover {{ border-color: rgba(0, 255, 213, 0.5); }}
                .select-box .arrow {{ font-size: 9px; color: #64748b; transition: transform 0.2s; }}
                
                .checkboxes {{ display: none; position: absolute; top: 100%; left: 0; right: 0; background: #070B13; border: 1px solid rgba(0, 255, 213, 0.3); border-top: none; border-radius: 0 0 8px 8px; max-height: 180px; overflow-y: auto; z-index: 10; padding: 4px; box-shadow: 0 10px 20px rgba(0,0,0,0.4); }}
                .custom-multiselect.open .checkboxes {{ display: block; }}
                .custom-multiselect.open .select-box {{ border-radius: 8px 8px 0 0; border-color: #00FFD5; }}
                .custom-multiselect.open .arrow {{ transform: rotate(180deg); color: #00FFD5; }}
                
                .check-item {{ display: flex; align-items: center; padding: 8px 10px; color: #e5e7eb; font-size: 13px; cursor: pointer; border-radius: 5px; margin-bottom: 2px; transition: background 0.15s; user-select: none; }}
                .check-item:hover {{ background: rgba(255, 255, 255, 0.04); }}
                .check-item input {{ display: none; }}
                
                /* DE VISUELLE FLUEBENSBOKSE */
                .custom-box {{ width: 15px; height: 15px; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; margin-right: 10px; display: inline-block; position: relative; background: #0B1220; flex-shrink: 0; }}
                .check-item input:checked + .custom-box {{ background: #00FFD5; border-color: #00FFD5; }}
                .check-item input:checked + .custom-box::after {{ content: '✓'; position: absolute; color: #070B13; font-size: 11px; font-weight: 900; top: 50%; left: 50%; transform: translate(-50%, -50%); }}
                
                .chart-container {{ padding: 25px; border-radius: 24px; background: #0B1220; border: 1px solid rgba(0,240,255,.08); display: flex; flex-direction: column; align-items: center; width: 100%; max-width: 680px; box-sizing: border-box; box-shadow: 0 20px 50px rgba(0,0,0,0.6); min-width: 0; }}
                .header-card {{ width: 100%; max-width: 100%; margin-bottom: 20px; border: 1px solid rgba(0, 240, 255, 0.08); border-radius: 16px; padding: 15px 20px; background: rgba(7, 11, 19, 0.5); box-sizing: border-box; }}
                .p-nm {{ font-size: 24px; font-weight: 900; margin: 0 0 5px; text-transform: uppercase; color: #fff; letter-spacing: -0.5px; }}
                .p-sub-bar {{ display: flex; align-items: center; gap: 12px; font-size: 12px; color: #94a3b8; font-weight: 700; }}
                
                svg {{ display: block; margin: auto; overflow: visible; width: 100%; height: auto; max-width: 710px; }}
                .grid-circle {{ fill: none; stroke: rgba(255,255,255,.08); }}
                .grid-line {{ stroke: rgba(255,255,255,.06); }}
                .ax-lbl {{ font-size: 11px; fill: #94a3b8; font-weight: 700; }}
                .slice-b {{ fill: {color}1a; stroke: {color}; stroke-width: 1.75; }}
                .bg-b {{ fill: #0f172a; stroke: {color}cc; }}
                .tx-b {{ fill: {color}; font-size: 11px; font-weight: 700; }}
                .download button {{ padding: 9px 16px; border-radius: 6px; border: 1px solid #1f2a37; background: #0B1220; color: #e5e7eb; cursor: pointer; font-size: 12px; font-weight: 700; margin-top: 15px; transition: background 0.2s; }}
                .download button:hover {{ background: #111a2e; }}
            </style>
        </head>
        <body>
            <aside>
                <div class="logo">⚽ PER 90</div>
                <nav>
                    <a href="/">🏠 Startside</a>
                    <a href="/pizza" class="active">📊 Pizza Diagram</a>
                    <a href="#">🏆 Leaderboard</a>
                    <a href="#">🏃 Spilleranalyse</a>
                </nav>
            </aside>
            <main>
                <div class="control-panel">
                    <form id="pizzaForm" action="/pizza" method="get">
                        <div class="form-group">
                            <label class="form-title">Vælg Spiller</label>
                            <select name="player" class="live-input">{p_opts}</select>
                        </div>
                        <div class="form-group">
                            <label class="form-title">Sammenlignings-position</label>
                            <select name="pos" class="live-input">{pos_opts}</select>
                        </div>
                        <div class="form-group">
                            <label class="form-title">Shooting Metrics</label>
                            {shoot_html}
                        </div>
                        <div class="form-group">
                            <label class="form-title">Passing Metrics</label>
                            {pass_html}
                        </div>

                        <div class="form-group">
                            <label class="form-title">Possession Metrics</label>
                            {poss_html}
                        </div>
                        <div class="form-group">
                            <label class="form-title">Defending Metrics</label>
                            {def_html}
                        </div>
                        <div class="form-group">
                            <label class="form-title">Diagram Farve</label>
                            <input type="color" name="color" class="live-input" value="{color}">
                        </div>
                    </form>
                </div>

                <div style="display:flex; flex-direction:column; align-items:center; flex-grow:1; min-width: 0; width: 100%;">
                    <div class="chart-container" id="chart-only">
                        <div class="header-card">
                            <h2 class="p-nm">{player}</h2>
                            <div class="p-sub-bar">
                                <div style="display:flex; align-items:center; gap:6px;">{logo_html}<span>{p_row['League']}</span></div>
                                <span>|</span><span>{pos}</span><span>|</span><span>{int(r1.get('total mins played', 0))} MIN.</span>
                            </div>
                        </div>
                        <svg width="710" height="570" viewBox="0 0 710 570">
                            <circle cx="{CX}" cy="{CY}" r="50" class="grid-circle" />
                            <circle cx="{CX}" cy="{CY}" r="100" class="grid-circle" />
                            <circle cx="{CX}" cy="{CY}" r="150" class="grid-circle" />
                            <circle cx="{CX}" cy="{CY}" r="{MAX_R}" class="grid-circle" />
                            {pizza_slices} {grid_lines} {labels}
                        </svg>
                    </div>
                    <div class="download"><button onclick="downloadPNG()">Download som PNG</button></div>
                </div>
            </main>
            
            <script>
            // Åben og luk dropdown-menuerne når der klikkes på dem
            function toggleDropdown(feltNavn) {{
                const el = document.getElementById('opts-' + feltNavn).parentElement;
                const isOpen = el.classList.contains('open');
                
                // Luk alle andre dropdowns først, så de ikke overlapper
                document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                    dropdown.classList.remove('open');
                }});
                
                if (!isOpen) {{
                    el.classList.add('open');
                }}
            }}

            // Luk dropdowns hvis brugeren klikker uden for menuerne
            document.addEventListener('click', function(e) {{
                if (!e.target.closest('.custom-multiselect')) {{
                    document.querySelectorAll('.custom-multiselect').forEach(dropdown => {{
                        dropdown.classList.remove('open');
                    }});
                }}
            }});

            // Auto-update: Indsend formularen når et input ændres eller der sættes/fjernes flueben
            document.querySelectorAll('.live-input').forEach(input => {{
                input.addEventListener('change', () => {{
                    document.getElementById('pizzaForm').submit();
                }});
            }});

            function downloadPNG() {{
                html2canvas(document.getElementById("chart-only"), {{ scale: 4, backgroundColor: "#0B1220", useCORS: true }}).then(canvas => {{
                    const link = document.createElement("a"); 
                    link.download = "report_" + "{player}".toLowerCase().replace(/ /g, "_") + ".png";
                    link.href = canvas.toDataURL("image/png"); 
                    link.click();
                }});
            }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<html><body style='background:#070B13; color:white; padding:40px;'><h2>Fejl: {str(e)}</h2></body></html>", status_code=500)

@router.get("/pizza", response_class=HTMLResponse)
def get_pizza_page(
    player: str = Query(None), 
    pos: str = Query(None), 
    shoot: list[str] = Query([]), 
    p_ass: list[str] = Query([]), 
    poss: list[str] = Query([]), 
    defend: list[str] = Query([]), 
    color: str = "#00FFD5"
):
    return vis_pizza_diagram(player, pos, shoot, p_ass, poss, defend, color)


       
