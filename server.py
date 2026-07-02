import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import re
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BANCO DE DADOS (MEMÓRIA DE LONGO PRAZO) ---
def init_db():
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS rules 
                      (id INTEGER PRIMARY KEY, category TEXT, content TEXT, severity TEXT, impact_score INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                      (id INTEGER PRIMARY KEY, timestamp TEXT, input TEXT, status TEXT, conflicts TEXT)''')
    
    # Regras Iniciais de "Educação"
    cursor.execute("SELECT count(*) FROM rules")
    if cursor.fetchone()[0] == 0:
        initial_rules = [
            ("Arquitetura", "A empresa utiliza exclusivamente Google Cloud (GCP). AWS/Azure são proibidos por compliance.", "Crítica", 10),
            ("Comercial", "Descontos acima de 15% exigem assinatura digital do CFO.", "Alta", 8),
            ("Comunicação", "Informações sobre salários ou bônus não devem ser discutidas em canais abertos.", "Alta", 9),
            ("Segurança", "Chaves de API e senhas nunca devem ser postadas em texto claro.", "Crítica", 10)
        ]
        cursor.executemany("INSERT INTO rules (category, content, severity, impact_score) VALUES (?,?,?,?)", initial_rules)
    conn.commit()
    conn.close()

init_db()

# --- MODELOS DE DADOS ---
class AnalysisRequest(BaseModel):
    text: str

class NewRule(BaseModel):
    category: str
    content: str
    severity: str

# --- MOTOR DE INTELIGÊNCIA APRIMORADO ---
def smart_analyzer(text):
    text = text.lower()
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT category, content, severity FROM rules")
    rules = cursor.fetchall()
    
    found_conflicts = []
    
    # Análise por "Gatilhos de Intenção"
    for category, content, severity in rules:
        # Criamos um set de palavras-chave da regra (removendo stop words simples)
        keywords = set(re.findall(r'\w+', content.lower()))
        input_words = set(re.findall(r'\w+', text))
        
        # Intersecção Semântica: Se o texto do usuário compartilha conceitos chave com a regra
        match_score = len(keywords.intersection(input_words))
        
        # Lógica específica para valores numéricos (Descontos)
        if "desconto" in text or "%" in text:
            numbers = re.findall(r'\d+', text)
            if numbers and int(numbers[0]) > 15 and category == "Comercial":
                found_conflicts.append({"category": category, "content": content, "severity": severity})
                continue

        # Lógica para Nuvem
        if any(cloud in text for cloud in ["aws", "azure", "amazon", "lambda"]) and category == "Arquitetura":
            found_conflicts.append({"category": category, "content": content, "severity": severity})
            continue

        # Se houver uma sobreposição forte de palavras (Simulando aprendizado de contexto)
        if match_score >= 3: 
            found_conflicts.append({"category": category, "content": content, "severity": severity})

    conn.close()
    return found_conflicts

# --- ENDPOINTS ---
@app.post("/analyze")
async def analyze(req: AnalysisRequest):
    conflicts = smart_analyzer(req.text)
    status = "ALERTA" if conflicts else "LIMPO"
    
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (timestamp, input, status, conflicts) VALUES (?,?,?,?)",
                   (datetime.now().strftime("%H:%M:%S"), req.text, status, str(conflicts)))
    conn.commit()
    conn.close()
    
    return {"status": status, "conflicts": conflicts, "timestamp": datetime.now().strftime("%H:%M:%S")}

@app.get("/dashboard-data")
async def get_data():
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10")
    logs_raw = cursor.fetchall()
    
    cursor.execute("SELECT count(*) FROM logs")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM rules")
    rules_count = cursor.fetchone()[0]
    
    # Formata os logs para o frontend
    history = []
    for l in logs_raw:
        history.append({
            "timestamp": l[1],
            "input": l[2],
            "status": l[3],
            "conflicts": eval(l[4]) # Converte string de volta para lista
        })
        
    conn.close()
    return {
        "stats": {"total": total, "rules": rules_count},
        "history": history
    }

@app.post("/teach")
async def teach(rule: NewRule):
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rules (category, content, severity, impact_score) VALUES (?,?,?,?)",
                   (rule.category, rule.content, rule.severity, 5))
    conn.commit()
    conn.close()
    return {"message": "Conhecimento assimilado."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
