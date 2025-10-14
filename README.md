# 📚 Documentação do SEGMA-SIS

**Sistema de Gestão Inteligente para Contratadas**

Bem-vindo à documentação central do SEGMA-SIS. Esta pasta contém todos os guias técnicos, de arquitetura e operacionais necessários para entender, desenvolver, manter e utilizar o sistema de forma eficaz.

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
- **[Modelos Utilizados](./AI_MODELS.md):** Especificações dos modelos do Google Gemini e suas responsabilidades.

### 📋 Operacional
- **[Manual do Usuário](./USER_MANUAL.md):** Guia não técnico para usuários finais sobre como operar o sistema.
- **[FAQ - Perguntas Frequentes](./FAQ.md):** Respostas para as dúvidas mais comuns.
- **[Troubleshooting](./TROUBLESHOOTING.md):** Como diagnosticar e resolver problemas comuns.

### 🔐 Segurança
- **[Políticas de Segurança](./SECURITY.md):** Visão geral das medidas de segurança implementadas.
- **[Gestão de Secrets](./SECRETS_MANAGEMENT.md):** Procedimento correto para gerenciar chaves de API e credenciais.
- **[Controle de Acesso](./ACCESS_CONTROL.md):** Detalhes sobre os papéis (roles) de usuário e suas permissões.

### 📊 Regras de Negócio
- **[Matriz de NRs](./NR_MATRIX.md):** Tabela de Normas Regulamentadoras cobertas pelo sistema.
- **[Validação de Carga Horária](./CH_VALIDATION.md):** Regras de negócio para validar a carga horária de treinamentos.
- **[Regras de Vencimento](./EXPIRATION_RULES.md):** Lógica para o cálculo de vencimento de documentos e treinamentos.

## 🌐 Links Úteis

- **Sistema em Produção:** [https://segma-sis.streamlit.app](https://segma-sis.streamlit.app)
- **Painel do Supabase:** [https://supabase.com/dashboard](https://supabase.com/dashboard)
- **Google AI Studio (Gemini):** [https://aistudio.google.com/](https://aistudio.google.com/)

## 📞 Suporte

Para suporte técnico ou dúvidas, contate:
- **Autor:** Cristian Ferreira Carlos
- **E-mail:** cristianfc2015@hotmail.com
- **LinkedIn:** [https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/](https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/)

---
*Esta documentação é um documento vivo e deve ser atualizada conforme o sistema evolui.*

**Última Atualização:** 24 de Maio de 2024