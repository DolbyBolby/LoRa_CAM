/*
  RadioLib SX128x Blocking Transmit Example

  This example transmits packets using SX1280 LoRa radio module.
  Each packet contains up to 256 bytes of data, in the form of:
  - Arduino String
  - null-terminated char array (C-string)
  - arbitrary binary data (byte array)

  Other modules from SX128x family can also be used.

  Using blocking transmit is not recommended, as it will lead
  to inefficient use of processor time!
  Instead, interrupt transmit is recommended.

  For default module settings, see the wiki page
  https://github.com/jgromes/RadioLib/wiki/Default-configuration#sx128x---lora-modem

  For full API reference, see the GitHub Pages
  https://jgromes.github.io/RadioLib/
*/

#include <Arduino.h>
#include <RadioLib.h>

// SX1280 has the following connections:
// NSS pin:   10
// DIO1 pin:  2
// NRST pin:  3
// BUSY pin:  9
SPIClass spi(VSPI);
SPISettings spiSettings(8000000, MSBFIRST, SPI_MODE0);
SX1280 radio = new Module(25, 14, 2, 13, spi, spiSettings);
//SX1281 radio = new Module(25, 27, 2, 13);

// or detect the pinout automatically using RadioBoards
// https://github.com/radiolib-org/RadioBoards
/*
#define RADIO_BOARD_AUTO
#include <RadioBoards.h>
Radio radio = new RadioModule();
*/

// save transmission state between loops
int transmissionState = RADIOLIB_ERR_NONE;

// flag to indicate that a packet was sent
volatile bool transmittedFlag = false;

// this function is called when a complete packet
// is transmitted by the module
// IMPORTANT: this function MUST be 'void' type
//            and MUST NOT have any arguments!
#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  // we sent a packet, set the flag
  transmittedFlag = true;
}

// Counter to keep track of transmitted packets
int count = 0;

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
  // Carrier frequency:           2400.0 MHz
  // Bandwidth:                   812.5 kHz
  // Spreading factor:            9
  // Coding rate:                 7
  // Output power:                10 dBm
  // Preamble length:             12 symbols
  // CRC:                         enabled
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

  // start transmitting the first packet
  //Serial.print(F("[SX1280] Sending first packet ... "));

  // you can transmit C-string or Arduino string up to
  // 256 characters long
  //transmissionState = radio.startTransmit("Hello World!");

  // Some modules have an external RF switch
  // controlled via two pins (RX enable, TX enable)s
  // to enable automatic control of the switch,
  // call the following method
  // RX enable:   4
  // TX enable:   5
  /*
    radio.setRfSwitchPins(4, 5);
  */
}

void loop() {
  // Lecture des données du port série
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      // String complète reçue
      if (serialBuffer.length() > 0) {
        Serial.print(F("[Serial] Received: "));
        Serial.println(serialBuffer);
        
        // Utiliser la string reçue pour la transmission radio
        Serial.print(F("[SX1280] Sending via radio: "));
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

    // clean up after transmission is finished
    // this will ensure transmitter is disabled,
    // RF switch is powered down etc.
    radio.finishTransmit();

    // wait a second before transmitting again
    delay(1000);

    // Optionnel: envoyer un message par défaut si rien reçu du série
    // Serial.print(F("[SX1280] Sending another packet ... "));
    // String str = "Hello World! #" + String(count++);
    // transmissionState = radio.startTransmit(str);
  }
}