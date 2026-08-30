import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 📁 VIGTIGT: Henter diagram-generatoren og filter-funktionen fra din pizza.py
from backend.routers.pizza import vis_pizza_diagram, hent_filtre

app = FastAPI(title="PER 90 // CORE ENGINE API")

# CORS tillader din HTML-frontend at hente data fejlfrit under lokal test
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📡 ENDPOINT: Sender listen af unikke spillere og positioner fra din CSV direkte til frontenden
@app.get("/api/pizza/filters")
def pizza_filter_api():
    return hent_filtre()

# 📡 ENDPOINT: Modtager parametre og spytter det færdige SVG/HTML-diagram ud som JSON
@app.get("/api/pizza")
def pizza_api(
    player: str = Query(None), 
    pos: str = Query(None), 
    shoot: list[str] = Query([]), 
    p_ass: list[str] = Query([]), 
    poss: list[str] = Query([]), 
    defend: list[str] = Query([]), 
    color: str = "#00FFD5"
):
    # Sender parametrene direkte videre til din datalogi i pizza.py
    data = vis_pizza_diagram(player, pos, shoot, p_ass, poss, defend, color)
    return data

# 🌐 FRONTEND: Rettet til at servere direkte fra test/frontend i stedet for backend/frontend
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

    @app.get("/")
    def laes_indeks():
        return FileResponse("frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    # host 0.0.0.0 og port 8000 sikrer fuld kompatibilitet lokalt og på Render
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
