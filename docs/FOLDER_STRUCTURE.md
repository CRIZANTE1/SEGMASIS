# 📂 Estrutura de Pastas

Esta é a estrutura de diretórios do projeto SEGMA-SIS, projetada para separar as responsabilidades e facilitar a navegação e manutenção do código.

segma-sis/
├── .streamlit/
│   ├── config.toml           # Configurações do Streamlit (tema, servidor)
│   └── secrets.toml          # ⚠️ (NÃO VERSIONADO) Chaves de API e credenciais
│
├── AI/
│   ├── __init__.py           # Exporta classes principais
│   ├── api_load.py           # Carrega os modelos Gemini (Flash e Pro)
│   └── api_Operation.py      # Classe PDFQA - Interface para chamadas de IA
│
├── analysis/
│   └── nr_analyzer.py        # Sistema RAG + Auditoria de conformidade NR
│
├── auth/
│   ├── __init__.py           # Exporta funções de autenticação
│   ├── auth_utils.py         # Autenticação OIDC e controle de permissões
│   └── login_page.py         # Componentes de UI para login/logout
│
├── docs/                     # 📚 DOCUMENTAÇÃO DO PROJETO
│   ├── README.md             # Índice da documentação
│   ├── ARCHITECTURE.md       # Arquitetura do sistema
│   ├── DATABASE_SCHEMA.md    # Schema do banco de dados
│   ├── FOLDER_STRUCTURE.md   # Este arquivo
│   ├── API_REFERENCE.md      # Referência das APIs
│   ├── INSTALLATION.md       # Guia de instalação
│   ├── QUICKSTART.md         # Início rápido
│   ├── USER_MANUAL.md        # Manual do usuário
│   ├── TROUBLESHOOTING.md    # Resolução de problemas
│   ├── SECURITY.md           # Políticas de segurança
│   ├── NR_MATRIX.md          # Matriz de NRs e validações
│   └── MIGRATION_GUIDE.md    # Guia de migração
│
├── front/
│   ├── administracao.py      # Página de administração (apenas admins)
│   ├── dashboard.py          # Dashboard principal de conformidade
│   └── plano_de_acao.py      # Gestão do plano de ação
│
├── managers/                 # 🔧 CAMADA DE GERENCIAMENTO
│   ├── __init__.py
│   ├── google_api_manager.py # Wrapper para Supabase Storage (compatibilidade)
│   ├── matrix_manager.py     # Gerencia dados GLOBAIS (usuários, unidades)
│   ├── supabase_config.py    # Configuração do cliente Supabase
│   └── supabase_storage.py   # Upload/download de arquivos no Storage
│
├── operations/               # 🧠 CAMADA DE NEGÓCIO
│   ├── action_plan.py        # Manager do Plano de Ação
│   ├── audit_logger.py       # Registro de ações do sistema (log de auditoria)
│   ├── cached_loaders.py     # Carregamento otimizado com cache (TTL 10min)
│   ├── company_docs.py       # Manager de Documentos da Empresa (PGR, PCMSO)
│   ├── employee.py           # Manager de Funcionários, ASOs e Treinamentos
│   ├── epi.py                # Manager de Fichas de EPI
│   ├── file_hash.py          # Cálculo de hash SHA-256 (anti-duplicação)
│   ├── sheet.py              # 🗑️ (LEGADO) Google Sheets - será removido
│   ├── supabase_operations.py # Camada de acesso a dados (Repository Pattern)
│   ├── training_matrix_manager.py # Manager da Matriz de Treinamentos por Unidade
│   └── utils.py              # Funções utilitárias gerais
│
├── scripts/                  # 🛠️ SCRIPTS DE MANUTENÇÃO
│   ├── add_id_funcionario_plano.py # Migração: adiciona id_funcionario no plano
│   ├── hash_migration.py     # Migração: adiciona coluna arquivo_hash
│   └── migrate_to_supabase.py # Migração completa Google Sheets → Supabase
│
├── ui/                       # 🎨 COMPONENTES DE INTERFACE
│   ├── metrics.py            # Widgets de métricas (dashboard cards)
│   └── ui_helpers.py         # Helpers de UI (highlight, dialogs, callbacks)
│
├── .cursorignore             # Arquivos ignorados pelo Cursor AI
├── .gitignore                # Arquivos ignorados pelo Git
├── LICENSE.txt               # Licença proprietária
├── README.md                 # README principal do projeto
├── requirements.txt          # Dependências Python
├── Segsisone.py              # 🚀 PONTO DE ENTRADA DA APLICAÇÃO
├── email_notifier.py         # Script de notificações automáticas (GitHub Actions)
├── rag_dataframe.pkl         # ⚠️ (NÃO VERSIONADO) Base de conhecimento RAG
└── rag_embeddings.npy        # ⚠️ (NÃO VERSIONADO) Vetores de embedding

*(Nota: Algumas pastas e arquivos legados ou de migração foram omitidos para clareza).*

---

## 📖 Descrição Detalhada dos Módulos

### 🚀 `Segsisone.py` (Ponto de Entrada)
É o orquestrador principal da aplicação.
- **Responsabilidades:**
  - Inicializa a aplicação Streamlit e as configurações da página.
  - Gerencia o fluxo de autenticação e a sessão do usuário.
  - Controla a navegação entre as páginas (Dashboard, Administração, etc.).
  - Inicializa os *managers* específicos da unidade operacional selecionada.
  - Implementa a troca de contexto de unidade para administradores (multi-tenancy).

### 🔐 `.streamlit/` (Configurações)
- **`secrets.toml`**: (⚠️ **NÃO VERSIONAR**) Arquivo crítico que armazena todas as credenciais sensíveis, como chaves do Supabase e do Google Gemini.

### 🤖 `AI/` (Inteligência Artificial)
- **`api_load.py`**: Carrega e configura os dois modelos Gemini (`gemini-1.5-flash` para extração, `gemini-1.5-pro` para auditoria) com suas respectivas chaves de API.
- **`api_Operation.py`**: Contém a classe `PDFQA`, uma interface unificada que implementa o **Strategy Pattern** para selecionar o modelo de IA correto com base na complexidade da tarefa (`task_type`).

### 🔍 `analysis/` (Análise e Auditoria)
- **`nr_analyzer.py`**: Implementa o sistema **RAG (Retrieval-Augmented Generation)**.
  - **RAG System**: Busca semanticamente em uma base de conhecimento de NRs (`rag_dataframe.pkl` e `rag_embeddings.npy`) para encontrar os trechos mais relevantes para uma auditoria.
  - **Auditoria**: Executa a função `perform_initial_audit()`, que gera prompts contextualizados com o conhecimento do RAG para validar a conformidade dos documentos, retornando um JSON estruturado.
  - **Plano de Ação**: Aciona a criação automática de itens de ação (`create_action_plan_from_audit()`) em caso de não conformidades.

### 🔐 `auth/` (Autenticação e Autorização)
- **`auth_utils.py`**: Funções centrais que verificam o status de login (OIDC), autenticam o usuário na base de dados, recuperam sua `role` (admin, editor, viewer) e seu `unit_id`.
- **`login_page.py`**: Renderiza os componentes de UI para o fluxo de login e o botão de logout.

### 📊 `front/` (Páginas da Aplicação)
Contém a lógica de renderização de cada página principal.
- **`dashboard.py`**: Dashboard principal, onde os usuários visualizam a conformidade e realizam o upload de documentos, disparando todo o fluxo de análise com IA.
- **`administracao.py`**: Painel de administração com visão global, gestão de usuários/unidades e logs de auditoria.
- **`plano_de_acao.py`**: Interface para gerenciar e tratar as não conformidades geradas pelas auditorias.

### 🔧 `managers/` (Gerenciamento Global)
- **`matrix_manager.py`**: Gerencia dados **globais** do sistema, como a lista de `usuarios` e `unidades`. É cacheado por 5 minutos para performance.

### 🧠 `operations/` (Camada de Negócio - Managers de Unidade)
Classes que encapsulam as regras de negócio para entidades específicas **dentro de uma unidade**.
- **`employee.py`**: Manager principal para funcionários, ASOs e treinamentos. Contém a lógica de análise de PDFs, validação de carga horária, cálculo de vencimentos e otimizações de performance com índices Pandas.
- **`company_docs.py`**: Manager para documentos da empresa (PGR, PCMSO).
- **`epi.py`**: Manager para fichas de EPI.
- **`action_plan.py`**: Manager para o plano de ação.
- **`training_matrix_manager.py`**: Manager para a matriz de treinamentos da unidade. Implementa fuzzy matching para cargos e *lazy loading* para dados.
- **`cached_loaders.py`**: Ponto central para carregamento de dados do Supabase, com cache de 10 minutos (`@st.cache_data(ttl=600)`), garantindo performance e consistência.
- **`audit_logger.py`**: Função `log_action` que registra todas as ações importantes no banco de dados.
- **`file_hash.py`**: Utilitário para calcular hash SHA-256 de arquivos para detecção de duplicatas.

### 🗄️ `storage/` (Camada de Persistência)
Abstrações para interagir com o backend Supabase.
- **`supabase_config.py`**: Configura e inicializa o cliente Supabase (usando o padrão Singleton).
- **`supabase_operations.py`**: Implementa o **Repository Pattern**, abstraindo as operações de CRUD (Create, Read, Update, Delete) no banco de dados PostgreSQL. Garante o isolamento multi-tenant adicionando/filtrando por `unit_id` em todas as operações.
- **`supabase_storage.py`**: Gerencia o upload, download e exclusão de arquivos no Supabase Storage, organizando os arquivos por `unit_id/doc_type/YYYY-MM/`.

### 🎨 `ui/` (Componentes de Interface)
Módulos com funções e componentes de UI reutilizáveis.
- **`metrics.py`**: Funções que calculam e renderizam os cards de métricas.
- **`ui_helpers.py`**: Funções auxiliares, como estilização de tabelas (`highlight_expired`) e os callbacks dos uploaders de arquivo (`process_aso_pdf`, etc.).

### 📧 `email_notifier.py` (Notificações)
- Script autônomo projetado para ser executado como uma tarefa agendada (ex: GitHub Actions cron job). Ele percorre todas as unidades, identifica documentos vencidos ou próximos do vencimento e envia relatórios por e-mail via SMTP.