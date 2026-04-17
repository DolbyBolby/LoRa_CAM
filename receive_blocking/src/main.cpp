#include <Arduino.h>
#include <RadioLib.h>

  SPIClass spi(VSPI);
  SPISettings spiSettings(8000000, MSBFIRST, SPI_MODE0);
  SX1280 radio = new Module(25, 27, 2, 13, spi, spiSettings);
//SX1281 radio = new Module(25, 14, 2, 13);

int transmissionState = RADIOLIB_ERR_NONE;

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
void setReceivedFlag(void) {
  receivedFlag = true;
}


float freq = 2450.0;
float bw = 203.125;
uint8_t sf = 12;
uint8_t cr = 7;
uint8_t syncW = RADIOLIB_SX128X_SYNC_WORD_PRIVATE;
int8_t pwr = 10;
uint16_t pl = 12; 



void setup() {
  Serial.begin(9600);

  // initialize SX1280 with default settings
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
  radio.setPacketReceivedAction(setReceivedFlag);

  // start listening for LoRa packets
  Serial.print(F("[SX1280] Starting to listen ... "));
  state = radio.startReceive();
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println(F("success!"));
  } else {
    Serial.print(F("failed, code "));
    Serial.println(state);
    while (true) { delay(10); }
  }
}

void loop() {
  // check if the flag is set
  if(receivedFlag) {
    // reset flag
    receivedFlag = false;

    String buffer;
    int receptionState = radio.readData(buffer);

    if (receptionState == RADIOLIB_ERR_NONE) {
      // packet was successfully received
      Serial.print(F("[SX1280] Received packet!"));

      // print data of the packet
      Serial.print(F("[SX1280] Data:\t\t"));
      Serial.println(buffer);

      radio.finishReceive();
      //delay(100);
      transmissionState = radio.startTransmit("ACK");
      if(transmittedFlag) {
        radio.finishTransmit();
        Serial.print(F("finish transmit"));
        //delay(100);
        radio.startReceive();
      }else {
        Serial.print(F("transmission ... :"));
        Serial.println(transmissionState);
      }


    } else if (receptionState == RADIOLIB_ERR_CRC_MISMATCH) {
      // packet was received, but is malformed
      Serial.println(F("CRC error!"));

    } else {
      // some other error occurred
      Serial.print(F("failed, code "));
      Serial.println(receptionState);

    }
  }
}