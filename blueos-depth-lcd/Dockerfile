FROM python:3.11-slim-bookworm

ARG TARGETARCH

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY depth_lcd ./depth_lcd

LABEL version="0.1.0"
LABEL permissions='{\
  "HostConfig": {\
    "Devices": [\
      {\
        "PathOnHost": "/dev/i2c-6",\
        "PathInContainer": "/dev/i2c-6",\
        "CgroupPermissions": "rwm"\
      }\
    ],\
    "ExtraHosts": [\
      "host.docker.internal:host-gateway"\
    ]\
  }\
}'
LABEL authors='[{"name":"Adalcir Moreira"}]'
LABEL company='{"about":"","name":"Adalcir Moreira","email":""}'
LABEL type="device-integration"
LABEL tags='["display","depth","mavlink","i2c"]'
LABEL requirements="core >= 1.1"
LABEL readme="https://raw.githubusercontent.com/Adalplay/blueos-depth-lcd/{tag}/README.md"
LABEL links='{"website":"https://github.com/Adalplay/blueos-depth-lcd","support":"https://github.com/Adalplay/blueos-depth-lcd/issues"}'

ENV PYTHONUNBUFFERED=1 \
    MAVLINK_ENDPOINT=udpout:host.docker.internal:14550 \
    DEPTH_SOURCE=GLOBAL_POSITION_INT \
    I2C_BUS=6 \
    LCD_ADDRESS=0x27 \
    LCD_EXPANDER=PCF8574 \
    UPDATE_INTERVAL=0.5 \
    STALE_TIMEOUT=5

ENTRYPOINT ["python", "-m", "depth_lcd.main"]
