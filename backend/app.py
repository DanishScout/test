import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
# Vi importerer Pydantic-modellen og routeren fra dit nye modul
from backend.routers.pizza import router as pizza_router, PizzaRequest

app = FastAPI(title="PER 90 - Fodbold Data App")

# --- KONFIGURATION & DATASTIER ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV1_PATH = os.path.join(BASE_DIR, 'den1.csv')
CSV2_PATH = os.path.join(BASE_DIR, 'den2.csv')
FRONTEND_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend', 'index.html'))

# Mount statiske filer (frontend-mappen)
app.mount("/static", StaticFiles(directory=os.path.dirname(FRONTEND_PATH)), name="static")

# --- GLOBAL METRICS KONFIGURATION ---
PIZZA_METRICS = {
    "Shooting": {"total goals_p90": "Goals", "xG_p90": "npxG", "total ontarget attempt_p90": "Shots\nOn Target"},
    "Passing": {"total assists_p90": "Assists", "xA_p90": "xA", "total att assist_p90": "Key Passes", "xT_pass_p90": "xT via\nLive Passes", "progressive_passes_p90": "Progressive\nPasses"},
    "Possession": {"total won contest_p90": "Successful\nDribbles", "total contest_p90": "Dribble\nAttempts", "dribble_success_pct_p90": "Dribble\nSuccess %"},
    "Defending": {"tackle_success_pct_p90": "Tackles\nWon %", "aerial_success_pct_p90": "Aerials\nWon %"}
}


def load_data():
    """ Indlæser og kombinerer automatisk dine rå CSV-liga-datafiler. """
    if not (os.path.exists(CSV1_PATH) and os.path.exists(CSV2_PATH)):
        raise HTTPException(500, "En eller begge CSV-filer mangler i backend mappen.")
    return pd.concat([pd.read_csv(CSV1_PATH), pd.read_csv(CSV2_PATH)], ignore_index=True)


# --- CORE ENDPOINTS ---
@app.get("/", response_class=HTMLResponse)
def get_index():
    """ Serverer din index.html fil direkte til browseren. """
    if not os.path.exists(FRONTEND_PATH):
        raise HTTPException(404, "index.html blev ikke fundet.")
    with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/initial-data")
def get_initial_data():
    """ Henter startdata til globale dropdown-menuer på frontend. """
    try:
        df = load_data()
        pos_col = 'Pos.' if 'Pos.' in df.columns else ('Position' if 'Position' in df.columns else df.columns)
        return {
            "players": sorted(df['Player Name'].dropna().unique().tolist()),
            "positions": sorted(df[pos_col].dropna().unique().tolist()),
            "metrics": PIZZA_METRICS
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# --- ROUTER INTEGRATION & WRAPPER ---
@app.post("/api/pizza/generate-pizza")
def wrap_generate_pizza(req: PizzaRequest):
    """ 
    Overskriver router-stien lokalt for at føre de globale funktioner 
    og konfigurationer sikkert ned i dit pizza-modul uden importfejl.
    """
    from routers.pizza import generate_pizza as run_pizza
    return run_pizza(req, PIZZA_METRICS, load_data)


# Vi inkluderer routeren formelt for at registrere tags og swagger-dokumentation
app.include_router(pizza_router)
