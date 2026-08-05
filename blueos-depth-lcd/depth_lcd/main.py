# Permite utilizar recursos modernos de anotações de tipo sem avaliá-los imediatamente.
from __future__ import annotations

# Importa o módulo usado para registrar mensagens de funcionamento e erros.
import logging
# Importa o módulo usado para ler as variáveis de ambiente da extensão.
import os
# Importa o módulo usado para tratar sinais de encerramento do contêiner.
import signal
# Importa o módulo usado para controlar o evento de parada da aplicação.
import threading
# Importa o módulo usado para medir intervalos de tempo.
import time

# Importa as ferramentas MAVLink da biblioteca pymavlink.
from pymavlink import mavutil

# Importa a função que converte mensagens MAVLink em profundidade.
from .depth import depth_from_message
# Importa a classe responsável por controlar o LCD I²C.
from .lcd import DepthLCD

# Lê o nível de log, usando INFO como padrão, e converte o texto para maiúsculas.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Lê o endereço da conexão MAVLink definido na configuração da extensão.
MAVLINK_ENDPOINT = os.getenv(
    # Define o nome da variável de ambiente e o endpoint padrão do BlueOS.
    "MAVLINK_ENDPOINT", "udpout:host.docker.internal:14550"
# Encerra a chamada que lê o endpoint MAVLink.
)
# Lê qual mensagem MAVLink deve ser usada como fonte de profundidade.
DEPTH_SOURCE = os.getenv("DEPTH_SOURCE", "GLOBAL_POSITION_INT").upper()
# Lê o número do barramento I²C, aceitando valores decimais ou com prefixo hexadecimal.
I2C_BUS = int(os.getenv("I2C_BUS", "6"), 0)
# Lê o endereço I²C do LCD, usando 0x27 como endereço padrão.
LCD_ADDRESS = int(os.getenv("LCD_ADDRESS", "0x27"), 0)
# Lê o modelo do expansor I²C instalado no módulo do LCD.
LCD_EXPANDER = os.getenv("LCD_EXPANDER", "PCF8574")
# Lê o intervalo de atualização e impede valores menores que 0,1 segundo.
UPDATE_INTERVAL = max(0.1, float(os.getenv("UPDATE_INTERVAL", "0.5")))
# Lê o tempo limite e impede valores menores que um segundo.
STALE_TIMEOUT = max(1.0, float(os.getenv("STALE_TIMEOUT", "5")))

# Configura o sistema de logs da aplicação.
logging.basicConfig(
    # Define quais níveis de mensagem serão exibidos.
    level=LOG_LEVEL,
    # Define o formato da data, nível, nome e conteúdo de cada mensagem.
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
# Encerra a configuração do sistema de logs.
)
# Cria o objeto de log identificado pelo nome depth-lcd.
LOGGER = logging.getLogger("depth-lcd")


# Define a função principal executada quando a extensão é iniciada.
def run() -> None:
    # Cria um evento compartilhado que indicará quando o programa deve encerrar.
    stop_event = threading.Event()

    # Define a função chamada quando o sistema solicitar o encerramento.
    def request_stop(_signum, _frame) -> None:
        # Marca o evento de parada para encerrar o laço principal com segurança.
        stop_event.set()

    # Associa o sinal SIGTERM, usado pelo Docker, à função de encerramento seguro.
    signal.signal(signal.SIGTERM, request_stop)
    # Associa o sinal SIGINT, normalmente gerado por Ctrl+C, à mesma função.
    signal.signal(signal.SIGINT, request_stop)

    # Registra no log os principais parâmetros usados ao iniciar a extensão.
    LOGGER.info(
        # Define o formato da mensagem inicial.
        "Iniciando: MAVLink=%s, fonte=%s, I2C=%d, LCD=0x%02X",
        # Informa o endpoint MAVLink selecionado.
        MAVLINK_ENDPOINT,
        # Informa a fonte de profundidade selecionada.
        DEPTH_SOURCE,
        # Informa o número do barramento I²C selecionado.
        I2C_BUS,
        # Informa o endereço I²C do LCD.
        LCD_ADDRESS,
    # Encerra a chamada que registra a mensagem inicial.
    )
    # Inicializa o LCD com o barramento, endereço e expansor configurados.
    lcd = DepthLCD(I2C_BUS, LCD_ADDRESS, LCD_EXPANDER)

    # Cria a conexão da extensão com o roteador MAVLink do BlueOS.
    connection = mavutil.mavlink_connection(
        # Informa o endereço utilizado para estabelecer a conexão.
        MAVLINK_ENDPOINT,
        # Identifica esta extensão como sistema MAVLink número 250.
        source_system=250,
        # Identifica esta extensão como componente MAVLink número 191.
        source_component=191,
        # Solicita reconexão automática se a comunicação for interrompida.
        autoreconnect=True,
    # Encerra a criação da conexão MAVLink.
    )

    # Armazena o instante da última amostra de profundidade recebida.
    last_sample_at = 0.0
    # Armazena o instante da última atualização feita no LCD.
    last_display_at = 0.0
    # Armazena o instante do último heartbeat MAVLink enviado.
    last_heartbeat_at = 0.0
    # Indica se o aviso de telemetria ausente já foi escrito no LCD.
    stale_displayed = False

    # Inicia um bloco que sempre liberará os recursos ao terminar.
    try:
        # Mantém a extensão em execução enquanto não houver pedido de parada.
        while not stop_event.is_set():
            # Obtém um relógio monotônico, que não é afetado por ajustes de data e hora.
            now = time.monotonic()
            # Verifica se já passou pelo menos um segundo desde o último heartbeat.
            if now - last_heartbeat_at >= 1.0:
                # Envia uma mensagem heartbeat para anunciar a extensão na rede MAVLink.
                connection.mav.heartbeat_send(
                    # Identifica o componente como um controlador embarcado.
                    mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
                    # Informa que a extensão não é um piloto automático.
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    # Informa zero como modo básico, pois a extensão não controla o veículo.
                    0,
                    # Informa zero como modo personalizado.
                    0,
                    # Informa que o componente está ativo.
                    mavutil.mavlink.MAV_STATE_ACTIVE,
                # Encerra o envio do heartbeat.
                )
                # Registra o momento em que o heartbeat foi enviado.
                last_heartbeat_at = now

            # Aguarda uma das mensagens MAVLink capazes de fornecer profundidade.
            message = connection.recv_match(
                # Limita a recepção aos três tipos de mensagem suportados.
                type=["GLOBAL_POSITION_INT", "LOCAL_POSITION_NED", "VFR_HUD"],
                # Faz a chamada aguardar por uma mensagem em vez de retornar imediatamente.
                blocking=True,
                # Limita a espera a um segundo para permitir verificar o encerramento.
                timeout=1,
            # Encerra a chamada de recepção da mensagem MAVLink.
            )
            # Atualiza o instante atual depois do período de espera da recepção.
            now = time.monotonic()

            # Verifica se alguma mensagem foi recebida.
            if message is not None:
                # Converte a mensagem recebida em uma amostra de profundidade.
                sample = depth_from_message(message, DEPTH_SOURCE)
                # Continua somente se a mensagem corresponder à fonte selecionada.
                if sample is not None:
                    # Registra o momento da última amostra válida.
                    last_sample_at = now
                    # Permite que um futuro aviso de perda de telemetria seja exibido.
                    stale_displayed = False
                    # Verifica se já chegou o momento de atualizar o LCD novamente.
                    if now - last_display_at >= UPDATE_INTERVAL:
                        # Escreve no LCD a profundidade e o nome da mensagem de origem.
                        lcd.show_depth(sample.depth_m, sample.source)
                        # Registra o momento da atualização do LCD.
                        last_display_at = now
                        # Registra a leitura detalhada quando o log estiver em DEBUG.
                        LOGGER.debug(
                            # Define o formato da mensagem de diagnóstico.
                            "Profundidade %.3f m via %s",
                            # Informa a profundidade calculada em metros.
                            sample.depth_m,
                            # Informa o tipo de mensagem MAVLink utilizado.
                            sample.source,
                        # Encerra o registro da mensagem de diagnóstico.
                        )

            # Verifica se havia telemetria, se ela expirou e se o aviso ainda não foi exibido.
            if (
                # Confirma que pelo menos uma amostra foi recebida anteriormente.
                last_sample_at
                # Confirma que o tempo sem amostras ultrapassou o limite configurado.
                and now - last_sample_at > STALE_TIMEOUT
                # Confirma que o aviso ainda não está sendo mostrado.
                and not stale_displayed
            # Encerra as condições da verificação de telemetria expirada.
            ):
                # Mostra no LCD que a comunicação MAVLink foi perdida.
                lcd.show_lines("Sem telemetria", "Verifique MAVLink")
                # Marca que o aviso já foi exibido para evitar reescritas contínuas.
                stale_displayed = True
            # Verifica se nenhuma amostra foi recebida e o aviso inicial ainda não foi mostrado.
            elif not last_sample_at and not stale_displayed:
                # Mostra no LCD que a extensão está aguardando dados do MAVLink.
                lcd.show_lines("Aguardando dados", "MAVLink...")
                # Marca que a mensagem de espera já foi exibida.
                stale_displayed = True
    # Define as ações que sempre serão executadas, mesmo em caso de erro.
    finally:
        # Limpa, fecha e libera o dispositivo LCD.
        lcd.close()
        # Fecha e libera a conexão MAVLink.
        connection.close()


# Verifica se este arquivo foi executado diretamente como módulo principal.
if __name__ == "__main__":
    # Inicia a função principal da extensão.
    run()
