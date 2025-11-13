/**
 * @file LEDs_klavesy.cpp
 * @author Bc. Jan Besta
 * @brief Fully working version of animations on number got from named pipeline of python script.
 */

#include <ws2811/ws2811.h>
#include <iostream>
#include <unistd.h>
#include <fcntl.h>
#include <cstring>
#include <chrono>
#include <thread>
#include <vector>
#include <random>
#include <cmath>
#include <sys/stat.h>

#define LED_COUNT 200
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

// ---------------- LED setup ----------------
ws2811_t ledstring = {
    .freq = WS2811_TARGET_FREQ,
    .dmanum = DMA,
    .channel =
        {
            [0] = {
                .gpionum = GPIO_PIN,
                .invert = 0,
                .count = LED_COUNT,
                .strip_type = WS2811_STRIP_GRB,
                .brightness = BRIGHTNESS,
            },
            [1] = {0},
        },
};

struct Snake {
    bool active = false;
    int origin = 0;
    int step = 0;
    int prevStep = -1;
    int length = SNAKE_LENGTH;
    uint8_t hue = 0;
    std::chrono::steady_clock::time_point lastUpdate;
    unsigned long stepInterval = SNAKE_STEP_MS;
};

std::vector<Snake> snakes(MAX_SNAKES);
uint16_t brightnessSum[LED_COUNT];
uint32_t hueWeightedSum[LED_COUNT];
uint8_t overlapCount[LED_COUNT];

std::mt19937 rng(std::random_device{}());

// ---------------- helper ----------------
static inline int clampInt(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

uint8_t brightnessForDistance(int dist, int length) {
    if (dist < 0 || dist >= length) return 0;
    if (length <= 1) return SNAKE_FADE_MAX;
    int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
    return (uint8_t)clampInt(b, 0, 255);
}

bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= LED_COUNT) return false;
    for (auto &s : snakes) {
        if (!s.active) {
            s.active = true;
            s.origin = originIndex;
            s.step = 0;
            s.prevStep = -1;
            s.length = SNAKE_LENGTH;
            s.hue = hue;
            s.lastUpdate = std::chrono::steady_clock::now();
            s.stepInterval = SNAKE_STEP_MS;
            return true;
        }
    }
    return false;
}

void killSnake(Snake &s) { s.active = false; }

void updateSnakes() {
    auto now = std::chrono::steady_clock::now();
    for (auto &s : snakes) {
        if (!s.active) continue;
        auto elapsed_ms_ll = std::chrono::duration_cast<std::chrono::milliseconds>(now - s.lastUpdate).count();
        unsigned long elapsed_ms = static_cast<unsigned long>(elapsed_ms_ll < 0 ? 0 : elapsed_ms_ll);
        if (elapsed_ms >= s.stepInterval) {
            s.lastUpdate = now;
            s.prevStep = s.step;
            s.step++;

            bool anyOnStrip = false;
            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < s.length; ++d) {
                    int pos = s.origin + (s.step - d) * dir;
                    if (pos >= 0 && pos < LED_COUNT) { anyOnStrip = true; break; }
                }
                if (anyOnStrip) break;
            }
            if (!anyOnStrip) killSnake(s);
        }
    }
}

void renderSnakesToBuffers() {
    uint32_t contributors[LED_COUNT];
    memset(brightnessSum, 0, sizeof(brightnessSum));
    memset(hueWeightedSum, 0, sizeof(hueWeightedSum));
    memset(contributors, 0, sizeof(contributors));
    memset(overlapCount, 0, sizeof(overlapCount));

    for (int s = 0; s < (int)snakes.size(); ++s) {
        if (!snakes[s].active) continue;
        Snake &sn = snakes[s];
        int origin = sn.origin;
        int len = sn.length;
        uint8_t hue = sn.hue;

        int fromStep = std::max(0, sn.prevStep);
        int toStep = sn.step;

        for (int stepVal = fromStep; stepVal <= toStep; ++stepVal) {
            if (stepVal == 0) {
                if (origin >= 0 && origin < LED_COUNT) {
                    int pos = origin;
                    uint32_t mask = (1UL << s);
                    if (!(contributors[pos] & mask)) {
                        uint8_t b = brightnessForDistance(0, len);
                        brightnessSum[pos] += b;
                        hueWeightedSum[pos] += (uint32_t)hue * b;
                        contributors[pos] |= mask;
                    }
                }
                continue;
            }
            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (stepVal - d) * dir;
                    if (pos < 0 || pos >= LED_COUNT) continue;
                    uint32_t mask = (1UL << s);
                    if (contributors[pos] & mask) continue;
                    uint8_t b = brightnessForDistance(d, len);
                    if (b == 0) continue;
                    brightnessSum[pos] += b;
                    hueWeightedSum[pos] += (uint32_t)hue * b;
                    contributors[pos] |= mask;
                }
            }
        }
    }

    for (int i = 0; i < LED_COUNT; ++i) {
        overlapCount[i] = __builtin_popcount((unsigned int)contributors[i]);
    }
}

uint32_t hsvToRgb(uint8_t h, uint8_t s, uint8_t v) {
    // jednoduchďż˝ konverze; vstupy: 0..255
    float H = (float)h * 360.0f / 255.0f;
    float S = (float)s / 255.0f;
    float V = (float)v / 255.0f;

    float C = V * S;
    float X = C * (1 - fabsf(fmodf(H / 60.0f, 2) - 1));
    float m = V - C;

    float r=0,g=0,b=0;
    if (H < 60) { r=C; g=X; b=0; }
    else if (H < 120) { r=X; g=C; b=0; }
    else if (H < 180) { r=0; g=C; b=X; }
    else if (H < 240) { r=0; g=X; b=C; }
    else if (H < 300) { r=X; g=0; b=C; }
    else { r=C; g=0; b=X; }

    uint8_t R = (uint8_t)clampInt((int)round((r + m) * 255.0f), 0, 255);
    uint8_t G = (uint8_t)clampInt((int)round((g + m) * 255.0f), 0, 255);
    uint8_t B = (uint8_t)clampInt((int)round((b + m) * 255.0f), 0, 255);

    return ((uint32_t)R << 16) | ((uint32_t)G << 8) | (uint32_t)B;
}

void composeAndShow() {
    for (int i = 0; i < LED_COUNT; ++i) {
        if (brightnessSum[i] == 0) {
            ledstring.channel[0].leds[i] = 0;
            continue;
        }

        uint16_t totalB = brightnessSum[i];
        uint8_t avgHue = (uint8_t)(hueWeightedSum[i] / totalB);
        uint8_t finalHue = avgHue;
        if (overlapCount[i] > 1) {
            int shift = (overlapCount[i] - 1) * HUE_SHIFT_PER_OVERLAP;
            finalHue = (avgHue + shift) & 0xFF;
        }

        uint8_t bright = totalB > 255 ? 255 : (uint8_t)totalB;
        ledstring.channel[0].leds[i] = hsvToRgb(finalHue, SATURATION, bright);
    }

    ws2811_render(&ledstring);
}

// ---------------- PIPE input ----------------
int openPipe(const char *path) {
    mkfifo(path, 0666);
    int fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) perror("openPipe");
    return fd;
}

// ---------------- MAIN ----------------
int main() {
    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!\n";
        return -1;
    }

    const char *pipePath = "/tmp/ledpipe";
    int pipeFd = openPipe(pipePath);

    auto lastRender = std::chrono::steady_clock::now();
    std::uniform_int_distribution<int> distIndex(0, LED_COUNT - 1);

    while (true) {
        // ďż˝ti ďż˝ďż˝slo z pipe
        char buf[32];
        int n = read(pipeFd, buf, sizeof(buf) - 1);
        if (n > 0) {
            buf[n] = '\0';
            int val = atoi(buf);
            if (val >= 1 && val <= 22) {
                uint8_t hue = (val * 10) % 255;
                spawnSnake(distIndex(rng), hue);
            }
        }

        updateSnakes();

        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - lastRender).count() >= 20) {
            lastRender = now;
            renderSnakesToBuffers();
            composeAndShow();
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    ws2811_fini(&ledstring);
    close(pipeFd);
    return 0;
}
