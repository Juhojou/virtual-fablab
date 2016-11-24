int pin3 = 2;
int state = 0;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
 pinMode(pin3,INPUT_PULLUP);
}

void loop() {
  // put your main code here, to run repeatedly:
  state = digitalRead(pin3);
  Serial.println(state);
  delay(500);
}
