#include <RadioLib.h>

enum State {
  RX_NODE,
  TX_NODE,
  WAIT_MSG,
  ERROR
};

SX1280 radio = new Module(25, 27, 2, 13);
State currentState = WAIT_MSG;
String buffer = "";

volatile bool operationDone = false;

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
        int radio_state = radio.readData(buffer);
        if (radio_state == RADIOLIB_ERR_NONE) {
          Serial.print(F("Data:\t\t"));
          Serial.println(buffer);

          // print RSSI (Received Signal Strength Indicator)
          Serial.print(F("[SX1280] RSSI:\t\t"));
          Serial.print(radio.getRSSI());
          Serial.println(F(" dBm"));

          // print SNR (Signal-to-Noise Ratio)
          Serial.print(F("[SX1280] SNR:\t\t"));
          Serial.print(radio.getSNR());
          Serial.println(F(" dB"));

          // print the Frequency Error
          // of the last received packet
          Serial.print(F("[SX1280] Frequency Error:\t"));
          Serial.print(radio.getFrequencyError());
          Serial.println(F(" Hz"));
        }
        if(buffer != "[INIT]") {
          currentState = TX_NODE;
          delay(100);
        }
        
      }
      break;
    }

     case TX_NODE: {
      int radio_state = radio.startTransmit(buffer);
      if (radio_state != RADIOLIB_ERR_NONE) {
          Serial.print(F("failed, code "));
          Serial.println(radio_state);
          while (true) { delay(10); }
        }
      buffer = "";
      currentState = RX_NODE;
      break;
    }

    case ERROR: {
      break;
    }
  }
  
}

