# Avaliação de modelos de embeddings — 2026-09-28

Tarefa: para cada uma de 247 tecnologias, encontrar as publicações que ela cita no portal (323 citações)
entre 5.304 publicações (as citadas + 5.000 sorteadas). Texto: título + resumo/descrição + palavras-chave.
Máquina: Intel i7-1355U (notebook, sem GPU; ~79 GFLOPS medidos), PyTorch 2.14 CPU.

| Modelo | recall@10 | MRR | docs/s (CPU) | horas p/ base completa (181.851 docs) |
|---|---|---|---|---|
| paraphrase-multilingual-MiniLM-L12-v2 | 16,7% | 0,120 | 16,6 | ~3 |
| **multilingual-e5-base** | **87,3%** | **0,675** | 2,2–3,5 | 16–23 |
| bge-m3 | interrompido | — | ~0,25 | > 200 |

**recall@10**: % das publicações citadas que aparecem entre as 10 mais parecidas com a tecnologia.
**MRR**: média de 1/posição da publicação citada (1 = sempre em 1º lugar).

## Conclusões
- **multilingual-e5-base** é o escolhido: 87% das publicações citadas aparecem no top-10, entre 5,3 mil.
- MiniLM é rápido mas fraco para este domínio (textos técnicos longos em português).
- bge-m3 é inviável nesta CPU (a avaliação sozinha levaria ~6 h).
- Distribuição de tokens (e5): mediana 106, p90 437; 28% dos textos passam de 256 tokens e 5% de 512.
  Cortar em 256 acelera ~40% na CPU.

## Execução
- Carga inicial (181 mil documentos): GPU (ex.: Google Colab) em minutos, ou CPU local em ~16 h.
- Atualizações mensais: só documentos novos (cache por hash do texto) — minutos na CPU.
