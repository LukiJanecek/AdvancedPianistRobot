# Base image pro Raspberry Pi
FROM --platform=linux/arm/v7 raspbian/stretch:latest

RUN apt-get update && \
    apt-get install -y build-essential cmake libtool libusb-1.0-0-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pianist_LED_animations_btm.cpp /app/

RUN g++ -std=c++17 -O2 pianist_LED_animations_btm.cpp -o pianist_LED_btm -lpthread -lws2811

CMD ["./pianist_LED_btm"]
