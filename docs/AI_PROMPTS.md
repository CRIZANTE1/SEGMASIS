# ✍️ Engenharia de Prompts

## 1. Princípios de Design de Prompts

A qualidade das respostas geradas pelos modelos Gemini depende diretamente da qualidade dos prompts. No SEGMA-SIS, seguimos os seguintes princípios para criar prompts eficazes:

1. **Definição de Persona:** O prompt sempre começa definindo uma persona clara para o modelo (ex: "Você é um Auditor Líder de SST", "Você é um especialista em RH"). Isso ancora o tom e o nível de especialização da resposta.
2. **Instruções Claras e Diretas:** As tarefas são descritas com verbos de ação e em etapas numeradas. Usamos negrito e maiúsculas para enfatizar regras críticas.
3. **Estrutura de Saída Obrigatória:** Exigimos que o modelo responda em um formato específico, quase sempre **JSON**. Isso torna a resposta previsível e fácil de ser processada pelo código Python, eliminando a necessidade de análises complexas de texto.
4. **Exemplos "One-Shot":** Fornecemos um exemplo de como a saída JSON deve se parecer. Isso é conhecido como "one-shot prompting" e melhora drasticamente a aderência do modelo ao formato desejado.
5. **Contextualização Dinâmica (RAG):** Para tarefas de auditoria, o prompt é dinamicamente enriquecido com informações contextuais, como trechos de NRs recuperados pelo sistema RAG e os dados já extraídos do documento.

## 2. Catálogo de Prompts Principais

### Prompt 1: Extração de Dados de ASO (Gemini 2.5 Flash)

- **Módulo:** `operations/employee.py`
- **Função:** `analyze_aso_pdf()`
- **Objetivo:** Extrair informações estruturadas de um PDF de ASO de forma rápida e barata.

```json
{
    "prompt_template": "Você é um assistente de extração de dados para documentos de Saúde e Segurança do Trabalho. Sua tarefa é analisar o ASO em PDF e extrair as informações abaixo.\nREGRAS OBRIGATÓRIAS:\n1. Responda APENAS com um bloco de código JSON válido. Não inclua a palavra 'json' ou qualquer outro texto antes ou depois do bloco JSON.\n2. Para todas as chaves de data, use ESTRITAMENTE o formato DD/MM/AAAA.\n3. Se uma informação não for encontrada de forma clara e inequívoca, o valor da chave correspondente no JSON deve ser null.\n4. IMPORTANTE: Os valores das chaves no JSON NÃO DEVEM conter o nome da chave. ERRADO: \"cargo\": \"Cargo: Operador\" CORRETO: \"cargo\": \"Operador\"\nJSON a ser preenchido:\n\n{\n  \"data_aso\": \"A data de emissão ou realização do exame clínico. Formato: DD/MM/AAAA.\",\n  \"vencimento_aso\": \"A data de vencimento explícita no ASO, se houver. Formato: DD/MM/AAAA.\",\n  \"riscos\": \"Uma string contendo os riscos ocupacionais listados, separados por vírgula.\",\n  \"cargo\": \"O cargo ou função do trabalhador.\",\n  \"tipo_aso\": \"O tipo de exame. Identifique como um dos seguintes: 'Admissional', 'Periódico', 'Demissional', 'Mudança de Risco', 'Retorno ao Trabalho', 'Monitoramento Pontual'.\"\n}\n"
}
```

### Prompt 3: Auditoria Avançada de Documento (Gemini 2.5 Pro + RAG)

- **Módulo:** `analysis/nr_analyzer.py`
- **Função:** `_get_advanced_audit_prompt()`
- **Objetivo:** Realizar uma auditoria de conformidade profunda, utilizando contexto de RAG para embasar as conclusões.

```python
# Este é um pseudo-código que monta o prompt final
def _get_advanced_audit_prompt(doc_info, relevant_knowledge):
        doc_type = doc_info.get("type")
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        checklist_instrucoes = get_checklist_for_doc_type(doc_type)
        json_example = get_json_example_for_doc_type(doc_type)

        prompt = f"""
        **Persona:** Você é um Auditor Líder de SST...

        **Contexto Crítico:** A data de hoje é **{data_atual}**.

        **Base de Conhecimento Normativa (Fonte da Verdade):**
        ---
        {relevant_knowledge}  # <-- CONTEÚDO DO RAG É INJETADO AQUI
        ---

        **Sua Tarefa (Regras de Análise):**
        1.  **Análise Crítica:** Use o **Checklist de Auditoria** abaixo...
                {checklist_instrucoes}
        
        2.  **Formatação da Resposta:** Apresente suas conclusões no seguinte formato JSON ESTRITO.
        
        3.  **Justificativa Robusta com Evidências:** ...a chave "referencia_normativa" DEVE ser preenchida com o item encontrado na **'Base de Conhecimento Normativa'**...

        **Estrutura JSON de Saída Obrigatória:**
        ```json
        {
            "parecer_final": "Conforme | Não Conforme | Conforme com Ressalvas",
            "resumo_executivo": "...",
            "pontos_de_nao_conformidade": [
                {
                    "item": "...",
                    "referencia_normativa": "...",
                    "observacao": "..."
                }
            ]
        }
        ```
        """
        return prompt
```

# 🤖 Modelos de IA Utilizados

## 1. Modelo de Extração: `gemini-2.5-flash`

- **Chave de API:** `GEMINI_EXTRACTION_KEY` em `.streamlit/secrets.toml`
- **Responsabilidade Principal:** Extração de dados estruturados a partir de documentos PDF
- **Tarefas:**
    - Análise de ASOs
    - Análise de Certificados de Treinamento
    - Análise de Documentos da Empresa
    - Análise de Fichas de EPI

### Por que `gemini-2.5-flash`?

1. **Velocidade:** Otimizado para baixa latência (5-15 segundos)
2. **Custo-Benefício:** Menor custo por token
3. **Janela de Contexto Ampla:** 1 milhão de tokens
4. **Capacidade Suficiente:** Excelente precisão para extração estruturada

## 2. Modelo de Auditoria: `gemini-2.5-pro`

- **Chave de API:** `GEMINI_AUDIT_KEY` em `.streamlit/secrets.toml`
- **Responsabilidade Principal:** Análise complexa e auditoria de conformidade
- **Tarefas:**
    - Auditoria de conformidade
    - Geração de recomendações para Matriz de Treinamentos

### Por que `gemini-2.5-pro`?

1. **Raciocínio Avançado:** Superior em tarefas multi-etapas
2. **Instruções Complexas:** Melhor capacidade de seguir diretrizes detalhadas
3. **Qualidade da Resposta:** Geração de texto mais sofisticada
4. **Uso Menos Frequente:** Custo justificado pela qualidade

## 3. Modelo de Embedding: `models/text-embedding-004`

- **Chave de API:** Usa `GEMINI_AUDIT_KEY`
- **Responsabilidade Principal:** Conversão texto-vetor
- **Tarefas:**
    - Geração offline de embeddings
    - Busca semântica em tempo real

### Por que `text-embedding-004`?

1. **Estado da Arte:** Otimizado para RAG
2. **Eficiência:** Bom equilíbrio custo-qualidade
3. **Compatibilidade:** Integração perfeita com Gemini

## Resumo da Estratégia

| Tarefa | Modelo | Justificativa |
|--------|--------|---------------|
| Extrair dados ASO | `gemini-2.5-flash` | Rápido e preciso |
| Auditar PGR | `gemini-2.5-pro` | Raciocínio complexo |
| Vetorizar NR | `text-embedding-004` | Otimizado para RAG |

---
**Próximo Documento:** [Manual do Usuário](./USER_MANUAL.md)
