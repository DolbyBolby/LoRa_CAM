#include <RadioLib.h>

// ---- Timing constants (ms) ----
#define SYNC_COUNT          2      // Nombre de SYNC envoyés avant chaque composition
#define SYNC_DELAY_MS       200    // Délai entre deux SYNC
#define SYNC_STABILIZE_MS   1000  // Attente après SYNC pour laisser le RX changer de config
#define INTER_PACKET_MS     100   // Délai minimum entre deux paquets de mesure
#define COOLDOWN_MS         1000  // Refroidissement après les paquets
#define TX_TIMEOUT_MS       15000 // Timeout max pour l'interruption TX (SF12 peut dépasser 5s)
#define PACKETS_PER_COMP    50    // Paquets de mesure par composition

SX1280 radio = new Module(25, 14, 2, 13);  // NSS, DIO1, RST, BUSY

volatile bool operationDone = false;

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  operationDone = true;
}

// ---- Tables de paramètres (ordre croissant) ----
const int   SFS[]    = {5, 6, 7, 8, 9, 10, 11, 12};
const float BWS[]    = {203.125, 406.25, 812.5, 1625.0};
const int   CRS[]    = {5, 6, 7, 8};            // 4/5, 4/6, 4/7, 4/8 (notation RadioLib)
const char* BW_STR[] = {"203", "406", "812", "1625"};
const char* CR_STR[] = {"4/5", "4/6", "4/7", "4/8"};

const int N_SF = 8, N_BW = 4, N_CR = 4;

// ---- Attend la fin d'une transmission (interrupt-driven) ----
bool waitForTx() {
  unsigned long start = millis();
  while (!operationDone) {
    if (millis() - start > TX_TIMEOUT_MS) {
      Serial.println(F("[TX] TIMEOUT"));
      operationDone = false;
      return false;
    }
  }
  operationDone = false;
  return true;
}

bool sendMsg(const char* msg) {
  int state = radio.startTransmit(msg);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print(F("[TX] startTransmit error: "));
    Serial.println(state);
    return false;
  }
  return waitForTx();
}

// ---- Reconfigure le radio sur une nouvelle composition ----
bool configureRadio(int sf, float bw, int cr) {
  int e1 = radio.setSpreadingFactor(sf);
  int e2 = radio.setBandwidth(bw);
  int e3 = radio.setCodingRate(cr);
  if (e1 || e2 || e3) {
    Serial.printf("[TX] Config error: SF=%d(%d) BW=%.1f(%d) CR=%d(%d)\n",
                  sf, e1, bw, e2, cr, e3);
    return false;
  }
  return true;
}

void setup() {
  Serial.begin(9600);

  Serial.print(F("[SX1280] Init ... "));
  int state = radio.begin();
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("OK"));
  } else {
    Serial.printf("FAIL (code %d)\n", state);
    while (true) { delay(10); }
  }

  radio.setCRC(2);
  radio.setDio1Action(setFlag);

  // Estimation durée totale (borne inférieure — le temps on-air SF12 allonge réellement)
  long n = (long)N_SF * N_BW * N_CR;
  long secs = n * (SYNC_STABILIZE_MS / 1000
                   + (long)PACKETS_PER_COMP * INTER_PACKET_MS / 1000
                   + COOLDOWN_MS / 1000);
  Serial.printf("[SWEEP] %ld compositions — durée estimée >= %ldh %ldmin\n",
                n, secs / 3600, (secs % 3600) / 60);

  // Compte à rebours : laisse le temps de lancer le script Python sur le PC
  Serial.println(F("[SWEEP] Demarrage dans 10s — lancez 'python main.py sweep-log' maintenant"));
  for (int i = 10; i > 0; i--) {
    Serial.printf("  %d...\n", i);
    delay(1000);
  }
  Serial.println(F("[SWEEP] GO !"));

  // ================================================================
  // SWEEP PRINCIPAL
  // ================================================================
  int compId = 0;

  for (int si = 0; si < N_SF; si++) {
    for (int bi = 0; bi < N_BW; bi++) {
      for (int ci = 0; ci < N_CR; ci++) {
        compId++;
        int   sf = SFS[si];
        float bw = BWS[bi];
        int   cr = CRS[ci];

        Serial.printf("\n[COMP %d/%ld] SF%d BW%s CR%s\n",
                      compId, n, sf, BW_STR[bi], CR_STR[ci]);

        // -- 1. Envoyer SYNC à l'ancienne config (RX est encore dessus) --
        char sync_msg[64];
        snprintf(sync_msg, sizeof(sync_msg),
                 "SYNC|SF:%d|BW:%s|CR:%s", sf, BW_STR[bi], CR_STR[ci]);

        for (int s = 0; s < SYNC_COUNT; s++) {
          sendMsg(sync_msg);
          if (s < SYNC_COUNT - 1) delay(SYNC_DELAY_MS);
        }

        // -- 2. Basculer sur la nouvelle config --
        if (!configureRadio(sf, bw, cr)) {
          Serial.println(F("[TX] Composition ignorée (config impossible)"));
          continue;
        }

        // -- 3. Stabilisation : laisser le RX switcher et se stabiliser --
        delay(SYNC_STABILIZE_MS);

        // -- 4. Envoyer les paquets de mesure --
        bool compFailed = false;
        for (int pkt = 0; pkt < PACKETS_PER_COMP; pkt++) {
          char pkt_msg[64];
          snprintf(pkt_msg, sizeof(pkt_msg),
                   "PKT|%d|SF:%d|BW:%s|CR:%s", pkt, sf, BW_STR[bi], CR_STR[ci]);

          bool ok = sendMsg(pkt_msg);
          Serial.printf("  [%3d/%d]%s\n", pkt + 1, PACKETS_PER_COMP,
                        ok ? "" : " FAIL");
          delay(INTER_PACKET_MS);
        }

        // -- 5. Cooldown avant la prochaine composition --
        Serial.println(F("[TX] Cooldown..."));
        delay(COOLDOWN_MS);
      }
    }
  }

  // -- Fin du sweep : signaler le RX (à la config de la dernière composition) --
  for (int s = 0; s < SYNC_COUNT; s++) {
    sendMsg("SWEEP_COMPLETE");
    if (s < SYNC_COUNT - 1) delay(SYNC_DELAY_MS);
  }
  Serial.println(F("\n[SWEEP] Terminé!"));
}

void loop() {
  // Tout le sweep se passe dans setup(); rien ici.
}
