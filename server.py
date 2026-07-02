import sqlite3
import uvicorn
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- BANCO DE DADOS UNIFICADO ---
def init_db():
    conn = sqlite3.connect('auramed_pro.db')
    cursor = conn.cursor()
    
    # Conhecimento Médico Global (Sem divisões chatas)
    cursor.execute('''CREATE TABLE IF NOT EXISTS medical_brain (
                        id INTEGER PRIMARY KEY, 
                        trigger_keywords TEXT, 
                        diagnosis TEXT, 
                        exams TEXT,
                        conduct TEXT,
                        urgency TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS duty_schedule (
                        id INTEGER PRIMARY KEY, doctor TEXT, date TEXT, shift TEXT, location TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY, role TEXT, message TEXT, timestamp TEXT)''')

    # Populando o Cérebro com conhecimento abrangente
    cursor.execute("SELECT count(*) FROM medical_brain")
    if cursor.fetchone()[0] == 0:
        base_data = [
            ("tosse, catarro, febre, falta de ar", "Pneumonia / Infecção Respiratória", "Raio-X de Tórax, Hemograma, Saturação", "Prescrever Antibioticoterapia, Hidratação, Repouso.", "Alta"),
            ("dor no peito, suor, queimação, braço", "Síndrome Coronariana Aguda (IAM)", "ECG, Troponina, Marcadores Cardíacos", "Protocolo de Dor Torácica: AAS, Nitratos (se não contraindicado), Oxigênio.", "Crítica"),
            ("dor de cabeça, luz, náusea, vômito", "Enxaqueca / Cefaleia Vascular", "Avaliação Clínica, Tomografia (se sinais de alarme)", "Analgésicos EV, Antieméticos, Ambiente Escuro.", "Média"),
            ("manchas vermelhas, coceira, criança", "Exantema a esclarecer (Virose)", "Avaliação Clínica, Sorologias se persistir", "Sintomáticos, monitorar sinais de alarme (febre persistente).", "Média"),
            ("dor pélvica, atraso, sangramento", "Urgência Ginecológica / Gravidez Ectópica", "Beta-HCG, Ultrassom Transvaginal", "Avaliação imediata por especialista, jejum se cirúrgico.", "Crítica"),
            ("tristeza, insônia, sem energia", "Transtorno Depressivo / Burnout", "Escalas de Depressão, Exames para excluir Tireoide", "Encaminhamento Psiquiatria/Psicologia, Higiene do Sono.", "Média")
        ]
        cursor.executemany("INSERT INTO medical_brain (trigger_keywords, diagnosis, exams, conduct, urgency) VALUES (?,?,?,?,?,?)", base_data)
    
    conn.commit()
    conn.close()

init_db()

# --- MODELOS ---
class ChatMessage(BaseModel):
    message: str

class DutyData(BaseModel):
    doctor: str
    date: str
    shift: str
    location: str

# --- LÓGICA DO CHAT INTELIGENTE ---
@app.post("/chat")
async def chat_with_ai(data: ChatMessage):
    msg = data.message.lower()
    conn = sqlite3.connect('auramed_pro.db')
    cursor = conn.cursor()
    
    # Salva mensagem do usuário
    ts = datetime.now().strftime("%H:%M:%S")
    cursor.execute("INSERT INTO chat_history (role, message, timestamp) VALUES (?,?,?)", ("user", data.message, ts))
    
    # Busca no Cérebro
    cursor.execute("SELECT diagnosis, exams, conduct, urgency FROM medical_brain")
    all_knowledge = cursor.fetchall()
    
    response_cards = []
    for diag, exams, conduct, urgency in all_knowledge:
        # Busca palavras chave no cérebro
        cursor.execute("SELECT trigger_keywords FROM medical_brain WHERE diagnosis = ?", (diag,))
        keywords = cursor.fetchone()[0].split(", ")
        
        matches = [k for k in keywords if k in msg]
        if matches:
            response_cards.append({
                "type": "diagnostic_card",
                "title": diag,
                "exams": exams,
                "conduct": conduct,
                "urgency": urgency
            })

    # Resposta padrão se não achar nada específico
    if not response_cards:
        ai_reply = "Entendi. Para este caso, recomendo uma avaliação física detalhada. Posso ajudar com protocolos de exames se você detalhar os sintomas."
    else:
        ai_reply = f"Identifiquei {len(response_cards)} possibilidade(s) diagnóstica(s) com base no seu relato."

    cursor.execute("INSERT INTO chat_history (role, message, timestamp) VALUES (?,?,?)", ("ai", ai_reply, ts))
    conn.commit()
    conn.close()
    
    return {"message": ai_reply, "cards": response_cards}

@app.get("/history")
async def get_history():
    conn = sqlite3.connect('auramed_pro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT 20")
    data = cursor.fetchall()
    conn.close()
    return [{"role": r[1], "message": r[2], "time": r[3]} for r in data][::-1]

@app.post("/schedule")
async def add_schedule(data: DutyData):
    conn = sqlite3.connect('auramed_pro.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO duty_schedule (doctor, date, shift, location) VALUES (?,?,?,?)", (data.doctor, data.date, data.shift, data.location))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/get_schedule")
async def get_schedule():
    conn = sqlite3.connect('auramed_pro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM duty_schedule ORDER BY date ASC")
    d = cursor.fetchall()
    conn.close()
    return [{"doctor": r[1], "date": r[2], "shift": r[3], "location": r[4]} for r in d]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
