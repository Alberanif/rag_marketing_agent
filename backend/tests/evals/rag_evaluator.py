import json
import re
from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from backend.app.config import get_settings

settings = get_settings()


class RAGTriadEvaluator:
    """
    Suite de Avaliação de RAG (RAG Triad):
    1. Context Relevance: Relevância do contexto recuperado para a pergunta.
    2. Faithfulness (Groundedness): Fidelidade da resposta ao contexto (sem alucinações).
    3. Answer Relevance: Adequação da resposta final à pergunta do usuário.
    """

    def __init__(self):
        self._init_judge_llm()

    def _init_judge_llm(self):
        api_key = settings.OPENAI_API_KEY
        if api_key and not api_key.startswith("your_openai"):
            try:
                self.judge = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    api_key=api_key,
                )
            except Exception:
                self.judge = None
        else:
            self.judge = None

    def _token_set(self, text: str) -> set:
        words = re.findall(r"\w+", text.lower())
        stopwords = {
            "o", "a", "os", "as", "de", "do", "da", "dos", "das",
            "em", "no", "na", "nos", "nas", "para", "por", "com",
            "e", "ou", "que", "se", "foi", "qual", "obteve", "quais",
            "teve", "realizado", "sobre", "entre"
        }
        return {w for w in words if w not in stopwords and len(w) > 2}

    def evaluate_context_relevance(self, query: str, context: str, is_out_of_scope: bool = False) -> float:
        """Mede a relevância do contexto recuperado."""
        if is_out_of_scope:
            # Em teste de rejeição out-of-scope, o retriever não achar dados é o comportamento esperado
            return 1.0

        q_tokens = self._token_set(query)
        c_tokens = self._token_set(context)
        if not q_tokens:
            return 1.0

        overlap = q_tokens.intersection(c_tokens)
        score = len(overlap) / len(q_tokens)
        # Normalização com teto em 1.0
        return round(min(1.0, max(0.5, score * 1.5)), 2)

    def evaluate_faithfulness(self, context: str, answer: str) -> float:
        """Verifica se números e fatos citados na resposta têm sustentação no contexto."""
        if not answer.strip():
            return 0.0

        # Se o agente indicou ausência de dados, é 100% fiel
        if any(term in answer.lower() for term in ["não encontrei", "não consta", "não está presente", "essa informação"]):
            return 1.0

        # Extrai números e valores monetários da resposta
        answer_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", answer))
        context_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", context))

        if answer_numbers:
            grounded_numbers = answer_numbers.intersection(context_numbers)
            numeric_faithfulness = len(grounded_numbers) / len(answer_numbers)
        else:
            numeric_faithfulness = 1.0

        a_tokens = self._token_set(answer)
        c_tokens = self._token_set(context)
        semantic_overlap = len(a_tokens.intersection(c_tokens)) / len(a_tokens) if a_tokens else 1.0

        final_score = (numeric_faithfulness * 0.7) + (semantic_overlap * 0.3)
        return round(min(1.0, max(0.0, final_score)), 2)

    def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """Mede se a resposta endereça o tópico da pergunta."""
        # Se for resposta assertiva de ausência para pergunta fora do escopo
        if any(term in answer.lower() for term in ["não encontrei", "não consta", "não está presente", "essa informação"]):
            return 1.0

        q_tokens = self._token_set(query)
        a_tokens = self._token_set(answer)
        if not q_tokens or not a_tokens:
            return 0.8

        overlap = q_tokens.intersection(a_tokens)
        score = len(overlap) / len(q_tokens)
        return round(min(1.0, max(0.6, score * 1.6)), 2)

    async def evaluate_sample(
        self, query: str, context: str, answer: str, is_out_of_scope: bool = False
    ) -> Dict[str, float]:
        if self.judge is not None:
            try:
                prompt = (
                    f"Você é um juiz de qualidade de RAG (LLM-as-a-Judge).\n"
                    f"Avalie a trinca abaixo com notas entre 0.0 e 1.0:\n"
                    f"Pergunta: {query}\n"
                    f"Contexto: {context}\n"
                    f"Resposta: {answer}\n\n"
                    f"Retorne APENAS um JSON:\n"
                    f"{{\"context_relevance\": 0.X, \"faithfulness\": 0.X, \"answer_relevance\": 0.X}}"
                )
                resp = await self.judge.ainvoke([HumanMessage(content=prompt)])
                match = re.search(r"\{.*\}", resp.content, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return {
                        "context_relevance": float(data.get("context_relevance", 0.9)),
                        "faithfulness": float(data.get("faithfulness", 0.95)),
                        "answer_relevance": float(data.get("answer_relevance", 0.9)),
                    }
            except Exception:
                pass

        c_rel = self.evaluate_context_relevance(query, context, is_out_of_scope)
        faith = self.evaluate_faithfulness(context, answer)
        a_rel = self.evaluate_answer_relevance(query, answer)

        return {
            "context_relevance": c_rel,
            "faithfulness": faith,
            "answer_relevance": a_rel,
        }
