import pandas as pd
from operations.cached_loaders import load_nr_rules_data
import logging
from fuzzywuzzy import process

logger = logging.getLogger(__name__)

class NRRulesManager:
    def __init__(self, unit_id: str = None):
        """
        Inicializa o gerenciador de regras de NRs.

        Args:
            unit_id (str, optional): O ID da unidade atual para buscar regras customizadas.
        """
        self.unit_id = unit_id
        self.all_rules_df = load_nr_rules_data()

    def find_training_rule(self, norma_nome: str, modulo_nome: str = None) -> pd.Series | None:
        """
        Encontra a regra de treinamento mais apropriada para uma norma e módulo,
        priorizando regras da unidade sobre as globais.

        Args:
            norma_nome (str): O nome da norma (ex: "NR 33").
            modulo_nome (str, optional): O nome do módulo (ex: "Supervisor").

        Returns:
            pd.Series: Uma linha do DataFrame contendo a regra encontrada, ou None.
        """
        if self.all_rules_df.empty:
            return None

        norma_lower = norma_nome.lower().strip()

        # 1. Filtra todas as regras ativas para a norma desejada
        potential_rules = self.all_rules_df[
            (self.all_rules_df['norma'].str.lower() == norma_lower) &
            (self.all_rules_df['norma_is_active'] == True) &
            (self.all_rules_df['treinamento_is_active'] == True)
        ].copy()

        if potential_rules.empty:
            return None

        # 2. Prioriza regras da unidade específica
        unit_rules = potential_rules[potential_rules['unit_id'] == self.unit_id]
        rules_to_search = unit_rules if not unit_rules.empty else potential_rules[potential_rules['unit_id'].isnull()]

        if rules_to_search.empty:
            return None

        # 3. Lógica para selecionar o treinamento correto (título/módulo)
        # Se houver apenas uma regra para a norma, retorne-a.
        if len(rules_to_search) == 1:
            return rules_to_search.iloc[0]

        # Se houver múltiplas regras, use o módulo para desambiguar.
        if modulo_nome:
            # Combina título e módulo para uma busca mais precisa
            rules_to_search['search_key'] = rules_to_search['titulo'].str.lower() + " " + rules_to_search.get('modulo', '').str.lower()

            # Usa fuzzy matching para encontrar o melhor candidato
            choices = rules_to_search['search_key'].tolist()
            best_match_key, score = process.extractOne(modulo_nome.lower(), choices)

            if score > 80: # Limiar de confiança
                best_rule = rules_to_search[rules_to_search['search_key'] == best_match_key]
                return best_rule.iloc[0]

        # Se não houver match satisfatório, retorna None
        logger.error(f"Ambiguidade: {len(rules_to_search)} regras para '{norma_nome}' sem critério de desempate claro")
        return None

    def get_norma_options(self) -> list:
        """Retorna uma lista de todas as normas ativas disponíveis."""
        if self.all_rules_df.empty:
            return []
        return sorted(self.all_rules_df['norma'].unique().tolist())

    def get_module_options_for_norma(self, norma_nome: str) -> list:
        """
        Retorna uma lista de títulos de treinamento (usados como módulos) para uma norma.
        Útil para preencher dropdowns dinamicamente na UI.

        Args:
            norma_nome (str): O nome da norma.

        Returns:
            List[str]: Uma lista dos títulos dos treinamentos associados.
        """
        if self.all_rules_df.empty:
            return []

        norma_lower = norma_nome.lower().strip()

        rules = self.all_rules_df[
            (self.all_rules_df['norma'].str.lower() == norma_lower) &
            (self.all_rules_df['norma_is_active'] == True) &
            (self.all_rules_df['treinamento_is_active'] == True)
        ]

        if not rules.empty:
            # Retorna os títulos únicos dos treinamentos
            return sorted(rules['titulo'].unique().tolist())

        return []
