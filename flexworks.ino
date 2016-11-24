int flexSensorPin = A5; //analog pin 0
int pin = A4;

void setup(){
  Serial.begin(9600);
}

void loop(){
  int flexSensorReading = analogRead(flexSensorPin); 
  int readpin = analogRead(pin);

  //Serial.println(flexSensorReading);
  //Serial.println(readpin);

  //In my tests I was getting a reading on the arduino between 512, and 614. 
  //Using map(), you can convert that to a larger range like 0-100.
  int flex0to100 = map(flexSensorReading, 320, 550, 0, 100);
  Serial.println(flex0to100);

  delay(250); //just here to slow down the output for easier reading
}
