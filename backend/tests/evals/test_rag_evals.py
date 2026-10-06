import json
import os
import pytest
from tabulate import tabulate

from backend.tests.evals.rag_evaluator import RAGTriadEvaluator


@pytest.mark.asyncio
async def test_rag_triad_evaluation_suite():
    evaluator = RAGTriadEvaluator()
    golden_file = os.path.join(os.path.dirname(__file__), "golden_dataset.json")

    with open(golden_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results_table = []
    total_c_rel = 0.0
    total_faith = 0.0
    total_a_rel = 0.0

    for item in dataset:
        scores = await evaluator.evaluate_sample(
            query=item["question"],
            context=item["ground_truth_context"],
            answer=item["ground_truth_answer"],
            is_out_of_scope=item.get("is_out_of_scope", False),
        )

        c_rel = scores["context_relevance"]
        faith = scores["faithfulness"]
        a_rel = scores["answer_relevance"]
        triad_avg = round((c_rel + faith + a_rel) / 3, 2)

        total_c_rel += c_rel
        total_faith += faith
        total_a_rel += a_rel

        results_table.append([
            item["id"],
            item["question"][:40] + "...",
            f"{c_rel:.2f}",
            f"{faith:.2f}",
            f"{a_rel:.2f}",
            f"{triad_avg:.2f}",
        ])

    count = len(dataset)
    avg_c_rel = total_c_rel / count
    avg_faith = total_faith / count
    avg_a_rel = total_a_rel / count
    overall_triad = (avg_c_rel + avg_faith + avg_a_rel) / 3

    headers = ["ID", "Pergunta", "Context Rel", "Faithfulness", "Answer Rel", "Media Triade"]
    table_str = tabulate(results_table, headers=headers, tablefmt="github")

    print("\n" + "=" * 70)
    print("RELATÓRIO DE AVALIAÇÃO DA TRÍADE DE RAG (LOLA AGENT EVALS)")
    print("=" * 70)
    print(table_str)
    print(f"\nResumo Global:")
    print(f"- Relevância de Contexto Média: {avg_c_rel:.2f}")
    print(f"- Fidelidade (Aterramento) Média: {avg_faith:.2f}")
    print(f"- Relevância de Resposta Média:   {avg_a_rel:.2f}")
    print(f"- Score Global da Tríade:         {overall_triad:.2f}")
    print("=" * 70 + "\n")

    # Assertions de rigor de qualidade
    assert avg_c_rel >= 0.70, f"Context Relevance abaixo da meta: {avg_c_rel}"
    assert avg_faith >= 0.85, f"Faithfulness abaixo da meta de zero alucinação: {avg_faith}"
    assert avg_a_rel >= 0.70, f"Answer Relevance abaixo da meta: {avg_a_rel}"
