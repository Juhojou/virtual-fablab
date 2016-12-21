# virtual-fablab
The purpose of this project is to make an open-source 3D-virtualization tool.
User can control and edit a 3D-object with e.g. power glove in 3D-computer graphic software called Blender.

We build a Power Glove which uses Arduino Uno, MPU6050 accelerometer, two bending resistor and two buttons.

This software is tested on Blender versions 2.76-2.78 on Windows 7 and 10. The software partial Linux support with limited functionality, tested on Ubuntu 14.04.  

# How to use this project:
1. `Install Arduino IDE`

  https://www.arduino.cc/en/Main/Software

2. `Download libraries for Arduino`

  Firstly, you have to download (and “install”) two libraries: `I2Cdevlib` and `MPU6050`. The former solves issues related to the communication   while the latter includes some useful functions to configure and operate the sensor. Both libraries can be downloaded from                 `https://github.com/jrowberg/i2cdevlib/Arduino`. The installation process is as easy as copying both folders within the Arduino IDE installation     path (typically `C:/Program Files (x86)/Arduino/libraries`).

3. `Download and install Blender`

  https://www.blender.org/download/

4. `Download and install pyserial`

  https://github.com/pyserial/pyserial
  
  Download the pySerial from link above as zip-file. Extract the zip-file and open the extracted folder.
  Copy folder `serial` to your `Blender Foundation\Blender\YourBlenderVersion\scripts\modules` folder.

  This is usually located in `Program Files` in 64-bit systems and `Program Files (x86)` in 32-bit system.
  Example path where to copy the folder: `C:\Program Files\Blender Foundation\Blender\2.78\scripts\modules`.

  You can test pySerial working properly by typing `import serial` in Blender's python console. If you don't 
  see any error  messages is pySerial installed properly.



5. `Installing the add-on`

  Download the file `VirtualizationTool.py` and save it to your computer.
 
  In Blender in `User Preferences` -view, click `Add-ons` and click `Install from File` button at the bottom.
  Now navigate and choose file you downloaded and click `Install from File`.

  Now you should see the program listed as add-on in `Object` category with name `control object`.
  Next enable add-on by checking its checkbox. Now `VirtualizationTool` panel should appear on very left of your 3D-view window.

  If you want to panel to start automatically on launch click `Save User Settings` button in `User Preferences` after
  checking the add-on checkbox. This will load the add-on always on Blender launch.

6. `Use the system and please feel free to edit the code!`
