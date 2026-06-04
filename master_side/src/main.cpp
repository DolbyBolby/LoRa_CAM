#include <RadioLib.h>

void handelSerialInput();
void logRejectedCommand();

SX1280 radio = new Module(25, 14, 2, 13);

enum State {
  WAIT_SERIAL,
  TX_NODE,
  RX_NODE,
  WAIT_ACK,
  SEND_CONFIRM,
  ERROR
};

State currentState = WAIT_SERIAL;

volatile bool operationDone = false;
unsigned long startTime = millis();
unsigned long timeout = 200;

byte dataArr[2];

// GET support: set when dataArr[1] == GET_FLAG (0xFF).
// NOTE: 0xFF cannot be used as a SEND value — it is reserved as the GET flag.
//       Valid SEND values are 0–254 (display range 0.0–25.4 with *10 encoding).
static bool isGetRequest = false;
static byte responseVal  = 0;   // stores the value returned by RX on a GET
static bool matchOk      = false;

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  operationDone = true;
}

void setup() {
  Serial.begin(9600);
  Serial.print(F("[SX1262] Initializing ... "));

  float freq = 2400;
  float bw   = 406.25;
  float sf   = 7;
  float cr   = 5;

  int radio_state = radio.begin();
  if (radio_state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(radio_state);
    while (true) { delay(10); }
  }

  int crc_state = radio.setCRC(2);
  if (crc_state != RADIOLIB_ERR_NONE) {
    Serial.print("setCRC failed: ");
    Serial.println(crc_state);
    while (true) { delay(10); }
  }

  radio.setDio1Action(setFlag);
}

void loop() {

  switch (currentState) {

    case WAIT_SERIAL: {
      if (Serial.available() >= 2) handelSerialInput();
      break;
    }

    case TX_NODE: {
      if (Serial.available()) logRejectedCommand();
      int radio_state = radio.startTransmit(dataArr, 2);
      if (radio_state != RADIOLIB_ERR_NONE) {
        Serial.print(F("failed transmit, "));
        Serial.println(radio_state);
        while (true) { delay(10); }
      }
      currentState = RX_NODE;
      break;
    }

    case RX_NODE: {
      if (Serial.available()) logRejectedCommand();
      if (operationDone) {
        operationDone = false;
        int radio_state = radio.startReceive();
        if (radio_state != RADIOLIB_ERR_NONE) {
          Serial.print(F("failed receive, "));
          Serial.println(radio_state);
          while (true) { delay(10); }
        }
        currentState = WAIT_ACK;
        startTime = millis();
      }
      break;
    }

    case WAIT_ACK: {
      if (Serial.available()) logRejectedCommand();
      while (millis() - startTime < timeout) {
        if (operationDone) {
          operationDone = false;
          byte echoArr[2] = {0, 0};
          int numBytes     = radio.getPacketLength();
          int radio_state  = radio.readData(echoArr, numBytes);
          if (radio_state == RADIOLIB_ERR_NONE && numBytes >= 2) {
            if (dataArr[1] == 0xFF) {
              // GET response: RX replied [cmd, stored_value].
              // Only the cmd byte is compared; the val byte IS the answer.
              isGetRequest = true;
              responseVal  = echoArr[1];
              matchOk      = (echoArr[0] == dataArr[0]);
            } else {
              // SEND echo: both bytes must match exactly.
              isGetRequest = false;
              matchOk = (echoArr[0] == dataArr[0] && echoArr[1] == dataArr[1]);
            }
            byte confirm = matchOk ? 0xAA : 0xFF;
            radio.startTransmit(&confirm, 1);
            currentState = SEND_CONFIRM;
          } else {
            // Bad read — retry transmission
            currentState = TX_NODE;
          }
          break;
        }
      }
      if (millis() - startTime >= timeout) {
        Serial.println(F("TIMEOUT, no message received, retrying..."));
        currentState = TX_NODE;
      }
      break;
    }

    case SEND_CONFIRM: {
      if (Serial.available()) logRejectedCommand();
      if (operationDone) {
        operationDone = false;
        if (matchOk) {
          if (isGetRequest) {
            // Format: "GET:[opcode]:[raw_value]" — parsed by CLI
            Serial.print(F("GET:"));
            Serial.print(dataArr[0]);
            Serial.print(F(":"));
            Serial.println(responseVal);
          } else {
            Serial.println(F("[ACK OK] Confirmation 0xAA sent"));
          }
          currentState = WAIT_SERIAL;
        } else {
          Serial.println(F("[MISMATCH] Rejection 0xFF sent, retransmitting..."));
          currentState = TX_NODE;
        }
      }
      break;
    }

    case ERROR: {
      break;
    }
  }
}

void handelSerialInput() {
  byte cmd   = Serial.read();
  byte value = Serial.read();
  dataArr[0] = cmd;
  dataArr[1] = value;

  if (value == 0xFF) {
    Serial.print(F("[GET request] cmd="));
    Serial.println(cmd);
  } else {
    Serial.print(F("[Command accepted] cmd="));
    Serial.print(dataArr[0]);
    Serial.print(F(" value="));
    Serial.println(dataArr[1]);
  }

  currentState = TX_NODE;
}

void logRejectedCommand() {
  while (Serial.available()) {
    Serial.read();
  }
  Serial.println(F("[Command REJECTED]"));
}
