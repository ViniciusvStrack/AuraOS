import json
import time

class AuraBrain:
    def __init__(self):
        # Memória simplificada do AuraOS
        self.knowledge_base = [
            {"topic": "arquitetura", "decision": "Usar PostgreSQL", "date": "2025-10-10"},
            {"topic": "cliente x", "rule": "Não dar desconto acima de 15%", "owner": "Financeiro"},
            {"topic": "vaga dev", "status": "congelada", "reason": "budget anual atingido"}
        ]

    def process_event(self, event_type, content):
        """
        Simula o processamento de um evento (Slack, Email, Transcrição de Reunião)
        """
        print(f"[AuraOS] Processando novo evento do {event_type}...")
        
        # Lógica de detecção de conflitos
        if "desconto" in content.lower() and "20%" in content:
            return "ALERTA: Você mencionou 20% de desconto. A regra do Financeiro para este cliente é de no máximo 15%."
        
        if "contratar" in content.lower() and "desenvolvedor" in content.lower():
            return "INSIGHT: Notei que você falou sobre contratar. O RH marcou esta vaga como CONGELADA devido ao orçamento."
        
        return "Sincronizado: Nenhuma inconsistência detectada."

# Simulação de uso real
aura = AuraBrain()

# Cenário 1: Conversa no Slack
message = "Olá time, vamos fechar com o cliente X dando um desconto de 20% para acelerar."
result = aura.process_event("Slack", message)
print(f"Resultado: {result}\n")

# Cenário 2: Reunião no Zoom
transcript = "Precisamos abrir uma nova vaga para desenvolvedor backend imediatamente."
result = aura.process_event("Zoom", transcript)
print(f"Resultado: {result}\n")
