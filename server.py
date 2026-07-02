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

# --- DEFINIÇÃO DOS NICHOS (O "Cérebro Universal") ---
NICHE_PACKS = {
    "Healthcare": [
        ("Privacidade", "HIPAA", "Dados de pacientes nunca devem ser compartilhados via chat sem criptografia de ponta a ponta.", 10),
        ("Protocolo", "Prescrição", "Prescrições médicas só podem ser validadas com assinatura digital padrão ICP-Brasil.", 9),
        ("Ética", "Prontuário", "O acesso a prontuários por funcionários sem relação direta com o tratamento é falta grave.", 10)
    ],
    "Legal": [
        ("Ética", "Sigilo Profissional", "Discussões sobre casos ativos em áreas comuns ou chats abertos violam o sigilo advogado-cliente.", 10),
        ("Compliance", "Prazos Processuais", "A menção a prazos fatais deve gerar um alerta imediato para o gestor da conta.", 8),
        ("Documentação", "Contratos", "Cláusulas de rescisão sem aviso prévio de 30 dias não são permitidas nos modelos da firma.", 7)
    ],
    "E-commerce": [
        ("Fraude", "Chargeback", "Transações acima de R$ 5.000 com cartões emitidos no exterior devem passar por análise manual.", 9),
        ("Logística", "SLA de Entrega", "Promessas de entrega em menos de 24h para a Região Norte são proibidas por inviabilidade logística.", 8),
        ("Pagamentos", "PCI-DSS", "Nunca armazene o código CVV ou dados completos do cartão em logs de transação.", 10)
    ],
    "Manufacturing": [
        ("Segurança", "NR-12", "Qualquer manutenção em máquinas deve ser precedida pelo protocolo de bloqueio e etiquetagem (LOTO).", 10),
        ("Qualidade", "Six Sigma", "Desvios acima de 0.5% na linha de produção devem interromper o lote imediatamente.", 9),
        ("Operação", "Turnos", "A troca de turno deve incluir obrigatoriamente o relatório de anomalias térmicas.", 7)
    ],
    "Fintech": [
        ("Compliance", "KYC", "Contas sem documento de identidade validado não podem realizar transferências acima de R$ 1.000.", 10),
        ("Risco", "Crédito", "Aumentos de limite para clientes com Score abaixo de 400 devem ser bloqueados automaticamente.", 9),
        ("Segurança", "Open Banking", "O compartilhamento de tokens de consentimento deve ser revogado a cada 90 dias.", 8)
    ]
}

class AuraBrain:
    def __init__(self):
        self.db = 'aura_memory.db'
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge 
                          (id INTEGER PRIMARY KEY, area TEXT, topic TEXT, content TEXT, weight INTEGER, niche TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS interactions 
                          (id INTEGER PRIMARY KEY, ts TEXT, input TEXT, analysis TEXT, severity TEXT)''')
        conn.commit()
        conn.close()

    def load_niche(self, niche_name):
        if niche_name not in NICHE_PACKS: return False
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        # Adiciona o pacote sem apagar o que já existe (Acumulativo)
        data = [(area, topic, content, weight, niche_name) for area, topic, content, weight in NICHE_PACKS[niche_name]]
        cursor.executemany("INSERT INTO knowledge (area, topic, content, weight, niche) VALUES (?,?,?,?,?)", data)
        conn.commit()
        conn.close()
        return True

    def analyze(self, text):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT area, topic, content, weight, niche FROM knowledge")
        rules = cursor.fetchall()
        
        found = []
        text_low = text.lower()
        
        for area, topic, content, weight, niche in rules:
            # Algoritmo de Similaridade Semântica Simples
            keywords = set(re.findall(r'\w+', content.lower()))
            input_words = set(re.findall(r'\w+', text_low))
            matches = keywords.intersection(input_words)
            
            if len(matches) >= 3 or (len(matches) >= 1 and weight == 10):
                found.append({
                    "niche": niche,
                    "area": area,
                    "topic": topic,
                    "insight": content,
                    "severity": "Crítica" if weight >= 9 else "Média"
                })
        conn.close()
        return found

brain = AuraBrain()

# --- API ---
class InputData(BaseModel):
    text: str

class NicheData(BaseModel):
    niche: str

@app.post("/analyze")
async def analyze_api(data: InputData):
    results = brain.analyze(data.text)
    severity = "Alta" if any(r['severity'] == "Crítica" for r in results) else "Baixa"
    
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interactions (ts, input, analysis, severity) VALUES (?,?,?,?)",
                   (datetime.now().strftime("%H:%M:%S"), data.text, json.dumps(results), severity))
    conn.commit()
    conn.close()
    return {"analysis": results, "severity": severity}

@app.post("/load-niche")
async def load_niche_api(data: NicheData):
    success = brain.load_niche(data.niche)
    if not success: raise HTTPException(status_code=404, detail="Nicho não encontrado")
    return {"message": f"Conhecimento de {data.niche} injetado com sucesso."}

@app.get("/stats")
async def get_stats():
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM knowledge")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT niche, count(*) FROM knowledge GROUP BY niche")
    niches = cursor.fetchall()
    cursor.execute("SELECT * FROM interactions ORDER BY id DESC LIMIT 10")
    history = cursor.fetchall()
    conn.close()
    
    return {
        "total_knowledge": count,
        "active_niches": {n: c for n, c in niches},
        "history": [{"ts": r[1], "input": r[2], "analysis": json.loads(r[3]), "severity": r[4]} for r in history]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
