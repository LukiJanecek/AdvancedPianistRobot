# Base image pro Raspberry Pi
FROM --platform=linux/arm/v7 raspbian/stretch:latest

# Instalace gcc, make a potřebných knihoven
RUN apt-get update && \
    apt-get install -y build-essential cmake libtool libusb-1.0-0-dev && \
    rm -rf /var/lib/apt/lists/*

# Nastavení pracovního adresáře
WORKDIR /app

# Zkopírování cpp souboru
COPY pianist_LED_animations_top.cpp /app/

# Kompilace
RUN g++ -std=c++17 -O2 pianist_LED_animations_top.cpp -o pianist_LED_top -lpthread -lws2811

# Spuštění
CMD ["./pianist_LED_top"]