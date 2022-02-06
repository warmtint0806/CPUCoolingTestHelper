// Including the ESP8266 WiFi library
#include <ESP8266WiFi.h>
#include <WEMOS_SHT3X.h>


// Replace with your network details
const char* ssid = "H&C";
const char* password = "babdbgh787";

//Sensor info 
const char* sensor_name="ext_temp_sensor_1";

// Web Server on port 80
WiFiServer server(80);

SHT3X sht30(0x45);

// only runs once on boot
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);  
  // Initializing serial port for debugging purposes
  digitalWrite(LED_BUILTIN, HIGH); 
  
  Serial.begin(115200);
  delay(10);

  // Assign IP Address

  IPAddress ip(172,30,1,100);
  IPAddress gateway(172,30,1,254);
  IPAddress subnet(255,255,255,0);
  
  // Connecting to WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.config(ip,gateway,subnet);
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
  delay(1000);
  
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
  bool com_log=false;
  WiFiClient client = server.available();
    sht_get=sht30.get();
    if(sht_get==0){
      h = sht30.humidity;
      t = sht30.cTemp;
      f = sht30.fTemp;
      if(com_log){
              
              
              Serial.print("Temperature in Celsius : ");
              Serial.println(t);
              
              Serial.print("Temperature in Fahrenheit : ");
              Serial.println(f);
              Serial.print("Relative Humidity : ");
              Serial.println(h);
              Serial.println();
              Serial.println(WiFi.localIP());
      }
    }
  if (client) {
    // bolean to locate when the http request ends
    while (client.connected()) {
      if (client.available()) {
            Serial.println("New client");
            digitalWrite(LED_BUILTIN, LOW);
            if(sht_get==0){
              client.println("HTTP/1.1 200 OK");
              client.println("Content-Type: application/json");
              client.println("Connection: close");
              client.println();
              client.println("{");
              client.println("\"t\":");
              client.println(t);
              client.println(",");
              client.println("\"h\":");
              client.println(h);
              client.println(",");
              client.println("\"name\":");
              client.println(String("\"" + String(sensor_name) + "\""));
              client.println("}");
              delay(1);
            }
            else
            {
              client.println("no data available");
              Serial.println("Error!");
            }
            if(com_log){
              delay(1000);
            }
            // closing the client connection
            digitalWrite(LED_BUILTIN, HIGH); 
            break;
            }else{
              Serial.println("Client disconnected.");
              
              client.stop();
              }
           
            
      }

  }
  if(com_log){
    delay(1000);
  }
}
