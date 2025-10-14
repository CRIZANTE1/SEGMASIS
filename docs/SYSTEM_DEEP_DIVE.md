# 📖 Descrição Detalhada dos Módulos e Fluxos

Este documento oferece um mergulho profundo na estrutura de código, responsabilidades dos módulos e fluxos de dados do sistema SEGMA-SIS.

## 🚀 `Segsisone.py` (Ponto de Entrada)

É o orquestrador principal da aplicação Streamlit.

### Responsabilidades
- Inicializa a página e as configurações globais do Streamlit
- Gerencia o fluxo de autenticação e a sessão do usuário via OIDC
- Controla a navegação entre as páginas principais (Dashboard, Administração, Plano de Ação)
- Inicializa os *managers* específicos da unidade operacional selecionada
- Implementa o sistema multi-tenant para troca de contexto entre unidades

### Fluxo Principal
1. Verifica a autenticação OIDC (`st.login()`)
2. Autentica o usuário na base de dados (`auth_utils.authenticate_user()`)
3. Carrega o contexto da unidade (`unit_id`) associada ao usuário
4. Inicializa os *managers* (`EmployeeManager`, `DocsManager`, etc.) com o `unit_id` correto
5. Renderiza a página selecionada no menu lateral

## 🔐 `.streamlit/` (Configurações)

Contém arquivos de configuração específicos do Streamlit.

### `secrets.toml` (⚠️ NUNCA VERSIONAR)

Arquivo crítico que armazena todas as credenciais sensíveis.

**Estrutura Esperada:**
```toml
# Chaves para conexão com o banco de dados e APIs
[supabase]
url = "https://xxx.supabase.co"
key = "eyJhbGc..."
service_role_key = "eyJhbGc..."  # ⚠️ ADMIN - Usar com cuidado

# Chaves para os modelos de Inteligência Artificial
[general]
GEMINI_EXTRACTION_KEY = "AIzaSy..."  # Usado pelo Gemini 1.5 Flash
GEMINI_AUDIT_KEY = "AIzaSy..."       # Usado pelo Gemini 1.5 Pro
```

## 🤖 `AI/` (Inteligência Artificial)

Módulo responsável por toda a interação com a API do Google Gemini.

### `api_load.py`
Carrega e configura os dois modelos Gemini com chaves de API separadas.

### `api_Operation.py`
Contém a classe `PDFQA` - interface unificada para todas as chamadas de IA.

#### Métodos Principais
- `answer_question(pdf_files, question, task_type='extraction')`: Roteador de modelos
- `_generate_response(model, pdf_files, question)`: Prepara requisições para API

## 🔍 `analysis/` (Análise e Auditoria)

### `nr_analyzer.py`
Implementa o sistema RAG e lógica de auditoria de conformidade.

#### Componentes
- **Sistema RAG**:
    - Busca semântica por similaridade de cossenos
    - Utiliza embeddings pré-calculados
    - Modelo: `text-embedding-004`
- **Auditoria**:
    - `perform_initial_audit()`: Valida conformidade com NRs
    - Gera prompts dinâmicos com contexto RAG
- **Plano de Ação**:
    - `create_action_plan_from_audit()`: Automatiza criação de ações

## 🔐 `auth/` (Autenticação e Autorização)

### `auth_utils.py`
Funções centrais para gestão de acesso e permissões.

#### Funções Principais
```python
is_user_logged_in() -> bool            # Verifica sessão OIDC
authenticate_user() -> bool            # Valida email
get_user_role() -> str                # Retorna nível de acesso
check_permission(level='editor')      # Valida permissão
get_user_unit_id() -> str | None      # Retorna ID da unidade
```

#### Hierarquia de Permissões
- **admin**: Acesso total e gestão de usuários
- **editor**: Gerencia documentos da unidade
- **viewer**: Acesso somente leitura

### `login_page.py`
Componentes UI para fluxo de login/logout

## 📊 `front/` (Páginas da Aplicação)

### `dashboard.py`
Dashboard principal de conformidade

#### Seções
- **Situação Geral**: Visão completa da empresa
- **Adicionar Documentos**: Upload e análise de documentos
- **Gerenciar Registros**: Interface para exclusão

#### Fluxo de Upload
1. Upload do PDF
2. Análise automática (callback)
3. Extração de dados (Gemini Flash)
4. Auditoria de conformidade (Gemini Pro + RAG)
5. Confirmação do usuário
6. Persistência dos dados
7. Criação de ações se necessário

### `administracao.py`
Interface administrativa (role: admin)

#### Funcionalidades
- Dashboard Global consolidado
- Logs de Auditoria
- Gestão de Usuários/Unidades
- Configuração da Matriz

### `plano_de_acao.py`
Gestão de não conformidades

#### Funcionalidades
- Visualização/filtragem de pendências
- Tratamento de não conformidades
- Acompanhamento de status
- Acesso aos documentos originais
