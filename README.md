# BlueOS Depth Display

Extensão BlueOS que recebe a profundidade calculada pelo ArduSub via MAVLink e
permite escolher entre dois displays I2C:

- LCD 16x2 com expansor PCF8574;
- display de sete segmentos, quatro dígitos, com controlador HT16K33.

A extensão não lê diretamente o Bar30. O controlador principal continua
responsável pelo sensor, e a extensão consulta a profundidade pelo MAVLink2Rest.

## Seleção do display

Use a variável `DISPLAY_TYPE` nos Custom Settings:

```text
DISPLAY_TYPE=LCD
```

ou:

```text
DISPLAY_TYPE=HT16K33
```

A seleção é feita quando a extensão inicia. Depois de alterar a variável,
reinicie a extensão.

## Formato do HT16K33

O HT16K33 mostra quatro algarismos e o ponto decimal não ocupa um dígito. A
profundidade é apresentada no formato `00.00`, por exemplo:

| Profundidade | Display |
|---:|:---|
| 0,00 m | `00.00` |
| 2,35 m | `02.35` |
| 12,34 m | `12.34` |
| 99,99 m | `99.99` |
| Sem valor válido ou fora da faixa | `----` |

A faixa suportada pelo display é de `0,00` a `99,99` metros. A página web
continua mostrando o valor completo recebido pelo MAVLink.

## Configurações

| Variável | Padrão | Descrição |
|---|---|---|
| `DISPLAY_TYPE` | `LCD` | Tipo do display: `LCD` ou `HT16K33` |
| `MAVLINK2REST_URL` | `http://host.docker.internal:6040/v1/mavlink` | API interna do MAVLink |
| `DEPTH_SOURCE` | `GLOBAL_POSITION_INT` | Fonte da profundidade |
| `I2C_BUS` | `6` | Barramento I2C da Navigator |
| `LCD_ADDRESS` | `0x27` | Endereço do LCD 16x2 |
| `LCD_EXPANDER` | `PCF8574` | Modelo do expansor do LCD |
| `LCD_TITLE` | `Profundidade:` | Primeira linha do LCD |
| `HT16K33_ADDRESS` | `0x70` | Endereço do HT16K33 |
| `HT16K33_BRIGHTNESS` | `8` | Brilho de `0` a `15` |
| `UPDATE_INTERVAL` | `0.5` | Intervalo de atualização em segundos |
| `STALE_TIMEOUT` | `5` | Tempo para indicar perda da telemetria |
| `DISPLAY_RETRY_INTERVAL` | `5` | Intervalo entre tentativas de conexão |
| `LOG_LEVEL` | `INFO` | Nível dos logs |

## Custom Settings para LCD

```text
DISPLAY_TYPE=LCD
I2C_BUS=6
LCD_ADDRESS=0x27
LCD_EXPANDER=PCF8574
LCD_TITLE=Profundidade:
DEPTH_SOURCE=GLOBAL_POSITION_INT
```

## Custom Settings para HT16K33

```text
DISPLAY_TYPE=HT16K33
I2C_BUS=6
HT16K33_ADDRESS=0x70
HT16K33_BRIGHTNESS=8
DEPTH_SOURCE=GLOBAL_POSITION_INT
```

## Ligações do HT16K33

O módulo normalmente possui `VCC`, `GND`, `SDA` e `SCL`. Confirme na
documentação do módulo a tensão de alimentação e os níveis lógicos aceitos
antes de conectá-lo à Navigator. Não presuma que todo módulo HT16K33 tenha o
mesmo circuito de alimentação ou conversão de nível.

O endereço padrão costuma ser `0x70`, mas pode variar se as pontes de endereço
do módulo tiverem sido alteradas.

## Página web

A página da extensão informa:

- profundidade atual;
- conexão MAVLink;
- tipo e estado do display selecionado;
- fonte MAVLink;
- erro de comunicação I2C;
- botão de teste do display.

A edição do texto da primeira linha aparece somente quando `DISPLAY_TYPE=LCD`,
pois o HT16K33 mostra apenas números e sinais simples.

## Testes

Os testes não precisam de display físico:

```sh
python -m unittest discover -s tests -v
```

## Build

A nova linha de desenvolvimento começa na versão `0.3.0`:

```sh
docker buildx build \
  --platform linux/arm/v7,linux/arm64 \
  -t adalcirjr/blueos-depth-lcd:0.3.0 \
  --push .
```

O `manifest.json` deve receber os digests ARMv7 e ARM64 somente depois que a
imagem `0.3.0` tiver sido publicada no Docker Hub.
