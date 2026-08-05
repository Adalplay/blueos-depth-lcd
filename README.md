# BlueOS Depth LCD

Extensão BlueOS que recebe a profundidade calculada pelo ArduSub via MAVLink e
mostra o valor em um LCD I²C 16x2. A extensão **não acessa o Bar30**; ela acessa
somente o endereço do LCD.

Desde a versão `0.2.0`, a extensão também disponibiliza uma página no menu do
BlueOS com profundidade em tempo real, estado do MAVLink, estado do LCD, teste
do display e edição temporária do texto da primeira linha. Se o LCD estiver
desconectado, a página continua funcionando e informa o erro encontrado.

## Hardware

Configuração padrão:

- LCD: PCF8574, endereço `0x27`
- Barramento: `/dev/i2c-6` da Navigator
- Display: 16 colunas por 2 linhas

O Bar30 (`0x76`) e o LCD (`0x27` ou `0x3F`) podem compartilhar SDA/SCL por
terem endereços diferentes. Confirme que o backpack do LCD não aplica 5 V às
linhas SDA/SCL da Raspberry Pi. Use um conversor de nível I²C se necessário.

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `MAVLINK2REST_URL` | `http://host.docker.internal:6040/v1/mavlink` | API interna usada pelo Inspector MAVLink |
| `DEPTH_SOURCE` | `GLOBAL_POSITION_INT` | `AUTO`, `GLOBAL_POSITION_INT`, `LOCAL_POSITION_NED` ou `VFR_HUD` |
| `I2C_BUS` | `6` | Número do barramento do LCD |
| `LCD_ADDRESS` | `0x27` | Endereço I²C do LCD |
| `LCD_EXPANDER` | `PCF8574` | Modelo do expansor aceito pelo RPLCD |
| `LCD_TITLE` | `Profundidade:` | Texto inicial da primeira linha do LCD |
| `UPDATE_INTERVAL` | `0.5` | Intervalo mínimo de atualização em segundos |
| `STALE_TIMEOUT` | `5` | Tempo para indicar perda de telemetria |
| `LOG_LEVEL` | `INFO` | Nível de log |

No modo `AUTO`, a extensão aceita:

1. `GLOBAL_POSITION_INT.relative_alt`, em milímetros e positivo para cima;
2. `LOCAL_POSITION_NED.z`, em metros e positivo para baixo;
3. `VFR_HUD.alt`, em metros e negativo abaixo da superfície.

Como mais de uma dessas mensagens pode estar disponível, o padrão fixa
`GLOBAL_POSITION_INT` para evitar alternância entre estimativas. Se ela não
estiver presente na sua configuração, selecione uma das outras fontes.

## Teste local

Os testes de conversão não precisam de hardware:

```sh
python -m unittest discover -s tests -v
```

## Build e publicação

O BlueOS instala extensões a partir de uma imagem em um registry. Execute em
uma máquina com Docker:

```sh
docker buildx create --name blueos-builder --use
docker buildx build \
  --platform linux/arm/v7,linux/arm64 \
  -t adalcirjr/blueos-depth-lcd:0.2.5 \
  --push .
```

Se a sua imagem do BlueOS for apenas 64-bit, pode publicar somente
`linux/arm64`.

## Instalação no BlueOS

1. Abra **Extensions > Installed**.
2. Clique no botão `+`.
3. Use:
   - Identifier: `adalcirjr.blueos-depth-lcd`
   - Name: `Depth LCD`
   - Docker image: `adalcirjr/blueos-depth-lcd`
   - Tag: `0.2.5`
4. Confirme as permissões e instale.
5. Consulte os logs da extensão.

### LCD em outro barramento

O `Dockerfile` concede acesso a `/dev/i2c-6`. Para usar, por exemplo,
`/dev/i2c-1`, altere **as duas ocorrências** do dispositivo nas permissões:

```json
{
  "HostConfig": {
    "Devices": [
      {
        "PathOnHost": "/dev/i2c-1",
        "PathInContainer": "/dev/i2c-1",
        "CgroupPermissions": "rwm"
      }
    ],
    "ExtraHosts": ["host.docker.internal:host-gateway"]
  }
}
```

Defina também `I2C_BUS=1`.

## Diagnóstico

- `No such file or directory`: o barramento configurado não existe no host.
- `Remote I/O error`: endereço incorreto, ligação elétrica ou alimentação.
- `Sem telemetria`: confirme o endpoint MAVLink e observe as mensagens no
  MAVLink Inspector do BlueOS.
- Profundidade sempre zero: selecione explicitamente outra `DEPTH_SOURCE`.
