// Teoreticky nastrel - prevedyn kod z Fastled z esp32 + implementovana funkce komhunikace pres named pipe - python kod


#include <ws2811/ws2811.h>
#include <iostream>
#include <unistd.h>
#include <cstring>
#include <fcntl.h>
#include <cstdlib>
#include <ctime>

#define NUM_LEDS 30
#define GPIO_PIN 18
#define DMA 10
#define BRIGHTNESS 255

#define MAX_SNAKES 10
#define SNAKE_LENGTH 5
#define SNAKE_STEP_MS 50
#define SNAKE_FADE_MIN 50
#define SNAKE_FADE_MAX 255
#define HUE_SHIFT_PER_OVERLAP 30
#define SATURATION 230

ws2811_t ledstring;

// --- Snake struct ---
struct Snake {
    bool active = false;
    int origin = 0;
    int step = 0;
    int prevStep = -1;
    int length = SNAKE_LENGTH;
    uint8_t hue = 0;
    unsigned long lastUpdate = 0;
    unsigned long stepInterval = SNAKE_STEP_MS;
};

Snake snakes[MAX_SNAKES];

// --- Buffers pro render ---
uint16_t brightnessSum[NUM_LEDS];
uint32_t hueWeightedSum[NUM_LEDS];
uint8_t overlapCount[NUM_LEDS];

// --- Random hue generator ---
uint8_t gHue = 0;

// --- Helper functions ---
uint8_t brightnessForDistance(int dist, int length) {
    if (dist < 0 || dist >= length) return 0;
    if (length <= 1) return SNAKE_FADE_MAX;
    int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
    if (b < 0) b = 0;
    if (b > 255) b = 255;
    return b;
}

bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= NUM_LEDS) return false;
    for (int i = 0; i < MAX_SNAKES; ++i) {
        if (!snakes[i].active) {
            snakes[i].active = true;
            snakes[i].origin = originIndex;
            snakes[i].step = 0;
            snakes[i].prevStep = -1;
            snakes[i].length = SNAKE_LENGTH;
            snakes[i].hue = hue;
            snakes[i].lastUpdate = millis();
            snakes[i].stepInterval = SNAKE_STEP_MS;
            return true;
        }
    }
    return false;
}

void killSnake(int idx) {
    if (idx >= 0 && idx < MAX_SNAKES) snakes[idx].active = false;
}

unsigned long millis() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

void setAll(uint32_t color) {
    for (int i = 0; i < NUM_LEDS; ++i)
        ledstring.channel[0].leds[i] = color;
    ws2811_render(&ledstring);
}

void updateSnakes() {
    unsigned long now = millis();
    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        if (now - snakes[s].lastUpdate >= snakes[s].stepInterval) {
            snakes[s].lastUpdate = now;
            snakes[s].prevStep = snakes[s].step;
            snakes[s].step++;

            // kill pokud už není žádná část na pásu
            bool anyOnStrip = false;
            int origin = snakes[s].origin;
            int len = snakes[s].length;
            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (snakes[s].step - d) * dir;
                    if (pos >= 0 && pos < NUM_LEDS) { anyOnStrip = true; break; }
                }
                if (anyOnStrip) break;
            }
            if (!anyOnStrip) killSnake(s);
        }
    }
}

void renderSnakesToBuffers() {
    static uint32_t contributors[NUM_LEDS];
    for (int i = 0; i < NUM_LEDS; ++i) {
        brightnessSum[i] = 0;
        hueWeightedSum[i] = 0;
        contributors[i] = 0;
        overlapCount[i] = 0;
    }

    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        int origin = snakes[s].origin;
        int len = snakes[s].length;
        uint8_t hue = snakes[s].hue;

        int fromStep = std::max(0, snakes[s].prevStep);
        int toStep = snakes[s].step;
        for (int stepVal = fromStep; stepVal <= toStep; ++stepVal) {
            if (stepVal == 0) {
                if (origin >= 0 && origin < NUM_LEDS) {
                    uint32_t mask = (1UL << s);
                    if (!(contributors[origin] & mask)) {
                        uint8_t b = brightnessForDistance(0, len);
                        brightnessSum[origin] += b;
                        hueWeightedSum[origin] += (uint32_t)hue * b;
                        contributors[origin] |= mask;
                    }
                }
                continue;
            }
            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (stepVal - d) * dir;
                    if (pos < 0 || pos >= NUM_LEDS) continue;
                    uint32_t mask = (1UL << s);
                    if (contributors[pos] & mask) continue;
                    uint8_t b = brightnessForDistance(d, len);
                    brightnessSum[pos] += b;
                    hueWeightedSum[pos] += (uint32_t)hue * b;
                    contributors[pos] |= mask;
                }
            }
        }
    }

    for (int i = 0; i < NUM_LEDS; ++i) {
        overlapCount[i] = __builtin_popcount((unsigned int)contributors[i]);
        uint16_t totalB = brightnessSum[i];
        if (totalB == 0) ledstring.channel[0].leds[i] = 0x000000;
        else {
            uint8_t avgHue = hueWeightedSum[i] / totalB;
            uint8_t finalHue = avgHue;
            if (overlapCount[i] > 1) finalHue = (avgHue + (overlapCount[i]-1)*HUE_SHIFT_PER_OVERLAP) & 0xFF;
            uint8_t val = (totalB > 255)? 255 : totalB;
            // jednoduchá aproximace HSV->RGB pro červené odstíny
            // jen pro test: map hue 0-255 na červené odstíny
            ledstring.channel[0].leds[i] = (val << 16); // červená
        }
    }
    ws2811_render(&ledstring);
}

// --- FIFO / pipe ---
const char *fifo_path = "/tmp/ledpipe";
int fd = -1;

void initPipe() {
    mkfifo(fifo_path, 0666);
    fd = open(fifo_path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        perror("open fifo");
        exit(1);
    }
}

void checkPipe() {
    char buf[128];
    ssize_t n = read(fd, buf, sizeof(buf)-1);
    if (n > 0) {
        buf[n] = '\0';
        int idx = atoi(buf);
        uint8_t hue = rand() % 256;
        spawnSnake(idx, hue);
        std::cout << "Spawn snake at " << idx << " hue=" << (int)hue << std::endl;
    }
}

// --- Main ---
int main() {
    srand(time(0));

    memset(&ledstring, 0, sizeof(ws2811_t));
    ledstring.freq = WS2811_TARGET_FREQ;
    ledstring.dmanum = DMA;
    ledstring.channel[0].gpionum = GPIO_PIN;
    ledstring.channel[0].invert = 0;
    ledstring.channel[0].count = NUM_LEDS;
    ledstring.channel[0].strip_type = WS2811_STRIP_GRB;
    ledstring.channel[0].brightness = BRIGHTNESS;

    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!" << std::endl;
        return -1;
    }

    initPipe();

    const unsigned long RENDER_INTERVAL = 20;
    unsigned long lastRender = 0;

    while (true) {
        checkPipe();
        updateSnakes();

        unsigned long now = millis();
        if (now - lastRender >= RENDER_INTERVAL) {
            lastRender = now;
            renderSnakesToBuffers();
        }

        usleep(1000); // 1 ms
    }

    ws2811_fini(&ledstring);
    close(fd);
    return 0;
}
