# 🏗️ Arquitetura do Sistema SEGMA-SIS

## 1. Visão Geral

O SEGMA-SIS é projetado como uma **aplicação web multi-tenant**, onde cada "tenant" (ou inquilino) é uma unidade operacional. A arquitetura é centrada em serviços de nuvem para garantir escalabilidade, segurança e manutenibilidade.

O sistema é dividido em quatro camadas principais:
1.  **Camada de Apresentação (Frontend):** A interface com o usuário, construída com Streamlit.
2.  **Camada de Lógica de Negócio (Backend):** O núcleo da aplicação, escrito em Python, que orquestra os dados e as operações.
3.  **Camada de Inteligência (IA):** Responsável pela extração e auditoria de documentos, utilizando o Google Gemini.
4.  **Camada de Persistência (Dados):** Onde os dados são armazenados e gerenciados, utilizando o Supabase.

## 2. Diagrama de Arquitetura

┌─────────────────────────────────────────────────────────────┐
│ CAMADA DE APRESENTAÇÃO │
│ (Streamlit Frontend) │
│ Responsável pela UI, interação com o usuário e visualização │
├─────────────────────────────────────────────────────────────┤
│ • Dashboard de Conformidade • Painel de Administração │
│ • Formulários de Upload • Visualização de Pendências │
│ • Plano de Ação Interativo • Gerenciamento de Registros │
└──────────────────────────┬──────────────────────────────────┘
│ (Interação do Usuário)
┌──────────────────────────▼──────────────────────────────────┐
│ CAMADA DE LÓGICA DE NEGÓCIO │
│ (Python - "Managers") │
│ Orquestra as regras de negócio e a comunicação entre camadas │
├─────────────────────────────────────────────────────────────┤
│ │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
│ │ Employee │ │ CompanyDocs │ │ ActionPlan │ │
│ │ Manager │ │ Manager │ │ Manager │ │
│ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ │
│ │ │ │ │
└──────────┼──────────────────┼──────────────────┼─────────────┘
│ (Chamadas de API)│(Chamadas de API) │ (Chamadas de API)
┌──────────▼──────────────────▼──────────────────▼─────────────┐
│ CAMADA DE PERSISTÊNCIA │
│ (Supabase Backend) │
│ Armazena dados estruturados, arquivos e gerencia auth │
├─────────────────────────────────────────────────────────────┤
│ │
│ ┌────────────────────┐ ┌────────────────────┐ ┌─────────┐│
│ │ PostgreSQL DB │ │ Storage (S3) │ │ Auth ││
│ │ • Tabelas de Dados │ │ • PDFs (ASOs, etc.)│ │ • OIDC ││
│ │ • RLS Policies │ │ • URLs Assinadas │ │ • Roles ││
│ └────────────────────┘ └────────────────────┘ └─────────┘│
│ │
└─────────────────────────────────────────────────────────────┘

*Diagrama simplificado do fluxo principal. A camada de IA é chamada pela Camada de Negócio durante o processo de upload.*

## 3. Stack Tecnológica

| Camada         | Tecnologia                  | Propósito                                                   |
|----------------|-----------------------------|-------------------------------------------------------------|
| **Frontend**   | Streamlit 1.33+             | Framework para a interface web interativa.                  |
| **Backend**    | Python 3.9+                 | Linguagem principal para a lógica de negócio.               |
| **Banco de Dados** | Supabase (PostgreSQL 15)    | Armazenamento de dados estruturados, relacionais e seguros. |
| **Armazenamento** | Supabase Storage            | Armazenamento de arquivos (PDFs de documentos).             |
| **Autenticação** | Supabase Auth (OIDC)        | Login seguro via Google e gerenciamento de usuários.        |
| **IA (Extração)** | Google Gemini 1.5 Flash   | Extração rápida e de baixo custo de informações de PDFs.    |
| **IA (Auditoria)** | Google Gemini 1.5 Pro     | Análise complexa e auditoria de conformidade (RAG).         |
| **Bibliotecas Chave** | Pandas, Scikit-learn, Fuzzywuzzy | Manipulação de dados, busca semântica e matching de strings. |

## 4. Padrões de Design Aplicados

A estrutura do código segue padrões que promovem a organização e a manutenibilidade.

#### **Manager Pattern**
- **O quê:** Classes como `EmployeeManager`, `CompanyDocsManager` e `MatrixManager` encapsulam a lógica de negócio para uma entidade específica.
- **Por quê:** Centraliza as regras de negócio, facilitando a manutenção e evitando a duplicação de código. Cada "Manager" é responsável por todas as operações (CRUD, análises, validações) relacionadas à sua entidade.

#### **Repository Pattern (Abstração de Dados)**
- **O quê:** A classe `SupabaseOperations` atua como uma camada de abstração entre os "Managers" e o banco de dados.
- **Por quê:** Isola a lógica de negócio da implementação específica do banco de dados. Se um dia o backend for trocado do Supabase para outro serviço, apenas a classe `SupabaseOperations` precisaria ser reescrita, sem impactar os "Managers".

#### **Caching Strategy**
- **O quê:** Uso extensivo do decorador `@st.cache_data` do Streamlit.
- **Por quê:** Reduz drasticamente o número de chamadas ao banco de dados, melhorando a performance e a responsividade da aplicação. Funções como `load_all_unit_data` carregam os dados uma vez e os mantêm em cache por um tempo determinado (TTL).

#### **Strategy Pattern (para IA)**
- **O quê:** A classe `PDFQA` seleciona dinamicamente qual modelo de IA (`extraction_model` ou `audit_model`) usar com base no `task_type`.
- **Por quê:** Permite usar o modelo mais adequado (e com o melhor custo-benefício) para cada tarefa, sem que o código que a chama precise conhecer os detalhes de cada modelo.

## 5. Segurança

A segurança é um pilar fundamental da arquitetura.

- **Isolamento de Dados (Multi-Tenancy):**
  - **RLS (Row Level Security):** O Supabase impõe que cada consulta ao banco de dados seja filtrada pelo `unit_id` do usuário autenticado. Isso garante que uma unidade **nunca** possa ver os dados de outra.
  - **Validação de Acesso:** A aplicação verifica a `role` ('admin', 'editor', 'viewer') do usuário para permitir ou bloquear ações específicas.

- **Gestão de Segredos:**
  - As chaves de API são gerenciadas exclusivamente através do `st.secrets` (arquivo `secrets.toml`), que nunca é versionado no Git.

- **Armazenamento de Arquivos:**
  - Os arquivos no Supabase Storage podem ser configurados como privados, sendo acessados apenas por meio de URLs assinadas com tempo de expiração, evitando acesso público não autorizado.

---
**Próximo Documento:** [Estrutura de Pastas](./FOLDER_STRUCTURE.md)