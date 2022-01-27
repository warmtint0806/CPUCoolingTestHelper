// Including the ESP8266 WiFi library
#include <ESP8266WiFi.h>
#include <WEMOS_SHT3X.h>

// Replace with your network details
const char* ssid = "Sngs";
const char* password = "123456789a";

// Web Server on port 80
WiFiServer server(80);

SHT3X sht30(0x45);

// only runs once on boot
void setup() {
  // Initializing serial port for debugging purposes
  Serial.begin(115200);
  delay(10);

  // Connecting to WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  
  // Starting the web server
  server.begin();
  Serial.println("Web server running. Waiting for the ESP IP...");
  delay(10000);
  
  // Printing the ESP IP address
  Serial.println(WiFi.localIP());
}

// runs over and over again
void loop() {
  // Listenning for new clients
  float h = 0;
  float t = 0;
  float f = 0;
  int sht_get=1; 
  WiFiClient client = server.available();
    sht_get=sht30.get();
    if(sht_get==0){
              h = sht30.humidity;
              t = sht30.cTemp;
              f = sht30.fTemp;
              
              Serial.print("Temperature in Celsius : ");
              Serial.println(t);
              
              Serial.print("Temperature in Fahrenheit : ");
              Serial.println(f);
              Serial.print("Relative Humidity : ");
              Serial.println(h);
              Serial.println();
    }
  
  if (client) {
    Serial.println("New client");
    // bolean to locate when the http request ends
    while (client.connected()) {
      if (client.available()) {
            if(sht_get==0){
              client.println("HTTP/1.1 200 OK");
              client.println("Content-Type: text/html");
              client.println("Connection: close");
              client.println();
              // your actual web page that displays temperature and humidity
              client.println("<!DOCTYPE HTML>");
              client.println("<html>");
              client.println("<head></head><body><h1>ESP8266 - Temperature and Humidity</h1><h3>Temperature in Celsius: ");
              client.println(t);
              client.println("*C</h3><h3>Temperature in Fahrenheit: ");
              client.println(f);
              client.println("*F</h3><h3>Humidity: ");
              client.println(h);
              client.println("%</h3><h3>");
              client.println("</body></html>");     
              break;
            }
            else
            {
              client.println("no data available");
              Serial.println("Error!");
            }
            delay(1000);
            // closing the client connection
            client.stop();
            Serial.println("Client disconnected.");
            }
            delay(1);
      }
  }
  delay(1000);
}
