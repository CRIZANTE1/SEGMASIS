# 🔐 Políticas de Row Level Security (RLS)

## 1. Conceito e Importância

**Row Level Security (RLS)** é um recurso do PostgreSQL que permite controlar quais linhas de uma tabela um usuário pode acessar. No SEGMA-SIS, o RLS é a **espinha dorsal da arquitetura multi-tenant**, garantindo que os dados de uma unidade operacional sejam completamente isolados e inacessíveis por outras unidades.

Cada política é uma expressão SQL que retorna `TRUE` ou `FALSE`. Se a política retornar `TRUE` para uma determinada linha, a operação (SELECT, INSERT, UPDATE, DELETE) é permitida. Caso contrário, a operação é bloqueada silenciosamente, como se a linha não existisse.

## 2. Funções de Autenticação do Supabase

As políticas RLS no Supabase utilizam funções especiais que fornecem informações sobre o usuário autenticado na sessão atual. As mais importantes para o SEGMA-SIS são:

- `auth.uid()`: Retorna o UUID do usuário autenticado
- `auth.role()`: Retorna o papel do usuário (no nosso caso, sempre `'authenticated'` para usuários logados)
- `auth.email()`: Retorna o e-mail do usuário autenticado

## 3. Estratégia de Implementação

A estratégia de RLS do sistema se baseia em duas fontes de verdade:

1. A tabela `public.usuarios`, que mapeia o e-mail do usuário (`auth.email()`) para sua `role` (`admin`, `editor`, `viewer`) e sua `unidade_associada` (um `UUID`)
2. A coluna `unit_id` presente em todas as tabelas de dados operacionais (ex: `empresas`, `funcionarios`, `asos`)

A lógica geral é:
- **Usuários Padrão (`editor`, `viewer`):** Só podem acessar linhas onde o `unit_id` da tabela corresponde ao `unidade_associada` do seu registro na tabela `usuarios`
- **Administradores (`admin`):** Podem acessar as linhas de **todas** as unidades. A política para eles geralmente verifica se a `role` do usuário é `admin`

## 4. Políticas Detalhadas por Tabela

### Tabela: `empresas` (e outras tabelas operacionais)

Esta é a política padrão para todas as tabelas que contêm a coluna `unit_id`.

#### Política de SELECT (Leitura)
- **Nome:** `Enable read access based on unit_id or admin role`
- **Objetivo:** Permitir que usuários vejam apenas as empresas de sua unidade, enquanto admins veem todas

```sql
-- Primeiro, obtemos o papel (role) e a unidade do usuário logado em uma subconsulta
WITH user_context AS (
    SELECT
        role,
        unidade_associada
    FROM public.usuarios
    WHERE email = auth.email()
)

-- A política retorna TRUE se:
(
    -- 1. O usuário for um 'admin'
    (SELECT role FROM user_context) = 'admin'
    OR
    -- 2. O 'unit_id' da linha da tabela 'empresas' for igual à unidade do usuário
    (
        SELECT unidade_associada FROM user_context
    ) = unit_id
)
```

### Política de INSERT (Escrita)

- **Nome:** `Enable insert access based on unit_id or admin role`
- **Objetivo:** Permitir que editores e admins insiram novas empresas, mas apenas na sua própria unidade (ou em qualquer unidade, no caso de admins)

```sql
-- Um usuário pode inserir uma linha se:
(
    -- 1. Ele for um admin (pode inserir em qualquer unidade)
    (SELECT role FROM public.usuarios WHERE email = auth.email()) = 'admin'
    OR
    -- 2. Ele for um editor E o 'unit_id' do NOVO registro que ele está tentando inserir
    --    corresponde à sua própria unidade.
    (
        (SELECT role FROM public.usuarios WHERE email = auth.email()) = 'editor'
        AND
        (SELECT unidade_associada FROM public.usuarios WHERE email = auth.email()) = unit_id
    )
)
```

**Nota:** Políticas de UPDATE e DELETE seguem uma lógica muito similar.

### Tabela: `usuarios` (Tabela Global)

Esta tabela é especial, pois não possui `unit_id`. As políticas são baseadas no e-mail do usuário.

#### Política de SELECT (Leitura)

- **Nome:** `Users can view their own data, Admins can view all`
- **Objetivo:** Garantir que um usuário só possa ler suas próprias informações, enquanto um administrador pode ver a lista de todos os usuários

```sql
(
    -- Permite se o usuário logado for um admin
    (SELECT role FROM public.usuarios WHERE email = auth.email()) = 'admin'
    OR
    -- Ou se o e-mail da linha que está sendo lida for o mesmo do usuário logado
    email = auth.email()
)
```

## 5. Ativação e Testes

### Ativação
Para cada tabela, o RLS deve ser explicitamente ativado no painel do Supabase ou via SQL:
```sql
ALTER TABLE public.empresas ENABLE ROW LEVEL SECURITY;
```

### Testes
É fundamental testar as políticas criando usuários com diferentes `roles` e `unidades_associadas` e verificando se o acesso aos dados é restrito conforme o esperado. O editor de SQL do Supabase permite executar consultas AS um usuário específico para facilitar os testes.