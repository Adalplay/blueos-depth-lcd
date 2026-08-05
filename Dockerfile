FROM python:3.11-slim-bookworm

ARG TARGETARCH

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY depth_lcd ./depth_lcd

EXPOSE 80/tcp

LABEL version="0.2.0"
LABEL permissions='{\
  "ExposedPorts": {\
    "80/tcp": {}\
  },\
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
    ],\
    "PortBindings": {\
      "80/tcp": [\
        {\
          "HostPort": ""\
        }\
      ]\
    }\
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
    LCD_TITLE=Profundidade: \
    UPDATE_INTERVAL=0.5 \
    STALE_TIMEOUT=5

ENTRYPOINT ["python", "-m", "depth_lcd.main"]
