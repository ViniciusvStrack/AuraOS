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

# --- CÉREBRO CLÍNICO AVANÇADO ---
class MedicalIntelligence:
    def __init__(self):
        self.db = 'auramed_pro.db'
        self._setup_knowledge()

    def _setup_knowledge(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS medical_brain (
                            id INTEGER PRIMARY KEY, 
                            topic TEXT,
                            synonyms TEXT, 
                            diagnosis TEXT, 
                            exams TEXT,
                            conduct TEXT,
                            urgency TEXT)''')
        
        # Base de Conhecimento Expandida e Inteligente
        cursor.execute("SELECT count(*) FROM medical_brain")
        if cursor.fetchone()[0] == 0:
            knowledge = [
                ("Respiratório", "tosse, catarro, secreção, febre, dispneia, falta de ar, cansaço", 
                 "Pneumonia / Bronquite Aguda", "Raio-X de Tórax, Hemograma Completo, Oximetria", 
                 "Iniciar antibioticoterapia se critérios de Centor/CURB-65 positivos. Hidratação vigorosa.", "Alta"),
                
                ("Cardiovascular", "dor peito, precordialgia, sudorese, suor, queimação, aperto, braço esquerdo, mandíbula", 
                 "Síndrome Coronariana Aguda (IAM)", "Eletrocardiograma (ECG) 12 derivações, Troponina I, CK-MB", 
                 "Protocolo MONA (Morfina, Oxigênio, Nitrato, AAS). Transferência para sala de emergência.", "Crítica"),
                
                ("Neurológico", "dor cabeça, cefaleia, fotofobia, enxaqueca, vômito, náusea, tontura", 
                 "Cefaleia Primária / Enxaqueca", "Exame físico neurológico, Tomografia se houver sinais de alerta (SNOOP)", 
                 "Analgesia venosa, repouso em local escuro, evitar gatilhos alimentares.", "Média"),
                
                ("Gastrointestinal", "dor barriga, dor abdominal, vômito, diarreia, enjoo, estômago", 
                 "Gastroenterite Aguda / Abdome Agudo a esclarecer", "Ultrassom Abdominal, Amilase/Lipase, Hemograma", 
                 "Reposição volêmica, antieméticos, avaliar sinais de peritonite (Blumberg).", "Média")
            ]
            cursor.executemany("INSERT INTO medical_brain (topic, synonyms, diagnosis, exams, conduct, urgency) VALUES (?,?,?,?,?,?)", knowledge)
        conn.commit()
        conn.close()

    def process_message(self, user_msg):
        text = user_msg.lower()
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT topic, synonyms, diagnosis, exams, conduct, urgency FROM medical_brain")
        rules = cursor.fetchall()
        
        matches = []
        for topic, synonyms, diag, exams, conduct, urgency in rules:
            syn_list = synonyms.split(", ")
            # Sistema de Pontuação: Quanto mais termos relacionados, mais certeza a IA tem
            score = sum(1 for syn in syn_list if syn in text)
            
            if score > 0:
                matches.append({
                    "score": score,
                    "title": diag,
                    "exams": exams,
                    "conduct": conduct,
                    "urgency": urgency
                })
        
        conn.close()
        # Ordena pelos resultados mais prováveis (maior score)
        return sorted(matches, key=lambda x: x['score'], reverse=True)

brain = MedicalIntelligence()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    user_text = req.message
    
    # Processamento de IA
    results = brain.process_message(user_text)
    
    # Lógica de Resposta Humanizada
    if not results:
        # Resposta genérica mas inteligente se não houver match clínico
        if len(user_text.split()) < 3:
            reply = "Poderia me dar mais detalhes sobre o quadro clínico do paciente? Sinais vitais ou sintomas específicos ajudariam."
        else:
            reply = "Analisei seu relato. Os sintomas são inespecíficos para um diagnóstico imediato. Recomendo monitorar sinais de alerta e realizar anamnese detalhada."
    else:
        top_result = results[0]
        reply = f"Com base nos sinais relatados, identifiquei uma forte suspeita de {top_result['title']}. Veja as condutas sugeridas nos cards abaixo."

    return {"message": reply, "cards": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
