from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# BANCO DE DADOS EM MEMÓRIA (Simulando uma Base de Vetores)
class CompanyMemory:
    def __init__(self):
        self.rules = [
            {"id": 1, "category": "Infraestrutura", "content": "A diretriz padrão para nuvem é Google Cloud (GCP). Uso de AWS/Azure requer aprovação do CTO.", "severity": "Alta"},
            {"id": 2, "category": "Comercial", "content": "Descontos acima de 15% em contratos anuais devem ser validados pelo Financeiro.", "severity": "Média"},
            {"id": 3, "category": "Cultura", "content": "Todas as reuniões de sexta-feira devem ter atas enviadas em até 2 horas.", "severity": "Baixa"}
        ]
        self.history = []
        self.stats = {"total_processed": 0, "conflicts_found": 0}

    def add_rule(self, category, content, severity):
        new_id = len(self.rules) + 1
        self.rules.append({"id": new_id, "category": category, "content": content, "severity": severity})
        return new_id

memory = CompanyMemory()

class AnalysisRequest(BaseModel):
    text: str
    context: str = "Geral"

class NewRule(BaseModel):
    category: str
    content: str
    severity: str

@app.post("/analyze")
async def analyze_interaction(req: AnalysisRequest):
    text = req.text.lower()
    detected_conflicts = []
    
    # MOTOR DE RACIOCÍNIO (Simulação de análise semântica)
    for rule in memory.rules:
        # Busca por conceitos relacionados (Nuvem, Dinheiro, Prazos)
        keywords = rule["content"].lower().split()
        matches = [word for word in keywords if len(word) > 3 and word in text]
        
        # Se houver uma combinação de conceitos (ex: AWS + Nuvem)
        if ("aws" in text or "azure" in text) and rule["id"] == 1:
            detected_conflicts.append(rule)
        elif ("desconto" in text or "%" in text) and rule["id"] == 2:
            # Tenta extrair o número para ver se passa de 15
            import re
            numbers = re.findall(r'\d+', text)
            for n in numbers:
                if int(n) > 15:
                    detected_conflicts.append(rule)

    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "input": req.text,
        "conflicts": detected_conflicts,
        "status": "CRÍTICO" if detected_conflicts else "LIMPO"
    }
    
    memory.history.insert(0, log_entry)
    memory.stats["total_processed"] += 1
    if detected_conflicts: memory.stats["conflicts_found"] += 1
    
    return log_entry

@app.get("/dashboard-data")
async def get_dashboard():
    return {
        "memory_size": len(memory.rules),
        "history": memory.history[:15],
        "stats": memory.stats,
        "rules": memory.rules
    }

@app.post("/teach")
async def teach_ai(rule: NewRule):
    rule_id = memory.add_rule(rule.category, rule.content, rule.severity)
    return {"status": "Apreendido", "rule_id": rule_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
