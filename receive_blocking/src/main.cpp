#include <RadioLib.h>

enum State {
  RX_NODE,
  TX_NODE,
  WAIT_MSG,
  ERROR
};

SX1280 radio = new Module(25, 27, 2, 13);
State currentState = WAIT_MSG;
//String buffer = "";


volatile bool operationDone = false;
byte dataArr[2];

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  // we sent or received a packet, set the flag
  operationDone = true;
}

void setup() {
  Serial.begin(9600);

  // initialize SX1262 with default settings
  Serial.print(F("[SX1262] Initializing ... "));
  int state = radio.begin();
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(state);
    while (true) { delay(10); }
  }
  int crc_state = radio.setCRC(2);   // CRC 2 bytes
  if (crc_state != RADIOLIB_ERR_NONE) {
    Serial.print("setCRC failed: ");
    Serial.println(crc_state);
  }

  radio.setDio1Action(setFlag);
  radio.startReceive();
}

void loop() {

  switch(currentState) {

    case RX_NODE: {
      if(operationDone) {
        operationDone = false;
        int radio_state = radio.startReceive();
        if (radio_state != RADIOLIB_ERR_NONE) {
            Serial.print(F("failed, code "));
            Serial.println(radio_state);
            while (true) { delay(10); }
          }
          currentState = WAIT_MSG;
      }
      break;
    }

    case WAIT_MSG: {
      if (operationDone) {
        operationDone = false;
        int numBytes = radio.getPacketLength();
        int radio_state = radio.readData(dataArr, numBytes);
        if (radio_state == RADIOLIB_ERR_NONE) {
          Serial.print(F("Cmd:\t"));
          Serial.print(dataArr[0]);
          Serial.print(F("\t value:\t"));
          Serial.println(dataArr[1]);
          
        }
        currentState = TX_NODE;
        
      }
      break;
    }

     case TX_NODE: {
      int radio_state = radio.startTransmit(dataArr,2);
      if (radio_state != RADIOLIB_ERR_NONE) {
          Serial.print(F("failed, code "));
          Serial.println(radio_state);
          while (true) { delay(10); }
        }
      memset(dataArr, 0, sizeof(dataArr));
      currentState = RX_NODE;
      break;
    }

    case ERROR: {
      break;
    }
  }
  
}
