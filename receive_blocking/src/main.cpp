#include <RadioLib.h>

SX1280 radio = new Module(25, 27, 2, 13);  // NSS, DIO1, RST, BUSY

volatile bool operationDone = false;
bool          sweepDone     = false;

// Payload buffer
String buffer = "";

// Composition courante (mise à jour à chaque SYNC)
int  compId  = 0;
char compSf[8]  = "";
char compBw[16] = "";
char compCr[8]  = "";

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  operationDone = true;
}

// ---- Convertit "203"/"406"/"812"/"1625" → float kHz pour RadioLib ----
float bwToFloat(const char* bw) {
  int v = atoi(bw);
  if (v == 203)  return 203.125f;
  if (v == 406)  return 406.25f;
  if (v == 812)  return 812.5f;
  if (v == 1625) return 1625.0f;
  return 812.5f;
}

// ---- Convertit "4/5"→5, "4/6"→6, etc. pour setCodingRate() ----
int crToInt(const char* cr) {
  const char* slash = strchr(cr, '/');
  return slash ? atoi(slash + 1) : 5;
}

// ---- Parse "SYNC|SF:7|BW:812|CR:4/5" → sf/bw/cr ----
void parseSync(const char* msg, char* sf, char* bw, char* cr) {
  // msg = "SYNC|SF:7|BW:812|CR:4/5"
  const char* p = strstr(msg, "SF:");
  if (p) {
    p += 3;
    const char* end = strchr(p, '|');
    int len = end ? (int)(end - p) : strlen(p);
    strncpy(sf, p, len); sf[len] = '\0';
  }
  p = strstr(msg, "BW:");
  if (p) {
    p += 3;
    const char* end = strchr(p, '|');
    int len = end ? (int)(end - p) : strlen(p);
    strncpy(bw, p, len); bw[len] = '\0';
  }
  p = strstr(msg, "CR:");
  if (p) {
    p += 3;
    strncpy(cr, p, 7); cr[7] = '\0';
  }
}

// ---- Parse "PKT|{seq}|..." → numéro de séquence ----
int parsePktSeq(const char* msg) {
  // msg = "PKT|42|SF:..."
  const char* p = msg + 4; // après "PKT|"
  return atoi(p);
}

// ---- Gère un message SYNC ----
void handleSync(const String& msg) {
  char sf_new[8] = "", bw_new[16] = "", cr_new[8] = "";
  char buf[64];
  msg.toCharArray(buf, sizeof(buf));
  parseSync(buf, sf_new, bw_new, cr_new);

  // Dédoublonnage : ignorer les SYNC redondants (même composition)
  if (strcmp(sf_new, compSf) == 0 &&
      strcmp(bw_new, compBw) == 0 &&
      strcmp(cr_new, compCr) == 0) {
    radio.startReceive();
    return;
  }

  // Nouvelle composition
  compId++;
  strncpy(compSf, sf_new, sizeof(compSf));
  strncpy(compBw, bw_new, sizeof(compBw));
  strncpy(compCr, cr_new, sizeof(compCr));

  // Signaler au data_logger
  Serial.print(F("COMP_START|"));
  Serial.print(compId);   Serial.print('|');
  Serial.print(compSf);   Serial.print('|');
  Serial.print(compBw);   Serial.print('|');
  Serial.println(compCr);

  // Reconfigurer le radio sur les nouveaux paramètres
  radio.setSpreadingFactor(atoi(sf_new));
  radio.setBandwidth(bwToFloat(bw_new));
  radio.setCodingRate(crToInt(cr_new));

  radio.startReceive();
}

// ---- Gère un paquet de mesure PKT ----
void handlePkt(const String& msg, float rssi, float snr, float freqErr) {
  char buf[64];
  msg.toCharArray(buf, sizeof(buf));
  int seq = parsePktSeq(buf);

  // Format parseable par data_logger.py
  Serial.print(F("PKT_RX|"));
  Serial.print(compId);  Serial.print('|');
  Serial.print(seq);     Serial.print('|');
  Serial.print(rssi, 2); Serial.print('|');
  Serial.print(snr, 2);  Serial.print('|');
  Serial.println(freqErr, 2);

  radio.startReceive();
}

void setup() {
  Serial.begin(9600);
  buffer.reserve(64);

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
  radio.startReceive();
  Serial.println(F("[RX] En attente du sweep..."));
}

void loop() {
  if (sweepDone || !operationDone) return;
  operationDone = false;

  int state = radio.readData(buffer);
  if (state != RADIOLIB_ERR_NONE) {
    // Erreur CRC ou autre (paquet corrompu) → relancer l'écoute
    radio.startReceive();
    return;
  }

  float rssi    = radio.getRSSI();
  float snr     = radio.getSNR();
  float freqErr = radio.getFrequencyError();

  if (buffer.startsWith("SYNC|")) {
    handleSync(buffer);                          // startReceive() appelé dedans

  } else if (buffer.startsWith("PKT|")) {
    handlePkt(buffer, rssi, snr, freqErr);       // startReceive() appelé dedans

  } else if (buffer == "SWEEP_COMPLETE") {
    sweepDone = true;
    Serial.println(F("SWEEP_DONE"));
    // Ne pas relancer startReceive : le sweep est terminé

  } else {
    radio.startReceive();
  }
}
