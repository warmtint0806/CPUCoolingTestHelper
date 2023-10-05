// Including the ESP8266 WiFi library
#include <ESP8266WiFi.h>
#include <WEMOS_SHT3X.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#define LED_PIN D4 // LED가 연결된 핀 (D4 핀을 사용하는 경우)

// Replace with your network details
const char* ssid = "tpsystem";
const char* password = "forwiz8020";

// 웹 서버 설정
const char *serverAddress = "192.168.0.2"; // 웹 서버 주소
const int serverPort = 80; // HTTP 포트 (일반적으로 80)

// 시간 간격 설정 (5초)
const unsigned long interval = 5000; // 5초

unsigned long previousMillis = 0;

SHT3X sht30(0x45);
void sendPostRequest(float h, float t, float f);
// only runs once on boot
void setup() {
  // Initializing serial port for debugging purposes
  Serial.begin(115200);
  delay(10);

  pinMode(LED_PIN, OUTPUT);
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
  
  // Printing the ESP IP address
  Serial.println(WiFi.localIP());
}

// runs over and over again
void loop() {
  // Listenning for new clients
  delay(1000);

  float h = 0;
  float t = 0;
  float f = 0;
  int sht_get=1; 
    // 5초 간격으로 HTTP POST 요청 보내기
  if (currentMillis - previousMillis >= interval) {
    digitalWrite(LED_PIN, HIGH); // LED 켜기

  
    previousMillis = currentMillis;

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
  
    // HTTP POST 요청 보내기
    sendPostRequest(h,t,f);
    
    digitalWrite(LED_PIN, LOW); // LED 끄기
  }
}

void sendPostRequest(float h, float t, float f) {
  HTTPClient http;

  // HTTP POST 요청 설정
  http.begin("http://" + String(serverAddress) + "/api/tp"); // 엔드포인트 URL 설정
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  // POST 데이터 설정
  String postData = "h=" + String(h) + "&t=" + String(t) + "&f=" + String(f);

  // HTTP POST 요청 보내기
  int httpResponseCode = http.POST(postData);

  if (httpResponseCode > 0) {
    Serial.print("HTTP Response Code: ");
    Serial.println(httpResponseCode);
    String response = http.getString();
    //response json result
    
    Serial.println(response);
  } else {
    Serial.print("HTTP Error: ");
    Serial.println(httpResponseCode);
  }

  http.end();
}