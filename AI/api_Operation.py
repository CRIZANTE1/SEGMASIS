import streamlit as st
import time
import threading
from queue import Queue, Empty
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from AI.api_load import load_models

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass


class RateLimiter:
    """
    Rate limiter baseado nos limites reais da API Gemini.

    Limites oficiais:
    - Gemini 2.5 Flash: 10 RPM / 250 RPD / 250.000 TPM
    - Gemini 2.5 Pro: 5 RPM / 100 RPD / 125.000 TPM
    """

    def __init__(self, rpm_limit=10, rpd_limit=250, name="default"):
        """
        Args:
            rpm_limit: Requests per minute (requisições por minuto)
            rpd_limit: Requests per day (requisições por dia)
            name: Nome do limitador (para logging)
        """
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.name = name

        # Armazena timestamps de chamadas por usuário
        self.minute_calls = defaultdict(list)
        self.day_calls = defaultdict(list)

        self.lock = threading.Lock()
        self.unlimited_users = set()

    def add_unlimited_user(self, user_id):
        """Adiciona um usuário à lista de acesso ilimitado (admins)."""
        with self.lock:
            self.unlimited_users.add(user_id)
            logger.info(f"Usuário {user_id} adicionado à lista ilimitada ({self.name})")

    def remove_unlimited_user(self, user_id):
        """Remove um usuário da lista de acesso ilimitado."""
        with self.lock:
            self.unlimited_users.discard(user_id)

    def is_allowed(self, user_id, user_role=None):
        """
        Verifica se o usuário pode fazer uma chamada à API.

        Args:
            user_id: Identificador do usuário
            user_role: Role do usuário ('admin', 'editor', 'viewer')

        Returns:
            bool: True se permitido, False caso contrário
        """
        # ✅ Super admin tem acesso ilimitado
        if user_role == 'admin':
            return True

        # ✅ Verifica lista de usuários ilimitados
        if user_id in self.unlimited_users:
            return True

        with self.lock:
            now = datetime.now()

            # ✅ Limpa chamadas antigas (minuto)
            one_minute_ago = now - timedelta(minutes=1)
            self.minute_calls[user_id] = [
                call_time for call_time in self.minute_calls[user_id]
                if call_time > one_minute_ago
            ]

            # ✅ Limpa chamadas antigas (dia)
            one_day_ago = now - timedelta(days=1)
            self.day_calls[user_id] = [
                call_time for call_time in self.day_calls[user_id]
                if call_time > one_day_ago
            ]

            # ✅ Verifica limite por minuto
            if len(self.minute_calls[user_id]) >= self.rpm_limit:
                logger.warning(
                    f"Usuário {user_id} atingiu limite RPM ({self.rpm_limit}) "
                    f"no limitador {self.name}"
                )
                return False

            # ✅ Verifica limite por dia
            if len(self.day_calls[user_id]) >= self.rpd_limit:
                logger.warning(
                    f"Usuário {user_id} atingiu limite RPD ({self.rpd_limit}) "
                    f"no limitador {self.name}"
                )
                return False

            # ✅ Registra a chamada
            self.minute_calls[user_id].append(now)
            self.day_calls[user_id].append(now)

            return True

    def get_wait_time_minutes(self, user_id):
        """Calcula tempo de espera em segundos até próxima chamada permitida (limite de minuto)."""
        with self.lock:
            if not self.minute_calls[user_id]:
                return 0

            oldest_call = min(self.minute_calls[user_id])
            elapsed = (datetime.now() - oldest_call).total_seconds()
            wait_time = max(0, 60 - elapsed)

            return int(wait_time)

    def get_remaining_calls(self, user_id, user_role=None):
        """
        Retorna informações sobre chamadas restantes.

        Returns:
            dict: {'per_minute': int, 'per_day': int} ou 'ilimitado'
        """
        if user_role == 'admin' or user_id in self.unlimited_users:
            return 'ilimitado'

        with self.lock:
            now = datetime.now()

            # Limpa listas
            one_minute_ago = now - timedelta(minutes=1)
            self.minute_calls[user_id] = [
                call_time for call_time in self.minute_calls[user_id]
                if call_time > one_minute_ago
            ]

            one_day_ago = now - timedelta(days=1)
            self.day_calls[user_id] = [
                call_time for call_time in self.day_calls[user_id]
                if call_time > one_day_ago
            ]

            return {
                'per_minute': self.rpm_limit - len(self.minute_calls[user_id]),
                'per_day': self.rpd_limit - len(self.day_calls[user_id])
            }

    def get_usage_stats(self, user_id):
        """Retorna estatísticas de uso do usuário."""
        with self.lock:
            return {
                'calls_last_minute': len(self.minute_calls[user_id]),
                'calls_today': len(self.day_calls[user_id]),
                'rpm_limit': self.rpm_limit,
                'rpd_limit': self.rpd_limit
            }


class PDFQA:
    # ✅ Rate limiters baseados nos limites REAIS da API Gemini
    _rate_limiters = {
        # Plano Pro usa Gemini 2.5 Flash (10 RPM / 250 RPD)
        'pro': RateLimiter(rpm_limit=10, rpd_limit=250, name="Flash-Pro"),

        # Plano Premium IA usa Gemini 2.5 Pro (5 RPM / 100 RPD)
        # Mas damos um buffer maior para múltiplos usuários Premium
        'premium_ia': RateLimiter(rpm_limit=5, rpd_limit=100, name="Pro-Premium")
    }

    def __init__(self):
        """
        Inicializa a classe carregando os dois modelos de IA (extração e auditoria)
        usando a função load_models().
        """
        self.extraction_model, self.audit_model = load_models()

    def answer_question(self, pdf_files, question, task_type='extraction'):
        """
        Função principal para responder a uma pergunta, selecionando o modelo apropriado.

        Args:
            pdf_files (list): Lista de caminhos ou objetos de arquivo PDF.
            question (str): A pergunta ou prompt.
            task_type (str): 'extraction' para tarefas simples (padrão), 'audit' para tarefas complexas.

        Returns:
            tuple: (response_text, duration) ou (None, 0) em caso de erro.
        """
        start_time = time.time()

        # ✅ Obter informações do usuário
        user_email, user_role, user_plan = self._get_user_info()

        # ✅ Determinar qual modelo usar
        if task_type == 'audit':
            model_to_use = self.audit_model
            model_name = "Gemini 2.5 Pro"
            if not model_to_use:
                st.error("O modelo de AUDITORIA não está disponível. Verifique sua chave 'GEMINI_AUDIT_KEY' nos secrets.")
                return None, 0
        else:
            model_to_use = self.extraction_model
            model_name = "Gemini 2.5 Flash"
            if not model_to_use:
                st.error("O modelo de EXTRAÇÃO não está disponível. Verifique sua chave 'GEMINI_EXTRACTION_KEY' nos secrets.")
                return None, 0

        # ✅ Rate limiting com exceção para admin
        if not self._check_rate_limit(user_email, user_role, user_plan, task_type):
            return None, 0

        try:
            answer = self._generate_response(model_to_use, pdf_files, question)
            if answer is not None:
                logger.info(
                    f"API call successful - User: {user_email}, "
                    f"Model: {model_name}, Duration: {time.time() - start_time:.2f}s"
                )
                return answer, time.time() - start_time
            else:
                st.warning("Não foi possível obter uma resposta do modelo.")
                return None, 0
        except Exception as e:
            st.error(f"Erro inesperado ao processar a pergunta para a tarefa '{task_type}': {e}")
            st.exception(e)
            return None, 0


    def _get_user_info(self):
        """Obtém informações do usuário para rate limiting."""
        try:
            if hasattr(st, 'session_state'):
                user_info = st.session_state.get('user_info', {})
                user_email = user_info.get('email', 'anonymous')
                user_role = st.session_state.get('role', 'viewer')
                user_plan = user_info.get('plano')

                # ✅ Validar plano - apenas 'pro' ou 'premium_ia' são permitidos
                if user_plan not in ['pro', 'premium_ia']:
                    logger.warning(f"Plano inválido '{user_plan}' para usuário {user_email}")
                    user_plan = None

                return user_email, user_role, user_plan
            return 'anonymous', 'viewer', None
        except:
            return 'anonymous', 'viewer', None

    def _check_rate_limit(self, user_email, user_role, user_plan, task_type):
        """
        Verifica rate limit baseado no plano do usuário.

        Args:
            user_email: Email do usuário
            user_role: Role do usuário
            user_plan: Plano de assinatura ('pro' ou 'premium_ia')
            task_type: Tipo de tarefa ('extraction' ou 'audit')

        Returns:
            bool: True se permitido, False se bloqueado
        """
        # ✅ Logging detalhado
        logger.info(
            f"Rate limit check - User: {user_email}, Role: {user_role}, "
            f"Plan: {user_plan}, Task: {task_type}"
        )

        # ✅ Admin não tem limites
        if user_role == 'admin':
            logger.info(f"Admin user {user_email} - unlimited access granted")
            return True

        # ✅ Usuário sem plano não pode usar IA
        if not user_plan:
            logger.warning(f"User {user_email} has no plan - access denied")
            st.error("""
            ❌ **Acesso à IA Não Disponível**

            Você não possui um plano ativo para usar análise com IA.

            Entre em contato com o administrador para ativar:
            - **🚀 Plano Pro**: Análise com Gemini Flash (10 análises/min, 250/dia)
            - **💎 Plano Premium IA**: Análise com Gemini Pro (5 análises/min, 100/dia)
            """)
            return False

        # ✅ Seleciona o rate limiter apropriado
        rate_limiter = self._rate_limiters.get(user_plan)

        if not rate_limiter:
            logger.error(f"Invalid plan '{user_plan}' for user {user_email}")
            st.error(f"❌ Plano '{user_plan}' não configurado corretamente.")
            return False

        # ✅ Verifica se está permitido
        if not rate_limiter.is_allowed(user_email, user_role):
            # Obtém informações sobre os limites
            remaining = rate_limiter.get_remaining_calls(user_email, user_role)
            wait_time = rate_limiter.get_wait_time_minutes(user_email)
            stats = rate_limiter.get_usage_stats(user_email)

            # ✅ Logging de bloqueio
            logger.warning(
                f"Rate limit exceeded - User: {user_email}, Plan: {user_plan}, "
                f"Calls/min: {stats['calls_last_minute']}/{stats['rpm_limit']}, "
                f"Calls/day: {stats['calls_today']}/{stats['rpd_limit']}"
            )

            # ✅ Determina qual limite foi atingido
            if stats['calls_last_minute'] >= stats['rpm_limit']:
                limit_type = "por minuto"
                limit_value = f"{stats['rpm_limit']} análises/minuto"
                wait_message = f"Aguarde **{wait_time} segundos** para fazer novas análises."
            else:
                limit_type = "diário"
                limit_value = f"{stats['rpd_limit']} análises/dia"
                wait_message = "Você atingiu seu limite diário. Aguarde até amanhã ou faça upgrade do plano."

            # ✅ Mensagem de erro customizada por plano
            plan_info = {
                'pro': {
                    'name': 'Pro',
                    'model': 'Gemini 2.5 Flash',
                    'rpm': '10 por minuto',
                    'rpd': '250 por dia',
                    'upgrade': 'Premium IA'
                },
                'premium_ia': {
                    'name': 'Premium IA',
                    'model': 'Gemini 2.5 Pro',
                    'rpm': '5 por minuto',
                    'rpd': '100 por dia',
                    'upgrade': None
                }
            }

            info = plan_info.get(user_plan, plan_info['pro'])

            error_message = f"""
            ⏳ **Limite {limit_type.title()} Atingido**

            **Seu Plano:** {info['name']} ({info['model']})
            **Limite Atual:** {limit_value}

            📊 **Uso de Hoje:**
            - Chamadas no último minuto: {stats['calls_last_minute']}/{stats['rpm_limit']}
            - Chamadas hoje: {stats['calls_today']}/{stats['rpd_limit']}

            ⏰ {wait_message}
            """

            # Adiciona sugestão de upgrade se disponível
            if info['upgrade']:
                error_message += f"""

            💡 **Precisa de mais análises?**
            Faça upgrade para o plano **{info['upgrade']}** e tenha acesso a mais recursos!
            """

            st.error(error_message)
            return False

        # ✅ Mostra informações de uso para usuários próximos do limite
        remaining = rate_limiter.get_remaining_calls(user_email, user_role)
        stats = rate_limiter.get_usage_stats(user_email)

        # Aviso se estiver com poucas análises restantes no minuto
        if isinstance(remaining, dict) and remaining['per_minute'] <= 2:
            st.warning(
                f"⚠️ Você tem apenas **{remaining['per_minute']}** "
                f"análise(s) restante(s) neste minuto."
            )

        # ✅ Logging de sucesso
        stats = rate_limiter.get_usage_stats(user_email)
        logger.info(
            f"Rate limit OK - User: {user_email}, "
            f"Usage: {stats['calls_last_minute']}/{stats['rpm_limit']} per min, "
            f"{stats['calls_today']}/{stats['rpd_limit']} per day"
        )

        # Aviso se estiver com poucas análises restantes no dia
        if isinstance(remaining, dict) and remaining['per_day'] <= 10:
            st.info(
                f"ℹ️ Você usou **{stats['calls_today']}/{stats['rpd_limit']}** "
                f"análises hoje. Restam **{remaining['per_day']}**."
            )

        return True

    def _generate_response(self, model, pdf_files, question):
        """
        Função interna que prepara e envia a requisição para um modelo Gemini específico, com timeout.
        """
        
        q = Queue()

        def worker():
            try:
                # Preparar os inputs para o modelo
                inputs = []
                
                for pdf_file in pdf_files:
                    if hasattr(pdf_file, 'read'):  # Se for um objeto de arquivo (como st.UploadedFile)
                        pdf_bytes = pdf_file.getvalue() # Use getvalue() que é mais seguro
                    else:  # Se for um caminho de arquivo (string)
                        with open(pdf_file, 'rb') as f:
                            pdf_bytes = f.read()
                    
                    part = {"mime_type": "application/pdf", "data": pdf_bytes}
                    inputs.append(part)
                
                # Adicionar a pergunta como texto
                inputs.append({"text": question})
                
                # Gerar resposta usando o modelo multimodal fornecido
                response = model.generate_content(inputs)
                
                q.put(response.text)
                
            except Exception as e:
                q.put(e)

        thread = threading.Thread(target=worker)
        thread.start()
        
        try:
            # Espera por 120 segundos
            result = q.get(timeout=120)
            if isinstance(result, Exception):
                raise result
            return result
        except Empty:
            st.error("A análise da IA excedeu o tempo limite (120s). Tente novamente.")
            return None
        except Exception as e:
            st.error(f"Erro na comunicação com a API Gemini: {str(e)}")
            return None
