# 📊 Matriz de Normas Regulamentadoras
**Sistema SEGMA-SIS | Documentação Técnica**

Este documento descreve todas as Normas Regulamentadoras (NRs) do Ministério do Trabalho e Emprego que são gerenciadas pelo SEGMA-SIS, incluindo suas regras de validação, cálculo de vencimento e requisitos específicos.

---

## 📑 Índice

- [Visão Geral](#-visão-geral)
- [NRs Implementadas](#-nrs-implementadas)
- [Regras de Vencimento](#-regras-de-vencimento)
- [Validação de Carga Horária](#-validação-de-carga-horária)
- [Casos Especiais](#-casos-especiais)
- [Referências Normativas](#-referências-normativas)

---

## 🎯 Visão Geral
O SEGMA-SIS gerencia treinamentos de segurança do trabalho de acordo com as Normas Regulamentadoras do MTE. Cada norma possui regras específicas para:

- **Carga horária mínima** (formação inicial e reciclagem)
- **Periodicidade de reciclagem** (validade do treinamento)
- **Módulos específicos** (quando aplicável)
- **Requisitos de conteúdo programático**

### Tipos de Treinamento

- **Formação Inicial:** Primeiro treinamento do trabalhador na atividade.
- **Reciclagem:** Atualização periódica obrigatória para manter a validade.

---

## 📚 NRs Implementadas

### NR-01 - Disposições Gerais e Gerenciamento de Riscos Ocupacionais
- **Status:** ✅ Implementado (Auditoria de PGR)
- **Documentos Gerenciados:**
  - Programa de Gerenciamento de Riscos (PGR)
  - Plano de Ação
- **Requisitos de Auditoria:**
  - Inventário de riscos com avaliação (severidade + probabilidade)
  - Plano de ação estruturado (cronograma + responsáveis)
  - Procedimentos de emergência
  - Data de emissão e assinaturas
- **Regras de Vencimento:**
  - **PGR:** 2 anos a partir da data de emissão.
  - Revisão obrigatória em caso de mudança de risco.

### NR-06 - Equipamentos de Proteção Individual (EPI)
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 3 horas  | 3 horas    | 10 anos       |

- **Documentos Gerenciados:**
  - Fichas de Controle de EPI
  - Certificados de treinamento
- **Campos Obrigatórios (Ficha de EPI):**
  - Nome do funcionário
  - Descrição do EPI
  - Certificado de Aprovação (CA)
  - Data de entrega
  - Assinatura do trabalhador
- **Observações:**
  - Periodicidade muito longa (10 anos) devido à natureza do treinamento.
  - Foco em conscientização sobre uso correto.

### NR-10 - Segurança em Instalações e Serviços em Eletricidade
- **Status:** ✅ Implementado (com módulos)

#### Módulos Disponíveis
**NR-10 Básico**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 40 horas | 40 horas   | 2 anos        |
- **Aplicável a:**
  - Trabalhadores que interagem com instalações elétricas energizadas.
  - Tensão até 1000V (Baixa Tensão).

**NR-10 SEP (Sistema Elétrico de Potência)**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 40 horas | 40 horas   | 2 anos        |
- **Aplicável a:**
  - Trabalhadores em subestações.
  - Alta tensão (acima de 1000V).
  - Sistema Elétrico de Potência.

⚠️ **IMPORTANTE:** NR-10 Básico **NÃO** cobre NR-10 SEP. São treinamentos distintos.

- **Detecção Automática (IA):**
  O sistema identifica automaticamente se o certificado é SEP através de palavras-chave:
  - "SEP"
  - "Sistema Elétrico de Potência"
  - "Alta Tensão"
  - "Subestação"

### NR-11 - Transporte, Movimentação, Armazenagem e Manuseio de Materiais
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 16 horas | 16 horas   | 3 anos        |

- **Aplicável a:**
  - Operadores de empilhadeiras
  - Operadores de pontes rolantes
  - Movimentação de cargas
- **Observações:**
  - Carga horária pode variar de 16 a 32 horas dependendo do equipamento.
  - Sistema valida mínimo de 16 horas.

### NR-12 - Segurança no Trabalho em Máquinas e Equipamentos
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 8 horas  | 8 horas    | 5 anos        |

- **Aplicável a:**
  - Operadores de máquinas
  - Manutenção de equipamentos
  - Trabalhos com dispositivos de segurança
- **Observações:**
  - Periodicidade de 5 anos (mais longa que a maioria).
  - Foco em proteções mecânicas e dispositivos de segurança.

### NR-18 - Condições e Meio Ambiente de Trabalho na Indústria da Construção
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 8 horas  | 8 horas    | 1 ano         |

- **Aplicável a:**
  - Trabalhadores da construção civil
  - Todos os níveis hierárquicos
- **Conteúdo Programático Mínimo:**
  - Riscos na construção
  - Equipamentos de proteção coletiva
  - Primeiros socorros
  - Ordem e limpeza

### NR-20 - Segurança e Saúde no Trabalho com Inflamáveis e Combustíveis
- **Status:** ✅ Implementado (4 módulos)

#### Matriz de Módulos
| Módulo        | Formação | Periodicidade | Reciclagem (C.H.) | Aplicável a                               |
|---------------|----------|---------------|-------------------|-------------------------------------------|
| **Básico**      | 8 horas  | 3 anos        | 4 horas           | Trabalhadores em postos de combustível    |
| **Intermediário** | 16 horas | 2 anos        | 4 horas           | Operadores de processos                   |
| **Avançado I**  | 20 horas | 2 anos        | 4 horas           | Manutenção e inspeção                     |
| **Avançado II** | 32 horas | 1 ano         | 4 horas           | Operações críticas                        |

- **Detecção Automática (IA):**
  O sistema infere o módulo pela carga horária do certificado quando não explícito.
- **Validação Especial:**
  ```python
  # Exemplo de lógica de validação NR-20
  if norma == "NR-20":
      if modulo == "Básico" and carga_horaria < 8:
          return False, "Básico requer 8h"
      elif modulo == "Intermediário" and carga_horaria < 16:
          return False, "Intermediário requer 16h"
      # ... etc
  ```

### NR-33 - Segurança e Saúde nos Trabalhos em Espaços Confinados
- **Status:** ✅ Implementado (2 módulos)

#### Módulos Disponíveis
**Trabalhador Autorizado**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 16 horas | 8 horas    | 1 ano         |
- **Aplicável a:** Trabalhadores que entram em espaços confinados.

**Supervisor de Entrada**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 40 horas | 8 horas    | 1 ano         |
- **Aplicável a:** Profissionais que autorizam e supervisionam entradas.

- **Conteúdo Programático Obrigatório:**
  - Identificação de espaços confinados
  - Avaliação de riscos
  - Teste de atmosfera
  - Procedimentos de resgate
- **Observações:**
  - Periodicidade anual (rigorosa).
  - Reciclagem única de 8h para ambos os módulos.

### NR-34 - Condições e Meio Ambiente de Trabalho na Indústria da Construção e Reparação Naval
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 8 horas  | 8 horas    | 1 ano         |

- **Aplicável a:**
  - Trabalhadores da indústria naval
  - Estaleiros

### NR-35 - Trabalho em Altura
- **Status:** ✅ Implementado

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 8 horas  | 8 horas    | 2 anos        |

- **Aplicável a:** Trabalhadores que executam atividades acima de 2 metros do nível inferior.
- **Conteúdo Programático Obrigatório:**
  - Análise de risco
  - Equipamentos de proteção individual
  - Sistemas de ancoragem
  - Técnicas de resgate
- **Observações:**
  - Uma das NRs mais comuns no sistema.
  - Periodicidade de 2 anos.

### NBR 16710 - Resgate Técnico
- **Status:** ✅ Implementado
- **Modalidade:** Resgate Técnico Industrial

| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 24 horas | 24 horas   | 2 anos        |

- **Aplicável a:**
  - Equipes de resgate em altura
  - Equipes de resgate em espaços confinados
  - Brigadistas especializados
- **Observações:**
  - Norma ABNT (não é NR do MTE).
  - Treinamento altamente especializado.
  - Exige prática e certificação.

### Brigada de Incêndio (IT-17 / NR-23)
- **Status:** ✅ Implementado (2 níveis)

**Brigada Básica**
| Item      | Formação      | Reciclagem | Periodicidade |
|-----------|---------------|------------|---------------|
| Carga Horária | Não especificado | Anual      | 1 ano         |

**Brigada Avançada**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 24 horas | 16 horas   | 1 ano         |

- **Aplicável a:**
  - Brigadistas voluntários
  - Equipes de emergência
- **Observações:**
  - Referência à IT-17 do Corpo de Bombeiros (SP).
  - Periodicidade anual rigorosa.

### Permissão de Trabalho (PT)
- **Status:** ✅ Implementado (2 módulos)

**Emitente de PT**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 16 horas | 4 horas    | 1 ano         |
- **Aplicável a:** Profissionais que emitem Permissões de Trabalho.

**Requisitante de PT**
| Item      | Formação | Reciclagem | Periodicidade |
|-----------|----------|------------|---------------|
| Carga Horária | 8 horas  | 4 horas    | 1 ano         |
- **Aplicável a:** Profissionais que solicitam Permissões de Trabalho.

- **Observações:**
  - Não é uma NR formal, mas prática comum em indústrias.
  - Sistema implementado devido à alta demanda.

---

## ⏰ Regras de Vencimento

### Cálculo Automático
O sistema calcula automaticamente a data de vencimento baseado em:
- Data de realização do treinamento
- Norma identificada
- Módulo (quando aplicável)
- Tipo (formação ou reciclagem)

**Exemplo de implementação:**
```python
def calcular_vencimento_treinamento(data, norma, modulo, tipo_treinamento):
    if norma == "NR-20" and modulo:
        config = nr20_config.get(modulo)
        anos = config.get('reciclagem_anos')
    else:
        config = nr_config.get(norma)
        anos = config.get('reciclagem_anos')
    
    return data + relativedelta(years=anos)
```

### Tabela Resumo de Periodicidades
| Norma                       | Periodicidade        | Observações             |
|-----------------------------|----------------------|-------------------------|
| NR-06                       | 10 anos              | ⏰ Mais longa           |
| NR-12                       | 5 anos               | 📅 Longa                |
| NR-11                       | 3 anos               | 📅 Média-longa          |
| NR-10, NR-35, NBR 16710     | 2 anos               | 📅 Padrão               |
| NR-20 (depende do módulo)   | 1-3 anos             | 📅 Variável             |
| NR-18, NR-33, NR-34, Brigada, PT | 1 ano              | ⚠️ Anual (rigorosa)    |

---

## ✅ Validação de Carga Horária

### Processo de Validação
O sistema valida a carga horária em 3 etapas:

**1. Extração (IA - Gemini Flash)**
```python
# Prompt de extração
"""
Extraia do certificado:
- data_realizacao: DD/MM/AAAA
- norma: Nome da norma (ex: NR-10 SEP)
- modulo: Módulo específico
- tipo_treinamento: 'formação' ou 'reciclagem'
- carga_horaria: Número inteiro de horas
"""
```

**2. Validação de Negócio**
```python
def validar_treinamento(norma, modulo, tipo, carga_horaria):
    # Busca configuração
    config = nr_config.get(norma)
    
    # Valida formação
    if tipo == 'formação' and 'inicial_horas' in config:
        if carga_horaria < config['inicial_horas']:
            return False, f"Mínimo {config['inicial_horas']}h"
    
    # Valida reciclagem
    elif tipo == 'reciclagem' and 'reciclagem_horas' in config:
        if carga_horaria < config['reciclagem_horas']:
            return False, f"Mínimo {config['reciclagem_horas']}h"
    
    return True, "Conforme"
```

**3. Auditoria com IA (Gemini Pro + RAG)**
```python
# Validação cruzada com base de conhecimento
audit_result = nr_analyzer.perform_initial_audit(doc_info, file_content)
```

### Regras Especiais

**NR-33 (Espaços Confinados)**
- **Supervisor vs. Trabalhador:**
  - **Supervisor:** Formação de 40h, reciclagem de 8h.
  - **Trabalhador:** Formação de 16h, reciclagem de 8h.
- **Detecção de módulo:**
  ```python
  if "supervisor" in modulo.lower():
      modulo_normalizado = "supervisor"
  elif "trabalhador" in modulo.lower() or "autorizado" in modulo.lower():
      modulo_normalizado = "trabalhador"
  ```

**Permissão de Trabalho**
- **Emitente vs. Requisitante:**
  - **Emitente:** Formação de 16h, reciclagem de 4h.
  - **Requisitante:** Formação de 8h, reciclagem de 4h.

**NR-10 vs. NR-10 SEP**
- **Crítico:** São treinamentos independentes:
  ```python
  # ❌ ERRADO: Considerar NR-10 Básico como válido para NR-10 SEP
  if 'SEP' in norma_required:
      # Deve ter certificado específico de SEP
      has_sep = any('SEP' in completed for completed in completed_trainings)
      if not has_sep:
          missing.append("NR-10 SEP")
  ```

---

## 🔍 Casos Especiais

**1. Treinamentos sem Vencimento**
- **ASO Demissional:**
  - Não possui vencimento.
  - Validade apenas para o ato de desligamento.

**2. Treinamentos com Módulos Múltiplos**
- **NR-20:**
  - Trabalhador pode ter múltiplos módulos simultaneamente.
  - Exemplo: Básico + Intermediário.
- **Sistema registra separadamente:**
  ```
  # Mesmo funcionário, normas diferentes no DataFrame
  funcionario_id | norma  | modulo        | vencimento
  123           | NR-20  | Básico        | 2026-05-10
  123           | NR-20  | Intermediário | 2025-08-15
  ```

**3. Reciclagem antes do Vencimento**
- **Regra:** Reciclagem substitui a formação anterior.
  ```python
  # Sistema sempre pega o treinamento mais recente
  latest_trainings = trainings.sort_values('data', ascending=False).groupby(
      ['funcionario_id', 'norma', 'modulo']
  ).head(1)
  ```
- **Exemplo:**
  - Formação NR-35: 15/05/2020 (vence em 15/05/2022)
  - Reciclagem NR-35: 01/03/2022 (vence em 01/03/2024)
  - **Sistema mostra:** Apenas a reciclagem de 2022.

**4. Normalização de Nomenclatura**
- **Problema:** Variações de escrita:
  - "NR 10" vs. "NR-10" vs. "NR10"
  - "BRIGADA" vs. "Brigada de Incêndio" vs. "IT-17"
- **Solução:** Função de padronização.
  ```python
  def _padronizar_norma(norma):
      norma_upper = norma.strip().upper()
      
      if "BRIGADA" in norma_upper or "IT-17" in norma_upper:
          return "BRIGADA DE INCÊNDIO"
      
      if "RESGATE" in norma_upper or "16710" in norma_upper:
          return "NBR-16710 RESGATE TÉCNICO"
      
      if "PERMISSÃO" in norma_upper or "PT" in norma_upper:
          return "PERMISSÃO DE TRABALHO (PT)"
      
      # Normaliza NR-XX
      match = re.search(r'NR\s?-?(\d+)', norma_upper)
      if match:
          return f"NR-{int(match.group(1)):02d}"
      
      return norma_upper
  ```

---

## 📖 Referências Normativas

### Legislação Base
- **Portaria MTE nº 3.214/1978**
  - Aprova as Normas Regulamentadoras.
  - Última atualização: Portaria MTE nº 1.109/2016.

### NR-01 (Gerenciamento de Riscos)
- **Portaria SEPRT nº 6.730/2020**
  - Item 1.5: PGR
  - Item 1.7: Treinamentos

### IT-17 (Instrução Técnica - Corpo de Bombeiros SP)
- **Decreto Estadual nº 63.911/2018**
  - Brigada de Incêndio

### NBR 16710 (ABNT)
- Resgate Técnico Industrial
- Versão: 2018

### Links Oficiais
- [MTE - Normas Regulamentadoras](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/arquivos/normas-regulamentadoras)
- [ABNT Catálogo](https://www.abnt.org.br/)

---

## 🛠️ Implementação Técnica

### Estrutura de Dados
**Dicionário de Configuração (Python):**
```python
nr_config = {
    'NR-35': {
        'inicial_horas': 8,
        'reciclagem_horas': 8,
        'reciclagem_anos': 2
    },
    'NR-10': {
        'inicial_horas': 40,
        'reciclagem_horas': 40,
        'reciclagem_anos': 2
    },
    # ... etc
}

nr20_config = {
    'Básico': {
        'inicial_horas': 8,
        'reciclagem_anos': 3,
        'reciclagem_horas': 4
    },
    # ... etc
}
```

### Funções Principais
- **Arquivo:** `operations/employee.py`
```python
class EmployeeManager:
    def calcular_vencimento_treinamento(self, data, norma, modulo, tipo):
        """Calcula vencimento baseado na norma"""
        
    def validar_treinamento(self, norma, modulo, tipo, carga_horaria):
        """Valida carga horária"""
        
    def _padronizar_norma(self, norma):
        """Normaliza nomenclatura"""
```

---

## 📊 Estatísticas de Uso
**NRs Mais Comuns (dados de produção):**

- **NR-35 (Trabalho em Altura)** - 35%
- **NR-10 (Eletricidade)** - 25%
- **NR-33 (Espaços Confinados)** - 15%
- **NR-18 (Construção Civil)** - 10%
- **Brigada de Incêndio** - 8%
- **Outras** - 7%

---

## 🔄 Manutenção e Atualizações

### Como Adicionar uma Nova NR

1.  **Atualizar `nr_config` em `operations/employee.py`:**
    ```python
    'NR-XX': {
        'inicial_horas': XX,
        'reciclagem_horas': XX,
        'reciclagem_anos': X
    }
    ```
2.  **Adicionar lógica de validação (se necessário):**
    ```python
    def validar_treinamento(self, norma, modulo, tipo, carga_horaria):
        # ... código existente ...
        
        if norma == "NR-XX":
            # Lógica específica
            pass
    ```
3.  **Atualizar documentação:**
    - Adicionar seção neste documento.
    - Atualizar `ui/ui_helpers.py` (expander de informações).
4.  **Testar:**
    - Upload de certificado.
    - Cálculo de vencimento.
    - Validação de carga horária.
    - Matriz de conformidade.

---

## ✅ Checklist de Conformidade
Para cada NR implementada:

- [ ] Carga horária mínima definida
- [ ] Periodicidade de reciclagem definida
- [ ] Função de validação implementada
- [ ] Cálculo de vencimento testado
- [ ] Documentação atualizada
- [ ] Casos especiais documentados
- [ ] Testes de integração passando

---

*Última Atualização: 14 de Outubro de 2025*
*Versão do Documento: 2.0*
*Autor: Cristian Ferreira Carlos*
