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
#include <cmath>
#include <cstring>

using namespace std::chrono;

// millis() using steady_clock
static inline uint64_t millis() {
    static const auto start = steady_clock::now();
    return duration_cast<milliseconds>(steady_clock::now() - start).count();
}

// ================== MACRA / SETTINGS ==================
#define LED_COUNT 200
#define GPIO_PIN 18
#define DMA 10
#define BRIGHTNESS 255

#define MAX_SNAKES 10
#define SNAKE_LENGTH 10
#define SNAKE_STEP_MS 10
#define SNAKE_FADE_MIN 230
#define SNAKE_FADE_MAX 255
#define HUE_SHIFT_PER_OVERLAP 30
#define SATURATION 230
#define PIPE_PATH "/tmp/ledpipe"

#define INACTIVITY_SECONDS 30    // kdyďż˝ 30s nic nepďż˝ijde -> passive/effects mode
#define EFFECT_SWITCH_MS 10000   // jak dlouho bďż˝ďż˝ jeden efekt v passive mode
#define MAIN_LOOP_MS 20

// ================== GLOBALS ==================
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
    int prevStep = -1;
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

// time of last input from pipe
std::atomic<steady_clock::time_point> lastInputTime(steady_clock::now());

// passive mode effect bookkeeping
int currentEffect = 0;
steady_clock::time_point effectStart = steady_clock::now();

// ================== HELPERS ==================
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

// Simple HSV->RGB converter returning 0xRRGGBB (based on PDF example).
static inline uint32_t CHSV_to_RGB(uint8_t h, uint8_t s, uint8_t v) {
    float H = (h / 255.0f) * 360.0f;
    float S = s / 255.0f;
    float V = v / 255.0f;
    float C = V * S;
    float X = C * (1.0f - std::fabs(fmod(H / 60.0f, 2.0f) - 1.0f));
    float m = V - C;
    float r=0,g=0,b=0;
    if (H < 60) { r=C; g=X; b=0; }
    else if (H<120) { r=X; g=C; b=0; }
    else if (H<180){ r=0; g=C; b=X; }
    else if (H<240){ r=0; g=X; b=C; }
    else if (H<300){ r=X; g=0; b=C; }
    else { r=C; g=0; b=X; }
    uint8_t R = (uint8_t)clampInt((int)round((r+m)*255.0f),0,255);
    uint8_t G = (uint8_t)clampInt((int)round((g+m)*255.0f),0,255);
    uint8_t B = (uint8_t)clampInt((int)round((b+m)*255.0f),0,255);
    return ((uint32_t)R<<16)|((uint32_t)G<<8)|((uint32_t)B);
}

// ================== SNAKES (spawn/update/render) ==================
bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= LED_COUNT) return false;
    for (int i = 0; i < MAX_SNAKES; ++i) {
        if (!snakes[i].active) {
            snakes[i].active = true;
            snakes[i].origin = originIndex;
            snakes[i].step = 0;
            snakes[i].prevStep = -1;
            snakes[i].length = SNAKE_LENGTH;
            snakes[i].hue = hue;
            snakes[i].lastUpdate = steady_clock::now();
            return true;
        }
    }
    return false;
}

void killSnake(int idx) { if (idx >= 0 && idx < MAX_SNAKES) snakes[idx].active = false; }

void updateSnakes() {
    auto now = steady_clock::now();
    for (int s = 0; s < MAX_SNAKES; ++s) {
        if (!snakes[s].active) continue;
        auto elapsed = duration_cast<milliseconds>(now - snakes[s].lastUpdate).count();
        if (elapsed >= snakes[s].stepInterval) {
            snakes[s].lastUpdate = now;
            snakes[s].prevStep = snakes[s].step;
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
            // convert HSV -> RGB using helper
            uint32_t rgb = CHSV_to_RGB(finalHue, SATURATION, (uint8_t)std::min((int)totalB, 255));
            color = (ws2811_led_t)rgb;
        }
        ledstring.channel[0].leds[i] = color;
    }
    // render is called by caller (main)
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
                    int idx = std::stoi(line);
                    if (idx >= 1 && idx <= LED_COUNT) {
                        spawnSnake(idx - 1, (uint8_t)(rand() % 256));
                        lastInputTime.store(steady_clock::now()); // reset inactivity timer
                        // debug
                        std::cout << "Spawn snake at LED " << idx << std::endl;
                    }
                } catch (...) {}
            }
            fifo.close();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

// ================== EFFECTS (non-blocking; only fill buffer) ==================
// Each effect should only write ledstring.channel[0].leds[] (no ws2811_render here) and return quickly.

void effect_rotate_white() {
    static int offset = 0;
    for (int i = 0; i < LED_COUNT; ++i) ledstring.channel[0].leds[i] = 0;
    for (int i = 0; i < LED_COUNT; ++i) {
        if ((i + offset) % 4 == 0) ledstring.channel[0].leds[i] = CHSV_to_RGB(0, 0, 255); // white via v=255,s=0
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

uint8_t gHue = 0;
void effect_rainbow_with_glitter() {
    for (int i = 0; i < LED_COUNT; ++i) {
        uint8_t hue = (gHue + i * 7) & 0xFF;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, 160);
    }
    // simple glitter: occasionally set a pixel to white
    if ((rand() & 0xFF) < 30) {
        int p = rand() % LED_COUNT;
        ledstring.channel[0].leds[p] = 0xFFFFFF;
    }
    gHue++;
}

void effect_toceniLedekbila() {
    static int phase = 0;
    // light every 4th led with a rotating offset
    for (int i = 0; i < LED_COUNT; ++i) ledstring.channel[0].leds[i] = 0;
    for (int q = 0; q < 4; ++q) {
        // show one sub-frame per call
        int offset = (phase + q) % 4;
        for (int i = 0; i < LED_COUNT; i += 4) {
            int idx = i + offset;
            if (idx < LED_COUNT) ledstring.channel[0].leds[idx] = CHSV_to_RGB(255, 0, 160);
        }
        break; // only do one sub-frame per main-loop iteration to avoid blocking
    }
    phase = (phase + 1) % 4;
}

void effect_toceniLedekbarva_paleta() {
    static uint8_t idx = 0;
    // emulate a color palette by shifting hue per block of 6
    for (int i = 0; i < LED_COUNT; ++i) {
        uint8_t block = (i / 6);
        uint8_t hue = idx + block * 8;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 200, 150);
    }
    idx += 3;
}


void effect_prolinani() {
    static uint8_t idx = 0;
    idx++;  // pohyb v paletďż˝

    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t hue = idx + i * 3;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, 255);
    }
}


void effect_confetti() {
    // mďż˝rnďż˝ vyblednutďż˝
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9;
        uint8_t g = ((c >> 8) & 0xFF) * 0.9;
        uint8_t b = (c & 0xFF) * 0.9;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    int pos = rand() % LED_COUNT;
    ledstring.channel[0].leds[pos] =
        CHSV_to_RGB(gHue + (rand() % 64), 200, 255);

    gHue++;
}


void effect_kometa() {
    // fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9;
        uint8_t g = ((c >> 8) & 0xFF) * 0.9;
        uint8_t b = (c & 0xFF) * 0.9;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    int pos = (int)( (sin( (millis()/1000.0) * 12 ) + 1) / 2 * (LED_COUNT-1) );
    
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue, 255, 255);
}


void effect_bpm() {
    static uint8_t beat = 0;
    beat += 3;

    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t hue = (i * 2 + beat);
        ledstring.channel[0].leds[i] =
            CHSV_to_RGB(hue, 255, (uint8_t)(128 + sin((beat + i * 5) * 0.05) * 127));
    }
}


void effect_juggle() {
    // slight fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.85;
        uint8_t g = ((c >> 8) & 0xFF) * 0.85;
        uint8_t b = (c & 0xFF) * 0.85;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    uint8_t hue = 0;
    for (int i = 0; i < 8; i++) {
        float pos = (sin((millis() / 800.0) * (i + 7)) + 1) * 0.5f;
        int pixel = (int)(pos * (LED_COUNT - 1));
        ledstring.channel[0].leds[pixel] =
            CHSV_to_RGB(hue, 255, 255);
        hue += 32;
    }
}


void effect_cylon() {
    static int pos = 0;
    static int dir = 1;

    // fade
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        ledstring.channel[0].leds[i] =
            ((uint8_t)(((c >> 16)&0xFF)*0.8)<<16) |
            ((uint8_t)(((c >> 8)&0xFF)*0.8)<<8) |
            ((uint8_t)((c&0xFF)*0.8));
    }

    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue, 255, 255);

    pos += dir;
    if (pos <= 0 || pos >= LED_COUNT - 1)
        dir = -dir;

    gHue += 2;
}


void effect_fire2012() {
    static uint8_t heat[LED_COUNT];

    // cool down
    for (int i = 0; i < LED_COUNT; i++) {
        heat[i] = std::max(0, heat[i] - (rand() % 5));
    }

    // heat diffusion upward
    for (int i = LED_COUNT - 1; i >= 2; i--) {
        heat[i] = (heat[i - 1] + heat[i - 2] + heat[i - 2]) / 3;
    }

    // new sparks
    if (rand() % 3 == 0) {
        int y = rand() % 7;
        heat[y] = std::min(255, heat[y] + (rand() % 120 + 135));
    }

    // convert heat[] to color
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t t = heat[i];
        uint8_t hue = (t < 128) ? (t * 2) : 255;
        uint8_t val = t;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}


void effect_sinelon() {
    // fade out
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = ((c >> 16) & 0xFF) * 0.9;
        uint8_t g = ((c >> 8) & 0xFF) * 0.9;
        uint8_t b = (c & 0xFF) * 0.9;
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }

    float pos = (sin(millis() / 400.0) + 1) * 0.5f;
    int pixel = (int)(pos * (LED_COUNT - 1));

    ledstring.channel[0].leds[pixel] = CHSV_to_RGB(gHue, 255, 255);

    gHue++;
}


void effect_meteor() {
    static uint8_t hue = 0;

    // fade all
    for (int i = 0; i < LED_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        ledstring.channel[0].leds[i] =
            ((uint8_t)(((c >> 16)&0xFF)*0.75)<<16) |
            ((uint8_t)(((c >> 8)&0xFF)*0.75)<<8) |
            ((uint8_t)((c&0xFF)*0.75));
    }

    float pos = (sin(millis() / 350.0) + 1) * 0.5f;
    int p = (int)(pos * (LED_COUNT - 1));

    ledstring.channel[0].leds[p] = CHSV_to_RGB(hue, 255, 255);

    hue += 2;
}

void effect_oceanWaves() {
    static uint8_t base = 0;
    base++;

    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t hue = base + (sin((millis() + i * 30) / 500.0) * 30);
        uint8_t val = 150 + sin((millis() + i * 40) / 300.0) * 100;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}


// Effects array for easy cycling
typedef void(*effect_fn)();
effect_fn effects[] = {
    effect_toceniLedekbila,
    effect_toceniLedekbarva_paleta,
    effect_rainbow_with_glitter,
    effect_color_shift,
    effect_rotate_white,
    effect_prolinani,
    effect_confetti,
    effect_kometa,
    effect_bpm,
    effect_juggle,
    effect_cylon,
    effect_fire2012,
    effect_sinelon,
    effect_meteor,
    effect_oceanWaves
};
const int EFFECT_COUNT = sizeof(effects) / sizeof(effects[0]);

// ================== MAIN ==================
int main() {
    // allocate buffer for rpi_ws281x
    ledstring.channel[0].leds = new uint32_t[LED_COUNT];

    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!" << std::endl;
        delete[] ledstring.channel[0].leds;
        return -1;
    }

    // init lastInputTime
    lastInputTime.store(steady_clock::now());

    // start Pipe reader
    std::thread reader(pipeThread);
    std::cout << "Listening on " << PIPE_PATH << " ..." << std::endl;

    // main loop
    while (running) {
        // --- SNAKES UPDATE & RENDER BUFFERS ---
        updateSnakes();
        renderSnakesToBuffers();

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
            }

            // call effect to fill ledstring.channel[0].leds (non-blocking)
            // effects overwrite the whole strip
            effects[currentEffect]();

            // render effect
            ws2811_render(&ledstring);
        } else {
            // normal mode: compose snakes into ledstring and show
            composeAndShow();
            ws2811_render(&ledstring);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(MAIN_LOOP_MS));
    }

    reader.join();
    ws2811_fini(&ledstring);
    delete[] ledstring.channel[0].leds;
    return 0;
}
