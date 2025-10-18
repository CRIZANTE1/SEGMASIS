# Exemplo de Configuração de Secrets (secrets.toml)

Este arquivo serve como um modelo para configurar o arquivo `.streamlit/secrets.toml` do seu projeto.

Copie este conteúdo para um novo arquivo chamado `secrets.toml` dentro da pasta `.streamlit` na raiz do seu projeto. Depois, substitua os valores de exemplo pelas suas chaves reais.

**Importante:** O arquivo `.streamlit/secrets.toml` já está no `.gitignore` do Streamlit, mas sempre confirme para nunca enviar suas chaves secretas para o repositório.

```toml
# =======================================
# Configuração do Supabase
# =======================================
[supabase]
url = "https://seu-projeto.supabase.co"
key = "sua-anon-key-publica-aqui"
service_role_key = "sua-service-role-key-secreta-aqui"

# =======================================
# Configuração das APIs de IA (Google Gemini)
# =======================================
[general]
GEMINI_EXTRACTION_KEY = "sua-chave-gemini-extraction"
GEMINI_AUDIT_KEY = "sua-chave-gemini-audit"
```

---

## Como Obter as Chaves

### Supabase
1.  Acesse o painel do seu projeto no [Supabase](https://supabase.com/).
2.  No menu à esquerda, vá para **Configurações do Projeto** (ícone de engrenagem).
3.  Selecione **API**.
4.  Na tela que aparecer, você encontrará:
    *   **URL do Projeto**: Este é o valor para a `url`.
    *   **Chaves de API do Projeto**:
        *   `key`: Use o valor da chave `anon` (pública).
        *   `service_role_key`: Use o valor da chave `service_role` (secreta).


**⚠️ AVISO DE SEGURANÇA CRÍTICO SOBRE A `service_role_key`**

A chave `service_role_key` tem acesso administrativo total ao seu banco de dados e pode **ignorar todas as suas políticas de Segurança em Nível de Linha (RLS)**.

- **NUNCA** exponha esta chave no frontend ou em código do lado do cliente (no navegador).
- Ela deve ser usada apenas para operações de servidor para servidor que exijam privilégios de administrador.
- Para esta aplicação, armazene-a de forma segura no arquivo `.streamlit/secrets.toml` e acesse-a apenas pelo código Python (`st.secrets`), nunca a envie para o navegador do usuário.

### Google Gemini
1.  Acesse o [Google AI Studio](https://aistudio.google.com/).
2.  Clique em **"Obter chave de API"** (Get API key).
3.  Crie e copie sua chave de API.