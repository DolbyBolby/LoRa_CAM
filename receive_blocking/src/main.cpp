#include <RadioLib.h>

enum State {
  RX_NODE,
  TX_NODE,
  WAIT_MSG,
  WAIT_CONFIRM,
  ERROR
};

SX1280 radio = new Module(25, 27, 2, 13);
State currentState = WAIT_MSG;

volatile bool operationDone = false;
byte dataArr[2];
unsigned long startTime = 0;
const unsigned long confirmTimeout = 300;

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  operationDone = true;
}

void setup() {
  Serial.begin(9600);

  Serial.print(F("[SX1262] Initializing ... "));
  int state = radio.begin();
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(state);
    while (true) { delay(10); }
  }
  int crc_state = radio.setCRC(2);
  if (crc_state != RADIOLIB_ERR_NONE) {
    Serial.print("setCRC failed: ");
    Serial.println(crc_state);
  }

  radio.setDio1Action(setFlag);
  radio.startReceive();
}

void loop() {

  switch(currentState) {

    // Waits for a received 2-byte command packet
    case WAIT_MSG: {
      if (operationDone) {
        operationDone = false;
        int numBytes = radio.getPacketLength();
        int radio_state = radio.readData(dataArr, numBytes);
        if (radio_state == RADIOLIB_ERR_NONE) {
          // Do not print yet — validation depends on TX confirmation
          currentState = TX_NODE;
        }
      }
      break;
    }

    // Echoes the received bytes back to the transmitter (non-blocking start)
    case TX_NODE: {
      int radio_state = radio.startTransmit(dataArr, 2);
      if (radio_state != RADIOLIB_ERR_NONE) {
        Serial.print(F("failed, code "));
        Serial.println(radio_state);
        while (true) { delay(10); }
      }
      currentState = RX_NODE;
      break;
    }

    // Waits for the echo TX to complete, then arms receive for confirm/reject
    case RX_NODE: {
      if(operationDone) {
        operationDone = false;
        int radio_state = radio.startReceive();
        if (radio_state != RADIOLIB_ERR_NONE) {
          Serial.print(F("failed, code "));
          Serial.println(radio_state);
          while (true) { delay(10); }
        }
        startTime = millis();
        currentState = WAIT_CONFIRM;
      }
      break;
    }

    // Waits for the 1-byte confirm (0xAA) or reject (0xFF) from the transmitter
    case WAIT_CONFIRM: {
      if (operationDone) {
        operationDone = false;
        byte confirm = 0;
        int numBytes = radio.getPacketLength();
        int radio_state = radio.readData(&confirm, numBytes);
        if (radio_state == RADIOLIB_ERR_NONE && confirm == 0xAA) {
          Serial.print(F("Cmd:\t"));
          Serial.print(dataArr[0]);
          Serial.print(F("\t value:\t"));
          Serial.println(dataArr[1]);
        } else {
          Serial.println(F("[REJECTED by TX]"));
        }
        memset(dataArr, 0, sizeof(dataArr));
        radio.startReceive();
        currentState = WAIT_MSG;
      } else if (millis() - startTime >= confirmTimeout) {
        Serial.println(F("[TIMEOUT waiting for confirm]"));
        memset(dataArr, 0, sizeof(dataArr));
        radio.startReceive();
        currentState = WAIT_MSG;
      }
      break;
    }

    case ERROR: {
      break;
    }
  }

}
