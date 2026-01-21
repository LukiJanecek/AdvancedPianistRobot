//============================================================================
// Name        : pianist_LED_animations_btm.cpp
// Author      : Bc. Jan Besta
// Version     :
// Copyright   : VSB-TUO FEI
// Description :
//  - Pipe/FIFO input handling
//  - Special effect song mode (1..3) and -1 logic
//  - Note-driven breath animations (>=4, released by 0)
//  - Passive / idle mode fallback
//  - Clear separation of state, rendering and input
// =============================================================


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
#include <mutex>
#include <algorithm>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <ctime>

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

std::atomic<bool> songRunning(false);
std::atomic<int>  specialEffect(-1);


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
    int ack_fd = -1;
    bool writerConnected = false;

    int fd = open(PIPE_PATH, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        std::cerr << "[pipeThread] ERROR: Cannot open FIFO: "
                  << strerror(errno) << "\n";
        return;
    }

    std::cout << "[pipeThread] FIFO opened, fd=" << fd << "\n";

    std::string acc;
    acc.reserve(1024);

    while (running) {
        char buf[256];
        ssize_t n = read(fd, buf, sizeof(buf) - 1);

        if (n > 0) {
            buf[n] = 0;
            acc.append(buf, n);

            size_t pos;
            while ((pos = acc.find('\n')) != std::string::npos) {
                std::string line = acc.substr(0, pos);
                acc.erase(0, pos + 1);

                int seq = -1;
                int value = -1;

                size_t sep = line.find(':');
                if (sep == std::string::npos)
                    continue;

                try {
                    seq   = std::stoi(line.substr(0, sep));
                    value = std::stoi(line.substr(sep + 1));
                } catch (...) {
                    continue;
                }

                lastInputTime.store(steady_clock::now());

                // =================================================
                // INPUT LOGIC (BTM / BREATH)
                // =================================================
                //  1..3  = start song (continuous)
                // -1     = stop song
                //  0     = ignored during song
                // INPUT_MIN..INPUT_MAX = spawn breath (only outside song)
                // =================================================

                if (value >= 1 && value <= 3) {
                    // START SONG
                    songRunning.store(true);
                    specialEffect.store(value);

                    std::cout << "[pipeThread] Song started: "
                              << value << "\n";
                }
                else if (value == -1) {
                    // STOP SONG
                    songRunning.store(false);
                    specialEffect.store(-1);

                    std::cout << "[pipeThread] Song stopped (-1)\n";
                }
                else if (!songRunning.load()) {
                    // NORMAL MODE INPUTS ONLY WHEN NO SONG
                    if (value >= INPUT_MIN && value <= INPUT_MAX) {
                        spawnBreath(value);
                    }
                }

                // ---------------- ACK ----------------
                if (seq >= 0) {
                    if (ack_fd < 0)
                        ack_fd = open(ACK_PIPE_PATH,
                                      O_WRONLY | O_NONBLOCK);

                    if (ack_fd >= 0) {
                        char ackbuf[64];
                        int len = snprintf(ackbuf, sizeof(ackbuf),
                                           "ACK:%d\n", seq);
                        write(ack_fd, ackbuf, len);
                    }
                }
            }
        }
        else {
            std::this_thread::sleep_for(milliseconds(5));
        }
    }

    close(fd);
    if (ack_fd >= 0)
        close(ack_fd);
}


// ================== EFFECTS (non-blocking; GPU-like drawing) ==================
// All effects below draw full-frame animations. Used in special-effect
// modes and passive idle mode. No blocking delays inside.
uint8_t gHue = 0;

void effect_special1() {
    static uint64_t t0 = millis();
    float t = (millis() - t0) * 0.002f;

    for (int i = 0; i < LED_COUNT; i++) {
        // background wave
        float w = (sin(t + i * 0.08f) + 1) * 0.5f;
        uint8_t val = 120 + w * 100;

        // cycling party palette (yellow - pink - teal)
        uint8_t hue = (uint8_t)((sin(t * 0.4f) * 0.5f + 0.5f) * 255);

        uint32_t baseColor = CHSV_to_RGB(hue, 170, val);
        ledstring.channel[0].leds[i] = baseColor;

        // streamer lines (moving color bands)
        if (((i + (int)(t * 40)) % 20) < 4) {
            uint8_t h2 = hue + 40;
            ledstring.channel[0].leds[i] = CHSV_to_RGB(h2, 255, 255);
        }
    }

    // occasional confetti pops
    if ((rand() & 0xFF) < 12) {
        int p = rand() % LED_COUNT;
        ledstring.channel[0].leds[p] = 0xFFFFFF;
    }
}

void effect_special2() {
    static uint64_t t0 = millis();
    float t = (millis() - t0) * 0.0015f;

    // center oscillates between -30 .. +30
    float shift = sin(t) * 30.0f;

    // center point around middle of strip
    float center = (LED_COUNT / 2) + shift;

    for (int i = 0; i < LED_COUNT; i++) {
        float dist = i - center;

        // negative = left side (blue), positive = right side (red)
        // blend in +-12 LED zone
        float blendZone = 12.0f;
        float f = dist / blendZone;

        if (f < -1) f = -1;
        if (f >  1) f =  1;

        uint8_t blueVal  = (uint8_t)((1 - (f + 1) * 0.5f) * 255);
        uint8_t redVal   = (uint8_t)(((f + 1) * 0.5f) * 255);

        // small breathing brightness mod
        uint8_t v = 150 + sin(t * 2.5f) * 50;

        ledstring.channel[0].leds[i] =
            ((redVal * v / 255) << 16) |
            (0 << 8) |
            ((blueVal * v / 255));
    }
}


struct Spark {
    int pos;
    uint8_t hue;      // 0 = gold, 0=white special (sat=0)
    bool isWhite;
    uint64_t tStart;  // ďż˝as spawn
    uint32_t lifeMS;  // dďż˝lka fade out
    bool active;
};

const int MAX_SPARKS = 80;
static Spark sparks[MAX_SPARKS];
static uint64_t t0 = millis();
static uint32_t bgColor[LED_COUNT]; // uchovďż˝vďż˝ aktuďż˝lnďż˝ pozadďż˝

void effect_special3() {
    uint64_t now = millis();
    float t = (now - t0) * 0.0015f; // ďż˝as pro pozadďż˝

    // --- pozadďż˝: tmavďż˝ -> azurovďż˝ ---
    for (int i = 0; i < LED_COUNT; i++) {
        float wave = (sin(t + i*0.05f) + 1.0f) * 0.5f; // 0..1
        uint8_t r = 0;
        uint8_t g = (uint8_t)(50 + wave * 105);   // 50..155
        uint8_t b = (uint8_t)(100 + wave * 155);  // 100..255
        bgColor[i] = (r<<16)|(g<<8)|b;
        ledstring.channel[0].leds[i] = bgColor[i];
    }

    // --- spawn vďż˝ce LED (bďż˝lďż˝ nebo zlatďż˝) ---
    if ((rand()%3) == 0) { // cca 33% ďż˝ance kaďż˝dďż˝ volďż˝nďż˝
        int spawnCount = 1 + rand()%3; // 1ďż˝3 LED
        for (int s=0; s<spawnCount; s++) {
            int p = rand() % LED_COUNT;
            bool isWhite = (rand()%2==0); // true = bďż˝lďż˝, false = zlatďż˝
            for (int i=0; i<MAX_SPARKS; i++) {
                if (!sparks[i].active) {
                    sparks[i].pos = p;
                    sparks[i].isWhite = isWhite;
                    sparks[i].hue = isWhite ? 0 : 30; // bďż˝lďż˝ = sat 0, zlatďż˝ = hue 30
                    sparks[i].tStart = now;
                    sparks[i].lifeMS = 800; // fade 0,8s
                    sparks[i].active = true;
                    break;
                }
            }
        }
    }

    // --- render sparks s fade do aktuďż˝lnďż˝ barvy pozadďż˝ ---
    for (int i=0;i<MAX_SPARKS;i++) {
        if (!sparks[i].active) continue;
        uint64_t age = now - sparks[i].tStart;
        float fade = 1.0f - ((float)age / sparks[i].lifeMS);
        if (fade <= 0.0f) { sparks[i].active = false; continue; }

        int p = sparks[i].pos;
        if (p < 0 || p >= LED_COUNT) continue;

        // background color of actual LED
        uint32_t bg = bgColor[p];
        uint8_t bgR = (bg >> 16) & 0xFF;
        uint8_t bgG = (bg >> 8) & 0xFF;
        uint8_t bgB = bg & 0xFF;

        uint8_t r,g,b;

        if (sparks[i].isWhite) {
            r = (uint8_t)(255*fade + bgR*(1.0f-fade));
            g = (uint8_t)(255*fade + bgG*(1.0f-fade));
            b = (uint8_t)(255*fade + bgB*(1.0f-fade));
        } else {
            // zlata
            uint32_t sparkColor = CHSV_to_RGB(30,255,(uint8_t)(255*fade));
            r = (uint8_t)((sparkColor>>16 & 0xFF)*fade + bgR*(1.0f-fade));
            g = (uint8_t)((sparkColor>>8 & 0xFF)*fade + bgG*(1.0f-fade));
            b = (uint8_t)((sparkColor & 0xFF)*fade + bgB*(1.0f-fade));
        }

        ledstring.channel[0].leds[p] = (r<<16)|(g<<8)|b;
    }
}




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


void effect_rotateColor_LED_palett() {
    static uint8_t idx = 0;
    for (int i = 0; i < LED_COUNT; ++i) {
        uint8_t block = (i / 6);
        uint8_t hue = idx + block * 8;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 200, 150);
    }
    idx += 3;
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

        float fade = 1.0f - fabs(i) / (float)W;
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
                waves[i].speed = 0.3f + (rand() % 100) / 200.0f; // 0.3..0.8
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
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.80f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.80f;
        uint8_t b = ((c      ) & 0xFF) * 0.80f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

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

    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        RGB oldColor = { (uint8_t)((c>>16)&0xFF), (uint8_t)((c>>8)&0xFF), (uint8_t)(c&0xFF) };
        oldColor.r = oldColor.r * 0.96f;
        oldColor.g = oldColor.g * 0.96f;
        oldColor.b = oldColor.b * 0.96f;
        ledstring.channel[0].leds[i] = (oldColor.r << 16) | (oldColor.g << 8) | oldColor.b;
    }

    for (int i = 0; i < LED_COUNT; i++) {
        float f1 = sinf(t0 * 0.8f + i * 0.02f) * 0.5f + 0.5f;
        float f2 = sinf(t0 * 1.3f + i * 0.05f) * 0.5f + 0.5f;
        float intensity = f1 * 0.7f + f2 * 0.4f;
        uint8_t hue = (uint8_t)((int)(80 + sinf(t0*0.2f + i*0.01f)*40.0f) & 0xFF);
        uint8_t val = (uint8_t)clampInt((int)(intensity*220.0f), 0, 255);

        RGB add = CHSV_to_RGB_struct(hue, 220, val);

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

    if (left.active && right.active && fabs(left.pos - right.pos) < 6.0f) {
        flash = 6;
        left.active = false; right.active = false;
    }

    if (flash > 0) {
        for (int i = 0; i < LED_COUNT; i++) {
            if ((i % 6) == (flash % 6)) ledstring.channel[0].leds[i] = CHSV_to_RGB(0,255,255);
        }
        flash--;
    }

    if (left.active && left.pos > LED_COUNT + 10) left.active = false;
    if (right.active && right.pos < -10) right.active = false;
}

void effect_policeStrobe() {
    static int frame = 0;
    frame = (frame + 1) % 12;

    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.9f;
        uint8_t b = ((c      ) & 0xFF) * 0.9f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    int segment = 10;
    if (frame < 6) {
        int center = (LED_COUNT/4) + (frame-3);
        for (int i = -segment; i <= segment; i++) {
            int p = center + i;
            if (p < 0 || p >= LED_COUNT) continue;
            float fade = 1.0f - fabs(i)/(float)segment;
            ledstring.channel[0].leds[p] = CHSV_to_RGB(0,255,(uint8_t)(fade*200));
        }
    } else {
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
    const int MAX_PART = 80;
    static Particle parts[MAX_PART];

    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.92f;
        uint8_t g = ((c >>  8) & 0xFF) * 0.92f;
        uint8_t b = ((c      ) & 0xFF) * 0.92f;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    if ((rand()%60)==0) {
        int center = 20 + rand() % (LED_COUNT - 40);
        uint8_t hue = rand()%255;
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

    for (int i = 0; i < MAX_PART; i++) {
        if (!parts[i].active) continue;
        parts[i].x += parts[i].vx;
        parts[i].vx *= 0.98f;
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
            stars[i].hue = 40 + rand()%40;
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


// Knight Rider effect - time-based fade, LEDs 55-145
void effect_knightRider() {
    static int pos = 55;
    static int dir = 1;
    static int trailLen = 30;
    static bool shrinking = false;
    static uint8_t brightness[256] = {0}; // red

    const int maxTrail = 30;
    const int start = 55;
    const int end = 142;
    const uint8_t hue = 0;
    const uint8_t fadeStep = 4; // time-based fade in ms = less slower

    // fade all LEDs in segment
    for (int i = start; i <= end; i++) {
        if (brightness[i] > fadeStep)
            brightness[i] -= fadeStep;
        else
            brightness[i] = 0;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, brightness[i]);
    }

    // set head LED to full brightness
    brightness[pos] = 255;
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(hue, 255, 255);

    // check edges to start shrinking
    if (!shrinking) {
        if ((dir > 0 && pos >= end) || (dir < 0 && pos <= start)) {
            shrinking = true;
        }
    }

    // move head
    pos += dir;

    // shrink or grow trail
    if (shrinking) {
        if (trailLen > 1) {
            trailLen--;
        } else {
            dir = -dir;
            shrinking = false;
        }
    } else {
        if (trailLen < maxTrail) trailLen++;
    }


    if (pos > end) pos = end;
    if (pos < start) pos = start;
}


// Effects array
typedef void(*effect_fn)();
effect_fn effects[] = {
	effect_knightRider,				//
	effect_rotateColor_LED_palett,	// upravit paletu na zajimavou
	effect_dualWaveCollision,		//
	effect_confetti,				//
	//effect_aurora,					//
    effect_rainbow_with_glitter,	//
    //effect_kometa,					// absolutnÄ› nedÄ›lĂˇ co by mÄ›la
    effect_bpm,						//
    effect_juggle,					// mozna vicero najednou?
    //effect_cylon,					// to je %x ledek... neni moc hezke
	effect_waveSpawner,				//
    //effect_fire2012,				// nehodi se
    //effect_sinelon,					// to je %x ledek... neni moc hezke
    effect_meteor,					//
    effect_oceanWaves,				//
    //effect_rotate_white,			// opravit smer sem a tam, ne jen jizda na jednu stranu
    effect_color_shift,				//
	effect_fireworks,				//
	//effect_starfall,				//
	effect_christmasSparkle,		//
	effect_matrix,					//
	//effect_policeStrobe,			// neni hezke
};
const int EFFECT_COUNT = sizeof(effects) / sizeof(effects[0]);



// ================== MAIN ==================
int main() {
    // allocate LED buffer
    ledstring.channel[1].leds = new uint32_t[LED_COUNT];
    for (int i = 0; i < LED_COUNT; ++i)
        ledstring.channel[1].leds[i] = 0;

    // init WS2811
    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!\n";
        delete[] ledstring.channel[1].leds;
        return -1;
    }

    lastInputTime.store(steady_clock::now());

    std::thread reader(pipeThread);
    std::cout << "Listening on " << PIPE_PATH << " ...\n";

    bool wasPassive = false;
    int lastPrintedEffect = -1;
    bool lastSongRunning = false;

    // ================== MAIN LOOP ==================
    while (running) {

        // -------------------------------------------------
        // SONG MODE (absolute priority)
        // -------------------------------------------------
        if (songRunning.load()) {

            int se = specialEffect.load();

            if (se == 1)      effect_special1();
            else if (se == 2) effect_special2();
            else if (se == 3) effect_special3();

            ws2811_render(&ledstring);

            // clean entry
            if (!lastSongRunning) {
                for (int i = 0; i < LED_COUNT; ++i)
                    ledstring.channel[1].leds[i] = 0;

                wasPassive = false;
                std::cout << "[MAIN] Song mode entered\n";
            }

            lastSongRunning = true;
            std::this_thread::sleep_for(milliseconds(MAIN_LOOP_MS));
            continue;
        }

        // -------------------------------------------------
        // SONG JUST ENDED
        // -------------------------------------------------
        if (lastSongRunning && !songRunning.load()) {
            for (int i = 0; i < LED_COUNT; ++i)
                ledstring.channel[1].leds[i] = 0;

            ws2811_render(&ledstring);

            lastSongRunning = false;
            std::cout << "[MAIN] Song mode exited\n";
        }

        // -------------------------------------------------
        // NORMAL MODE (breaths + passive)
        // -------------------------------------------------

        updateBreaths();

        auto now = steady_clock::now();
        auto idleSec =
            duration_cast<seconds>(now - lastInputTime.load()).count();

        bool passiveMode = (idleSec > INACTIVITY_SECONDS);

        if (passiveMode) {
            auto ms =
                duration_cast<milliseconds>(now - effectStart).count();

            if (ms > EFFECT_SWITCH_MS) {
                currentEffect = (currentEffect + 1) % EFFECT_COUNT;
                effectStart = now;
            }

            if (!wasPassive || lastPrintedEffect != currentEffect) {
                std::cout << "[MAIN] Passive mode. Effect index: "
                          << currentEffect << "\n";
                lastPrintedEffect = currentEffect;
            }

            effects[currentEffect]();
            ws2811_render(&ledstring);
            wasPassive = true;
        }
        else {
            if (wasPassive) {
                for (int i = 0; i < LED_COUNT; ++i)
                    ledstring.channel[1].leds[i] = 0;

                wasPassive = false;
                std::cout << "[MAIN] Exiting passive mode\n";
            }

            composeBreathsAndShow();
        }

        std::this_thread::sleep_for(milliseconds(MAIN_LOOP_MS));
    }

    // ================== SHUTDOWN ==================
    reader.join();
    ws2811_fini(&ledstring);
    delete[] ledstring.channel[1].leds;

    return 0;
}
