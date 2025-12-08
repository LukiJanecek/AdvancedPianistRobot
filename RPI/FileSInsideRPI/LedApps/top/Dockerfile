FROM --platform=linux/arm/v7 debian:bullseye

RUN apt-get update && \
    apt-get install -y build-essential git scons libusb-1.0-0-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build knihovny rpi_ws281x
RUN git clone https://github.com/jgarff/rpi_ws281x.git /tmp/rpi_ws281x && \
    cd /tmp/rpi_ws281x && \
    scons && \
    mkdir -p /usr/local/include/ws2811 && \
    cp *.h /usr/local/include/ws2811/ && \
    cp libws2811.a /usr/local/lib/ && \
    cd / && rm -rf /tmp/rpi_ws281x

# Kopírování CPP aplikace
COPY pianist_LED_animations_top.cpp /app/

# Kompilace aplikace
RUN g++ -std=c++17 -O2 pianist_LED_animations_top.cpp -o pianist_LED_top \
    -lpthread -lws2811 -I/usr/local/include -L/usr/local/lib

# Entrypoint skript
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
