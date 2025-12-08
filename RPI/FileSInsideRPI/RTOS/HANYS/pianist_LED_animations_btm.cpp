// pianist_led_effects_and_breath.cpp

#include <ws2811/ws2811.h>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <ctime>
#include <algorithm> // pro efekty - std::min

using namespace std::chrono; // millis() helper uses steady_clock

static inline uint64_t millis() {
    static const auto start = steady_clock::now();
    return duration_cast<milliseconds>(steady_clock::now() - start).count();
}

// ================== MACRA / SETTINGS ==================
#define LED_COUNT 290 // navysit podle metru pasku
#define GPIO_PIN 13
#define DMA 10
#define BRIGHTNESS 255

// INPUT interval: nastav zde nejnizsi a nebo nejvyssi hodnotu
#define INPUT_MIN 60
#define INPUT_MAX 106
#define INPUT_COUNT (INPUT_MAX - INPUT_MIN + 1)

// Breath params (ms)
#define BREATH_RISE_MS 200
#define BREATH_HOLD_MS 80
#define BREATH_FALL_MS 420
#define BREATH_TOTAL_MS (BREATH_RISE_MS + BREATH_HOLD_MS + BREATH_FALL_MS)

#define MAX_BREATHS 15

// Time fade used previously for snake-layer decay (ke konzistentnimu vzhledu)
#define SNAKE_TIME_FADE 0.92f

#define SATURATION_MAX 230

#define PIPE_PATH "/tmp/led/pipe"
#define INACTIVITY_SECONDS 20 // do passive rezimu po 20s necinnosti
#define EFFECT_SWITCH_MS 10000 // jak dlouho jede jeden efekt v passive rezimu
#define MAIN_LOOP_MS 20

// ================== GLOBALS ==================
ws2811_t ledstring = {
    .freq = WS2811_TARGET_FREQ,
    .dmanum = DMA,
    .channel = {
        [0] = {                     // Channel 0
            .gpionum = 0,
            .invert = 0,
            .count = 0,
            .strip_type = WS2811_STRIP_GRB,
            .brightness = 0,
        },
        [1] = {                     // Channel 1 = PWM1 = GPIO13 nebo GPIO19
            .gpionum = 13,          // <-- tady nastav GPIO13
            .invert = 0,
            .count = LED_COUNT,
            .strip_type = WS2811_STRIP_GRB,
            .brightness = BRIGHTNESS,
        },
    },
};

// (starďż˝) pomocnďż˝ pole (teďż˝ uďż˝ nejsou nutnďż˝ pro breath, ale nechďż˝vďż˝m je)
uint16_t brightnessSum[LED_COUNT];
uint32_t hueWeightedSum[LED_COUNT];
uint8_t overlapCount[LED_COUNT];

std::atomic<bool> running(true);
std::atomic<steady_clock::time_point> lastInputTime(steady_clock::now());

// passive mode bookkeeping
int currentEffect = 0;
steady_clock::time_point effectStart = steady_clock::now();

// ================== HELPERS ==================
static inline int clampInt(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

// Simple HSV->RGB converter returning 0xRRGGBB (same as pďż˝vodnďż˝)
static inline uint32_t CHSV_to_RGB(uint8_t h, uint8_t s, uint8_t v) {
    float H = (h / 255.0f) * 360.0f;
    float S = s / 255.0f;
    float V = v / 255.0f;
    float C = V * S;
    float X = C * (1.0f - std::fabs(fmod(H / 60.0f, 2.0f) - 1.0f));
    float m = V - C;
    float r = 0, g = 0, b = 0;
    if (H < 60) { r = C; g = X; b = 0; }
    else if (H < 120) { r = X; g = C; b = 0; }
    else if (H < 180) { r = 0; g = C; b = X; }
    else if (H < 240) { r = 0; g = X; b = C; }
    else if (H < 300) { r = X; g = 0; b = C; }
    else { r = C; g = 0; b = X; }
    uint8_t R = (uint8_t)clampInt((int)round((r + m) * 255.0f), 0, 255);
    uint8_t G = (uint8_t)clampInt((int)round((g + m) * 255.0f), 0, 255);
    uint8_t B = (uint8_t)clampInt((int)round((b + m) * 255.0f), 0, 255);
    return ((uint32_t)R << 16) | ((uint32_t)G << 8) | (uint32_t)B;
}

// ================== BREATH (spawn/update/render) ==================
struct Breath {
    bool active = false;
    int inputValue = 0; // pďż˝vodnďż˝ ďż˝ďż˝slo z pipe
    uint8_t hue = 0;
    uint8_t sat = 200;
    uint8_t peakVal = 255; // max brightness (0..255) pro CHSV.v
    steady_clock::time_point startTime;
};

Breath breaths[MAX_BREATHS];

bool spawnBreath(int inputValue) {
    if (inputValue < INPUT_MIN || inputValue > INPUT_MAX) return false;
    for (int i = 0; i < MAX_BREATHS; ++i) {
        if (!breaths[i].active) {
            // normalizovanďż˝ pozice 0..1 podle inputValue
            float norm = 0.0f;
            if (INPUT_COUNT > 1) norm = (float)(inputValue - INPUT_MIN) / (float)(INPUT_COUNT - 1);
            // nďż˝hodnďż˝ base hue kaďż˝dďż˝ zapnutďż˝ -> zaruďż˝ďż˝ jinďż˝ barvy pro stejnďż˝ ďż˝ďż˝slo
            uint8_t randHue = (uint8_t)(rand() & 0xFF);
            // upravďż˝me saturation/peak podle norm: vyďż˝ďż˝ďż˝ ďż˝ďż˝slo -> svďż˝tlejďż˝ďż˝ => higher V, lower saturation
            int sat = clampInt((int)round(255 - norm * 150.0f), 50, 255); // 255..~105
            int peak = clampInt((int)round(100 + norm * 155.0f), 0, 255); // 100..255

            breaths[i].active = true;
            breaths[i].inputValue = inputValue;
            breaths[i].hue = randHue;
            breaths[i].sat = (uint8_t)sat;
            breaths[i].peakVal = (uint8_t)peak;
            breaths[i].startTime = steady_clock::now();
            return true;
        }
    }
    return false;
}

void updateBreaths() {
    auto now = steady_clock::now();
    for (int i = 0; i < MAX_BREATHS; ++i) {
        if (!breaths[i].active) continue;
        auto elapsed = duration_cast<milliseconds>(now - breaths[i].startTime).count();
        if (elapsed >= BREATH_TOTAL_MS) {
            breaths[i].active = false;
        }
    }
}

// Compose breaths on top of existing buffer and show (time-based fade + blending)
void composeBreathsAndShow() {
    // 1) TIME-BASED FADE ďż˝ fade old pixels (ke stejnďż˝mu vzhledu jako pďż˝vodnďż˝)
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * SNAKE_TIME_FADE);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * SNAKE_TIME_FADE);
        uint8_t b = (uint8_t)((c & 0xFF) * SNAKE_TIME_FADE);
        ledstring.channel[0].leds[i] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
    }

    // 2) For each active breath, compute envelope and blend across whole strip
    auto now = steady_clock::now();
    for (int b = 0; b < MAX_BREATHS; ++b) {
        if (!breaths[b].active) continue;
        auto elapsed = duration_cast<milliseconds>(now - breaths[b].startTime).count();
        float alpha = 0.0f; // 0..1
        if (elapsed < 0) alpha = 0.0f;
        else if (elapsed < BREATH_RISE_MS) {
            alpha = (float)elapsed / (float)BREATH_RISE_MS;
        } else if (elapsed < (BREATH_RISE_MS + BREATH_HOLD_MS)) {
            alpha = 1.0f;
        } else if (elapsed < BREATH_TOTAL_MS) {
            int t = (int)elapsed - (BREATH_RISE_MS + BREATH_HOLD_MS);
            alpha = 1.0f - (float)t / (float)BREATH_FALL_MS;
        } else {
            alpha = 0.0f;
        }

        if (alpha <= 0.001f) continue;

        // value to use inside CHSV (0..255) scaled by peakVal * alpha
        uint8_t v_for_hsv = (uint8_t)clampInt((int)round((float)breaths[b].peakVal * alpha), 0, 255);
        uint32_t s_color = CHSV_to_RGB(breaths[b].hue, breaths[b].sat, v_for_hsv);

        uint8_t sr = (s_color >> 16) & 0xFF;
        uint8_t sg = (s_color >> 8) & 0xFF;
        uint8_t sb = s_color & 0xFF;

        // blend into each LED (prefer full replacement when brightness large)
        uint8_t sval = v_for_hsv;
        for (int i = 0; i < LED_COUNT; ++i) {
            uint32_t c = ledstring.channel[0].leds[i];
            uint8_t cr = (c >> 16) & 0xFF;
            uint8_t cg = (c >> 8) & 0xFF;
            uint8_t cb = c & 0xFF;

            if (sval >= 200) {
                // strong breath -> replace
                cr = sr; cg = sg; cb = sb;
            } else {
                int alpha_int = sval; // 0..255
                cr = (uint8_t)((sr * alpha_int + cr * (255 - alpha_int)) / 255);
                cg = (uint8_t)((sg * alpha_int + cg * (255 - alpha_int)) / 255);
                cb = (uint8_t)((sb * alpha_int + cb * (255 - alpha_int)) / 255);
            }
            ledstring.channel[0].leds[i] = ((uint32_t)cr << 16) | ((uint32_t)cg << 8) | (uint32_t)cb;
        }
    }

    // finally render
    ws2811_render(&ledstring);
}

// ================== PIPE THREAD ==================
void pipeThread() {
    std::ifstream fifo;
    std::string line;
    while (running) {
        fifo.open(PIPE_PATH);
        if (fifo.is_open()) {
            while (std::getline(fifo, line)) {
                try {
                    int val = std::stoi(line);
                    // pipe should now send tone numbers in interval INPUT_MIN..INPUT_MAX
                    if (val >= INPUT_MIN && val <= INPUT_MAX) {
                        bool ok = spawnBreath(val);
                        lastInputTime.store(steady_clock::now()); // reset inactivity timer
                        if (ok) {
                            std::cout << "Spawn breath for value " << val << "\n";
                        } else {
                            std::cout << "No free breath slot for value " << val << "\n";
                        }
                    } else {
                        // ignore out-of-range numbers (or you can map if desired)
                        std::cout << "Received out-of-range input: " << val << " (expected " << INPUT_MIN << "-" << INPUT_MAX << ")\n";
                    }
                } catch (...) {
                    // ignore parse errors
                }
            }
            fifo.close();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

// ================== EFFECTS ==================
uint8_t gHue = 0;

void effect_rotate_white() {
    static int offset = 0;
    for (int i = 0; i < LED_COUNT; ++i) ledstring.channel[0].leds[i] = 0;
    for (int i = 0; i < LED_COUNT; ++i) {
        if ((i + offset) % 4 == 0) ledstring.channel[0].leds[i] = CHSV_to_RGB(0, 0, 255);
    }
    offset = (offset + 1) % 4;
}

void effect_color_shift() {
    static uint8_t hue = 0;
    for (int i = 0; i < LED_COUNT; ++i) {
        ledstring.channel[0].leds[i] = CHSV_to_RGB((uint8_t)(hue + i * 2), 255, 200);
    }
    hue += 2;
}

void effect_rainbow_with_glitter() {
    for (int i = 0; i < LED_COUNT; ++i) {
        uint8_t hue = (gHue + i * 7) & 0xFF;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, 160);
    }
    if ((rand() & 0xFF) < 30) {
        int p = rand() % LED_COUNT;
        ledstring.channel[0].leds[p] = 0xFFFFFF;
    }
    gHue++;
}

void effect_toceniLedekbila() {
    static int phase = 0;
    for (int i = 0; i < LED_COUNT; ++i) ledstring.channel[0].leds[i] = 0;
    int o = phase % 4;
    for (int i = 0; i < LED_COUNT; i += 4) {
        int idx = i + o;
        if (idx < LED_COUNT) ledstring.channel[0].leds[idx] = CHSV_to_RGB(255, 0, 160);
    }
    phase = (phase + 1) % 4;
}


void effect_toceniLedekbarva_paleta() {
    static uint8_t idx = 0;
    for (int i = 0; i < LED_COUNT; ++i) {
        uint8_t block = (i / 6);
        uint8_t hue = idx + block * 8;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 200, 150);
    }
    idx += 3;
}

void effect_prolinani() {
    static uint8_t idx = 0;
    idx++;
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t hue = idx + i * 3;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, 255);
    }
}

void effect_confetti() {
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.9f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.9f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.9f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    int pos = rand() % LED_COUNT;
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue + (rand() % 64), 200, 255);
    gHue++;
}

void effect_kometa() {
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.9f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.9f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.9f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    float t = (float)millis() / 1000.0f;
    int pos = (int)((sin(t * 12.0f) + 1.0f) * 0.5f * (LED_COUNT - 1));
    pos = clampInt(pos, 0, LED_COUNT - 1);
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue, 255, 255);
}

void effect_bpm() {
    static uint8_t beat = 0;
    beat += 3;
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t hue = (i * 2 + beat);
        float valF = 128.0f + sin((beat + i * 5) * 0.05f) * 127.0f;
        uint8_t val = (uint8_t)clampInt((int)round(valF), 0, 255);
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}

void effect_juggle() {
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.85f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.85f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.85f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    uint8_t hue = 0;
    for (int i = 0; i < 8; i++) {
        float posf = (sin((millis() / 800.0f) * (i + 7)) + 1.0f) * 0.5f;
        int pixel = (int)(posf * (LED_COUNT - 1));
        pixel = clampInt(pixel, 0, LED_COUNT - 1);
        ledstring.channel[0].leds[pixel] = CHSV_to_RGB(hue, 255, 255);
        hue += 32;
    }
}

void effect_cylon() {
    static int pos = 0;
    static int dir = 1;
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.8f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.8f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.8f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue, 255, 255);
    pos += dir;
    if (pos <= 0 || pos >= LED_COUNT - 1) dir = -dir;
    gHue += 2;
}

void effect_fire2012() {
    static std::vector<uint8_t> heat(LED_COUNT, 0);
    for (int i = 0; i < LED_COUNT; i++) {
        int v = (int)heat[i] - (rand() % 5);
        heat[i] = (uint8_t)clampInt(v, 0, 255);
    }
    for (int i = LED_COUNT - 1; i >= 2; i--) {
        int v = (int)heat[i - 1] + (int)heat[i - 2] + (int)heat[i - 2];
        heat[i] = (uint8_t)(v / 3);
    }
    if (rand() % 3 == 0) {
        int y = rand() % 7;
        int nv = std::min(255, (int)heat[y] + (rand() % 120 + 135));
        heat[y] = (uint8_t)nv;
    }
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t t = heat[i];
        uint8_t hue = (t < 128) ? (t * 2) : 255;
        uint8_t val = t;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}

void effect_sinelon() {
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.9f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.9f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.9f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    float posf = (sin(millis() / 400.0f) + 1.0f) * 0.5f;
    int pixel = (int)(posf * (LED_COUNT - 1));
    pixel = clampInt(pixel, 0, LED_COUNT - 1);
    ledstring.channel[0].leds[pixel] = CHSV_to_RGB(gHue, 255, 255);
    gHue++;
}

void effect_meteor() {
    static uint8_t hue = 0;
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.75f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.75f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.75f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    float posf = (sin(millis() / 350.0f) + 1.0f) * 0.5f;
    int p = (int)(posf * (LED_COUNT - 1));
    p = clampInt(p, 0, LED_COUNT - 1);
    ledstring.channel[0].leds[p] = CHSV_to_RGB(hue, 255, 255);
    hue += 2;
}

void effect_singleDotSmooth() {
    static float pos = 0.0f;
    static float speed = 0.25f;
    static int dir = 1;

    // fade-out before drawing new pos
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.85f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.85f;
        uint8_t b = ((c      ) & 0xFF) * 0.85f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    pos += speed * dir;
    if (pos <= 0) { pos = 0; dir = 1; }
    if (pos >= LED_COUNT - 1) { pos = LED_COUNT - 1; dir = -1; }

    ledstring.channel[0].leds[(int)pos] = CHSV_to_RGB(gHue, 255, 255);

    gHue += 2;
}

void effect_waveRunner() {
    static float head = 0.0f;
    static float speed = 0.40f;

    // clear
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.9f;
        uint8_t b = ((c      ) & 0xFF) * 0.9f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    // wave width
    const int W = 10;

    for (int i = -W; i <= W; i++) {
        int p = (int)(head + i);
        if (p < 0 || p >= LED_COUNT) continue;

        float fade = 1.0f - fabs(i) / (float)W; // 1.0 ďż˝ 0
        uint8_t v = (uint8_t)(fade * 255.0f);
        ledstring.channel[0].leds[p] = CHSV_to_RGB(gHue, 255, v);
    }

    head += speed;
    if (head >= LED_COUNT + W) head = -W; // opakuje se

    gHue++;
}


void effect_oceanWaves() {
    static uint8_t base = 0;
    base++;
    for (int i = 0; i < LED_COUNT; i++) {
        float hf = sin(((float)millis() + i * 30.0f) / 500.0f) * 30.0f;
        uint8_t hue = (uint8_t)(base + hf);
        float vf = 150.0f + sin(((float)millis() + i * 40.0f) / 300.0f) * 100.0f;
        uint8_t val = (uint8_t)clampInt((int)round(vf), 0, 255);
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}

struct Wave {
    float pos;
    float speed;
    uint8_t hue;
    int width;
    bool active;
};

void effect_waveSpawner() {
    const int MAX_WAVES = 5;
    static Wave waves[MAX_WAVES];

    // fade background
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.90f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.90f;
        uint8_t b = ((c      ) & 0xFF) * 0.90f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    // spawn new wave sometimes
    if ((rand() % 20) == 0) { 
        for (int i = 0; i < MAX_WAVES; i++) {
            if (!waves[i].active) {
                waves[i].active = true;
                waves[i].pos = -10.0f;
                waves[i].speed = 0.3f + (rand() % 100) / 200.0f; // 0.3ďż˝0.8
                waves[i].hue = rand() % 255;
                waves[i].width = 6 + rand() % 10;
                break;
            }
        }
    }

    // update waves
    for (int w = 0; w < MAX_WAVES; w++) {
        if (!waves[w].active) continue;

        waves[w].pos += waves[w].speed;

        if (waves[w].pos > LED_COUNT + 20) {
            waves[w].active = false;
            continue;
        }

        int W = waves[w].width;

        for (int i = -W; i <= W; i++) {
            int p = (int)(waves[w].pos + i);
            if (p < 0 || p >= LED_COUNT) continue;

            float fade = 1.0f - fabs(i) / (float)W;
            uint8_t v = (uint8_t)(fade * 255.0f);
            ledstring.channel[0].leds[p] = CHSV_to_RGB(waves[w].hue, 255, v);
        }
    }
}


void effect_christmasSparkle() {
    // global fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.80f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.80f;
        uint8_t b = ((c      ) & 0xFF) * 0.80f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    // spawn many tiny sparkles
    for (int s = 0; s < 8; s++) {  
        int p = rand() % LED_COUNT;
        uint8_t hue = (rand() % 2) ? 0 : 96; // red / green
        uint8_t val = 200 + rand() % 55;
        ledstring.channel[0].leds[p] = CHSV_to_RGB(hue, 255, val);
    }
}


struct RGB { uint8_t r, g, b; };


RGB addRGB(const RGB &a, const RGB &b) {
    return {
        (uint8_t)std::min(255, a.r + b.r),
        (uint8_t)std::min(255, a.g + b.g),
        (uint8_t)std::min(255, a.b + b.b)
    };
}

// prevod HSV -> RGB
RGB CHSV_to_RGB_struct(uint8_t h, uint8_t s, uint8_t v) {
    uint32_t c = CHSV_to_RGB(h, s, v);
    return { 
        (uint8_t)((c >> 16) & 0xFF),
        (uint8_t)((c >> 8) & 0xFF),
        (uint8_t)(c & 0xFF)
    };
}

void effect_aurora() {
    static float t0 = 0.0f;
    t0 += 0.004f;

    // fade background
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        RGB oldColor = { (uint8_t)((c>>16)&0xFF), (uint8_t)((c>>8)&0xFF), (uint8_t)(c&0xFF) };
        oldColor.r = oldColor.r * 0.96f;
        oldColor.g = oldColor.g * 0.96f;
        oldColor.b = oldColor.b * 0.96f;
        ledstring.channel[0].leds[i] = (oldColor.r << 16) | (oldColor.g << 8) | oldColor.b;
    }

    // aurora overlay
    for (int i = 0; i < LED_COUNT; i++) {
        float f1 = sinf(t0 * 0.8f + i * 0.02f) * 0.5f + 0.5f;
        float f2 = sinf(t0 * 1.3f + i * 0.05f) * 0.5f + 0.5f;
        float intensity = f1 * 0.7f + f2 * 0.4f;
        uint8_t hue = (uint8_t)((int)(80 + sinf(t0*0.2f + i*0.01f)*40.0f) & 0xFF);
        uint8_t val = (uint8_t)clampInt((int)(intensity*220.0f), 0, 255);

        RGB add = CHSV_to_RGB_struct(hue, 220, val);

        // additive blend
        uint32_t c_old = ledstring.channel[0].leds[i];
        RGB oldColor = { (uint8_t)((c_old>>16)&0xFF), (uint8_t)((c_old>>8)&0xFF), (uint8_t)(c_old&0xFF) };
        RGB result = addRGB(oldColor, add);
        ledstring.channel[0].leds[i] = (result.r << 16) | (result.g << 8) | result.b;
    }
}
void effect_matrix() {
    const int MAX_DROPS = 20;
    struct Drop { int pos; int speed; int length; uint8_t life; bool active; };
    static Drop drops[MAX_DROPS];

    // fade background stronger for trailing look
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.86f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.86f;
        uint8_t b = ((c      ) & 0xFF) * 0.86f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    if ((rand() % 8) == 0) {
        for (int i = 0; i < MAX_DROPS; i++) if (!drops[i].active) {
            drops[i].active = true;
            drops[i].pos = rand() % LED_COUNT;
            drops[i].speed = 1 + rand()%3;
            drops[i].length = 6 + rand()%20;
            drops[i].life = 255;
            break;
        }
    }

    for (int i = 0; i < MAX_DROPS; i++) {
        if (!drops[i].active) continue;
        drops[i].pos = (drops[i].pos + drops[i].speed) % LED_COUNT;
        drops[i].life = (drops[i].life > 4) ? drops[i].life - 4 : 0;
        if (drops[i].life == 0) { drops[i].active = false; continue; }

        // draw drop with bright head and trailing fade
        for (int t = 0; t < drops[i].length; t++) {
            int p = drops[i].pos - t;
            if (p < 0) break;
            float fade = 1.0f - (float)t / (float)drops[i].length;
            uint8_t val = (uint8_t)(fade * drops[i].life);
            ledstring.channel[0].leds[p] = CHSV_to_RGB(100, 200, val); // greenish
        }
    }
}


void effect_dualWaveCollision() {
    struct W { float pos; float speed; uint8_t hue; bool active; };
    static W left = { -10.0f, 0.6f, 0, false };
    static W right = { LED_COUNT + 10.0f, -0.6f, 160, false };
    static int flash = 0;

    // fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.88f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.88f;
        uint8_t b = ((c      ) & 0xFF) * 0.88f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    if (!left.active && (rand()%50)==0) { left.active = true; left.pos = -8.0f; left.speed = 0.4f + (rand()%60)/100.0f; left.hue = rand()%120; }
    if (!right.active && (rand()%50)==0) { right.active = true; right.pos = LED_COUNT + 8.0f; right.speed = - (0.4f + (rand()%60)/100.0f); right.hue = 100 + rand()%120; }

    if (left.active) left.pos += left.speed;
    if (right.active) right.pos += right.speed;

    // draw waves
    auto drawWave = [&](W &w){
        if (!w.active) return;
        int WID = 8;
        for (int i = -WID; i <= WID; i++) {
            int p = (int)(w.pos + i);
            if (p < 0 || p >= LED_COUNT) continue;
            float fade = 1.0f - fabs(i)/(float)WID;
            uint8_t val = (uint8_t)(fade*200.0f);
            ledstring.channel[0].leds[p] = CHSV_to_RGB(w.hue, 255, val);
        }
    };

    drawWave(left); drawWave(right);

    // collision check
    if (left.active && right.active && fabs(left.pos - right.pos) < 6.0f) {
        flash = 6; // short bright flash
        left.active = false; right.active = false;
    }

    if (flash > 0) {
        for (int i = 0; i < LED_COUNT; i++) {
            if ((i % 6) == (flash % 6)) ledstring.channel[0].leds[i] = CHSV_to_RGB(0,255,255);
        }
        flash--;
    }

    // keep waves deactivated once out of bounds
    if (left.active && left.pos > LED_COUNT + 10) left.active = false;
    if (right.active && right.pos < -10) right.active = false;
}


void effect_policeStrobe() {
    static int frame = 0;
    frame = (frame + 1) % 12;

    // small global fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.9f;
        uint8_t b = ((c      ) & 0xFF) * 0.9f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    int segment = 10; // width of a block
    // left side red pulse
    if (frame < 6) {
        int center = (LED_COUNT/4) + (frame-3);
        for (int i = -segment; i <= segment; i++) {
            int p = center + i;
            if (p < 0 || p >= LED_COUNT) continue;
            float fade = 1.0f - fabs(i)/(float)segment;
            ledstring.channel[0].leds[p] = CHSV_to_RGB(0,255,(uint8_t)(fade*200));
        }
    } else {
        // right side blue pulse
        int center = (LED_COUNT*3/4) + (frame-9);
        for (int i = -segment; i <= segment; i++) {
            int p = center + i;
            if (p < 0 || p >= LED_COUNT) continue;
            float fade = 1.0f - fabs(i)/(float)segment;
            ledstring.channel[0].leds[p] = CHSV_to_RGB(160,255,(uint8_t)(fade*200));
        }
    }
}


void effect_fireworks() {
    struct Particle { float x,y; float vx,vy; uint8_t hue; int life; bool active; };
    // we emulate in 1D: particle.x is position on strip, vy unused - just vertical illusion via brightness
    const int MAX_PART = 80;
    static Particle parts[MAX_PART];

    // fade background
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.92f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.92f;
        uint8_t b = ((c      ) & 0xFF) * 0.92f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    // spawn rockets occasionally
    if ((rand()%60)==0) {
        // create a burst at random pos
        int center = 20 + rand() % (LED_COUNT - 40);
        uint8_t hue = rand()%255;
        // spawn many particles radiating outwards
        for (int p = 0; p < 20; p++) {
            for (int i = 0; i < MAX_PART; i++) {
                if (!parts[i].active) {
                    float ang = (float)p * (6.283185f/20.0f) + ((rand()%100)/100.0f);
                    float speed = 0.6f + (rand()%100)/200.0f;
                    parts[i].active = true;
                    parts[i].x = (float)center;
                    parts[i].vx = cosf(ang) * speed;
                    parts[i].life = 20 + rand()%40;
                    parts[i].hue = hue;
                    break;
                }
            }
        }
    }

    // update particles
    for (int i = 0; i < MAX_PART; i++) {
        if (!parts[i].active) continue;
        parts[i].x += parts[i].vx;
        parts[i].vx *= 0.98f; // drag
        parts[i].life--;
        if (parts[i].life <= 0 || parts[i].x < 0 || parts[i].x >= LED_COUNT) { parts[i].active = false; continue; }
        int p = (int)parts[i].x;
        uint8_t val = (uint8_t)clampInt(parts[i].life * 6, 0, 255);
        ledstring.channel[0].leds[p] = CHSV_to_RGB(parts[i].hue, 255, val);
    }
}


void effect_starfall() {
    const int MAX_STAR = 30;
    struct Star { float x; float speed; uint8_t hue; int life; bool active; };
    static Star stars[MAX_STAR];

    // strong fade for trails
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.82f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.82f;
        uint8_t b = ((c      ) & 0xFF) * 0.82f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    if ((rand()%15)==0) {
        for (int i = 0; i < MAX_STAR; i++) if (!stars[i].active) {
            stars[i].active = true;
            stars[i].x = rand() % LED_COUNT;
            stars[i].speed = 0.6f + (rand()%100)/150.0f;
            stars[i].hue = 40 + rand()%40; // warm white/yellowish
            stars[i].life = 40 + rand()%60;
            break;
        }
    }

    for (int i = 0; i < MAX_STAR; i++) {
        if (!stars[i].active) continue;
        stars[i].x += stars[i].speed;
        stars[i].life--;
        if (stars[i].x >= LED_COUNT || stars[i].life <= 0) { stars[i].active = false; continue; }
        int p = (int)stars[i].x;
        ledstring.channel[0].leds[p] = CHSV_to_RGB(stars[i].hue, 180, 240);
        // small trail behind
        if (p-1 >= 0) ledstring.channel[0].leds[p-1] = CHSV_to_RGB(stars[i].hue, 160, 120);
        if (p-2 >= 0) {
            uint32_t c = ledstring.channel[0].leds[p-2];
            uint8_t r = ((c >> 16) & 0xFF) * 0.9f;
            uint8_t g = ((c >>  8) & 0xFF) * 0.9f;
            uint8_t b = ((c      ) & 0xFF) * 0.9f;
            ledstring.channel[0].leds[p-2] = (r << 16) | (g << 8) | b;
        }
    }
}

// Effects array
typedef void(*effect_fn)();
effect_fn effects[] = {
    effect_rotate_white,        // rotateWhite
    effect_color_shift,         // colorShift
    effect_rainbow_with_glitter,// rainbowWithGlitter
    //effect_toceniLedekbila,     // staggeredWhiteRotate
    effect_toceniLedekbarva_paleta, // rotatingColorBlocks
    effect_prolinani,           // smoothBlend
    effect_confetti,            // confetti
    effect_kometa,              // sineComet
    effect_bpm,                 // bpm
    effect_juggle,              // juggle
    effect_cylon,               // cylonScanner
    effect_fire2012,            // fire2012
    effect_sinelon,             // sinelon
    effect_meteor,              // meteor
    effect_oceanWaves,          // oceanWaves
    effect_waveRunner,          // waveRunner
    effect_waveSpawner,         // waveSpawner
    effect_christmasSparkle,    // christmasSparkle
    effect_aurora,              // aurora
    effect_matrix,              // matrixDrops
    effect_dualWaveCollision,   // dualWaveCollision
    effect_policeStrobe,        // policeStrobe
    effect_fireworks,           // fireworks
    effect_starfall,            // starfall
    effect_singleDotSmooth      // singleDotSmooth
};
const int EFFECT_COUNT = sizeof(effects) / sizeof(effects[0]);

// ================== MAIN ==================
int main() {
    srand((unsigned int)time(nullptr));

    // allocate buffer for rpi_ws281x
    ledstring.channel[0].leds = new uint32_t[LED_COUNT];
    // init to 0
    for (int i = 0; i < LED_COUNT; ++i) ledstring.channel[0].leds[i] = 0;

    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!" << std::endl;
        delete[] ledstring.channel[0].leds;
        return -1;
    }

    lastInputTime.store(steady_clock::now());

    // start pipe reader
    std::thread reader(pipeThread);
    std::cout << "Listening on " << PIPE_PATH << " ..." << std::endl;

    // main loop
    while (running) {
        // update breaths
        updateBreaths();

        // decide passive mode
        auto now = steady_clock::now();
        auto idleSec = duration_cast<seconds>(now - lastInputTime.load()).count();
        bool passiveMode = (idleSec > INACTIVITY_SECONDS);

        if (passiveMode) {
            // switch effect if needed
		auto ms = duration_cast<milliseconds>(now - effectStart).count();

		if (ms > EFFECT_SWITCH_MS) {
			currentEffect = (currentEffect + 1) % EFFECT_COUNT;
			effectStart = now;

        // debug vypis do terminalu
        std::cout << "Switched to effect " << currentEffect << std::endl;
    }

    // call effect to fill ledstring.channel[0].leds (non-blocking)
    effects[currentEffect]();            // render effect
            ws2811_render(&ledstring);
        } else {
            // normal mode: compose breaths and show
            composeBreathsAndShow();
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(MAIN_LOOP_MS));
    }

    reader.join();
    ws2811_fini(&ledstring);
    delete[] ledstring.channel[0].leds;
    return 0;
}
