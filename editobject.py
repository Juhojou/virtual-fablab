bl_info = {"name": "control object","category": "User"}

import bpy
import serial
import time
import queue
import serial.tools.list_ports
import threading
import sys
import ctypes
from ctypes import *
from bpy.app.handlers import persistent

class SerialLink(threading.Thread):
    # Thread for reading the usb port and adding to the queue 
    _ser = None
    _open = None
    def __init__(self,name,q, qlock):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
        self.qlock = qlock
    def addBuffer1(self):
        try:
            #print("add buffer")
            quit = 0
            ctr = 0
            tempB = 0
            tempC = 0
            defA, defB, defC = None, None, None
            s = threading.currentThread()
            connection = self.openConnection()
            while getattr(s,"do_run", True) and connection: # waits for the event for the blender window
                try:
                    #print("print asd")
                    line = self._ser.readline()
                    #print("add buffer mk2")
                    line = line.decode('utf-8')
                    if not line.find("demo") == -1:
                        self._ser.write(str.encode("a"))
                        defA = None
                        ctr = 0
                        continue
                    else:
                        line = line.strip('\r\n')
                        line = line.split('\t')
                        print(line)
                        if len(line) == 4:
                            self.qlock.acquire()
                            a = float(line[1])
                            b = float(line[2])
                            c = float(line[3])
                            
                            if ctr < 5:
                                #print("aasi")
                                if (c == tempC and b == tempB):
                                    ctr += 1
                                    print(ctr)
                                else:
                                    #print("else ctr")
                                    ctr = 0
                                tempC = c
                                tempB = b
                                if ctr == 3:
                                    defA, defB, defC = float(a), float(b), float(c)
                                    ctr = 6
                                    print("YAW alustettu")
                            
                            if defA:
                                if a > defA + 30 or a < defA - 30 or b > defB + 30 or b < defB - 30 or c > defC + 30 or c < defC - 30:
                                    #print(line)
                                    line.append(defB)
                                    line.append(defC)
                                    self.q.put(line)
                            
                            #q.put(line)
                        #print(line)
                        #q.put(line)
                            self.qlock.release()
                except TypeError:
                    pass
                    #print("type error")
                except UnicodeError:
                    pass
                except ValueError:

                    pass
                except KeyboardInterrupt:
                    pass
        except serial.serialutil.SerialException: # FileNotFoundError
            print("Serial error!!")

    def openConnection(self):
        """Opens the connection to the arduino device and returns TRUE if successful"""
        ports = []
        port = None
        ctr = 0
        while port == None:
            ctr += 1
            if (ctr > 4):
                print("Couldn't find arduino in reasonable time exiting program")
                return False
            time.sleep(5)
            print("checking for arduino connected to a usb port")
            ports = list(serial.tools.list_ports.comports())
            if sys.platform.startswith('win'):
                for a in ports:
                    if "Arduino" in a[1]:
                        port = a[0]
                if port == None:
                    print("Arduino not found retrying in 5 seconds")
                    continue
            elif sys.platform.startswith('linux'):
                if len(ports) > 0:
                    for b in ports:
                        port = b[0]
        closed = False
        ctr = 0
        while not closed:
            try:
                self._ser = serial.Serial(port,115200, write_timeout=5) # opens the serial connection
                closed = True
            except SerialException:
                print("problem opening connection retrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    print("Couldn't find open serial port in reasonable time exiting program")
                    return False
                time.sleep(5)
        write = False
        ctr = 0
        while not write: # tries to write to the arduino so that the arduino knows to start sending data
            try:
                self._ser.write(str.encode('A')) # the arduino waits for a character to start sending data
                print("Sent character to arduino")
                print("calibrating")
                time.sleep(10) # waits for 10 seconds so that the accelerometer values normalise
                print("done calibrating")
                write =  True
            except:
                print("Couldn't write to the serial port\nRetrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    print("Couldn't find write to the serial port in reasonable time exiting program")
                    return False
        return True

    def closeSerial(self):
        self._ser.close()

    def run(self):
        time.sleep(3)
        print("slept")
        self.addBuffer1()

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    limits = bpy.props.IntProperty(default=0)
    _timer = None
    
    def rotateObject(self):
        #try:
        obj = bpy.context.active_object
        #print("rota")
        if not p.q.empty():
            #print("ting")
            p.qlock.acquire()
            line = p.q.get();
            a = float(line[1])
            b = float(line[2])
            c = float(line[3])
            defB = float(line[4])
            defC = float(line[5])
            pi = 3.14159265358979
            p.qlock.release()
            #obj.rotation_euler = (b , c , a)
            
            """Determines the object rotation directions and if the sensor has moved enough to rotate the object"""
            if a > obj.rotation_euler.z + 30:
     #           rotation.append("+a")
                #obj.rotation_euler.z -= pi/16
                pass
                           
            if a < obj.rotation_euler.z - 30:
    #            rotation.append("-a")       
                #obj.rotation_euler.z += pi/16
                pass
                    
            if c > defC + 30: # c < obj.rotation_euler.y + 30
                #rotation.append("+b") 
                obj.rotation_euler.y += pi/16
                #pass     
            if c < defC - 30: # c > obj.rotation_euler.y
                #rotation.append("-b")
                obj.rotation_euler.y -= pi/16
                #pass
                    
            if b > defB + 30: # b > obj.rotation_euler.x
                #rotation.append("+c") 
                obj.rotation_euler.x += pi/16     
                #pass
            if b < defB - 30: # b > obj.rotation_euler.x
                #rotation.append("-c")
                obj.rotation_euler.x -= pi/16
                #pass
            
            #time.sleep(0.1)
        #bpy.ops.transform.rotate(value=0.283/8, axis=(0,0,1))
        #except KeyboardInterrupt:

    def modal(self, context, event):
        
        if event.type in {'RIGHTMOUSE', 'ESC'} or self.limits > 30:
            self.limits = 0
            self.cancel(context)
            print("Exiting program")
            p.do_run = False
            try:
                p.closeSerial() # try to close the serial
            except:
                pass
            try:
                p.qlock.release() # release the queue lock if it is locked
            except RuntimeError:
                pass
                #print("runtime error")
            p.join()
            return {'FINISHED'}

        if event.type == 'TIMER':
            self.rotateObject()

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
        #rotateCamera()
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

# Definition of point structure - Windows
class POINT(Structure):
    _fields_ = [("x", c_ulong), ("y", c_ulong)]

# Get cursor position - Windows
def getCursorPosition():
   point = POINT()
   windll.user32.GetCursorPos(byref(point))
   return point.x, point.y

# Set cursor position - Windows
def setCursorPosition(x, y):
   windll.user32.SetCursorPos(x, y)

# Left mouse button click - Windows
def click():
    ctypes.windll.user32.mouse_event(0x2, 0,0,0,0)    # MouseLeft clicked Down
    ctypes.windll.user32.mouse_event(0x4, 0,0,0,0)    # MouseLeft clicked Up
    
# Get coordinates for center of screen - Windows
def getScreenCenter():
    user32 = ctypes.windll.user32
    x = int(user32.GetSystemMetrics(0)/2)
    y = int(user32.GetSystemMetrics(1)/2)
    return x, y
       
def zoom():
    value = 1 #If value > 0 = zoom in, value < 0 = zoom out
    for window in bpy.context.window_manager.windows:
    	screen = window.screen
    	for area in screen.areas: 
    		if area.type == 'VIEW_3D':
    			for region in area.regions:
    				if region.type == 'WINDOW':
    					override = {'window': window, 'screen': screen, 'area': area, 'region': region}
    					bpy.ops.view3d.zoom(override, delta=value, mx=0, my=0)
    					break

def rotateCamera():
    #bpy.ops.object.delete(use_global=False)
    #bpy.ops.mesh.primitive_cube_add()
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override['area'] = area
            bpy.ops.view3d.viewnumpad(override, type = 'FRONT')
            #bpy.ops.view3d.view_orbit(type = 'ORBITUP')
            bpy.ops.object.mode_set(mode = 'EDIT')
            #bpy.ops.mesh.subdivide(number_cuts = 20)
            bpy.ops.object.mode_set(mode='SCULPT')
            break

"""https://blenderartists.org/forum/showthread.php?340820-How-to-start-a-Modal-Timer-at-launch-in-an-addon
was used as a guideline how to implement modal timer operator in a blender addon"""
@persistent
def my_handler2(scene):
    bpy.ops.wm.modal_timer_operator()
    bpy.app.handlers.frame_change_post.remove(my_handler2)

@persistent
def my_handler(scene):
    bpy.app.handlers.frame_change_post.append(my_handler2)
    bpy.context.scene.frame_current=bpy.context.scene.frame_current
    bpy.app.handlers.scene_update_post.remove(my_handler)


def register():
    global p
    qlock = threading.Lock() # thread lock
    q = queue.Queue() # the queue
    p = SerialLink('serial thread',q, qlock) # create the thread
    p.start()

    bpy.utils.register_module(__name__)
    bpy.app.handlers.scene_update_post.append(my_handler)
    print("Thread made and establishing connecion with arduino device")
    if sys.platform.startswith('win'):
        width, height = getScreenCenter()
        setCursorPosition(width, height)

def unregister():
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register() #  running from text editor
