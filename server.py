import sqlite3
import re
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CORE DA INTELIGÊNCIA ---
class AuraBrain:
    def __init__(self):
        self.db = 'aura_memory.db'
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge 
                          (id INTEGER PRIMARY KEY, area TEXT, topic TEXT, content TEXT, level TEXT, weight INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS interactions 
                          (id INTEGER PRIMARY KEY, ts TEXT, input TEXT, analysis TEXT, severity TEXT)''')
        conn.commit()
        conn.close()

    def inject_curriculum(self):
        """Injeta o conhecimento do básico ao avançado"""
        curriculum = [
            # NÍVEL: BÁSICO (Operação)
            ("Operações", "Ponto Eletrônico", "O registro de ponto deve ser feito no início e fim da jornada. Esquecimentos devem ser justificados em 24h.", "Básico", 5),
            ("TI", "Senhas", "Senhas devem ter 12+ caracteres, símbolos e nunca serem compartilhadas via chat.", "Básico", 10),
            
            # NÍVEL: INTERMEDIÁRIO (Processos)
            ("Engenharia", "Code Review", "Nenhum código vai para produção sem revisão de pelo menos dois desenvolvedores seniores.", "Intermediário", 8),
            ("Jurídico", "LGPD", "Dados sensíveis de clientes (CPF, Endereço) devem ser criptografados e nunca exportados em CSV.", "Intermediário", 9),
            
            # NÍVEL: AVANÇADO (Estratégia e Risco)
            ("Estratégia", "M&A", "Qualquer menção a fusões ou aquisições é confidencial nível 1. Discutir isso fora de salas protegidas é infração grave.", "Avançado", 10),
            ("Financeiro", "Burn Rate", "Se o gasto mensal exceder 500k USD, todos os novos contratos de ferramentas SaaS devem ser congelados.", "Avançado", 9),
            ("Arquitetura", "Microserviços", "Projetos novos devem seguir a arquitetura de Event-Driven. Monólitos estão proibidos.", "Avançado", 7)
        ]
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge") # Limpa para o novo currículo
        cursor.executemany("INSERT INTO knowledge (area, topic, content, level, weight) VALUES (?,?,?,?,?)", curriculum)
        conn.commit()
        conn.close()

    def analyze(self, text):
        text_low = text.lower()
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT area, topic, content, level, weight FROM knowledge")
        all_knowledge = cursor.fetchall()
        
        found_issues = []
        highest_severity = "Baixa"

        for area, topic, content, level, weight in all_knowledge:
            # Algoritmo de Correspondência de Conceitos
            keywords = set(re.findall(r'\w+', content.lower() + " " + topic.lower()))
            input_words = set(re.findall(r'\w+', text_low))
            
            match_score = len(keywords.intersection(input_words))
            
            # Se a IA identificar que o usuário está falando de um tópico proibido ou sensível
            if match_score >= 2:
                severity = "Crítica" if weight >= 9 else "Média" if weight >= 6 else "Informativa"
                found_issues.append({
                    "area": area,
                    "topic": topic,
                    "insight": content,
                    "level": level,
                    "severity": severity
                })
                if weight > 8: highest_severity = "Alta"

        conn.close()
        return found_issues, highest_severity

brain = AuraBrain()
brain.inject_curriculum()

# --- API ENDPOINTS ---
class InputData(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_api(data: InputData):
    issues, severity = brain.analyze(data.text)
    
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interactions (ts, input, analysis, severity) VALUES (?,?,?,?)",
                   (datetime.now().strftime("%H:%M:%S"), data.text, str(issues), severity))
    conn.commit()
    conn.close()
    
    return {"analysis": issues, "overall_severity": severity}

@app.get("/stats")
async def get_stats():
    conn = sqlite3.connect('aura_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM knowledge")
    k_count = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM interactions ORDER BY id DESC LIMIT 10")
    recent = cursor.fetchall()
    conn.close()
    
    formatted_history = []
    for r in recent:
        formatted_history.append({"ts": r[1], "input": r[2], "analysis": eval(r[3]), "severity": r[4]})
        
    return {"knowledge_base_size": k_count, "history": formatted_history}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
