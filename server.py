import sqlite3
import re
import uvicorn
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- BASE DE CONHECIMENTO MÉDICO (AuraMed Core) ---
MEDICAL_KNOWLEDGE = {
    "Interações": [
        ("Farmacologia", "Varfarina + AAS", "Risco altíssimo de hemorragia. Evitar associação ou monitorar INR rigidamente.", 10),
        ("Farmacologia", "Sildenafila + Nitratos", "Risco de hipotensão severa e óbito. Associação contraindicada.", 10),
        ("Farmacologia", "Digoxina + Furosemida", "Risco de toxicidade digitálica por hipocalemia.", 8)
    ],
    "Protocolos": [
        ("Emergência", "Protocolo de Sepse", "Febre + Hipotensão + Taquicardia: Iniciar protocolo de sepse (Lactato, Hemoculturas, Antibiótico na 1ª hora).", 10),
        ("Cardiologia", "IAM com Supra", "Tempo porta-balão deve ser inferior a 90 minutos. Iniciar AAS + Clopidogrel imediatamente.", 10),
        ("Neurologia", "AVC Isquêmico", "Janela de trombólise é de até 4.5 horas do início dos sintomas. Realizar TC de crânio urgente.", 10)
    ],
    "Diagnóstico": [
        ("Sintomas", "Dengue", "Febre alta, dor retro-orbital, mialgia. Alerta para sinais de alarme: dor abdominal intensa, vômitos persistentes.", 8),
        ("Sintomas", "Diabetes Mellitus", "Poliúria, polidipsia, perda de peso. Glicemia de jejum > 126 mg/dL em duas ocasiões.", 7),
        ("Sintomas", "Apendicite", "Dor que inicia na região periumbilical e migra para fossa ilíaca direita. Sinal de Blumberg positivo.", 9)
    ],
    "Cuidados de Enfermagem": [
        ("Procedimento", "Sonda Vesical", "Manter bolsa coletora abaixo do nível da bexiga para evitar infecção urinária retrógrada.", 8),
        ("Procedimento", "Acesso Central", "Monitorar sinais de flogose e curativo estéril. Troca conforme protocolo da CCIH.", 7)
    ]
}

class AuraMedBrain:
    def __init__(self):
        self.db = 'auramed_memory.db'
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS clinical_knowledge 
                          (id INTEGER PRIMARY KEY, category TEXT, topic TEXT, content TEXT, priority INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS clinical_logs 
                          (id INTEGER PRIMARY KEY, ts TEXT, case_input TEXT, analysis TEXT, risk_level TEXT)''')
        
        cursor.execute("SELECT count(*) FROM clinical_knowledge")
        if cursor.fetchone()[0] == 0:
            for cat, items in MEDICAL_KNOWLEDGE.items():
                for topic, sub, content, priority in items:
                    cursor.execute("INSERT INTO clinical_knowledge (category, topic, content, priority) VALUES (?,?,?,?)",
                                   (cat, topic, content, priority))
        conn.commit()
        conn.close()

    def clinical_analysis(self, text):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT category, topic, content, priority FROM clinical_knowledge")
        knowledge = cursor.fetchall()
        
        found_insights = []
        text_low = text.lower()
        
        for cat, topic, content, priority in knowledge:
            # Busca por palavras-chave médicas
            keywords = set(re.findall(r'\w+', content.lower() + " " + topic.lower()))
            input_words = set(re.findall(r'\w+', text_low))
            matches = keywords.intersection(input_words)
            
            if len(matches) >= 2:
                found_insights.append({
                    "category": cat,
                    "topic": topic,
                    "insight": content,
                    "priority": "Urgente" if priority >= 9 else "Monitorar"
                })
        conn.close()
        return found_insights

brain = AuraMedBrain()

class CaseData(BaseModel):
    text: str

@app.post("/analyze_case")
async def analyze_case(data: CaseData):
    results = brain.clinical_analysis(data.text)
    risk = "ALTO" if any(r['priority'] == "Urgente" for r in results) else "Normal"
    
    conn = sqlite3.connect('auramed_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clinical_logs (ts, case_input, analysis, risk_level) VALUES (?,?,?,?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data.text, json.dumps(results), risk))
    conn.commit()
    conn.close()
    return {"analysis": results, "risk": risk}

@app.get("/hospital_dashboard")
async def get_dashboard():
    conn = sqlite3.connect('auramed_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clinical_logs ORDER BY id DESC LIMIT 20")
    logs = cursor.fetchall()
    conn.close()
    
    return {
        "recent_cases": [{"id": r[0], "ts": r[1], "input": r[2], "analysis": json.loads(r[3]), "risk": r[4]} for r in logs]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
