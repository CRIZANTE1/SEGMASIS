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
# 🛂 Controle de Acesso (RBAC)

## 1. Visão Geral

O SEGMA-SIS utiliza um modelo de **Controle de Acesso Baseado em Papel (RBAC - Role-Based Access Control)** para gerenciar o que cada usuário pode ver e fazer dentro do sistema. Este modelo é simples, mas eficaz, garantindo que os usuários tenham acesso apenas às funcionalidades necessárias para suas funções, seguindo o **princípio do menor privilégio**.

A `role` (papel) de um usuário é a principal autoridade que define suas permissões.

## 2. Definição dos Papéis (`Roles`)

Existem três papéis definidos no sistema, armazenados na coluna `role` da tabela `public.usuarios`.

### a) `admin` (Administrador)
-   **Descrição:** O nível de permissão mais alto. Geralmente reservado para gestores do sistema ou da área de SST corporativa.
-   **Privilégios:**
    -   **Visão Global:** Pode visualizar os dados consolidados de **todas as unidades operacionais**.
    -   **Troca de Contexto:** Pode operar "como se estivesse" em qualquer unidade específica, selecionando-a no menu lateral.
    -   **Gestão de Usuários:** Pode adicionar, editar e remover usuários do sistema.
    -   **Gestão de Unidades:** Pode provisionar novas unidades operacionais.
    -   **Acesso Total:** Possui permissões de leitura e escrita (`editor`) em todas as unidades.
    -   **Logs:** Acesso completo aos logs de auditoria do sistema.

### b) `editor` (Editor)
-   **Descrição:** O papel padrão para os usuários que gerenciam ativamente a documentação de uma unidade (ex: técnicos de segurança, analistas de SST).
-   **Privilégios:**
    -   **Acesso Restrito à Unidade:** Pode ver e interagir **apenas** com os dados da sua `unidade_associada`. O isolamento é garantido por RLS.
    -   **Leitura e Escrita:** Pode visualizar, adicionar, editar e excluir todos os tipos de registros (empresas, funcionários, documentos) dentro da sua unidade.
    -   **Plano de Ação:** Pode tratar e atualizar os itens do plano de ação da sua unidade.
    -   **Sem Acesso Global:** Não pode ver dados de outras unidades nem acessar as funcionalidades de gerenciamento global.

### c) `viewer` (Visualizador)
-   **Descrição:** Um papel de "somente leitura", ideal for gestores, auditores externos ou clientes que precisam consultar o status de conformidade sem poder alterar nada.
-   **Privilégios:**
    -   **Acesso Restrito à Unidade:** Pode visualizar **apenas** os dados da sua `unidade_associada`.
    -   **Somente Leitura:** Pode navegar pelo dashboard, visualizar documentos e o plano de ação, mas **não verá** botões para adicionar, editar ou excluir registros.
    -   **Sem Permissões de Escrita:** Qualquer tentativa de modificar dados será bloqueada tanto na interface quanto na camada de banco de dados.

## 3. Implementação Técnica

O controle de acesso é implementado em duas camadas principais:

### Camada de Aplicação (Frontend)
-   **Arquivo:** `auth/auth_utils.py`
-   **Funções Chave:**
    -   `get_user_role() -> str`: Retorna a `role` do usuário logado, lida do `st.session_state`.
    -   `check_permission(level='editor')`: Uma função de "guarda". Ela é chamada no início de páginas ou seções que exigem um certo nível de permissão. Se o usuário não atender ao requisito, a função exibe uma mensagem de erro e interrompe a execução da página com `st.stop()`.

    ```python
    # Exemplo de uso em front/administracao.py
    import streamlit as st
    from auth.auth_utils import check_permission

    def show_admin_page():
        # Esta linha bloqueia o acesso a qualquer usuário que não seja 'admin'
        if not check_permission(level='admin'):
            st.stop() # A execução da página para aqui

        st.title("Painel de Administração")
        # ... resto do código da página ...
    ```

### Camada de Banco de Dados (Backend)
-   **Tecnologia:** Políticas de Row Level Security (RLS) no Supabase/PostgreSQL.
-   **Lógica:** As políticas de RLS no banco de dados espelham a lógica das `roles`.
    -   Políticas de `INSERT`, `UPDATE`, `DELETE` geralmente contêm uma verificação para garantir que o usuário tenha a `role` de `admin` ou `editor`. Usuários com `role` de `viewer` serão bloqueados pelo banco de dados se tentarem realizar uma operação de escrita, adicionando uma camada extra de segurança.
-   Consulte o documento [RLS Policies](./RLS_POLICIES.md) para os detalhes do SQL.

## 4. Gerenciamento de Papéis

O gerenciamento de papéis (atribuir, alterar ou remover a `role` de um usuário) é uma tarefa administrativa e só pode ser realizada por um usuário com a `role` de **`admin`** através da página de **Administração**, na seção de "Gerenciamento Global".

---
