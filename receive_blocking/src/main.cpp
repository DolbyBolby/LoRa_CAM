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

// #if defined(INITIATING_NODE)
//     // send the first packet on this node
//     Serial.print(F("[SX1262] Sending first packet ... "));
//     transmissionState = radio.startTransmit("Hello World!");
//     transmitFlag = true;
//   #else
//     // start listening for LoRa packets on this node
//     Serial.print(F("[SX1262] Starting to listen ... "));
//     state = radio.startReceive();
//     if (state == RADIOLIB_ERR_NONE) {
//       Serial.println(F("success!"));
//     } else {
//       Serial.print(F("failed, code "));
//       Serial.println(state);
//       while (true) { delay(10); }
//     }
//   #endif

// // check if the previous operation finished
//   if(operationDone) {
//     // reset flag
//     operationDone = false;

//     if(transmitFlag) {
//       // the previous operation was transmission, listen for response
//       // print the result
//       if (transmissionState == RADIOLIB_ERR_NONE) {
//         // packet was successfully sent
//         Serial.println(F("transmission finished!"));

//       } else {
//         Serial.print(F("failed, code "));
//         Serial.println(transmissionState);

//       }

//       // listen for response
//       radio.startReceive();
//       transmitFlag = false;

//     } else {
//       // the previous operation was reception
//       // print data and send another packet
//       String str;
//       int state = radio.readData(str);

//       if (state == RADIOLIB_ERR_NONE) {
//         // packet was successfully received
//         Serial.println(F("[SX1262] Received packet!"));

//         // print data of the packet
//         Serial.print(F("[SX1262] Data:\t\t"));
//         Serial.println(str);

//         // print RSSI (Received Signal Strength Indicator)
//         Serial.print(F("[SX1262] RSSI:\t\t"));
//         Serial.print(radio.getRSSI());
//         Serial.println(F(" dBm"));

//         // print SNR (Signal-to-Noise Ratio)
//         Serial.print(F("[SX1262] SNR:\t\t"));
//         Serial.print(radio.getSNR());
//         Serial.println(F(" dB"));

//       }

//       // wait a second before transmitting again
//       delay(1000);

//       // send another one
//       Serial.print(F("[SX1262] Sending another packet ... "));
//       transmissionState = radio.startTransmit("Hello World!");
//       transmitFlag = true;
//     }
  
//   }