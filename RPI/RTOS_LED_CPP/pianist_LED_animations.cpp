//=====================================================================================
// Name        : pianist_LED_animations.cpp
// Author      : Bc. Jan Besta
// Version     : 0.0
// Copyright   : VSB-TUO FEI
// Description :
//  - LED effects and animations with library rpi_ws281x for LED strips
//  - Pipe/FIFO input handling
//  - Special effect song mode (1..3) ended by -1
//  - Note-driven breath animations (>=4, released by 0)
//  - Passive / idle mode fallback
//=====================================================================================

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

std::mutex snakesMutex;
std::mutex breathMutex;


using namespace std::chrono; // millis() helper uses steady_clock

static inline uint64_t millis() {
    static const auto start = steady_clock::now();
    return duration_cast<milliseconds>(steady_clock::now() - start).count();
}

// ================== MACROS / SETTINGS ==================
#define DMA 10
#define BRIGHTNESS 255

#define PIPE_PATH "/tmp/led/pipe"
#define ACK_PIPE_PATH "/tmp/led/ack_pipe"
#define INACTIVITY_SECONDS 5 // enter passive mode after inactivity timeout
#define EFFECT_SWITCH_MS 15000 // duration of each passive mode effect
#define MAIN_LOOP_MS 20

// -------- TOP (snakes strip) --------
#define LED_TOP_COUNT 200
#define GPIO_TOP_PIN 18         // <-- GPIO pro vrchni pasek

#define SNAKE_LENGTH 5
#define SNAKE_STEP_MS 50
#define SNAKE_TIME_FADE 0.92f
#define SNAKE_FADE_MIN 50
#define SNAKE_FADE_MAX 255

#define HUE_SHIFT_PER_OVERLAP 30
#define SATURATION 230

// -------- BTM (breath strip) --------
#define LED_BTM_COUNT 112		// presny pocet - jeden kus o 1 led delsi nez druhy
#define GPIO_BTM_PIN  13         // <-- GPIO pro spodni pasek

#define TONE_MIN 74
#define TONE_MAX 124
#define TONE_RANGE (TONE_MAX - TONE_MIN)

#define BREATH_FALL_MS 420
#define BREATH_ATTACK_MS 40


// ================== GLOBALS ==================
ws2811_t ledstring = {
    .freq = WS2811_TARGET_FREQ,
    .dmanum = DMA,
    .channel = {
        [0] = {
            .gpionum = GPIO_TOP_PIN,
            .invert = 0,
            .count = LED_TOP_COUNT,
            .strip_type = WS2811_STRIP_GRB,
            .brightness = BRIGHTNESS,
        },
        [1] = {
    		.gpionum = GPIO_BTM_PIN,
    		.invert = 0,
    		.count = LED_BTM_COUNT,
    		.strip_type = WS2811_STRIP_GRB,
    		.brightness = BRIGHTNESS,
	},
    },
};

// ================== TOP - GLOBAL SNAKES STATE ==================

struct Snake {
    bool active = false;        // snake instance enabled flag
    int origin = 0;             // starting LED index
    int step = 0;               // current step forward
    int prevStep = -1;          // previous step for rendering
    int targetLength = SNAKE_LENGTH; // length goal of snake
    int currentLength = 1;      // current head-to-tail length
    uint8_t hue = 0;            // snake color hue
    steady_clock::time_point lastUpdate; // last step timestamp
    int stepInterval = SNAKE_STEP_MS;    // ms per step
};

std::vector<Snake> snakes;

uint16_t brightnessSum[LED_TOP_COUNT];     // accum brightness per LED
uint32_t hueWeightedSum[LED_TOP_COUNT];    // hue-weight accumulator
uint8_t overlapCount[LED_TOP_COUNT];       // number of overlapping snakes

std::atomic<bool> running(true);
std::atomic<steady_clock::time_point> lastInputTime(steady_clock::now());

int currentEffect = 0; // current passive-mode effect
steady_clock::time_point effectStart = steady_clock::now();


std::atomic<int> heldKey(-1);          // key currently held
std::atomic<bool> holdActive(false);   // key hold indicator
std::atomic<int> heldHueInt(0);        // random hue for hold preview
std::atomic<int> specialEffect(-1);    // 1..3 special effect modes
std::atomic<bool> songRunning(false);  // special effect -1 logic


// ================== SIMPLE HELPERS ==================
static inline int clampInt(int v, int lo, int hi) { if (v<lo) return lo; if (v>hi) return hi; return v; }
static inline int mapTopToBtm(int i) { return (i * LED_BTM_COUNT) / LED_TOP_COUNT; }
static inline void drawTopToBtm(
    int topIndex,
    uint32_t color
) {
    int a = ( topIndex      * LED_BTM_COUNT) / LED_TOP_COUNT;
    int b = ((topIndex + 1) * LED_BTM_COUNT) / LED_TOP_COUNT;

    for (int j = a; j < b; j++) {
        ledstring.channel[1].leds[j] = color;
    }
}



uint8_t brightnessForDistance(int dist, int length) {
    if (dist < 0 || dist >= length) return 0;
    if (length <= 1) return SNAKE_FADE_MAX;
    int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
    return (uint8_t)clampInt(b, 0, 255);
}

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
    return ((uint32_t)R << 16) | ((uint32_t)G << 8) | ((uint32_t)B);
}

// for effects
static inline uint32_t addColor(uint32_t a, uint32_t b) {
    uint8_t ar = (a >> 16) & 0xFF;
    uint8_t ag = (a >> 8)  & 0xFF;
    uint8_t ab =  a        & 0xFF;

    uint8_t br = (b >> 16) & 0xFF;
    uint8_t bg = (b >> 8)  & 0xFF;
    uint8_t bb =  b        & 0xFF;

    uint8_t r = (ar + br > 255) ? 255 : ar + br;
    uint8_t g = (ag + bg > 255) ? 255 : ag + bg;
    uint8_t b2 = (ab + bb > 255) ? 255 : ab + bb;

    return (r << 16) | (g << 8) | b2;
}

// for effects
static inline uint32_t scaleColor(uint32_t c, uint8_t scale) {
    uint8_t r = (c >> 16) & 0xFF;
    uint8_t g = (c >> 8)  & 0xFF;
    uint8_t b =  c        & 0xFF;

    r = (uint16_t(r) * scale) >> 8;
    g = (uint16_t(g) * scale) >> 8;
    b = (uint16_t(b) * scale) >> 8;

    return (r << 16) | (g << 8) | b;
}



// ================== SNAKES (spawn/update/render) ==================
// Snake system spawns short mirrored trails on keypress and moves them
// outwards with fade. Multiple snakes may overlap.

bool spawnSnake(int originIndex, uint8_t hue = 0) {
    if (originIndex < 0 || originIndex >= LED_TOP_COUNT - 1) return false;
    Snake s;
    s.active = true;
    s.origin = originIndex;
    s.step = 0;
    s.prevStep = 0;
    s.targetLength = SNAKE_LENGTH;
    s.currentLength = SNAKE_LENGTH;
    s.step = 1;
    s.hue = hue;
    s.lastUpdate = steady_clock::now();
    {
        std::lock_guard<std::mutex> lk(snakesMutex);
        snakes.push_back(s);
    }
    std::cerr << "[spawnSnake] origin=" << originIndex << " hue=" << (int)hue << '\n';
    return true;
}

void killSnake(int idx) {
    if (idx >= 0 && idx < (int)snakes.size()) snakes[idx].active = false;
}

void updateSnakes() {
    auto now = steady_clock::now();
    for (int s = 0; s < (int)snakes.size(); ++s) {
        if (!snakes[s].active) continue;
        auto elapsed = duration_cast<milliseconds>(now - snakes[s].lastUpdate).count();
        if (elapsed >= snakes[s].stepInterval) {
            snakes[s].lastUpdate = now;
            snakes[s].prevStep = snakes[s].step;

            if (snakes[s].currentLength < snakes[s].targetLength) {
                snakes[s].currentLength++;
            } else {
                snakes[s].step++;
            }

            bool anyOnStrip = false;
            int origin = snakes[s].origin;
            int len = snakes[s].currentLength;
            int stepToCheck = snakes[s].step;

            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (stepToCheck - d) * dir;
                    if (pos >= 0 && pos < LED_TOP_COUNT) { anyOnStrip = true; break; }
                }
                if (anyOnStrip) break;
            }

            if (!anyOnStrip) {
                if (origin >= 0 && origin < LED_TOP_COUNT) anyOnStrip = true;
                int rpos = origin + 1;
                if (!anyOnStrip && rpos >= 0 && rpos < LED_TOP_COUNT) anyOnStrip = true;
            }

            if (!anyOnStrip) killSnake(s);
        }
    }
}

void renderSnakesToBuffers() {
    // clear accumulators
    static uint32_t contributors[LED_TOP_COUNT];
    for (int i = 0; i < LED_TOP_COUNT; ++i) {
        brightnessSum[i] = 0;
        hueWeightedSum[i] = 0;
        contributors[i] = 0;
        overlapCount[i] = 0;
    }

    // accumulate brightness and hue contributions
    for (int s = 0; s < (int)snakes.size(); ++s) {
        if (!snakes[s].active) continue;
        int origin = snakes[s].origin;
        int len = snakes[s].currentLength;
        uint8_t hue = snakes[s].hue;
        int fromStep = std::max(0, snakes[s].prevStep);
        int toStep = snakes[s].step;

        for (int stepVal = fromStep; stepVal <= toStep; ++stepVal) {
            if (stepVal == 0) {
                // origin and origin+1 handled once per snake
                if (origin >= 0 && origin < LED_TOP_COUNT) {
                    uint32_t mask = (1UL << s);
                    if (!(contributors[origin] & mask)) {
                        uint8_t b = brightnessForDistance(0, len);
                        brightnessSum[origin] += b;
                        hueWeightedSum[origin] += (uint32_t)hue * b;
                        contributors[origin] |= mask;
                    }
                }
                int rpos = origin + 1;
                if (rpos >= 0 && rpos < LED_TOP_COUNT) {
                    uint32_t mask = (1UL << s);
                    if (!(contributors[rpos] & mask)) {
                        uint8_t b = brightnessForDistance(0, len);
                        brightnessSum[rpos] += b;
                        hueWeightedSum[rpos] += (uint32_t)hue * b;
                        contributors[rpos] |= mask;
                    }
                }
                continue;
            }

            for (int dir = -1; dir <= 1; dir += 2) {
                for (int d = 0; d < len; ++d) {
                    int pos = origin + (stepVal - d) * dir;
                    if (pos < 0 || pos >= LED_TOP_COUNT) continue;
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

    for (int i = 0; i < LED_TOP_COUNT; ++i) overlapCount[i] = __builtin_popcount((unsigned int)contributors[i]);
}

void composeAndShow() {
    // fade existing content
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * SNAKE_TIME_FADE);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * SNAKE_TIME_FADE);
        uint8_t b = (uint8_t)((c & 0xFF) * SNAKE_TIME_FADE);
        ledstring.channel[0].leds[i] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
    }

    // blend new snake data
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        if (brightnessSum[i] == 0) continue;
        uint16_t totalB = brightnessSum[i];
        uint8_t avgHue = (uint8_t)(hueWeightedSum[i] / (totalB ? totalB : 1));
        uint8_t finalHue = avgHue;
        if (overlapCount[i] > 1) {
            int shift = (overlapCount[i] - 1) * HUE_SHIFT_PER_OVERLAP;
            finalHue = (uint8_t)((avgHue + shift) & 0xFF);
        }
        uint8_t val = (uint8_t)std::min((int)totalB, 255);
        uint32_t s = CHSV_to_RGB(finalHue, SATURATION, val);
        uint8_t sval = val;

        uint8_t sr = (s >> 16) & 0xFF;
        uint8_t sg = (s >> 8) & 0xFF;
        uint8_t sb = s & 0xFF;

        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t cr = (c >> 16) & 0xFF;
        uint8_t cg = (c >> 8) & 0xFF;
        uint8_t cb = c & 0xFF;

        if (sval >= 200) {
            cr = sr; cg = sg; cb = sb;
        } else {
            int alpha = sval;
            cr = (uint8_t)((sr * alpha + cr * (255 - alpha)) / 255);
            cg = (uint8_t)((sg * alpha + cg * (255 - alpha)) / 255);
            cb = (uint8_t)((sb * alpha + cb * (255 - alpha)) / 255);
        }

        ledstring.channel[0].leds[i] = ((uint32_t)cr << 16) | ((uint32_t)cg << 8) | (uint32_t)cb;
    }
}

// ================== BTM - GLOBAL BREATH STATE ==================
struct GlobalBreath {
    uint8_t hue;
    uint8_t sat;
    uint8_t val;

    bool holding = false;
    bool attacking = false;
    bool releasing = false;

    steady_clock::time_point phaseStart;
};

GlobalBreath gBreath = {
    .hue = 0,
    .sat = 255,
    .val = 0,
    .holding = false,
    .attacking = false,
    .releasing = false,
    .phaseStart = steady_clock::now()
};


struct BreathColor {
    uint8_t h, s;
};

BreathColor pickColorForTone(int value)
{
    float t = (float)(value - TONE_MIN) / TONE_RANGE;
    t = std::clamp(t, 0.0f, 1.0f);

    BreathColor c;

    // =========================
    // LOW
    // =========================
    if (t < 0.50f) {

        uint8_t hueRanges[][2] = {
            {160, 255},   // blue - purple  
            {0, 40},      // red
            {80, 140}     // green  
        };

        auto &r = hueRanges[rand() % 3];
        c.h = r[0] + rand() % (r[1] - r[0]);

        c.s = 190 + rand() % 50;
    }

    // =========================
    // MID
    // =========================
    else if (t < 0.90f) {

        c.h = rand() & 0xFF;

        // hold color
        c.s = 130 + rand() % 90;   // 130..220
    }

    // =========================
    // HIGH
    // =========================
    else {

        uint8_t hueRanges[][2] = {
            {30, 70},     // yellow - gold
            {80, 120},    // light green
            {120, 160},   // azure
            {200, 240}    // red
        };

        auto &r = hueRanges[rand() % 4];
        c.h = r[0] + rand() % (r[1] - r[0]);

        float u = (t - 0.80f) / 0.20f;   // 0..1 only in high range

        // saturace drops slowly, white only at top
        c.s = (uint8_t)(120 - u * 100);  // 120 .. 20
    }

    return c;
}


void onBreathKeyDown(int value)
{
    auto col = pickColorForTone(value);

    std::lock_guard<std::mutex> lock(breathMutex);

    gBreath.hue = col.h;
    gBreath.sat = col.s;
    gBreath.val = 255;

    gBreath.holding   = true;
    gBreath.attacking = true;
    gBreath.releasing = false;
    gBreath.phaseStart = steady_clock::now();
}

void onBreathKeyUp()
{
    std::lock_guard<std::mutex> lock(breathMutex);

    gBreath.holding   = false;
    gBreath.attacking = false;
    gBreath.releasing = true;
    gBreath.phaseStart = steady_clock::now();
}


void renderGlobalBreath()
{
    std::lock_guard<std::mutex> lock(breathMutex);

    auto now = steady_clock::now();
    float alpha = 0.0f;

    if (gBreath.attacking) {
        auto elapsed =
            duration_cast<milliseconds>(now - gBreath.phaseStart).count();

        if (elapsed >= BREATH_ATTACK_MS) {
            gBreath.attacking = false;
            alpha = 1.0f;
        } else {
            alpha = (float)elapsed / BREATH_ATTACK_MS;
        }
    }
    else if (gBreath.releasing) {
        auto elapsed =
            duration_cast<milliseconds>(now - gBreath.phaseStart).count();

        if (elapsed >= BREATH_FALL_MS) {
            gBreath.releasing = false;
            alpha = 0.0f;
        } else {
            alpha = 1.0f - (float)elapsed / BREATH_FALL_MS;
        }
    }
    else if (gBreath.holding) {
        alpha = 1.0f;
    }

    // fade
    uint8_t v = (uint8_t)(255 * alpha);

    uint32_t color = (v == 0)
        ? 0
        : CHSV_to_RGB(gBreath.hue, gBreath.sat, v);

    for (int i = 0; i < LED_BTM_COUNT; ++i)
        ledstring.channel[1].leds[i] = color;
}



// ================== PIPE THREAD ==================
void pipeThread() {
    int ack_fd = -1;

    int fd = open(PIPE_PATH, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        std::cerr << "[pipeThread] ERROR: Cannot open read FIFO: "
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

                // =====================================
                // INPUT LOGIC
                // =====================================

                if (value >= 1 && value <= 3) {
                    // START SONG
                    songRunning.store(true);
                    specialEffect.store(value);

                    holdActive.store(false);
                    heldKey.store(-1);

                    std::cout << "[pipeThread] Song started: "
                              << value << "\n";
                }
                else if (value == -1) {
                    // STOP SONG
                    songRunning.store(false);
                    specialEffect.store(-1);

                    holdActive.store(false);
                    heldKey.store(-1);

                    std::cout << "[pipeThread] Song stopped (-1)\n";
                }
                else if (value == 0) {
                    // IGNORE key release during song
                    if (!songRunning.load() && holdActive.load()) {
                        int hk  = heldKey.load();
                        int hue = heldHueInt.load();
                        if (hk >= 1 && hk <= LED_TOP_COUNT - 1)
                            spawnSnake(hk - 1, (uint8_t)hue);

                        holdActive.store(false);
                        heldKey.store(-1);

			// BTM - BREATHS
			onBreathKeyUp();

                    }

                }
                else if (value >= 4 && value <= LED_TOP_COUNT - 1) {
                    if (!songRunning.load()) {
                        holdActive.store(true);
                        heldKey.store(value);
                        heldHueInt.store(rand() % 256);

			// BTM - BREATHS
			onBreathKeyDown(value);
                    }
                }

                // ACK
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

// ================== EFFECTS - special song modes ==================

void effect_special_happy_birthday() {
    static uint64_t t0 = millis();
    float t = (millis() - t0) * 0.002f;

    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float w = (sin(t + i * 0.08f) + 1) * 0.5f;
        uint8_t val = 120 + w * 100;

        uint8_t hue = (uint8_t)((sin(t * 0.4f) * 0.5f + 0.5f) * 255);

        uint32_t c = CHSV_to_RGB(hue, 170, val);

        if (((i + (int)(t * 40)) % 20) < 4) {
            c = CHSV_to_RGB(hue + 40, 255, 255);
        }

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }

    if ((rand() & 0xFF) < 12) {
        int p = rand() % LED_TOP_COUNT;
        ledstring.channel[0].leds[p] = 0xFFFFFF;
        ledstring.channel[1].leds[mapTopToBtm(p)] = 0xFFFFFF;
    }
}



void effect_special_star_wars() {
    static uint64_t t0 = millis();
    float t = (millis() - t0) * 0.0015f;

    float center = (LED_TOP_COUNT / 2) + sin(t) * 30.0f;

    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float dist = i - center;
        float f = dist / 12.0f;
        if (f < -1) f = -1;
        if (f >  1) f =  1;

        uint8_t blueVal = (uint8_t)((1 - (f + 1) * 0.5f) * 255);
        uint8_t redVal  = (uint8_t)(((f + 1) * 0.5f) * 255);
        uint8_t v = 150 + sin(t * 2.5f) * 50;

        uint32_t c =
            ((redVal * v / 255) << 16) |
            ((blueVal * v / 255));

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }
}

struct Spark {
    int pos;
    uint8_t hue;      // 0 = gold, 0=white special (sat=0)
    bool isWhite;
    uint64_t tStart;  // start time
    uint32_t lifeMS;  // duration of fade out
    bool active;
};

const int MAX_SPARKS = 80;
static Spark sparks[MAX_SPARKS];
static uint64_t t0 = millis();

void effect_special_mozart() {
    uint64_t now = millis();
    float t = (now - t0) * 0.0015f;

    // --- background ---
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float wave = (sin(t + i * 0.05f) + 1.0f) * 0.5f;
        uint8_t g = 50 + wave * 105;
        uint8_t b = 100 + wave * 155;

        uint32_t c = (g << 8) | b;

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }

    // --- spawn ---
    if ((rand() % 3) == 0) {
        int p = rand() % LED_TOP_COUNT;
        bool isWhite = rand() & 1;

        for (int i = 0; i < MAX_SPARKS; i++) {
            if (!sparks[i].active) {
                sparks[i].active = true;
                sparks[i].pos = p;
                sparks[i].isWhite = isWhite;
                sparks[i].tStart = now;
                sparks[i].lifeMS = 800;
                break;
            }
        }
    }

    // --- render sparks ---
    for (int i = 0; i < MAX_SPARKS; i++) {
        if (!sparks[i].active) continue;

        float fade = 1.0f - (now - sparks[i].tStart) / float(sparks[i].lifeMS);
        if (fade <= 0) {
            sparks[i].active = false;
            continue;
        }

        uint32_t c = sparks[i].isWhite
            ? ((uint8_t)(255 * fade) << 16 |
               (uint8_t)(255 * fade) << 8  |
               (uint8_t)(255 * fade))
            : CHSV_to_RGB(30, 255, uint8_t(255 * fade));

        int p = sparks[i].pos;
        ledstring.channel[0].leds[p] = c;
        ledstring.channel[1].leds[mapTopToBtm(p)] = c;
    }
}


// ================== EFFECTS - basic ==================

void effect_rainbow() {
    static float baseHue = 0.0f;
    static auto last = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < 20) return;
    last = now;

    baseHue += 0.8f;
    if (baseHue >= 255.0f) baseHue -= 255.0f;

    float topCycles = 3.0f;
    float btmCycles = 2.5f;

    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float n = (float)i / (LED_TOP_COUNT - 1);
        uint8_t h = baseHue + n * 255.0f * topCycles;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(h, 255, 255);
    }

    for (int i = 0; i < LED_BTM_COUNT; i++) {
        float n = (float)i / (LED_BTM_COUNT - 1);
        uint8_t h = baseHue + n * 255.0f * btmCycles;
        int p = LED_BTM_COUNT - 1 - i; // mirror
        ledstring.channel[1].leds[p] = CHSV_to_RGB(h, 255, 255);
    }
}

void effect_sinelon() {
    static uint64_t last = 0;
    uint64_t now = millis();
    if (now - last < 16) return;   // ~60 FPS
    last = now;

    static float basePhase = 0.0f;
    static uint8_t hue = 0;

    const float speed = 0.0065f;   // very close to FASTLED beatsin16(7)
    const uint8_t fadeTop = 22;
    const uint8_t fadeBtm = 18;

    // --- smooth color drift  ---
    hue++;

    basePhase += speed;
    if (basePhase > 6.283f) basePhase -= 6.283f;

    // --- fade ---
    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 255 - fadeTop);

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] =
            scaleColor(ledstring.channel[1].leds[i], 255 - fadeBtm);

    // --- MULTI-LAYER DRAW ---
    // trick which draws 3 overlapping sine waves with phase shift
    for (int layer = 0; layer < 3; layer++) {
        float phase = basePhase + layer * 0.45f;

        int posTop = (sin(phase) * 0.5f + 0.5f) * (LED_TOP_COUNT - 1);
        int posBtm = (sin(phase) * 0.5f + 0.5f) * (LED_BTM_COUNT - 1);

        uint8_t val = 192 - layer * 40;   // weaker for distant layers
        uint32_t c = CHSV_to_RGB(hue + layer * 6, 255, val);

        ledstring.channel[0].leds[posTop] =
            addColor(ledstring.channel[0].leds[posTop], c);

        ledstring.channel[1].leds[posBtm] =
            addColor(ledstring.channel[1].leds[posBtm], c);
    }
}



void effect_confetti() {
    static auto last = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < 25) return;
    last = now;

    // fade
    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 235);

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] =
            scaleColor(ledstring.channel[1].leds[i], 235);

    // spawn TOP
    if ((rand() & 0xFF) < 90) {
        int pos = rand() % LED_TOP_COUNT;
        uint8_t h = rand() & 0xFF;
        ledstring.channel[0].leds[pos] =
            addColor(ledstring.channel[0].leds[pos], CHSV_to_RGB(h, 255, 255));
    }

    // spawn BTM (independent)
    if ((rand() & 0xFF) < 120) {
        int pos = rand() % LED_BTM_COUNT;
        uint8_t h = rand() & 0xFF;
        ledstring.channel[1].leds[pos] =
            addColor(ledstring.channel[1].leds[pos], CHSV_to_RGB(h, 255, 255));
    }
}

#define MAX_TRAILS_TOP 20
#define MAX_TRAILS_BTM 30

#define FRAME_MS 20
#define GLOBAL_FADE 150

struct Trail {
    bool active;
    float pos;
    float speed;
    int dir;
    float length;
    float life;
    float decay;
    uint8_t hue;
};

void effect_ambient_trails() {
    static Trail trails_top[MAX_TRAILS_TOP];
    static Trail trails_btm[MAX_TRAILS_BTM];
    static auto last = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < FRAME_MS) return;
    last = now;

    // ---- global fade ----
    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], GLOBAL_FADE);

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] =
            scaleColor(ledstring.channel[1].leds[i], GLOBAL_FADE);

    // ================= TOP =================
    int activeTop = 0;
    for (int i = 0; i < MAX_TRAILS_TOP; i++)
        if (trails_top[i].active) activeTop++;

    for (int i = 0; i < MAX_TRAILS_TOP; i++) {
        Trail& t = trails_top[i];

        if (!t.active && activeTop < 4) {
            t.active = true;
            t.dir = (rand() & 1) ? 1 : -1;
            t.pos = (t.dir > 0) ? 0.0f : (LED_TOP_COUNT - 1);
            t.speed = 0.8f + (rand() % 100) / 350.0f;
            t.length = 8.0f + (rand() % 12);
            t.life = 1.0f;
            t.decay = 0.0025f;
            t.hue = rand() % 256;
            activeTop++;
        }

        if (!t.active) continue;

        for (int s = 0; s < (int)t.length; s++) {
            int idx = (int)(t.pos - s * t.dir + 0.5f);
            if (idx < 0 || idx >= LED_TOP_COUNT) continue;

            float a = (1.0f - (float)s / t.length) * t.life;
            ledstring.channel[0].leds[idx] =
                addColor(
                    ledstring.channel[0].leds[idx],
                    CHSV_to_RGB(t.hue, 180, (uint8_t)(a * 255))
                );
        }

        t.pos += t.speed * t.dir;
        t.life -= t.decay;

        if (t.life <= 0.0f)
            t.active = false;
    }

    // ================= BTM =================
    int activeBtm = 0;
    for (int i = 0; i < MAX_TRAILS_BTM; i++)
        if (trails_btm[i].active) activeBtm++;

    for (int i = 0; i < MAX_TRAILS_BTM; i++) {
        Trail& t = trails_btm[i];

        if (!t.active && activeBtm < 3) {
            t.active = true;
            t.dir = (rand() & 1) ? 1 : -1;
            t.pos = (t.dir > 0) ? 0.0f : (LED_BTM_COUNT - 1);
            t.speed = 1.8f + (rand() % 100) / 400.0f;
            t.length = 7.0f + (rand() % 10);
            t.life = 1.0f;
            t.decay = 0.020f;
            t.hue = rand() % 256;
            activeBtm++;
        }

        if (!t.active) continue;

        for (int s = 0; s < (int)t.length; s++) {
            int idx = (int)(t.pos - s * t.dir + 0.5f);
            if (idx < 0 || idx >= LED_BTM_COUNT) continue;

            float a = (1.0f - (float)s / t.length) * t.life;
            ledstring.channel[1].leds[idx] =
                addColor(
                    ledstring.channel[1].leds[idx],
                    CHSV_to_RGB(t.hue, 180, (uint8_t)(a * 255))
                );
        }

        t.pos += t.speed * t.dir;
        t.life -= t.decay;

        if (t.life <= 0.0f)
            t.active = false;
    }
}


void effect_juggle() {
    static float t = 0.0f;
    static auto last = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < 20) return;
    last = now;

    t += 0.05f;

    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 220);

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] =
            scaleColor(ledstring.channel[1].leds[i], 220);

    for (int d = 0; d < 8; d++) {
        float f = t * (0.7f + d * 0.15f);

        int tp = (sin(f) * 0.5f + 0.5f) * (LED_TOP_COUNT - 1);
        int bp = (sin(f) * 0.5f + 0.5f) * (LED_BTM_COUNT - 1);

        uint8_t h = d * 32;

        ledstring.channel[0].leds[tp] =
            addColor(ledstring.channel[0].leds[tp], CHSV_to_RGB(h, 255, 255));

        int p = LED_BTM_COUNT - 1 - bp;
        ledstring.channel[1].leds[p] =
            addColor(ledstring.channel[1].leds[p], CHSV_to_RGB(h, 255, 255));
    }
}


void effect_bpm() {
    static float phase = 0.0f;
    static auto last = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < 20) return;
    last = now;

    phase += 0.04f;
    if (phase > 6.283f) phase -= 6.283f;

    float beat = sin(phase) * 0.5f + 0.5f;

    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float n = (float)i / LED_TOP_COUNT;
        uint8_t h = (uint8_t)(phase * 40 + n * 255);
        uint8_t v = 120 + beat * 135;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(h, 255, v);
    }

    for (int i = 0; i < LED_BTM_COUNT; i++) {
        float n = (float)i / LED_BTM_COUNT;
        uint8_t h = (uint8_t)(phase * 40 + n * 255);
        uint8_t v = 120 + beat * 135;
        int p = LED_BTM_COUNT - 1 - i;
        ledstring.channel[1].leds[p] = CHSV_to_RGB(h, 255, v);
    }
}

void effect_rainbow_waves() {
    static uint8_t beat = 0;
    beat += 3;
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint8_t hue = (i * 2 + beat);
        float valF = 128.0f + sin((beat + i * 5) * 0.05f) * 127.0f;
        uint8_t val = (uint8_t)clampInt((int)round(valF), 0, 255);
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, val);
    }
}


#define MAX_CYLON_TOP 15
#define MAX_CYLON_BTM 25

#define FADE_FACTOR 0.80f

struct Cylon {
    bool active;
    float pos;
    float speed;
    int dir;
    uint8_t hue;
};

void effect_cylon_multi() {
    static Cylon top[MAX_CYLON_TOP];
    static Cylon btm[MAX_CYLON_BTM];

    static auto last = steady_clock::now();
    static auto nextSpawnTop = steady_clock::now();
    static auto nextSpawnBtm = steady_clock::now();

    auto now = steady_clock::now();
    if (duration_cast<milliseconds>(now - last).count() < FRAME_MS) return;
    last = now;

    // ---------- FADE ----------
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        ledstring.channel[0].leds[i] =
            ((uint8_t)(((c >> 16) & 0xFF) * FADE_FACTOR) << 16) |
            ((uint8_t)(((c >> 8) & 0xFF) * FADE_FACTOR) << 8) |
            ((uint8_t)((c & 0xFF) * FADE_FACTOR));
    }

    for (int i = 0; i < LED_BTM_COUNT; i++) {
        uint32_t c = ledstring.channel[1].leds[i];
        ledstring.channel[1].leds[i] =
            ((uint8_t)(((c >> 16) & 0xFF) * FADE_FACTOR) << 16) |
            ((uint8_t)(((c >> 8) & 0xFF) * FADE_FACTOR) << 8) |
            ((uint8_t)((c & 0xFF) * FADE_FACTOR));
    }

    // ---------- SPAWN TOP ----------
    if (now >= nextSpawnTop) {
        for (int i = 0; i < MAX_CYLON_TOP; i++) {
            if (!top[i].active) {
                top[i].active = true;
                top[i].dir = (rand() & 1) ? 1 : -1;
                top[i].pos = (top[i].dir > 0) ? 0.0f : (LED_TOP_COUNT - 1);
                top[i].speed = 0.6f + (rand() % 100) / 120.0f;
                top[i].hue = rand() % 256;
                break;
            }
        }
        nextSpawnTop = now + milliseconds((rand() % 600) + 200);
    }

    // ---------- SPAWN BTM ----------
    if (now >= nextSpawnBtm) {
        for (int i = 0; i < MAX_CYLON_BTM; i++) {
            if (!btm[i].active) {
                btm[i].active = true;
                btm[i].dir = (rand() & 1) ? 1 : -1;
                btm[i].pos = (btm[i].dir > 0) ? 0.0f : (LED_BTM_COUNT - 1);
                btm[i].speed = 0.5f + (rand() % 100) / 150.0f;
                btm[i].hue = rand() % 256;
                break;
            }
        }
        nextSpawnBtm = now + milliseconds((rand() % 700) + 300);
    }

    // ---------- UPDATE + DRAW TOP ----------
    for (int i = 0; i < MAX_CYLON_TOP; i++) {
        if (!top[i].active) continue;

        int idx = (int)(top[i].pos + 0.5f);
        if (idx >= 0 && idx < LED_TOP_COUNT)
            ledstring.channel[0].leds[idx] =
                addColor(
                    ledstring.channel[0].leds[idx],
                    CHSV_to_RGB(top[i].hue, 255, 255)
                );

        top[i].pos += top[i].speed * top[i].dir;

        if (top[i].pos < 0 || top[i].pos >= LED_TOP_COUNT)
            top[i].active = false;
    }

    // ---------- UPDATE + DRAW BTM ----------
    for (int i = 0; i < MAX_CYLON_BTM; i++) {
        if (!btm[i].active) continue;

        int idx = (int)(btm[i].pos + 0.5f);
        if (idx >= 0 && idx < LED_BTM_COUNT)
            ledstring.channel[1].leds[idx] =
                addColor(
                    ledstring.channel[1].leds[idx],
                    CHSV_to_RGB(btm[i].hue, 255, 255)
                );

        btm[i].pos += btm[i].speed * btm[i].dir;

        if (btm[i].pos < 0 || btm[i].pos >= LED_BTM_COUNT)
            btm[i].active = false;
    }
}

void effect_dot_spawner() {

    // ---------- FADE TOP ----------
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.85f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.85f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.85f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;

        // ---------- FADE BTM (mapped) ----------
        int bi = mapTopToBtm(i);
        uint32_t cb = ledstring.channel[1].leds[bi];
        uint8_t br = (uint8_t)(((cb >> 16) & 0xFF) * 0.85f);
        uint8_t bg = (uint8_t)(((cb >> 8) & 0xFF) * 0.85f);
        uint8_t bb = (uint8_t)((cb & 0xFF) * 0.85f);
        ledstring.channel[1].leds[bi] = (br << 16) | (bg << 8) | bb;
    }

    // ---------- SPAWN DOTS ----------
    uint8_t hue = 0;

    for (int i = 0; i < 8; i++) {
        float posf = (sin((millis() / 800.0f) * (i + 7)) + 1.0f) * 0.5f;
        int pixel = (int)(posf * (LED_TOP_COUNT - 1));
        pixel = clampInt(pixel, 0, LED_TOP_COUNT - 1);

        uint32_t c = CHSV_to_RGB(hue, 255, 255);

        // TOP
        ledstring.channel[0].leds[pixel] = c;

        // BTM (mapped)
        ledstring.channel[1].leds[mapTopToBtm(pixel)] = c;

        hue += 32;
    }
}




void effect_oceanWaves() {
    static uint8_t base = 0;
    base++;

    uint32_t now = millis();

    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float hf = sin((now + i * 30.0f) / 500.0f) * 30.0f;
        uint8_t hue = (uint8_t)(base + hf);

        float vf = 150.0f + sin((now + i * 40.0f) / 300.0f) * 100.0f;
        uint8_t val = (uint8_t)clampInt((int)round(vf), 0, 255);

        uint32_t c = CHSV_to_RGB(hue, 255, val);

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }
}


void effect_color_shift() {
    static uint8_t hue = 0;

    for (int i = 0; i < LED_TOP_COUNT; ++i) {
        uint32_t c = CHSV_to_RGB((uint8_t)(hue + i * 2), 255, 200);

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }

    hue += 2;
}


void effect_fireworks() {
    struct Particle {
        float x;
        float vx;
        uint8_t hue;
        int life;
        bool active;
    };

    const int MAX_PART = 80;
    static Particle parts[MAX_PART];

    // --------------------------------------------------
    // 1) FADE OUT
    // --------------------------------------------------
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 235);

        int b = mapTopToBtm(i);
        ledstring.channel[1].leds[b] =
            scaleColor(ledstring.channel[1].leds[b], 235);
    }

    // --------------------------------------------------
    // 2) SPAWN EXPLOZE
    // --------------------------------------------------
    if ((rand() % 35) == 0) {
        int center = 20 + rand() % (LED_TOP_COUNT - 40);
        uint8_t hue = rand() % 255;

        for (int p = 0; p < 20; p++) {
            for (int i = 0; i < MAX_PART; i++) {
                if (!parts[i].active) {
                    float ang = (float)p * (6.283185f / 20.0f);
                    float speed = 0.6f + (rand() % 100) / 200.0f;

                    parts[i].active = true;
                    parts[i].x = (float)center;
                    parts[i].vx = cosf(ang) * speed;
                    parts[i].life = 20 + rand() % 40;
                    parts[i].hue = hue;
                    break;
                }
            }
        }
    }

    // ----------------------------------------
    // 3) UPDATE + RENDER PARTICLES (TOP + BTM)
    // ----------------------------------------
    for (int i = 0; i < MAX_PART; i++) {
        if (!parts[i].active) continue;

        parts[i].x += parts[i].vx;
        parts[i].life--;

        if (parts[i].life <= 0 ||
            parts[i].x < 0 ||
            parts[i].x >= LED_TOP_COUNT) {
            parts[i].active = false;
            continue;
        }

        int p = (int)parts[i].x;

        uint8_t v = parts[i].life * 6;
        if (v > 255) v = 255;

        uint32_t c = CHSV_to_RGB(parts[i].hue, 255, v);

        ledstring.channel[0].leds[p] =
            addColor(ledstring.channel[0].leds[p], c);

        ledstring.channel[1].leds[mapTopToBtm(p)] =
            addColor(ledstring.channel[1].leds[mapTopToBtm(p)], c);
    }
}

/*
void effect_comet() {
    const uint8_t fadeTop   = 128;
    const uint8_t fadeBtm   = 200;
    const int cometSize     = 5;
    const uint8_t deltaHue  = 2;

    static uint8_t hue = 0;
    static int direction = 1;
    static int pos = 0;

    hue += deltaHue;

    pos += direction;
    if (pos <= 0 || pos >= (LED_TOP_COUNT - cometSize)) {
        direction *= -1;
    }

    // --- draw comet head ---
    for (int i = 0; i < cometSize; i++) {
        int p = pos + i;
        if (p < 0 || p >= LED_TOP_COUNT) continue;

        uint32_t c = CHSV_to_RGB(hue, 255, 255);

        ledstring.channel[0].leds[p] = c;
        ledstring.channel[1].leds[mapTopToBtm(p)] = c;
    }

    // --- random fade (FastLED-like chaos) ---
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        if ((rand() % 10) > 5) {
            ledstring.channel[0].leds[i] =
                scaleColor(ledstring.channel[0].leds[i], 255 - fadeTop);

            int b = mapTopToBtm(i);
            ledstring.channel[1].leds[b] =
                scaleColor(ledstring.channel[1].leds[b], 255 - fadeBtm);
        }
    }
}


void effect_cylon() {
    static int pos = 0;
    static int dir = 1;
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.8f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.8f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.8f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    ledstring.channel[0].leds[pos] = CHSV_to_RGB(gHue, 255, 255);
    pos += dir;
    if (pos <= 0 || pos >= LED_TOP_COUNT - 1) dir = -dir;
    gHue += 2;
}


void effect_dot_spawner() {
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        uint32_t c = ledstring.channel[0].leds[i];
        uint8_t r = (uint8_t)(((c >> 16) & 0xFF) * 0.85f);
        uint8_t g = (uint8_t)(((c >> 8) & 0xFF) * 0.85f);
        uint8_t b = (uint8_t)((c & 0xFF) * 0.85f);
        ledstring.channel[0].leds[i] = (r << 16) | (g << 8) | b;
    }
    uint8_t hue = 0;
    for (int i = 0; i < 8; i++) {
        float posf = (sin((millis() / 800.0f) * (i + 7)) + 1.0f) * 0.5f;
        int pixel = (int)(posf * (LED_TOP_COUNT - 1));
        pixel = clampInt(pixel, 0, LED_TOP_COUNT - 1);
        ledstring.channel[0].leds[pixel] = CHSV_to_RGB(hue, 255, 255);
        hue += 32;
    }
}

*/

#define MAX_COMETS_TOP  12
#define MAX_COMETS_BTM  20

struct Comet {
    float pos;
    int dir;
    uint8_t hue;
    bool active;
};


static Comet cometsTop[MAX_COMETS_TOP];
static Comet cometsBtm[MAX_COMETS_BTM];

static uint32_t nextSpawnTop = 0;
static uint32_t nextSpawnBtm = 0;

void spawnComet(Comet* arr, int maxCount, int ledCount) {
    for (int i = 0; i < maxCount; i++) {
        if (!arr[i].active) {
            arr[i].active = true;
            arr[i].dir = (rand() & 1) ? 1 : -1;
            arr[i].pos = rand() % ledCount;
            arr[i].hue = rand() & 0xFF;
            return;
        }
    }
}

void effect_comet() {
    const uint8_t fadeTop  = 130;
    const uint8_t fadeBtm  = 200;
    const int cometSizeTop = 6;
    const int cometSizeBtm = 9;

    uint32_t now = millis();

    // ---- SPAWN TIMERS ----
    if (now > nextSpawnTop) {
        spawnComet(cometsTop, MAX_COMETS_TOP, LED_TOP_COUNT);
        nextSpawnTop = now + (rand() % 600) + 200;
    }

    if (now > nextSpawnBtm) {
        spawnComet(cometsBtm, MAX_COMETS_BTM, LED_BTM_COUNT);
        nextSpawnBtm = now + (rand() % 600) + 200;
    }

    // ---- TOP COMETS ----
    for (int c = 0; c < MAX_COMETS_TOP; c++) {
        if (!cometsTop[c].active) continue;

        cometsTop[c].pos += cometsTop[c].dir * 0.6f;
        cometsTop[c].hue += 2;

        if (cometsTop[c].pos < -cometSizeTop ||
            cometsTop[c].pos > LED_TOP_COUNT + cometSizeTop) {
            cometsTop[c].active = false;
            continue;
        }

        uint32_t col = CHSV_to_RGB(cometsTop[c].hue, 255, 255);

        for (int i = 0; i < cometSizeTop; i++) {
            int p = (int)cometsTop[c].pos + i;
            if (p >= 0 && p < LED_TOP_COUNT) {
                ledstring.channel[0].leds[p] = col;
            }
        }
    }

    // ---- BOTTOM COMETS ----
    for (int c = 0; c < MAX_COMETS_BTM; c++) {
        if (!cometsBtm[c].active) continue;

        cometsBtm[c].pos += cometsBtm[c].dir * 0.5f;
        cometsBtm[c].hue += 2;

        if (cometsBtm[c].pos < -cometSizeBtm ||
            cometsBtm[c].pos > LED_BTM_COUNT + cometSizeBtm) {
            cometsBtm[c].active = false;
            continue;
        }

        uint32_t col = CHSV_to_RGB(cometsBtm[c].hue, 255, 255);

        for (int i = 0; i < cometSizeBtm; i++) {
            int p = (int)cometsBtm[c].pos + i;
            if (p >= 0 && p < LED_BTM_COUNT) {
                ledstring.channel[1].leds[p] = col;
            }
        }
    }

    // ---- FASTLED-LIKE RANDOM FADE ----
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        if ((rand() % 10) > 5) {
            ledstring.channel[0].leds[i] =
                scaleColor(ledstring.channel[0].leds[i], 255 - fadeTop);
        }
    }

    for (int i = 0; i < LED_BTM_COUNT; i++) {
        if ((rand() % 10) > 5) {
            ledstring.channel[1].leds[i] =
                scaleColor(ledstring.channel[1].leds[i], 255 - fadeBtm);
        }
    }
}



void effect_christmasSparkle() {
    static uint64_t lastTop = 0;
    static uint64_t lastBtm = 0;
    uint64_t now = millis();

    // --- fade ---
    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 220);

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] =
            scaleColor(ledstring.channel[1].leds[i], 200);

    // --- TOP sparkle ---
    if (now - lastTop > 20) {
        lastTop = now;

        int p = rand() % LED_TOP_COUNT;
        uint8_t hue = (rand() & 1) ? 0 : 96;
        ledstring.channel[0].leds[p] =
            CHSV_to_RGB(hue, 255, 255);
    }

    // --- BTM sparkle ---
    if (now - lastBtm > 10) {
        lastBtm = now;

        int p = rand() % LED_BTM_COUNT;
        uint8_t hue = (rand() & 1) ? 0 : 96;
        ledstring.channel[1].leds[p] =
            CHSV_to_RGB(hue, 255, 200);
    }
}


/*
void effect_christmasSparkle_old() {

    // --- fade out ---
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        ledstring.channel[0].leds[i] =
            scaleColor(ledstring.channel[0].leds[i], 204); // ~80%

        int b = mapTopToBtm(i);
        ledstring.channel[1].leds[b] =
            scaleColor(ledstring.channel[1].leds[b], 204);
    }

    // --- sparkle ---
    for (int s = 0; s < 8; s++) {
        int p = rand() % LED_TOP_COUNT;
        uint8_t hue = (rand() % 2) ? 0 : 96; // red / green
        uint8_t val = 200 + rand() % 55;

        uint32_t c = CHSV_to_RGB(hue, 255, val);

        ledstring.channel[0].leds[p] = c;
        ledstring.channel[1].leds[mapTopToBtm(p)] = c;
    }
}
*/

void effect_marquee() {
    static uint64_t last = 0;
    if (millis() - last < 50) return;
    last = millis();

    static uint8_t j_top = 0;
    static uint8_t j_btm = 0;
    static int scroll_top = 0;
    static int scroll_btm = 0;

    j_top += 4;
    j_btm += 4;
    scroll_top++;
    scroll_btm++;

    // =========================
    // CLEAR BUFFERS
    // =========================
    for (int i = 0; i < LED_TOP_COUNT; i++)
        ledstring.channel[0].leds[i] = 0x000000;

    for (int i = 0; i < LED_BTM_COUNT; i++)
        ledstring.channel[1].leds[i] = 0x000000;

    // =========================
    // TOP
    // =========================
    {
        uint8_t k = j_top;
        int half = (LED_TOP_COUNT + 1) / 2;

        for (int i = 0; i < half; i++) {
            uint32_t c = CHSV_to_RGB(k, 255, 255);
            k += 8;

            if (((i + scroll_top) % 5) == 0)
                c = 0x000000;

            int left  = i;
            int right = LED_TOP_COUNT - 1 - i;

            ledstring.channel[0].leds[left]  = c;
            ledstring.channel[0].leds[right] = c;
        }
    }

    // =========================
    // BTM
    // =========================
    {
        uint8_t k = j_btm;
        int half = (LED_BTM_COUNT + 1) / 2;

        for (int i = 0; i < half; i++) {
            uint32_t c = CHSV_to_RGB(k, 255, 255);
            k += 8;

            if (((i + scroll_btm) % 5) == 0)
                c = 0x000000;

            int left  = i;
            int right = LED_BTM_COUNT - 1 - i;

            ledstring.channel[1].leds[left]  = c;
            ledstring.channel[1].leds[right] = c;
        }
    }
}

void effect_rainbow_with_glitter() {
    for (int i = 0; i < LED_TOP_COUNT; ++i) {
        uint8_t hue = (gHue + i * 7) & 0xFF;
        ledstring.channel[0].leds[i] = CHSV_to_RGB(hue, 255, 160);
        ledstring.channel[1].leds[mapTopToBtm(i)] = CHSV_to_RGB(hue, 255, 160);
    }
    if ((rand() & 0xFF) < 20) {
        int p = rand() % LED_TOP_COUNT;
        ledstring.channel[0].leds[p] = 0xFFFFFF;
        ledstring.channel[1].leds[mapTopToBtm(p)] = 0xFFFFFF;
    }
    gHue++;
}


// Knight Rider effect - time-based fade
void effect_knightRider() {

    // =========================
    // TOP STRIP
    // =========================
    static int pos_top = 55;		// manual = start_btm
    static int dir_top = 1;
    static int trailLen_top = 30;
    static bool shrinking_top = false;
    static uint8_t brightness_top[256] = {0};

    const int start_top = 55;		// manual
    const int end_top   = 142;		// manual
    const int maxTrail  = 30;
    const uint8_t hue   = 0;
    const uint8_t fadeStep = 4;

    // clear TOP outside active range
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        if (i < start_top || i > end_top) {
            ledstring.channel[0].leds[i] = 0x000000;
            brightness_top[i] = 0;
        }
     }


    // fade TOP
    for (int i = start_top; i <= end_top; i++) {
        if (brightness_top[i] > fadeStep)
            brightness_top[i] -= fadeStep;
        else
            brightness_top[i] = 0;

        ledstring.channel[0].leds[i] =
            CHSV_to_RGB(hue, 255, brightness_top[i]);
    }

    // head TOP
    brightness_top[pos_top] = 255;
    ledstring.channel[0].leds[pos_top] =
        CHSV_to_RGB(hue, 255, 255);

    // edge detect TOP
    if (!shrinking_top) {
        if ((dir_top > 0 && pos_top >= end_top) ||
            (dir_top < 0 && pos_top <= start_top)) {
            shrinking_top = true;
        }
    }

    // move TOP
    pos_top += dir_top;

    // trail control TOP
    if (shrinking_top) {
        if (trailLen_top > 1) {
            trailLen_top--;
        } else {
            dir_top = -dir_top;
            shrinking_top = false;
        }
    } else {
        if (trailLen_top < maxTrail)
            trailLen_top++;
    }

    // clamp TOP
    if (pos_top > end_top)   pos_top = end_top;
    if (pos_top < start_top) pos_top = start_top;


    // =========================
    // BTM STRIP
    // =========================
    static int pos_btm = 25;      // manual = start_btm
    static int dir_btm = 1;
    static int trailLen_btm = 30;
    static bool shrinking_btm = false;
    static uint8_t brightness_btm[256] = {0};

    const int start_btm = 25;     // manual
    const int end_btm   = LED_BTM_COUNT;    // manual

    // fade BTM
    for (int i = start_btm; i <= end_btm; i++) {
        if (brightness_btm[i] > fadeStep)
            brightness_btm[i] -= fadeStep;
        else
            brightness_btm[i] = 0;

        ledstring.channel[1].leds[i] =
            CHSV_to_RGB(hue, 255, brightness_btm[i]);
    }

    // head BTM
    brightness_btm[pos_btm] = 255;
    ledstring.channel[1].leds[pos_btm] =
        CHSV_to_RGB(hue, 255, 255);

    // edge detect BTM
    if (!shrinking_btm) {
        if ((dir_btm > 0 && pos_btm >= end_btm) ||
            (dir_btm < 0 && pos_btm <= start_btm)) {
            shrinking_btm = true;
        }
    }

    // move BTM
    pos_btm += dir_btm;

    // trail control BTM
    if (shrinking_btm) {
        if (trailLen_btm > 1) {
            trailLen_btm--;
        } else {
            dir_btm = -dir_btm;
            shrinking_btm = false;
        }
    } else {
        if (trailLen_btm < maxTrail)
            trailLen_btm++;
    }

    // clamp BTM
    if (pos_btm > end_btm)   pos_btm = end_btm;
    if (pos_btm < start_btm) pos_btm = start_btm;
}



// effect_FEI - waving flag with breathing and color morph
// ---- configuration ----
#define FEI_WAVE_SPEED        5.0f     // spatial wave speed
#define FEI_WAVE_SCALE        0.23f    // spatial phase between LEDs
#define FEI_BREATH_SPEED      2.0f    // global breathing speed

#define FEI_MIN_BRIGHTNESS    0.4f
#define FEI_MAX_BRIGHTNESS    1.00f

#define FEI_COLOR_SWITCH_MS   10000		    // color morph period

// ---- colors ----
// FEI = #05c3de
#define FEI_R1  5
#define FEI_G1  195
#define FEI_B1  222

// VSB = #00b84c
#define FEI_R2  0
#define FEI_G2  184
#define FEI_B2  76

void effect_FEI() {
    static uint64_t t0 = millis();
    uint32_t now = millis();
    float t = (now - t0) * 0.001f;

    // ---- color morph (time based) ----
    float morph = (float)(now % FEI_COLOR_SWITCH_MS) / FEI_COLOR_SWITCH_MS;

    uint8_t baseR = FEI_R1 + morph * (FEI_R2 - FEI_R1);
    uint8_t baseG = FEI_G1 + morph * (FEI_G2 - FEI_G1);
    uint8_t baseB = FEI_B1 + morph * (FEI_B2 - FEI_B1);

    // ---- global breathing ----
    float breath = (sinf(t * FEI_BREATH_SPEED) + 1.0f) * 0.5f;
    float globalBrightness =
        FEI_MIN_BRIGHTNESS +
        breath * (FEI_MAX_BRIGHTNESS - FEI_MIN_BRIGHTNESS);

    // ---- per LED wave (flag motion) ----
    for (int i = 0; i < LED_TOP_COUNT; i++) {
        float wave =
            sinf(t * FEI_WAVE_SPEED + i * FEI_WAVE_SCALE);

        float local = (wave + 1.0f) * 0.5f;   // 0..1
        float brightness = globalBrightness * (0.45f + 0.55f * local);


        uint8_t r = (uint8_t)(baseR * brightness);
        uint8_t g = (uint8_t)(baseG * brightness);
        uint8_t b = (uint8_t)(baseB * brightness);

        uint32_t c = (r << 16) | (g << 8) | b;

        ledstring.channel[0].leds[i] = c;
        ledstring.channel[1].leds[mapTopToBtm(i)] = c;
    }
}




// Effects array
typedef void(*effect_fn)();
effect_fn effects[] = {
	effect_FEI,
	effect_bpm,						// normal rainbow - ma jet rainbow sem a tam -  opravit a pouzit
	effect_knightRider,				//
	//effect_juggle,				// dole ok, nahore chaos - zjemnit -  opravit a pouzit
	effect_cylon_multi,				// problem se spodkem - vizualni -  opravit a pouzit
	effect_fireworks,				//
	//effect_dot_spawner,           // problem se spodkem - problikava-  opravit a pouzit
    effect_rainbow,
	effect_comet,
	//effect_christmasSparkle,		// problem se spodkem - problikava - opravit a pouzit
    //effect_ambient_trails,
	//effect_sinelon,			    //
	effect_rainbow_waves,
	//effect_marquee,

	//effect_rotateColor_LED_palet,	// upravit paletu na zajimavou
	//effect_dualWaveCollision,		//
	// effect_confetti,				// malo a problem spodek - problikava - opravit a pouzit
	//effect_aurora,				//
	effect_rainbow_with_glitter,	//
    //effect_kometa, 				// absolutne nedela co by mela
    //effect_cylon,					// to je %x ledek... neni moc hezke
	//effect_waveSpawner,				//
    //effect_fire2012,				// nehodi se
    //effect_meteor,				//
    effect_oceanWaves,				//
    //effect_rotate_white,			// opravit smer sem a tam, ne jen jizda na jednu stranu
    effect_color_shift,				//
	//effect_starfall,				//
	//effect_matrix,					//
	//effect_policeStrobe,			// neni hezke
};
const int EFFECT_COUNT = sizeof(effects) / sizeof(effects[0]);

// ================== MAIN ==================
int main() {
    // allocate LED buffer for top
    ledstring.channel[0].leds = new uint32_t[LED_TOP_COUNT];
    for (int i = 0; i < LED_TOP_COUNT; ++i)
        ledstring.channel[0].leds[i] = 0;

    // allocate LED buffer for btm
    ledstring.channel[1].leds = new uint32_t[LED_BTM_COUNT];
    for (int i = 0; i < LED_BTM_COUNT; ++i)
        ledstring.channel[1].leds[i] = 0;


    // init WS2811
    if (ws2811_init(&ledstring) != WS2811_SUCCESS) {
        std::cerr << "ws2811_init failed!\n";
        delete[] ledstring.channel[0].leds;
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

            // render selected song effect continuously
            if (se == 1)      effect_special_happy_birthday();
            else if (se == 2) effect_special_star_wars();
            else if (se == 3) effect_special_mozart();

            ws2811_render(&ledstring);

            // reset passive + snakes state ONCE on song entry
            if (!lastSongRunning) {
                for (int i = 0; i < LED_TOP_COUNT; ++i) {
                    brightnessSum[i]  = 0;
                    hueWeightedSum[i] = 0;
                    overlapCount[i]   = 0;
                }

		for (int i = 0; i < LED_BTM_COUNT; ++i)
    		    ledstring.channel[1].leds[i] = 0;

                wasPassive = false;
                std::cout << "[MAIN] Song mode entered\n";
            }

            lastSongRunning = true;
            std::this_thread::sleep_for(milliseconds(MAIN_LOOP_MS));
            continue;   // NOTHING else may run during song
        }

        // -------------------------------------------------
        // SONG JUST ENDED - CLEAN FRAME ONCE
        // -------------------------------------------------
        if (lastSongRunning && !songRunning.load()) {
            for (int i = 0; i < LED_TOP_COUNT; ++i)
                ledstring.channel[0].leds[i] = 0;

	    for (int i = 0; i < LED_BTM_COUNT; ++i)
        	ledstring.channel[1].leds[i] = 0;

            ws2811_render(&ledstring);

            lastSongRunning = false;
            std::cout << "[MAIN] Song mode exited\n";
        }

        // -------------------------------------------------
        // NORMAL MODE (snakes + idle)
        // -------------------------------------------------

        updateSnakes();
        renderSnakesToBuffers();

        auto now = steady_clock::now();
        auto idleSec =
            duration_cast<seconds>(now - lastInputTime.load()).count();

        bool passiveMode = (idleSec > INACTIVITY_SECONDS);

        if (passiveMode) {
	// BTM: clear breath strip when entering passive mode
	    for (int i = 0; i < LED_BTM_COUNT; ++i)
    		ledstring.channel[1].leds[i] = 0;
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
            // exit passive mode cleanly
            if (wasPassive) {
                for (int i = 0; i < LED_TOP_COUNT; ++i)
                    ledstring.channel[0].leds[i] = 0;

                for (int i = 0; i < LED_TOP_COUNT; ++i) {
                    brightnessSum[i]  = 0;
                    hueWeightedSum[i] = 0;
                    overlapCount[i]   = 0;
                }

                wasPassive = false;
                std::cout << "[MAIN] Exiting passive mode\n";
            }

            composeAndShow();
	        renderGlobalBreath();


            // key-hold preview (only outside song)
            if (holdActive.load()) {
                int hk  = heldKey.load();
                int hue = heldHueInt.load();
                int origin = hk - 1;

                if (origin >= 0 && origin < LED_TOP_COUNT - 1) {
                    uint32_t col =
                        CHSV_to_RGB((uint8_t)hue,
                                    SATURATION,
                                    SNAKE_FADE_MAX);
                    ledstring.channel[0].leds[origin]   = col;
                    ledstring.channel[0].leds[origin+1] = col;
                }
            }

            ws2811_render(&ledstring);
        }

        std::this_thread::sleep_for(milliseconds(MAIN_LOOP_MS));
    }

    // ================== SHUTDOWN ==================
    reader.join();
    ws2811_fini(&ledstring);
    delete[] ledstring.channel[0].leds;
    delete[] ledstring.channel[1].leds;


    return 0;
}
