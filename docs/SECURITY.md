# 🔐 Políticas de Segurança

A segurança é um componente fundamental no design e na operação do SEGMA-SIS. Este documento descreve as principais medidas implementadas para proteger os dados, garantir a privacidade e controlar o acesso ao sistema.

## 1. Modelo de Segurança em Camadas

Adotamos uma abordagem de "defesa em profundidade", onde a segurança é aplicada em múltiplas camadas, desde a interface do usuário até o banco de dados.

| Camada         | Medida de Segurança Implementada                                    |
|----------------|---------------------------------------------------------------------|
| **Aplicação**  | Controle de Acesso Baseado em Papel (RBAC)                          |
| **Servidor Web** | Criptografia de Tráfego (HTTPS/TLS) via Streamlit Cloud             |
| **Autenticação** | OIDC (OpenID Connect) com provedor Google Workspace                 |
| **Banco de Dados**| Isolamento Multi-Tenant via Row Level Security (RLS)                |
| **Armazenamento**| URLs Assinadas (Signed URLs) para acesso a arquivos privados        |
| **Código-Fonte** | Gestão de Segredos via `st.secrets` e `.gitignore`                  |

---
## 2. Controle de Acesso e Autenticação

### Autenticação via OIDC
-   O sistema **não armazena senhas**. A autenticação é delegada a um provedor OIDC confiável (Google).
-   Isso garante que o login utilize as políticas de segurança do provedor, como autenticação de múltiplos fatores (MFA), se habilitado.

### Autorização (RBAC - Role-Based Access Control)
-   Após a autenticação, o sistema realiza a autorização com base na tabela `usuarios`.
-   Cada usuário possui uma `role` que define seu nível de permissão:
    -   **`admin`**: Acesso irrestrito. Pode gerenciar usuários, unidades e ver dados de toda a organização.
    -   **`editor`**: Acesso de leitura e escrita. Pode visualizar, adicionar, editar e excluir dados **apenas da sua unidade associada**.
    -   **`viewer`**: Acesso somente leitura. Pode visualizar os dados **apenas da sua unidade associada**, mas não pode realizar nenhuma modificação.
-   A função `auth.auth_utils.check_permission()` é usada no início de seções críticas do código para bloquear a execução se o usuário não tiver a `role` necessária.

---
## 3. Segurança de Dados

### Isolamento de Dados (Multi-Tenancy com RLS)
-   Esta é a medida de segurança de dados mais crítica do sistema.
-   As políticas de **Row Level Security (RLS)** no PostgreSQL garantem que qualquer consulta (leitura ou escrita) feita por um usuário seja **automaticamente filtrada** pelo `unit_id` da sua unidade.
-   Isso torna impossível, a nível de banco de dados, que um usuário da "Unidade A" acesse os dados da "Unidade B", mesmo que um bug hipotético na aplicação tentasse fazer isso.
-   Consulte o documento [RLS Policies](./RLS_POLICIES.md) para detalhes técnicos.

### Segurança no Armazenamento de Arquivos
-   Os arquivos PDF (ASOs, certificados, etc.) são armazenados no Supabase Storage.
-   Os buckets podem ser configurados como **privados**, o que significa que os arquivos não são acessíveis publicamente.
-   O acesso a um arquivo privado é feito através de uma **URL Assinada (Signed URL)**, que é gerada em tempo real pela aplicação. Essa URL:
    -   É única para cada requisição.
    -   Possui um **tempo de expiração** curto (geralmente de alguns minutos a uma hora).
    -   Garante que apenas usuários autenticados e autorizados possam visualizar os documentos.

### Proteção contra Duplicatas e Integridade
-   O sistema calcula um hash **SHA-256** para cada arquivo no momento do upload.
-   Esse hash é armazenado junto com os metadados do documento.
-   Antes de salvar um novo registro, o sistema verifica se já existe um documento com o mesmo hash para aquele funcionário/empresa, prevenindo o cadastro de dados duplicados e economizando espaço de armazenamento.

---
## 4. Gestão de Segredos e Credenciais

-   **NUNCA armazene segredos no código-fonte.**
-   Todas as chaves de API (Supabase, Google Gemini) e outras informações sensíveis devem ser armazenadas exclusivamente no arquivo `.streamlit/secrets.toml`.
-   O arquivo `.gitignore` está configurado para **impedir** que o `secrets.toml` seja acidentalmente enviado para o repositório Git. É responsabilidade de cada desenvolvedor garantir que esta regra seja seguida.
-   A chave `service_role_key` do Supabase concede acesso administrativo total e **NUNCA** deve ser usada no código do frontend. Seu uso é restrito a scripts de backend seguros, como o notificador de e-mails ou migrações.

## 5. Responsabilidades

-   **Desenvolvedores:** São responsáveis por seguir as práticas de codificação segura, gerenciar seus secrets locais corretamente e implementar verificações de permissão (`check_permission`) onde necessário.
-   **Administradores do Sistema:** São responsáveis por gerenciar os papéis dos usuários na tabela `usuarios`, garantindo que as permissões sejam concedidas com base no princípio do menor privilégio.

---
**Próximo Documento:** [Gestão de Secrets](./SECRETS_MANAGEMENT.md)