# 📋 Manual do Usuário do SEGMA-SIS

Bem-vindo ao **Sistema de Gestão Inteligente para Contratadas (SEGMA-SIS)**!

Este manual é um guia prático para ajudá-lo a utilizar todas as funcionalidades do sistema de forma eficiente.

## 1. Acessando o Sistema

### Fazendo Login
1.  Acesse o link da aplicação: [https://segma-sis.streamlit.app](https://segma-sis.streamlit.app)
2.  Na tela inicial, clique no botão **"Fazer Login com Google"**.
3.  Utilize sua conta de e-mail corporativa que foi previamente cadastrada no sistema.
4.  Após o login, você será direcionado para o Dashboard principal.

### Saindo do Sistema
-   No menu lateral esquerdo, no final, clique no botão **"Sair do Sistema"**.

## 2. Navegação Principal

A navegação do sistema é feita pelo menu localizado na barra lateral esquerda.

-   **Dashboard:** A tela principal para visualização de conformidade e upload de documentos.
-   **Plano de Ação:** Central para gerenciar todas as não conformidades encontradas pela IA.
-   **Administração:** Área restrita para administradores, usada para gerenciar usuários, unidades e configurações globais.

## 3. Dashboard de Conformidade

Esta é a sua área de trabalho principal.

### Selecionando uma Empresa
-   No topo da página, utilize a caixa de seleção **"Selecione uma empresa para ver os detalhes"** para carregar os dados de uma contratada específica.
-   Após selecionar uma empresa, a página será preenchida com todas as informações de documentos e funcionários dela.

### Interpretando a Situação Geral
-   **Documentos da Empresa:** Mostra os documentos como PGR e PCMSO. Linhas destacadas em **vermelho** indicam que o documento está vencido.
-   **Funcionários:** Cada funcionário é listado em uma seção expansível.
    -   O ícone ao lado do nome (✅ ou ⚠️) indica o status geral de conformidade daquele funcionário.
    -   Dentro da seção, você encontrará métricas sobre o **Status do ASO** e **Treinamentos Vencidos**.
    -   As tabelas detalham todos os ASOs e Treinamentos mais recentes, com vencidos também destacados em **vermelho**.
    -   A **Matriz de Conformidade** mostra automaticamente se o funcionário possui todos os treinamentos obrigatórios para o seu cargo.

## 4. Adicionando Documentos (Fluxo com IA)

O processo de adicionar qualquer documento (ASO, Treinamento, etc.) segue um fluxo simples de 3 passos.

1.  **Selecione a Empresa:** Primeiro, escolha a empresa no seletor principal do dashboard.
2.  **Acesse a Aba Correta:** Clique na aba correspondente ao tipo de documento que deseja adicionar (ex: "Adicionar ASO").
3.  **Faça o Upload e Confirme:**
    -   Selecione o funcionário (se aplicável).
    -   Clique para fazer o upload do arquivo PDF.
    -   **Aguarde a análise da IA.** Em segundos, o sistema exibirá as informações que a IA extraiu (datas, nomes, etc.) e o resultado da auditoria.
    -   **Verifique as informações.** Se tudo estiver correto, clique no botão **"Confirmar e Salvar"**.

O documento será salvo e a página será atualizada automaticamente. Se a IA encontrar uma não conformidade, um item será criado no Plano de Ação.

## 5. Gerenciando o Plano de Ação

Esta página lista todas as pendências que precisam de atenção.

1.  **Selecione a Empresa:** Use o seletor para filtrar as pendências de uma empresa específica.
2.  **Visualize as Pendências:** Cada pendência é exibida em um card.
    -   **Item:** Descreve a não conformidade.
    -   **Referência Normativa:** Mostra o item da NR que não foi atendido.
    -   **Status:** Indica o estado atual (`🔴 Aberto`, `🟡 Em Tratamento`, etc.).
    -   **Botão 📄 PDF:** Clique para abrir o documento original que gerou a pendência.
3.  **Tratar uma Pendência:**
    -   Clique no botão **"⚙️ Tratar"**.
    -   Na janela que se abrir, preencha o **Plano de Ação** (o que será feito), o **Responsável** e o **Prazo**.
    -   Atualize o **Status** conforme o andamento (ex: para "Em Tratamento").
    -   Clique em **"💾 Salvar"**.
    -   Quando a pendência for resolvida, volte, mude o status para **"Concluído"** e salve novamente.

## 6. Funcionalidades de Administração (Apenas para Admins)

### Visão Global
-   Na barra lateral, selecione **"Global"** no seletor de unidades.
-   A aba **"Dashboard Global"** na página de Administração mostrará métricas consolidadas de todas as unidades, ideal para uma visão executiva.
-   A aba **"Logs de Auditoria"** mostra um histórico de todas as ações realizadas no sistema.

### Gerenciamento de Usuários e Unidades
-   Na visão **Global**, a aba **"Gerenciamento Global"** permite:
    -   Adicionar novos usuários e definir suas permissões.
    -   Editar ou remover usuários existentes.
    -   Provisionar novas unidades operacionais no sistema.

### Gerenciamento da Matriz de Treinamentos
-   Selecione uma **unidade específica** na barra lateral.
-   Na página de **Administração**, as abas "Gerenciar Matriz" e "Assistente de Matriz (IA)" permitem:
    -   Cadastrar as funções existentes na unidade.
    -   Mapear quais treinamentos são obrigatórios para cada função.
    -   Usar a IA para obter sugestões de treinamentos com base no nome de uma função.

---
**Próximo Documento:** [FAQ - Perguntas Frequentes](./FAQ.md)