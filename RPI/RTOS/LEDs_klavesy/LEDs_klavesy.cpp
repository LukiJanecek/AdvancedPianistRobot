#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <cmath>
#include <cstring>
#include <ws2811/ws2811.h>

using namespace std;

////////// HW / LED nastavení //////////
#define NUM_LEDS 150
#define LED_PIN 18
#define LED_FREQ WS2811_TARGET_FREQ
#define DMA 10
#define BRIGHTNESS 255
#define STRIP_TYPE WS2811_STRIP_GRB // WS2812B = GRB

////////// Parametry hadů //////////
#define MAX_SNAKES 16
#define SNAKE_LENGTH 4
#define SNAKE_STEP_MS 80
#define SNAKE_FADE_MIN 50
#define SNAKE_FADE_MAX 255
#define HUE_SHIFT_PER_OVERLAP 30
#define SATURATION 230
#define RENDER_INTERVAL 20

////////// Struktura hada //////////
struct Snake {
    bool active = false;
    int origin = 0;
    int step = 0;
    int length = SNAKE_LENGTH;
    uint8_t hue = 0;
    uint64_t lastUpdate = 0;
    uint64_t stepInterval = SNAKE_STEP_MS;
};

////////// Globální proměnné //////////
ws2811_t ledstring = {
    .freq = LED_FREQ,
    .dmanum = DMA,
    .channel = {
        [0] = {
            .gpionum = LED_PIN,
            .invert = 0,
            .count = NUM_LEDS,
            .strip_type = STRIP_TYPE,
            .brightness = BRIGHTNESS,
        },
        [1] = {0},
    },
};

Snake snakes[MAX_SNAKES];
uint16_t brightnessSum[NUM_LEDS];
uint32_t hueWeightedSum[NUM_LEDS];
uint8_t overlapCount[NUM_LEDS];

////////// Utility funkce //////////
uint64_t millis() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

uint8_t hue8_to_0_255(int h) {
    return static_cast<uint8_t>(h & 0xFF);
}

uint8_t brightnessForDistance(int dist, int length) {
    if (dist < 0 || dist >= length) return 0;
    int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
    b = std::clamp(b, 0, 255);
    return (uint8_t)b;
}

// HSV → RGB (jednoduchá verze)
uint32_t hsvToRgb(uint8_t h, uint8_t s, uint8_t v) {
    float hf = h / 255.0f * 360.0f;
    float sf = s / 255.0f;
    float vf = v / 255.0f;

    float c = vf * sf;
    float x = c * (1 - fabs(fmod(hf / 60.0f, 2) - 1));
    float m = vf - c;
    float r, g, b;

    if (hf < 60) { r = c; g = x; b = 0; }
    else if (hf < 120) { r = x; g = c; b = 0; }
    else if (hf < 180) { r = 0; g = c; b = x; }
    else if (hf < 240) { r = 0; g = x; b = c; }
    else if (hf < 300) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }

    uint8_t R = (uint8_t)((r + m) * 255);
    uint8_t G = (uint8_t)((g + m) * 255);
    uint8_t B = (uint8_t)((b + m) * 255);

    return (R << 16) | (G << 8) | B;
}

////////// Logika hadů //////////
bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= NUM_LEDS) return false;
    for (int i = 0; i < MAX_SNAKES; ++i) {
        if (!snakes[i].active) {
            snakes[i].active = true;
            snakes[i].origin = originIndex;
            snakes[i].step = 0;
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
    snakes[idx].active = false;
}

void updateSnakes() {
    uint64_t now = millis();
    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        if (now - snakes[s].lastUpdate >= snakes[s].stepInterval) {
            snakes[s].lastUpdate = now;
            snakes[s].step++;
            int left = snakes[s].origin - snakes[s].step - (snakes[s].length - 1);
            int right = snakes[s].origin + snakes[s].step + (snakes[s].length - 1);
            if (left < 0 && right >= NUM_LEDS)
                killSnake(s);
        }
    }
}

void renderSnakesToBuffers() {
    memset(brightnessSum, 0, sizeof(brightnessSum));
    memset(hueWeightedSum, 0, sizeof(hueWeightedSum));
    memset(overlapCount, 0, sizeof(overlapCount));

    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        int origin = snakes[s].origin;
        int step = snakes[s].step;
        int len = snakes[s].length;
        uint8_t hue = snakes[s].hue;

        if (step == 0) {
            if (origin >= 0 && origin < NUM_LEDS) {
                uint8_t b = brightnessForDistance(0, len);
                brightnessSum[origin] += b;
                hueWeightedSum[origin] += hue * b;
                overlapCount[origin]++;
            }
            continue;
        }

        for (int dir = -1; dir <= 1; dir += 2) {
            for (int d = 0; d < len; ++d) {
                int pos = origin + (step - d) * dir;
                if (pos < 0 || pos >= NUM_LEDS) continue;
                uint8_t b = brightnessForDistance(d, len);
                if (b == 0) continue;
                brightnessSum[pos] += b;
                hueWeightedSum[pos] += hue * b;
                overlapCount[pos]++;
            }
        }
    }
}

void composeAndShow() {
    for (int i = 0; i < NUM_LEDS; ++i) {
        if (overlapCount[i] == 0 || brightnessSum[i] == 0) {
            ledstring.channel[0].leds[i] = 0;
            continue;
        }
        uint16_t totalB = brightnessSum[i];
        uint8_t avgHue = hueWeightedSum[i] / totalB;
        int shift = (int)(overlapCount[i] - 1) * HUE_SHIFT_PER_OVERLAP;
        int finalHue = (avgHue + shift) & 0xFF;
        uint16_t b = std::min(totalB, (uint16_t)255);
        ledstring.channel[0].leds[i] = hsvToRgb(finalHue, SATURATION, (uint8_t)b);
    }
    ws2811_render(&ledstring);
}

////////// Main //////////
int main() {
    if (ws2811_init(&ledstring)) {
        cerr << "WS2811 init failed!" << endl;
        return -1;
    }

    uint64_t lastRender = 0;
    string input;

    cout << "Type index (0-" << NUM_LEDS - 1 << ") and press Enter to spawn snake.\n";

    while (true) {
        // neblokující čtení z konzole
        if (cin.rdbuf()->in_avail() > 0) {
            getline(cin, input);
            if (input.size()) {
                int idx = stoi(input);
                if (idx >= 0 && idx < NUM_LEDS) {
                    uint8_t hue = rand() % 256;
                    if (!spawnSnake(idx, hue))
                        cout << "No free snake slot!\n";
                    else
                        cout << "Spawned snake at " << idx << endl;
                }
            }
        }

        updateSnakes();
        uint64_t now = millis();
        if (now - lastRender >= RENDER_INTERVAL) {
            lastRender = now;
            renderSnakesToBuffers();
            composeAndShow();
        }

        this_thread::sleep_for(chrono::milliseconds(5));
    }

    ws2811_fini(&ledstring);
    return 0;
}
