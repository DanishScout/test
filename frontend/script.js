// ==========================================================================
// # GLOBALE APP-VARIABLER
// ==========================================================================
let allMetrics = {};
let radarMetrics = {};
let nuvaerendeSpillerNavn = "report";

/* --------------------------------------------------------------------------
   # GLOBALE NAVIGATION FUNKTIONER
   # Styrer faneskift i topmenuen og aktiverer de korrekte diagramkald.
   -------------------------------------------------------------------------- */
function switchPage(pageId, e) {
    const targetPage = ['home', 'pizza', 'scatter', 'radar'].includes(pageId) ? pageId : 'placeholder';
    document.querySelectorAll('.nav-menu .nav-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.page-content').forEach(page => page.classList.remove('active'));

    if (e && e.target) {
        e.target.classList.add('active');
        if (targetPage === 'placeholder') {
            const moduleName = e.target.innerText;
            document.getElementById('placeholder-sidebar-title').innerText = moduleName + " Setup";
            document.getElementById('placeholder-main-title').innerText = moduleName + " Visualisering";
        }
    }
    document.getElementById(`page-${targetPage}`).classList.add('active');
    
    // Henter automatisk data, når brugeren skifter til en aktiv diagramside
    if (targetPage === 'pizza') { fetchPizza(); }
    if (targetPage === 'radar') { fetchRadar(); }
}

/* --------------------------------------------------------------------------
   # GLOBAL DATA INITIALISERING
   # Henter kun ægte data fra din app.py backend og fylder alle dropdown-menuer.
   -------------------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/initial-data')
        .then(res => {
            if (!res.ok) throw new Error(`Kunne ikke hente startdata: ${res.status}`);
            return res.json();
        })
        .then(data => {
            const playerSel = document.getElementById('playerSelect');
            const posSel = document.getElementById('posSelect');
            const radarP1Sel = document.getElementById('radarPlayer1Select');
            const radarP2Sel = document.getElementById('radarPlayer2Select');
            
            // Fyld Pizza dropdowns
            if (playerSel && posSel) {
                data.players.forEach(p => playerSel.add(new Option(p, p)));
                data.positions.forEach(pos => posSel.add(new Option(pos, pos)));
            }
            
            // Fyld Radar dropdowns med den samme komplette spillerliste
            if (radarP1Sel && radarP2Sel) {
                data.players.forEach(p => radarP1Sel.add(new Option(p, p)));
                data.players.forEach(p => radarP2Sel.add(new Option(p, p)));
                // Sætter Spiller 2 til indeks 1 som standard, så der vælges to forskellige spillere ved start
                if (radarP2Sel.options.length > 1) radarP2Sel.selectedIndex = 1;
            }
            
            allMetrics = data.metrics;
            // Fallback til standard metrics, hvis radar_metrics ikke er defineret særskilt i din backend endnu
            radarMetrics = data.radar_metrics || data.metrics;
            
            // Byg afkrydsningsmenuerne i dine dropdowns uafhængigt af hinanden
            buildMetricsCheckboxes();
            buildRadarMetricsCheckboxes();
        })
        .catch(err => {
            console.error("Kritisk fejl under initialisering:", err);
            const msg = '<p style="color: #ef4444; text-align: center;">Kunne ikke indlæse data fra serveren. Tjek om din backend (app.py) kører.</p>';
            if (document.getElementById('chart-container')) document.getElementById('chart-container').innerHTML = msg;
            if (document.getElementById('radar-chart-container')) document.getElementById('radar-chart-container').innerHTML = msg;
        });
});
/* --------------------------------------------------------------------------
   # PIZZA CHART EXCLUSIVE LOGIK
   # Styrer dropdown-synlighed, metric-valg og POST-kald for Pizza-diagrammet.
   -------------------------------------------------------------------------- */
function toggleMetricDropdown(e) { 
    e.stopPropagation(); 
    document.getElementById('metricsWrapper').classList.toggle('show'); 
}

window.addEventListener('click', () => { 
    if (document.getElementById('metricsWrapper')) {
        document.getElementById('metricsWrapper').classList.remove('show'); 
    }
});

// Forhindrer dropdown-menuen i at lukke sig, når der klikkes på selve elementerne
setTimeout(() => {
    const el = document.getElementById('metricsWrapper');
    if (el) el.addEventListener('click', (e) => { e.stopPropagation(); });
}, 100);

function buildMetricsCheckboxes() {
    const wrapper = document.getElementById('metricsWrapper');
    if (!wrapper) return;
    wrapper.innerHTML = "";

    for (const [category, metricsObj] of Object.entries(allMetrics)) {
        const catLabel = document.createElement('div');
        catLabel.className = "metric-group-title";
        catLabel.innerText = category;
        wrapper.appendChild(catLabel);

        let isFirstInMetricCategory = true;
        for (const [key, displayName] of Object.entries(metricsObj)) {
            const item = document.createElement('div');
            item.className = "checkbox-item";
            const isCheckedStr = isFirstInMetricCategory ? "checked" : "";
            
            item.innerHTML = `
                <input type="checkbox" name="pizzaMetrics" value="${key}" id="chk-${key}" ${isCheckedStr} onchange="updateDropdownStatus(); fetchPizza();">
                <label for="chk-${key}" style="flex:1; cursor:pointer;">${displayName.replace('\n', ' ')}</label>
            `;
            wrapper.appendChild(item);
            isFirstInMetricCategory = false; 
        }
    }
    updateDropdownStatus();
    fetchPizza(); 
}

function updateDropdownStatus() {
    const checkedBoxes = document.querySelectorAll('input[name="pizzaMetrics"]:checked');
    const trigger = document.getElementById('metricDropdownTrigger');
    if (trigger) {
        trigger.innerText = checkedBoxes.length === 0 ? "Vælg metrics..." : `${checkedBoxes.length} metrics valgt`;
    }
}

function fetchPizza() {
    const playerSelectEl = document.getElementById('playerSelect');
    const posSelectEl = document.getElementById('posSelect');
    const colorPickerEl = document.getElementById('colorPicker');

    if (!playerSelectEl || !posSelectEl || !colorPickerEl) return;

    const player = playerSelectEl.value || "";
    const position = posSelectEl.value || "";
    const color = colorPickerEl.value;
    const checkedBoxes = document.querySelectorAll('input[name="pizzaMetrics"]:checked');
    const selectedMetrics = Array.from(checkedBoxes).map(cb => cb.value);

    if (selectedMetrics.length < 3) {
        document.getElementById('chart-container').innerHTML = '<p style="color: #64748b; text-align: center;">Vælg mindst 3 metrics i dropdown-menuen for at bygge dit pizza-diagram...</p>';
        return;
    }

    if (!player || !position) return;

    fetch('/api/pizza/generate-pizza', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player, position, color, metrics: selectedMetrics })
    })
    .then(res => res.json())
    .then(data => {
        if (data.html) {
            document.getElementById('chart-container').innerHTML = data.html;
            nuvaerendeSpillerNavn = data.player_name || "report";
            
            // SIMPELT: Tvinger dropdown-menuen på skærmen til at matche spillerens sande position
            if (data.position) {
                document.getElementById('posSelect').value = data.position;
            }
        }
    });

}

function downloadPNG() {
    const el = document.getElementById("chart-only");
    if (!el) return;
    
    const title = document.querySelector('.p-nm'); 
    if (title) { title.style.webkitTextFillColor = '#fff'; title.style.color = '#fff'; } 
    
    html2canvas(el, { scale: 4, backgroundColor: "#0B1220", useCORS: true, logging: false }).then(canvas => { 
        if (title) title.style.webkitTextFillColor = '#fff'; 
        const link = document.createElement("a"); 
        link.download = "pizza_" + nuvaerendeSpillerNavn.toLowerCase().replace(/ /g, "_") + ".png"; 
        link.href = canvas.toDataURL("image/png"); 
        link.click(); 
    }).catch(e => console.error(e)); 
}
/* --------------------------------------------------------------------------
   # RADAR CHART EXCLUSIVE LOGIK
   # Styrer dropdown-synlighed, metric-valg og POST-kald for to-spillers radaren.
   -------------------------------------------------------------------------- */
function toggleRadarMetricDropdown(e) { 
    e.stopPropagation(); 
    document.getElementById('radarMetricsWrapper').classList.toggle('show'); 
}

window.addEventListener('click', () => { 
    if (document.getElementById('radarMetricsWrapper')) {
        document.getElementById('radarMetricsWrapper').classList.remove('show'); 
    }
});

// Forhindrer dropdown-menuen i at lukke sig, når der klikkes på selve elementerne
setTimeout(() => {
    const el = document.getElementById('radarMetricsWrapper');
    if (el) el.addEventListener('click', (e) => { e.stopPropagation(); });
}, 100);

function buildRadarMetricsCheckboxes() {
    const wrapper = document.getElementById('radarMetricsWrapper');
    if (!wrapper) return;
    wrapper.innerHTML = "";

    for (const [category, metricsObj] of Object.entries(radarMetrics)) {
        const catLabel = document.createElement('div');
        catLabel.className = "metric-group-title";
        catLabel.innerText = category;
        wrapper.appendChild(catLabel);

        let isFirstInMetricCategory = true;
        for (const [key, displayName] of Object.entries(metricsObj)) {
            const item = document.createElement('div');
            item.className = "checkbox-item";
            const isCheckedStr = isFirstInMetricCategory ? "checked" : "";
            
            item.innerHTML = `
                <input type="checkbox" name="radarMetrics" value="${key}" id="chk-radar-${key}" ${isCheckedStr} onchange="updateRadarDropdownStatus(); fetchRadar();">
                <label for="chk-radar-${key}" style="flex:1; cursor:pointer;">${displayName.replace('\n', ' ')}</label>
            `;
            wrapper.appendChild(item);
            isFirstInMetricCategory = false; 
        }
    }
    updateRadarDropdownStatus();
    fetchRadar(); 
}

function updateRadarDropdownStatus() {
    const checkedBoxes = document.querySelectorAll('input[name="radarMetrics"]:checked');
    const trigger = document.getElementById('radarMetricDropdownTrigger');
    if (trigger) {
        trigger.innerText = checkedBoxes.length === 0 ? "Vælg radar metrics..." : `${checkedBoxes.length} metrics valgt`;
    }
}

function fetchRadar() {
    const p1Sel = document.getElementById('radarPlayer1Select');
    const p2Sel = document.getElementById('radarPlayer2Select');

    if (!p1Sel || !p2Sel) return;

    const player1 = p1Sel.value || "";
    const player2 = p2Sel.value || "";
    const checkedBoxes = document.querySelectorAll('input[name="radarMetrics"]:checked');
    const selectedMetrics = Array.from(checkedBoxes).map(cb => cb.value);

    if (selectedMetrics.length < 3) {
        document.getElementById('radar-chart-container').innerHTML = '<p style="color: #64748b; text-align: center;">Vælg mindst 3 metrics i dropdown-menuen for at bygge dit radardiagram...</p>';
        return;
    }

    if (!player1 || !player2) return;

    fetch('/api/radar/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player1, player2, metrics: selectedMetrics })
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP fejlstatus: ${res.status}`);
        return res.json();
    })
    .then(data => {
        if (data.html) {
            document.getElementById('radar-chart-container').innerHTML = data.html;
        }
    })
    .catch(e => {
        console.error("Fejl under generering af radardiagram:", e);
        document.getElementById('radar-chart-container').innerHTML = '<p style="color: #ef4444; text-align: center;">Kunne ikke hente radardiagram. Tjek din serverforbindelse.</p>';
    });
}

function downloadRadarPNG() {
    const el = document.getElementById("chart-only");
    if (!el) return;
    
    html2canvas(el, { scale: 4, backgroundColor: "#0B1220", useCORS: true, logging: false }).then(canvas => { 
        const link = document.createElement("a"); 
        link.download = "radar_comparison.png"; 
        link.href = canvas.toDataURL("image/png"); 
        link.click(); 
    }).catch(e => console.error("Eksportfejl på radar:", e));
}