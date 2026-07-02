import sqlite3
import uvicorn
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- BANCO DE DADOS GIGANTE (AuraMed Enterprise) ---
def init_db():
    conn = sqlite3.connect('auramed_v3.db')
    cursor = conn.cursor()
    
    # Tabela de Conhecimento por Especialidade
    cursor.execute('''CREATE TABLE IF NOT EXISTS specialty_knowledge (
                        id INTEGER PRIMARY KEY, 
                        specialty TEXT, 
                        symptoms TEXT, 
                        diagnosis TEXT, 
                        exams TEXT,
                        priority TEXT)''')
    
    # Tabela de Agenda de Plantão
    cursor.execute('''CREATE TABLE IF NOT EXISTS duty_schedule (
                        id INTEGER PRIMARY KEY, 
                        doctor_name TEXT, 
                        date TEXT, 
                        shift TEXT, 
                        location TEXT)''')
    
    # Tabela de Logs de Consultas (Para aprendizado)
    cursor.execute('''CREATE TABLE IF NOT EXISTS clinical_cases (
                        id INTEGER PRIMARY KEY, 
                        ts TEXT, 
                        specialty TEXT, 
                        input_text TEXT, 
                        output_analysis TEXT)''')

    # Populando Conhecimento Inicial por Áreas
    cursor.execute("SELECT count(*) FROM specialty_knowledge")
    if cursor.fetchone()[0] == 0:
        knowledge_base = [
            ("Clínica Médica", "tosse, catarro, febre", "Pneumonia, Bronquite, Influenza", "Raio-X de Tórax, Hemograma, Proteína C Reativa", "Média"),
            ("Pediatria", "febre, manchas vermelhas, coceira", "Varicela, Sarampo, Escarlatina", "Sorologia, Avaliação Clínica", "Alta"),
            ("Cardiologia", "dor no peito, falta de ar, suor frio", "IAM, Angina Instável, Dissecção de Aorta", "ECG, Troponina, Ecocardiograma", "Crítica"),
            ("Ginecologia", "dor pélvica, atraso menstrual", "Gravidez Ectópica, Cisto Ovariano", "Beta-HCG, Ultrassom Transvaginal", "Alta"),
            ("Ortopedia", "dor lombar, irradiação para perna", "Hérnia de Disco, Ciatalgia", "Ressonância de Coluna, Teste de Lasègue", "Média"),
            ("Psiquiatria", "tristeza profunda, falta de energia, insônia", "Transtorno Depressivo Maior, Burnout", "Escala de Hamilton, Avaliação Clínica", "Média"),
            ("Dermatologia", "lesão descamativa, bordas irregulares", "Psoríase, Carcinoma Basocelular", "Biópsia de Pele, Dermatoscopia", "Baixa")
        ]
        cursor.executemany("INSERT INTO specialty_knowledge (specialty, symptoms, diagnosis, exams, priority) VALUES (?,?,?,?,?)", knowledge_base)
    
    conn.commit()
    conn.close()

init_db()

# --- MODELOS ---
class CaseInput(BaseModel):
    specialty: str
    text: str

class DutyInput(BaseModel):
    doctor: str
    date: str
    shift: str
    location: str

# --- LÓGICA DE INTELIGÊNCIA ---
@app.post("/clinical_ai")
async def clinical_ai(data: CaseInput):
    conn = sqlite3.connect('auramed_v3.db')
    cursor = conn.cursor()
    
    # Busca conhecimento na especialidade ou global
    cursor.execute("SELECT diagnosis, exams, priority FROM specialty_knowledge WHERE specialty = ? OR specialty = 'Clínica Médica'", (data.specialty,))
    knowledge = cursor.fetchall()
    
    results = []
    text_low = data.text.lower()
    
    for diag, exams, prio in knowledge:
        # Verifica se algum sintoma da base está no texto do médico
        # (Em produção usaríamos NLP avançado, aqui usamos match de conceitos)
        cursor.execute("SELECT symptoms FROM specialty_knowledge WHERE diagnosis = ?", (diag,))
        symptoms = cursor.fetchone()[0].split(", ")
        
        match_count = sum(1 for s in symptoms if s in text_low)
        if match_count > 0:
            results.append({
                "possible_diagnosis": diag,
                "suggested_exams": exams,
                "priority": prio
            })

    # Salva o caso para a IA "aprender" no futuro
    cursor.execute("INSERT INTO clinical_cases (ts, specialty, input_text, output_analysis) VALUES (?,?,?,?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), data.specialty, data.text, json.dumps(results)))
    
    conn.commit()
    conn.close()
    return {"results": results}

@app.post("/add_duty")
async def add_duty(data: DutyInput):
    conn = sqlite3.connect('auramed_v3.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO duty_schedule (doctor_name, date, shift, location) VALUES (?,?,?,?)",
                   (data.doctor, data.date, data.shift, data.location))
    conn.commit()
    conn.close()
    return {"status": "Plantão agendado"}

@app.get("/get_duties")
async def get_duties():
    conn = sqlite3.connect('auramed_v3.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM duty_schedule ORDER BY date ASC")
    duties = cursor.fetchall()
    conn.close()
    return [{"id": d[0], "doctor": d[1], "date": d[2], "shift": d[3], "location": d[4]} for d in duties]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
