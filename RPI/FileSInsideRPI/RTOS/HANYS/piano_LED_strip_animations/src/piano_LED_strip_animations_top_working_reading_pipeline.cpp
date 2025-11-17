//============================================================================
// Name        : piano_LED_strip_animations_top.cpp
// Author      : Jan Besta
// Version     : 
// Copyright   : 
// Description : 
//============================================================================

#include <ws2811/ws2811.h>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <cmath>

static inline int clampInt(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

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
#define PIPE_PATH "/tmp/ledpipe"

using namespace std::chrono;

ws2811_t ledstring = {
    .freq = WS2811_TARGET_FREQ,
    .dmanum = DMA,
    .channel =
    {
        [0] =
        {
            .gpionum    = GPIO_PIN,
            .invert     = 0,
            .count      = LED_COUNT,
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
    int prevStep = -1; // <-- přidáno
    int length = SNAKE_LENGTH;
    uint8_t hue = 0;
    steady_clock::time_point lastUpdate;
    int stepInterval = SNAKE_STEP_MS;
};

Snake snakes[MAX_SNAKES];

uint16_t brightnessSum[LED_COUNT];
uint32_t hueWeightedSum[LED_COUNT];
uint8_t overlapCount[LED_COUNT];

std::atomic<bool> running(true);

// ---------- Helper ----------
uint8_t brightnessForDistance(int dist, int length) {
    if (dist < 0 || dist >= length) return 0;
    if (length <= 1) return SNAKE_FADE_MAX;
    int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
    return (uint8_t)clampInt(b, 0, 255);
}

bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= LED_COUNT) return false;
    for (int i = 0; i < MAX_SNAKES; ++i) {
        if (!snakes[i].active) {
            snakes[i].active = true;
            snakes[i].origin = originIndex;
            snakes[i].step = 0;
            snakes[i].prevStep = -1; // reset prevStep
            snakes[i].length = SNAKE_LENGTH;
            snakes[i].hue = hue;
            snakes[i].lastUpdate = steady_clock::now();
            return true;
        }
    }
    return false;
}

void killSnake(int idx) { if (idx>=0 && idx<MAX_SNAKES) snakes[idx].active = false; }

void updateSnakes() {
    auto now = steady_clock::now();
    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        auto elapsed = duration_cast<milliseconds>(now - snakes[s].lastUpdate).count();
        if (elapsed >= snakes[s].stepInterval) {
            snakes[s].lastUpdate = now;
            snakes[s].prevStep = snakes[s].step; // <-- uložíme předchozí krok
            snakes[s].step++;

            bool anyOnStrip = false;
            int origin = snakes[s].origin;
            int len = snakes[s].length;
            int stepToCheck = snakes[s].step;
            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (stepToCheck - d) * dir;
                    if (pos >= 0 && pos < LED_COUNT) { anyOnStrip = true; break; }
                }
                if (anyOnStrip) break;
            }
            if (!anyOnStrip && snakes[s].step == 0 && origin >= 0 && origin < LED_COUNT) anyOnStrip = true;

            if (!anyOnStrip) killSnake(s);
        }
    }
}

void renderSnakesToBuffers() {
    static uint32_t contributors[LED_COUNT];

    for (int i = 0; i < LED_COUNT; ++i) {
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
                if (origin >= 0 && origin < LED_COUNT) {
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

    for (int i = 0; i < LED_COUNT; ++i)
        overlapCount[i] = __builtin_popcount((unsigned int)contributors[i]);
}

void composeAndShow() {
    for (int i = 0; i < LED_COUNT; ++i) {
        ws2811_led_t color;
        if (brightnessSum[i] == 0) color = 0x000000;
        else {
            uint16_t totalB = brightnessSum[i];
            uint8_t avgHue = (uint8_t)(hueWeightedSum[i] / totalB);
            uint8_t finalHue = avgHue;
            if (overlapCount[i] > 1) {
                int shift = (overlapCount[i] - 1) * HUE_SHIFT_PER_OVERLAP;
                finalHue = (uint8_t)((avgHue + shift) & 0xFF);
            }

            float H = finalHue / 255.0f * 360.0f;
            float S = SATURATION / 255.0f;
            float V = std::min(totalB, (uint16_t)255) / 255.0f;

            float C = V * S;
            float X = C * (1 - std::fabs(fmod(H / 60.0f, 2.0f) - 1));
            float m = V - C;

            float r=0,g=0,b=0;
            if (H < 60) { r=C; g=X; b=0; }
            else if (H<120) { r=X; g=C; b=0; }
            else if(H<180){ r=0; g=C; b=X; }
            else if(H<240){ r=0; g=X; b=C; }
            else if(H<300){ r=X; g=0; b=C; }
            else{ r=C; g=0; b=X; }

            uint8_t R = (uint8_t)clampInt((int)round((r+m)*255.0f),0,255);
            uint8_t G = (uint8_t)clampInt((int)round((g+m)*255.0f),0,255);
            uint8_t B = (uint8_t)clampInt((int)round((b+m)*255.0f),0,255);
            color = ((uint32_t)R<<16)|((uint32_t)G<<8)|(uint32_t)B;
        }
        ledstring.channel[0].leds[i]=color;
    }

    ws2811_render(&ledstring);
}

// --- FIFO thread ---
void pipeThread() {
    std::ifstream fifo;
    std::string line;
    while (running) {
        fifo.open(PIPE_PATH);
        if (fifo.is_open()) {
            while (std::getline(fifo, line)) {
                try {
                    int idx = std::stoi(line);
                    if (idx >= 1 && idx <= LED_COUNT) {
                        spawnSnake(idx - 1, (uint8_t)(rand() % 256));
                        std::cout << "Spawn snake at LED " << idx << std::endl;
                    }
                } catch (...) {}
            }
            fifo.close();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

// --- MAIN ---
int main() {
    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!" << std::endl;
        return -1;
    }

    std::thread reader(pipeThread);
    std::cout << "Listening on " << PIPE_PATH << " ..." << std::endl;

    while (running) {
        updateSnakes();
        renderSnakesToBuffers();
        composeAndShow();
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }

    reader.join();
    ws2811_fini(&ledstring);
    return 0;
}

