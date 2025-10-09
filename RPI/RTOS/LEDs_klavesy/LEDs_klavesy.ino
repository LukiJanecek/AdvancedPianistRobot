#include <FastLED.h>

// ---------- HW / LED nastavení ----------
#define NUM_LEDS 150           // počet LED na pásku - uprav podle potřeby
#define DATA_PIN 5             // pin, kam je připojen datový vodič LED pásku
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

CRGB leds[NUM_LEDS];

// ---------- Parametry hadů (lze upravit) ----------
#define MAX_SNAKES 16          // max souběžně aktivních hadů
#define SNAKE_LENGTH 4         // počet LED na každé straně "had" (v zadání 4)
#define SNAKE_STEP_MS 80       // čas mezi kroky jednoho hada (ms)
#define SNAKE_FADE_MIN 50      // nejnižší jas (tail)
#define SNAKE_FADE_MAX 255     // nejvyšší jas (head)
#define HUE_SHIFT_PER_OVERLAP 30 // přičtení hue pokud se na LED sejde víc hadů (pro 2 hadi +30, pro 3 +60,...)
#define SATURATION 230         // sytost výsledné barvy (0..255)

// ---------- Datové struktury ----------
struct Snake {
  bool active = false;
  int origin = 0;            // centrum (index LED)
  int step = 0;              // kolik kroků už had udělal; step==0 => pouze střed
  int length = SNAKE_LENGTH; // délka hadího ramene
  uint8_t hue = 0;           // základní barva hada (0..255)
  unsigned long lastUpdate = 0;
  unsigned long stepInterval = SNAKE_STEP_MS;
};

Snake snakes[MAX_SNAKES];

// Pomocné buffery pro skládání příspěvků jednotlivých hadů na každé LED
// Používáme vážený průměr barev podle jasu.
uint16_t brightnessSum[NUM_LEDS];     // součet jasů (0..65535)
uint32_t hueWeightedSum[NUM_LEDS];    // součet (hue * brightness)
uint8_t overlapCount[NUM_LEDS];       // kolik hadů ovlivnilo tuto LED

// ---------- Helpery ----------
uint8_t hue8_to_0_255(int h) {
  // safe convert, modular
  return (uint8_t)(h & 0xFF);
}

// map brightness lineárně od vzdálenosti (0..length-1) -> [SNAKE_FADE_MAX .. SNAKE_FADE_MIN]
uint8_t brightnessForDistance(int dist, int length) {
  if (dist < 0 || dist >= length) return 0;
  if (length <= 1) return SNAKE_FADE_MAX;
  // lineární interp
  int b = SNAKE_FADE_MAX - ((SNAKE_FADE_MAX - SNAKE_FADE_MIN) * dist) / (length - 1);
  if (b < 0) b = 0;
  if (b > 255) b = 255;
  return (uint8_t)b;
}

// spawn nového hada; hue = 0..255 (pokud nechceš specifikovat, použij random8())
bool spawnSnake(int originIndex, uint8_t hue = 0) {
  if (originIndex < 0 || originIndex >= NUM_LEDS) return false;
  // najdi volný slot
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
  // žádný volný slot
  return false;
}

// ukonči hada (interně)
void killSnake(int idx) {
  snakes[idx].active = false;
}

// ---------- update logiky hadů (pseudoparalelismus) ----------
void updateSnakes() {
  unsigned long now = millis();
  for (int s = 0; s < MAX_SNAKES; ++s) {
    if (!snakes[s].active) continue;
    // posun hadího kroku podle intervalu
    if (now - snakes[s].lastUpdate >= snakes[s].stepInterval) {
      snakes[s].lastUpdate = now;
      snakes[s].step++; // had se posune o jeden krok ven
      // ukonči hada pokud už jeho rameno vyšlo z pásku na obou stranách
      int furthestLeft = snakes[s].origin - snakes[s].step - (snakes[s].length - 1);
      int furthestRight = snakes[s].origin + snakes[s].step + (snakes[s].length - 1);
      if (furthestLeft < 0 && furthestRight >= NUM_LEDS) {
        // celý had opustil pás
        killSnake(s);
      }
    }
  }
}

// ---------- vykreslení všech hadů do bufferů a skládání výsledku ----------
void renderSnakesToBuffers() {
  // vyčisti buffery
  for (int i = 0; i < NUM_LEDS; ++i) {
    brightnessSum[i] = 0;
    hueWeightedSum[i] = 0;
    overlapCount[i] = 0;
  }

  // projdi všechny hady a přidej jejich příspěvky
  for (int s = 0; s < MAX_SNAKES; ++s) {
    if (!snakes[s].active) continue;
    int origin = snakes[s].origin;
    int step = snakes[s].step;
    int len = snakes[s].length;
    uint8_t hue = snakes[s].hue;

    // Speciální: když step == 0 -> jen rozsvícený střed
    if (step == 0) {
      if (origin >= 0 && origin < NUM_LEDS) {
        uint8_t b = brightnessForDistance(0, len);
        brightnessSum[origin] += b;
        hueWeightedSum[origin] += (uint32_t)hue * b;
        overlapCount[origin] += 1;
      }
      continue;
    }

    // pro každou stranu (left = -1, right = +1) přidej ramena
    for (int dir = -1; dir <= 1; dir += 2) {
      for (int d = 0; d < len; ++d) {
        // pozice = origin + (step - d) * dir
        int pos = origin + (step - d) * dir;
        if (pos < 0 || pos >= NUM_LEDS) continue;
        uint8_t b = brightnessForDistance(d, len);
        if (b == 0) continue;
        brightnessSum[pos] += b;
        hueWeightedSum[pos] += (uint32_t)hue * b;
        overlapCount[pos] += 1;
      }
    }

    // volitelně můžeme také/nebo rozsvítit "head" na vzdálenost step (když step>0)
    // → už pokryto smyčkami výše (d=0 => head)
  }
}

// ---------- finální skládání a vykreslení do leds[] ----------
void composeAndShow() {
  for (int i = 0; i < NUM_LEDS; ++i) {
    if (overlapCount[i] == 0 || brightnessSum[i] == 0) {
      leds[i] = CRGB::Black;
      continue;
    }
    // vážený průměr hue podle jasu příspěvků
    uint16_t totalB = brightnessSum[i]; // 16-bit
    // average hue in 0..255:
    uint8_t avgHue = (uint8_t)(hueWeightedSum[i] / totalB);

    // posun hue podle overlapCount: (count - 1) * HUE_SHIFT_PER_OVERLAP
    int shift = (int)(overlapCount[i] - 1) * HUE_SHIFT_PER_OVERLAP;
    int finalHue = (avgHue + shift) & 0xFF;

    // jas: omezíme max 255 (může se sčítat)
    uint16_t b = totalB;
    if (b > 255) b = 255;

    // použij CHSV -> převedeno FastLED
    CHSV hsv(finalHue, SATURATION, (uint8_t)b);
    leds[i] = hsv; // FastLED provede konverzi
  }

  FastLED.show();
}

// ---------- Setup / Loop ----------
void setup() {
  Serial.begin(115200);
  delay(100);
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.clear(true);

  // Příklad: spawn několika testovacích hadů při startu (odstraň když nechceš)
  // spawnSnake(10, random8()); // náhodná barva
  // spawnSnake(40, 32);
}

unsigned long lastRender = 0;
const unsigned long RENDER_INTERVAL = 20; // ms mezi redraw (měň dle potřeby)

void loop() {
  // --- Zpracuj dotazy ze sériového portu (pošli číslo indexu) ---
  if (Serial.available()) {
    String s = Serial.readStringUntil('\n');
    s.trim();
    if (s.length()) {
      int idx = s.toInt();
      if (idx >= 0 && idx < NUM_LEDS) {
        uint8_t hue = random8(); // default: náhodná barva; můžeš upravit
        if (!spawnSnake(idx, hue)) {
          Serial.println("Nenalezen volný slot pro nového hada.");
        } else {
          Serial.print("Spawned snake at ");
          Serial.println(idx);
        }
      } else {
        Serial.print("Index mimo rozsah: ");
        Serial.println(s);
      }
    }
  }

  // --- aktualizace logiky hadů (pseudoparalelismus) ---
  updateSnakes();

  // --- render (bufferování + show) ---
  unsigned long now = millis();
  if (now - lastRender >= RENDER_INTERVAL) {
    lastRender = now;
    renderSnakesToBuffers();
    composeAndShow();
  }
}
