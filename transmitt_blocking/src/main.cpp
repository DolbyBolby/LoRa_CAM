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

#if defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setTransmitFlag(void) {
  transmittedFlag = true;
}

#if defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setReceivedFlaf(void) {
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

  radio.setPacketSentAction(setFlag);

}

void loop() {
  // Lecture des données du port série
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      // String complète reçue
      if (serialBuffer.length() > 0) {
        //Serial.print(F("[Serial] Received: "));
        //Serial.println(serialBuffer);
        
        // Utiliser la string reçue pour la transmission radio
        //Serial.print(F("[SX1280] Sending via radio: "));
        Serial.println(serialBuffer);
        transmissionState = radio.startTransmit(serialBuffer);
        
        // Vider le buffer
        serialBuffer = "";
      }
    } else if (c != '\r') {
      // Ajouter le caractère au buffer
      serialBuffer += c;
    }
  }

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
    delay(100);
    radio.startReceive();
  }
}

if 