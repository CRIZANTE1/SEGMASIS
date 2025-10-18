# 📚 Documentação do SEGMA-SIS

**Sistema de Gestão Inteligente para Contratadas**

Bem-vindo à documentação central do SEGMA-SIS. Esta pasta contém todos os guias técnicos, de arquitetura e operacionais necessários para entender, desenvolver, manter e utilizar o sistema de forma eficaz.

## 🚀 Visão Geral

O SEGMA-SIS é um sistema multi-tenant de gestão de conformidade de Saúde e Segurança do Trabalho, com recursos de IA para auditoria automática de documentos e análise de conformidade com Normas Regulamentadoras brasileiras.

### Arquitetura Atual

- **Frontend:** Streamlit (Python)
- **Backend:** Supabase (PostgreSQL + Storage + Auth)
- **IA:** Google Gemini 2.5 (Flash para extração, Pro para auditoria)
- **Autenticação:** OIDC via Streamlit Cloud
- **Versionamento:** Git + GitHub
- **Deploy:** Streamlit Cloud (produção)

## 📑 Índice de Documentos

### 🚀 Começando
- **[Instalação e Configuração](./INSTALLATION.md):** Guia passo a passo para configurar o ambiente de desenvolvimento local.
- **[Guia de Início Rápido](./QUICKSTART.md):** Execute a aplicação pela primeira vez em menos de 5 minutos.
- **[Requisitos do Sistema](./REQUIREMENTS.md):** Software e hardware necessários para rodar o projeto.

### 🏗️ Arquitetura
- **[Visão Geral da Arquitetura](./ARCHITECTURE.md):** Um olhar aprofundado sobre os componentes do sistema e como eles interagem.
- **[Estrutura de Pastas](./FOLDER_STRUCTURE.md):** Descrição do propósito de cada diretório e arquivo principal.
- **[Diagrama de Fluxo de Dados](./DATA_FLOW.md):** Ilustração dos principais fluxos de dados, como o upload de um documento.

### 🔧 Desenvolvimento
- **[Guia de Contribuição](./CONTRIBUTING.md):** Como contribuir com o projeto, incluindo fluxo de trabalho de git e padrões de pull request.
- **[Padrões de Código](./CODE_STANDARDS.md):** Diretrizes de estilo, linting e boas práticas adotadas no projeto.
- **[API Reference](./API_REFERENCE.md):** Documentação das principais classes e métodos (Managers, Operations, etc.).

### 🗄️ Banco de Dados
- **[Schema do Supabase](./DATABASE_SCHEMA.md):** Descrição detalhada de todas as tabelas, colunas e relacionamentos.
- **[Políticas RLS](./RLS_POLICIES.md):** Explicação das políticas de segurança em nível de linha que garantem o isolamento de dados (multi-tenant).
- **[Migrações](./MIGRATIONS.md):** Histórico e guia para execução de scripts de migração de schema.

### 🤖 Inteligência Artificial
- **[Sistema RAG](./RAG_SYSTEM.md):** Detalhes sobre a implementação do Retrieval-Augmented Generation para auditorias.
- **[Engenharia de Prompts](./AI_PROMPTS.md):** Catálogo dos principais prompts utilizados para extração e auditoria.
- **[Modelos Utilizados](./AI_MODELS.md):** Especificações dos modelos do Google Gemini e suas responsabilidades:
  - **Gemini 2.5 Flash:** Extração rápida de dados (ASOs, Treinamentos, Documentos)
  - **Gemini 2.5 Pro:** Auditorias complexas com RAG

### 📋 Operacional
- **[Manual do Usuário](./USER_MANUAL.md):** Guia não técnico para usuários finais sobre como operar o sistema.
- **[FAQ - Perguntas Frequentes](./FAQ.md):** Respostas para as dúvidas mais comuns.
- **[Troubleshooting](./TROUBLESHOOTING.md):** Como diagnosticar e resolver problemas comuns.

### 🔐 Segurança
- **[Políticas de Segurança](./SECURITY.md):** Visão geral das medidas de segurança implementadas.
- **[Gestão de Secrets](./SECRETS_MANAGEMENT.md):** Procedimento correto para gerenciar chaves de API e credenciais.
- **[Controle de Acesso](./ACCESS_CONTROL.md):** Detalhes sobre os papéis (roles) de usuário e suas permissões:
  - **Admin:** Acesso total, provisiona unidades, gerencia usuários globalmente
  - **Editor:** Gerencia documentos e funcionários dentro de sua unidade
  - **Viewer:** Apenas visualização de dados

### 📊 Regras de Negócio
- **[Matriz de NRs](./NR_MATRIX.md):** Tabela de Normas Regulamentadoras cobertas pelo sistema.
- **[Validação de Carga Horária](./CH_VALIDATION.md):** Regras de negócio para validar a carga horária de treinamentos.
- **[Regras de Vencimento](./EXPIRATION_RULES.md):** Lógica para o cálculo de vencimento de documentos e treinamentos.

## 🛠️ Stack Tecnológica

### Backend & Infraestrutura
- **Supabase** (PostgreSQL 15)
  - Row Level Security (RLS) para multi-tenancy
  - Storage para arquivos PDF
  - Realtime subscriptions (futuro)
  
### Frontend & Interface
- **Streamlit** 1.44.0+
  - OIDC Authentication
  - Session State Management
  - Custom Components (streamlit-option-menu)

### Inteligência Artificial
- **Google Gemini API**
  - Gemini 2.5 Flash (extração)
  - Gemini 2.5 Pro (auditoria)
  - Text Embedding 004 (RAG)
- **Bibliotecas ML**
  - scikit-learn (cosine similarity)
  - fuzzywuzzy (fuzzy matching)

### Processamento de Dados
- **pandas** (manipulação de dados)
- **openpyxl** (Excel - legado)
- **python-dateutil** (parsing de datas)

## 📁 Estrutura de Diretórios
```
SEGMA-SIS/
├── AI/                          # Módulos de Inteligência Artificial
│   ├── api_Operation.py         # PDFQA - orquestrador de análises
│   └── api_load.py              # Carregamento de modelos Gemini
│
├── analysis/                    # Análise e auditoria de documentos
│   └── nr_analyzer.py           # NRAnalyzer com RAG
│
├── auth/                        # Autenticação e autorização
│   ├── auth_utils.py            # Funções utilitárias de autenticação
│   └── login_page.py            # Interface de login OIDC
│
├── front/                       # Páginas da aplicação
│   ├── dashboard.py             # Dashboard principal
│   ├── administracao.py         # Painel administrativo
│   └── plano_de_acao.py         # Gestão de não conformidades
│
├── managers/                    # Gerenciadores de alto nível
│   ├── matrix_manager.py        # Gestão global (usuários/unidades)
│   ├── google_api_manager.py    # Interface com Storage (legado)
│   ├── supabase_config.py       # Configuração do Supabase
│   └── supabase_storage.py      # Gestão de arquivos no Storage
│
├── operations/                  # Operações de negócio
│   ├── employee.py              # Gestão de funcionários
│   ├── company_docs.py          # Documentos da empresa
│   ├── epi.py                   # Fichas de EPI
│   ├── action_plan.py           # Plano de ação
│   ├── supabase_operations.py   # CRUD genérico Supabase
│   ├── cached_loaders.py        # Cache de dados
│   ├── file_hash.py             # Detecção de duplicatas
│   ├── audit_logger.py          # Log de auditoria
│   └── training_matrix_manager.py # Matriz de treinamentos
│
├── ui/                          # Componentes de interface
│   ├── ui_helpers.py            # Helpers de UI
│   └── metrics.py               # Dashboard de métricas
│
├── Segsisone.py                 # Entry point da aplicação
├── email_notifier.py            # Notificações automáticas (GitHub Actions)
├── requirements.txt             # Dependências Python
└── .streamlit/
    └── secrets.toml             # Configurações sensíveis (local)
```

## 🔑 Configuração de Secrets

O sistema requer as seguintes variáveis de ambiente no `.streamlit/secrets.toml`:
```toml
[supabase]
url = "https://seu-projeto.supabase.co"
key = "sua-chave-publica"

[general]
GEMINI_EXTRACTION_KEY = "sua-chave-gemini-flash"
GEMINI_AUDIT_KEY = "sua-chave-gemini-pro"
```

## 🚦 Fluxo de Trabalho Principal

1. **Autenticação:** Usuário faz login via Google OIDC
2. **Carregamento:** Sistema carrega dados da unidade do Supabase (cache 10min)
3. **Upload de Documento:** 
   - IA extrai informações (Gemini Flash)
   - Sistema audita com RAG (Gemini Pro)
   - Arquivo salvo no Supabase Storage
   - Registro salvo no PostgreSQL
4. **Não Conformidades:** Adicionadas automaticamente ao Plano de Ação
5. **Notificações:** GitHub Actions envia alertas de vencimento via e-mail

## 🌐 Links Úteis

- **Sistema em Produção:** [https://segma-sis.streamlit.app](https://segma-sis.streamlit.app)
- **Painel do Supabase:** [https://supabase.com/dashboard](https://supabase.com/dashboard)
- **Google AI Studio (Gemini):** [https://aistudio.google.com/](https://aistudio.google.com/)
- **Repositório:** [GitHub - SEGMA-SIS](https://github.com/seu-usuario/segma-sis)

## 📊 Métricas do Sistema

- **Multi-Tenancy:** Suporte a múltiplas unidades operacionais isoladas
- **Performance:** Cache de 10 minutos para otimizar consultas
- **Segurança:** RLS no nível do banco de dados + OIDC
- **IA:** ~95% de precisão na extração de dados estruturados

## 🔄 Changelog Recente

### v2.0.0 (Janeiro 2025)
- **BREAKING:** Migração completa do Google Drive para Supabase Storage
- **BREAKING:** Substituição de Google Sheets por PostgreSQL
- **NEW:** Sistema de cache otimizado com `@st.cache_data`
- **NEW:** Detecção de duplicatas por hash SHA-256
- **IMPROVED:** Performance 10x mais rápida no carregamento de dados
- **FIXED:** Bugs de sincronização multi-usuário

## 📞 Suporte

Para suporte técnico ou dúvidas, contate:
- **Autor:** Cristian Ferreira Carlos
- **E-mail:** cristianfc2015@hotmail.com
- **LinkedIn:** [Cristian Ferreira Carlos](https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/)

## 📝 Licença

Copyright 2024-2025, Cristian Ferreira Carlos. Todos os direitos reservados.

O uso, redistribuição ou modificação deste código é estritamente proibido sem a permissão expressa do autor.

---

*Esta documentação é um documento vivo e deve ser atualizada conforme o sistema evolui.*

**Última Atualização:** 14 de Outubro de 2025
