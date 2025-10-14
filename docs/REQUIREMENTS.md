# 📋 Requisitos do Sistema

Este documento especifica os requisitos de software, hardware e serviços de nuvem necessários para o desenvolvimento e implantação do sistema SEGMA-SIS.

## Requisitos para Desenvolvimento Local

Estes são os requisitos para configurar e executar o projeto em uma máquina de desenvolvimento.

### Software
- **Sistema Operacional:**
  - Windows 10/11
  - macOS 12 (Monterey) ou superior
  - Linux (Ubuntu 20.04+, Debian 11+, etc.)
- **Python:**
  - Versão: **3.9 a 3.11**. A versão 3.10 é a recomendada.
  - Ferramenta de ambiente virtual (ex: `venv`, `conda`).
- **Git:**
  - Versão 2.30 ou superior para controle de versão.
- **Navegador Web Moderno:**
  - Google Chrome (recomendado)
  - Mozilla Firefox
  - Microsoft Edge

### Hardware (Mínimo Recomendado)
- **Processador:** Dual-core 2.0 GHz ou superior.
- **Memória RAM:** 8 GB (16 GB recomendados para um desempenho mais fluido, especialmente ao lidar com a base de conhecimento RAG).
- **Armazenamento:** 5 GB de espaço livre em disco para o código-fonte, dependências e arquivos de cache.

## Requisitos para Implantação (Produção)

Estes são os requisitos para hospedar a aplicação para usuários finais.

### Plataforma de Hospedagem
- **Streamlit Community Cloud:**
  - **Tipo:** Plataforma gerenciada (PaaS), ideal para o projeto.
  - **Recursos:** O plano gratuito é suficiente para iniciar, mas pode ser necessário um upgrade dependendo do tráfego de usuários.
  - **Requisitos Adicionais:** Conta no GitHub para vincular o repositório.

### Serviços de Backend e APIs
- **Supabase:**
  - **Plano:** O plano gratuito (`Free Tier`) é suficiente para desenvolvimento e uso moderado, incluindo:
    - Banco de dados PostgreSQL.
    - 500 MB de armazenamento de arquivos (Storage).
    - 50.000 invocações de Edge Functions por mês.
    - Autenticação de usuários.
  - **Observação:** Monitore o uso do armazenamento. Pode ser o primeiro limite a ser atingido.
- **Google Cloud Platform (para Gemini API):**
  - **Serviço:** Google AI Platform / Vertex AI.
  - **API:** Gemini API (`gemini-1.5-flash`, `gemini-1.5-pro`).
  - **Plano:** Requer uma conta Google Cloud com faturamento ativado. O uso da API é cobrado com base no consumo (tokens de entrada/saída). Há um nível de uso gratuito generoso para começar.
  - **Credenciais:** Requer a criação de chaves de API.

## Dependências de Software (Python)

A lista completa de bibliotecas Python está no arquivo [`requirements.txt`](../requirements.txt). As principais são:

| Biblioteca            | Versão Mínima | Propósito                                       |
|-----------------------|---------------|-------------------------------------------------|
| `streamlit`           | 1.33.0        | Framework principal da aplicação web.           |
| `supabase`            | 2.0.0         | Cliente oficial para interagir com o Supabase.  |
| `google-generativeai` | 0.5.4         | Cliente para a API do Google Gemini.            |
| `pandas`              | 2.0.0         | Manipulação e análise de dados em memória.      |
| `scikit-learn`        | 1.3.0         | Usado para cálculo de similaridade de cossenos (RAG). |
| `gspread`             | 5.12.0        | Interação com Google Sheets (scripts de migração). |
| `python-dotenv`       | 1.0.0         | Carregamento de variáveis de ambiente localmente. |
| `fuzzywuzzy`          | 0.18.0        | Correspondência aproximada de strings (cargos). |

---
*Verifique sempre o arquivo `requirements.txt` para a lista mais atualizada de dependências e versões exatas.*