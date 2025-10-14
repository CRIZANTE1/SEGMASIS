# 🌊 Diagrama de Fluxo de Dados

Este documento detalha os principais fluxos de dados do sistema SEGMA-SIS, com foco no processo de ponta a ponta de upload e análise de um documento.

## Fluxo Principal: Upload e Análise de Documento (ASO)

Este é o fluxo mais complexo e crítico do sistema. Ele combina interação do usuário, armazenamento de arquivos, múltiplas chamadas de IA e persistência de dados.

### Diagrama de Sequência

```mermaid
sequenceDiagram
    participant User as Usuário (Frontend)
    participant Dashboard as front/dashboard.py
    participant Callbacks as ui/ui_helpers.py
    participant EmployeeMgr as operations/employee.py
    participant NRAnalyzer as analysis/nr_analyzer.py
    participant Supabase as Backend (DB + Storage)

    User->>Dashboard: 1. Faz upload de um arquivo PDF (ASO)
    Dashboard->>Callbacks: 2. Aciona on_change=process_aso_pdf()
    Callbacks-->>Callbacks: 3. Calcula Hash SHA-256 do arquivo
    Callbacks-->>Dashboard: 4. Armazena PDF e hash no st.session_state
    Dashboard->>EmployeeMgr: 5. Chama analyze_aso_pdf(pdf)
    EmployeeMgr->>AI (Gemini Flash): 6. Envia PDF para extração de dados
    AI (Gemini Flash)-->>EmployeeMgr: 7. Retorna dados estruturados (JSON)
    EmployeeMgr-->>Dashboard: 8. Retorna dados extraídos
    Dashboard->>NRAnalyzer: 9. Chama perform_initial_audit(dados, pdf)
    NRAnalyzer->>NRAnalyzer: 10. Busca semântica (RAG) na base de conhecimento
    NRAnalyzer->>AI (Gemini Pro): 11. Envia PDF + Dados + Contexto RAG para auditoria
    AI (Gemini Pro)-->>NRAnalyzer: 12. Retorna parecer de conformidade (JSON)
    NRAnalyzer-->>Dashboard: 13. Retorna resultado da auditoria
    Dashboard->>User: 14. Exibe dados extraídos e resultado da auditoria para confirmação
    User->>Dashboard: 15. Clica em "Confirmar e Salvar"
    Dashboard->>Supabase: 16. Faz upload do arquivo PDF para o Storage
    Supabase-->>Dashboard: 17. Retorna a URL do arquivo
    Dashboard->>Supabase: 18. Salva os metadados do ASO no PostgreSQL (tabela 'asos')
    Supabase-->>Dashboard: 19. Retorna o ID do novo registro
    alt Se "Não Conforme"
        Dashboard->>Supabase: 20. Cria item(ns) no Plano de Ação (tabela 'plano_acao')
    end
    Dashboard->>User: 21. Exibe mensagem de sucesso e atualiza a UI
```

### Etapas Detalhadas

1. **Upload (Usuário)**
   - O usuário seleciona um arquivo PDF na interface do dashboard.py

2. **Callback on_change**
   - O componente st.file_uploader aciona imediatamente a função de callback process_aso_pdf

3. **Cálculo de Hash**
   - Calcula o hash SHA-256 do arquivo para futura detecção de duplicatas

4. **Armazenamento em Sessão**
   - O objeto do arquivo e seu hash são armazenados no st.session_state

5. **Extração com IA (Flash)**
   - A classe EmployeeManager utiliza o Gemini 1.5 Flash para análise rápida
   - Extrai informações básicas como datas, nomes e tipo de ASO

6. **Auditoria com IA (Pro + RAG)**
   - A classe NRAnalyzer realiza:
     - Busca semântica na base de conhecimento local
     - Monta prompt com documento, dados extraídos e contexto RAG
     - Envia ao Gemini 1.5 Pro para auditoria de conformidade

7. **Confirmação do Usuário**
   - Interface exibe resultados da extração e auditoria
   - Aguarda validação humana das informações

8. **Persistência**
   - Upload do PDF para Supabase Storage
   - Salvamento dos metadados no PostgreSQL
   - Criação condicional de plano de ação (se não conforme)

## Fluxo de Autenticação

1. **Acesso Inicial**
   - Usuário acessa a URL
   - Segsisone.py verifica is_user_logged_in()

2. **Redirecionamento**
   - Se não logado, exibe botão de login Google
   - Redireciona para autenticação OIDC

3. **Callback e Autorização**
   - Retorno pós-login Google
   - authenticate_user() verifica permissões
   - Carrega role e unit_id na sessão

4. **Carregamento de Dados**
   - Inicialização dos managers com unit_id
   - Aplicação de políticas RLS
   - Renderização da página solicitada