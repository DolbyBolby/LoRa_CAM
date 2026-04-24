#include <RadioLib.h>

//#define INITIATING_NODE

void handelSerialInput();
void logRejectedCommand();

SX1280 radio = new Module(25, 14, 2, 13);

enum State {
  WAIT_SERIAL,
  TX_NODE,
  RX_NODE,
  WAIT_ACK,
  ERROR
};

State currentState = WAIT_SERIAL;
String serialBuffer = "";

//bool transmitFlag = false;
volatile bool operationDone = false;
unsigned long startTime = millis();
unsigned long timeout = 200;

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  operationDone = true;
}

void setup() {
  Serial.begin(9600);
  Serial.print(F("[SX1262] Initializing ... "));

  int radio_state = radio.begin();
  if (radio_state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(radio_state);
    while (true) { delay(10); }
  }

  int crc_state = radio.setCRC(2);   // CRC 2 bytes
  if(crc_state != RADIOLIB_ERR_NONE) {
    Serial.print("setCRC failed: ");
    Serial.println(crc_state);
  }

  radio.setDio1Action(setFlag);
}

void loop() {

  switch(currentState) {

    case WAIT_SERIAL: {
      if(Serial.available()) handelSerialInput();
      break;
    }

    case TX_NODE: {
      if(Serial.available()) logRejectedCommand();
      int radio_state = radio.startTransmit(serialBuffer);
      if (radio_state != RADIOLIB_ERR_NONE) {
        Serial.print(F("failed transmit, "));
        Serial.println(radio_state);
        while (true) { delay(10); }
      }
      currentState = RX_NODE;
      break;
    }

    case RX_NODE: {
      if(Serial.available()) logRejectedCommand();
      if(operationDone) {
        operationDone = false; //reset flag
        int radio_state = radio.startReceive();
        if (radio_state != RADIOLIB_ERR_NONE) {
          Serial.print(F("failed receive,"));
          Serial.println(radio_state);
          while (true) { delay(10); }
        }
        currentState = WAIT_ACK;
        startTime = millis();
      }
      break;
    }

    case WAIT_ACK: {
      if(Serial.available()) logRejectedCommand();
      while(millis() - startTime < timeout){
        if(operationDone) {
          serialBuffer = "";
          int radio_state = radio.readData(serialBuffer);
          if (radio_state == RADIOLIB_ERR_NONE) {
            Serial.print(F("Data:\t\t"));
            Serial.println(serialBuffer);
          }
          currentState = WAIT_SERIAL;
          break;
        }
      }
      if(millis() - startTime >= timeout) {
        Serial.print(F("TIMEOUT, no message receive, try another ..."));
        currentState = TX_NODE;
      }
      break;
    }
    case ERROR: {
      break;
    }
  }
}  

void handelSerialInput() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      if (serialBuffer.length() > 0) {
        Serial.print("[Command accepted] ");
        Serial.println(serialBuffer);
        currentState = TX_NODE;
      }
    } else if (c != '\r') {
      serialBuffer += c;
    }
  }
}

void logRejectedCommand() {
  while (Serial.available()) {
    char c = Serial.read();
  }
  Serial.println("[Command REJECTED]");
}


 // #if defined(INITIATING_NODE)
  //   // send the first packet on this node
  //   Serial.print(F("[SX1262] Sending first packet ... "));
  //   transmissionState = radio.startTransmit("Hello World!");
  //   transmitFlag = true;
  // #else
  //   // start listening for LoRa packets on this node
  //   Serial.print(F("[SX1262] Starting to listen ... "));
  //   state = radio.startReceive();
  //   if (state == RADIOLIB_ERR_NONE) {
  //     Serial.println(F("success!"));
  //   } else {
  //     Serial.print(F("failed, code "));
  //     Serial.println(state);
  //     while (true) { delay(10); }
  //   }
  // #endif

// check if the previous operation finished
  // if(operationDone) {
  //   // reset flag
  //   operationDone = false;

  //   if(transmitFlag) {
  //     // the previous operation was transmission, listen for response
  //     // print the result
  //     if (transmissionState == RADIOLIB_ERR_NONE) {
  //       // packet was successfully sent
  //       Serial.println(F("transmission finished!"));

  //     } else {
  //       Serial.print(F("failed, code "));
  //       Serial.println(transmissionState);

  //     }

  //     // listen for response
  //     radio.startReceive();
  //     transmitFlag = false;

  //   } else {
  //     // the previous operation was reception
  //     // print data and send another packet
  //     String str;
  //     int state = radio.readData(str);

  //     if (state == RADIOLIB_ERR_NONE) {
  //       // packet was successfully received
  //       Serial.println(F("[SX1262] Received packet!"));

  //       // print data of the packet
  //       Serial.print(F("[SX1262] Data:\t\t"));
  //       Serial.println(str);

  //       // print RSSI (Received Signal Strength Indicator)
  //       Serial.print(F("[SX1262] RSSI:\t\t"));
  //       Serial.print(radio.getRSSI());
  //       Serial.println(F(" dBm"));

  //       // print SNR (Signal-to-Noise Ratio)
  //       Serial.print(F("[SX1262] SNR:\t\t"));
  //       Serial.print(radio.getSNR());
  //       Serial.println(F(" dB"));

  //     }

  //     // wait a second before transmitting again
  //     delay(1000);

  //     // send another one
  //     Serial.print(F("[SX1262] Sending another packet ... "));
  //     transmissionState = radio.startTransmit("Hello World!");
  //     transmitFlag = true;
  //   }
  
  //}
