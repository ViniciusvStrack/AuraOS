from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

app = FastAPI()

# Permitir que o navegador acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Banco de dados temporário (Memória do AuraOS)
knowledge_base = [
    {"id": 1, "topic": "Arquitetura", "content": "Usar Google Cloud (GCP) para todos os projetos de 2026.", "user": "CTO"},
    {"id": 2, "topic": "Financeiro", "content": "Desconto máximo permitido é 15%.", "user": "CFO"}
]

logs = []

class Message(BaseModel):
    text: str
    source: str = "Simulação"

@app.get("/knowledge")
def get_knowledge():
    return knowledge_base

@app.post("/add_knowledge")
def add_knowledge(item: dict):
    item["id"] = len(knowledge_base) + 1
    knowledge_base.append(item)
    return {"status": "success"}

@app.post("/analyze")
def analyze(msg: Message):
    text = msg.text.lower()
    alert = None
    
    # Lógica de detecção de conflitos
    if "aws" in text or "azure" in text:
        alert = "CONFLITO: Detectamos uma menção a AWS/Azure. A diretriz oficial (ID 1) exige Google Cloud."
    
    if "desconto" in text and any(x in text for x in ["20%", "25%", "30%"]):
        alert = "RISCO: Você mencionou um desconto alto. O limite da empresa é 15% (ID 2)."

    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "text": msg.text,
        "alert": alert,
        "status": "CRÍTICO" if alert else "OK"
    }
    logs.insert(0, log_entry)
    
    return log_entry

@app.get("/logs")
def get_logs():
    return logs[:10]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
