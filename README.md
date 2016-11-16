# virtual-fablab
The purpose of this project is to make an open-source 3D-virtualization tool.
User can control and edit a 3D-object with a power glove in 3D-computer graphic software called Blender.

Our Power Glove uses Arduino Uno, MPU6050 accelerometer, two bending resistor and two buttons.

# How to use this project:
1. Install Arduino IDE
https://www.arduino.cc/en/Main/Software

2. Download libraries for Arduino
Firstly, you have to download (and “install”) two libraries: I2Cdevlib and MPU6050. The former solves issues related to the communication while the latter includes some useful functions to configure and operate the sensor. Both libraries can be downloaded from https://github.com/jrowberg/i2cdevlib. The installation process is as easy as copying both folders within the Arduino IDE installation path (typically c:/Program Files (x86)/Arduino/libraries).

3. Download and install Blender
https://www.blender.org/download/

4. Open Blender and go to Scripting view

5. Fork/download our codes and open the python file in Blender

6. Use the system and please feel free to edit the code!
