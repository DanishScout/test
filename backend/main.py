from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
# Her importerer vi din nye pizza-fil fra routers-mappen
from routers import pizza

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# HER FORBINDER VI LANDINGSSIDEN TIL DIN PIZZA-FIL:
app.include_router(pizza.router)

@app.get("/", response_class=HTMLResponse)
def landing_page():
    html_content = """
    <!DOCTYPE html>
    <html lang="da">
    <head>
        <meta charset="UTF-8">
        <title>PER 90 Dashboard</title>
        <link href="https://googleapis.com" rel="stylesheet">
        <style>
            body {
                margin: 0;
                font-family: 'Gabarito', sans-serif;
                background-color: #070B13;
                color: #e5e7eb;
                display: flex;
                min-height: 100vh;
            }
            
            /* SIDEBAR STYLING */
            aside {
                width: 260px;
                background: #0B1220;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                padding: 30px 20px;
                display: flex;
                flex-direction: column;
                box-sizing: border-box;
            }
            .logo {
                font-size: 22px;
                font-weight: 900;
                color: #00FFD5;
                letter-spacing: -0.5px;
                margin-bottom: 40px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            nav {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            nav a {
                color: #94a3b8;
                text-decoration: none;
                padding: 12px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                transition: all 0.2s;
            }
            nav a:hover, nav a.active {
                background: rgba(0, 255, 213, 0.1);
                color: #00FFD5;
            }
            
            /* MAIN CONTENT STYLING */
            main {
                flex-grow: 1;
                padding: 50px;
                box-sizing: border-box;
                max-width: 1000px;
            }
            h1 {
                font-size: 36px;
                font-weight: 900;
                color: #fff;
                margin-top: 0;
                margin-bottom: 10px;
                letter-spacing: -1px;
            }
            p.subtitle {
                color: #64748b;
                font-size: 16px;
                margin-bottom: 40px;
            }
            
            /* INFOBOKSE STYLING */
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .card {
                background: #0B1220;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            }
            .card h3 {
                margin-top: 0;
                color: #fff;
                font-size: 18px;
                margin-bottom: 12px;
            }
            .card p {
                color: #94a3b8;
                font-size: 14px;
                line-height: 1.6;
                margin: 0;
            }
            .status-tag {
                display: inline-block;
                padding: 4px 8px;
                background: rgba(0, 255, 213, 0.1);
                color: #00FFD5;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>

        <!-- SIDEBAR -->
        <aside>
            <div class="logo">⚽ PER 90</div>
            <nav>
                <a href="/" class="active">🏠 Startside</a>
                <a href="/pizza">📊 Pizza Diagram</a>
                <a href="#">🏆 Leaderboard</a>
                <a href="#">🏃 Spilleranalyse</a>
            </nav>
        </aside>

        <!-- VELKOMST / INDHOLD -->
        <main>
            <h1>Velkommen til PER 90</h1>
            <p class="subtitle">Din personlige platform til avanceret fodbold- og begivenhedsdata.</p>
            
            <div class="grid">
                <div class="card">
                    <h3>📊 Indlæste Datasæt</h3>
                    <p>Applikationen er forbundet lokalt til dine CSV-datafiler, som dækker statistikker for både den danske Superliga (den1.csv) og den tyrkiske Süper Lig (tur1.csv).</p>
                    <div class="status-tag">STATUS: FORBUNDET</div>
                </div>
                
                <div class="card">
                    <h3>⚡ Avanceret Metrik</h3>
                    <p>Brug menuen i venstre side til at navigere mellem dine visualiseringer. Vores Pizza Diagram udregner automatisk percentiler på tværs af specifikke ligaer og positioner.</p>
                </div>
            </div>

            <div class="card" style="max-width: 100%;">
                <h3>📌 Om Platformen</h3>
                <p>Dette web-interface er bygget oven på en lynhurtig Python FastAPI-motor og fjerner alle de tidligere begrænsninger fra Streamlit. Det sikrer dig fuld kontrol over designet, hurtigere indlæsningstider og mulighed for udbygning med ægte frontend-rammeværktøjer i fremtiden.</p>
            </div>
        </main>

    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
