#include <Arduino.h>
#include <RadioLib.h>


SPIClass spi(VSPI);
SPISettings spiSettings(8000000, MSBFIRST, SPI_MODE0);
SX1280 radio = new Module(25, 14, 2, 13, spi, spiSettings);
//SX1281 radio = new Module(25, 27, 2, 13);


// save transmission state between loops
int transmissionState = RADIOLIB_ERR_NONE;

// flag to indicate that a packet was sent
volatile bool transmittedFlag = false;
volatile bool receivedFlag = false;

enum States {
  WAIT_CMD,
  TX_MOD,
  WAIT_ACK
};

States states = WAIT_CMD;

#if defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setTransmitFlag(void) {
  transmittedFlag = true;
}

#if defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setReceivedFlag(void) {
  receivedFlag = true;
}

// String buffer for serial data
String serialBuffer = "";

float freq = 2450.0;
float bw = 203.125;
uint8_t sf = 12;
uint8_t cr = 7;
uint8_t syncW = RADIOLIB_SX128X_SYNC_WORD_PRIVATE;
int8_t pwr = 10;
uint16_t pl = 12;  

void setup() {
  Serial.begin(9600);

  // Initialize SX1280 with default settings
  Serial.print(F("[SX1280] Initializing ... "));
  spi.begin(18,19,23,25);
  int state = radio.begin(freq,bw,sf,cr,syncW,pwr,pl);
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(state);
    while (true) { delay(10); }
  }

  radio.setPacketSentAction(setTransmitFlag);
}

void loop() {
  // Lecture des données du port série
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      // String complète reçue
      if (serialBuffer.length() > 0) {
        // Serial.print(F("[Serial] Received: "));
        // Serial.println(serialBuffer);
        
        // Utiliser la string reçue pour la transmission radio
        //Serial.print(F("[SX1280] Sending via radio: "));
        //Serial.println(serialBuffer);

        transmissionState = radio.startTransmit(serialBuffer);
        // Vider le buffer
        serialBuffer = "";
      }
    } else if (c != '\r') {
      // Ajouter le caractère au buffer
      serialBuffer += c;
    }
  }

  // uint32_t irqFlags = radio.getIrqFlags();
  // Serial.print("IRQ Flags: 0x");
  // Serial.println(irqFlags, HEX);

  // if (irqFlags & (1UL << RADIOLIB_IRQ_TX_DONE)) {
  //   Serial.println("TX_DONE flag detected!");
  // }
  // if (irqFlags & (1UL << RADIOLIB_IRQ_RX_DONE)) {
  //   Serial.println("RX_DONE flag detected!");
  // }

  // check if the previous transmission finished
  if(transmittedFlag) {
    // reset flag
    transmittedFlag = false;
    if (transmissionState == RADIOLIB_ERR_NONE) {
      // packet was successfully sent
      Serial.print(F("transmission finished!"));
    } else {
      Serial.print(F("failed, code "));
      Serial.println(transmissionState);
    }
    radio.finishTransmit();
    radio.clearPacketSentAction();
    radio.setPacketReceivedAction(setReceivedFlag);
    int rxState = radio.startReceive(); 
    Serial.print(F("startReceive"));                              
    if(rxState != RADIOLIB_ERR_NONE) {
      Serial.print("startReceive failed, code ");
      Serial.println(rxState);
      //exchangeInProgress = false;
    }
  }

  if(receivedFlag) {
    receivedFlag = false;
    String ack;
    int receptionState = radio.readData(ack);
    if(receptionState == RADIOLIB_ERR_NONE) {
      if(ack == "ACK") {
        Serial.println("ACK received");
      } else {
        Serial.print("Unexpected response: ");
        Serial.println(ack);
      }
      // Serial.print(F("from receiver to transmitter : "));
      // Serial.println(ack);
    }else{
      Serial.print(F("error reception : "));
      Serial.println(receptionState);
    }
    radio.finishReceive();
    radio.clearPacketReceivedAction();
    radio.setPacketSentAction(setTransmitFlag);
    //delay(100);
    //radio.startReceive();
  }
}