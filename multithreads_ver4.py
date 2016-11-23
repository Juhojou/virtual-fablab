import bpy
import serial
import time
import queue
import serial.tools.list_ports
import threading
import sys
import ctypes
from ctypes import *

class serialLink(threading.Thread):
    # Thread for reading the usb port and adding to the queue 
    _ser = None
    _open = None
    def __init__(self,name,q):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q   
    def addBuffer1(self):
        try:
            if self._open == None:
                self.setup1()
                open = 1
                print("opened ser")
            #print("add buffer")
            quit = 0
            ctr = 0
            tempB = 0
            tempC = 0
            defA, defB, defC = None, None, None
            s = threading.currentThread()
            while getattr(s,"do_run", True): # waits for the event for the blender window
                try:
                    line = self._ser.readline()
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
                            qlock.acquire()
                            a = float(line[1])
                            b = float(line[2])
                            c = float(line[3])
                            
                            if ctr < 5:
                                print("aasi")
                                if (c == tempC and b == tempB):
                                    ctr += 1
                                    print(ctr)
                                else:
                                    #print("else ctr")
                                    ctr = 0
                                tempC = c
                                tempB = b
                                if ctr == 5:
                                    defA, defB, defC = float(a), float(b), float(c)
                                    ctr = 6
                                    print("YAW alustettu")
                            
                            if defA:
                                if a > defA + 30 or a < defA - 30 or b > defB + 30 or b < defB - 30 or c > defC + 30 or c < defC - 30:
                                    #print(line)
                                    line.append(defB)
                                    line.append(defC)
                                    q.put(line)
                            
                            #q.put(line)
                        #print(line)
                        #q.put(line)
                            qlock.release()
                except TypeError:
                    print("type error")
                except UnicodeError:
                    print("unicode error")
                    continue
                except ValueError:
                    print("value error")
                    continue
                except KeyboardInterrupt:
                    print("KeyboardInterrupt!!!!")
                    
                    self._ser.close()
                    quit = 1
                #finally:
                #    ser.close()
        except serial.serialutil.SerialException: # FileNotFoundError
            #closeSerial()
            #ser.close()
            print("Serial error!!")
        #ser.close()
    def setup1(self):
        # setup the serial connection
        self.openSerial()
        time.sleep(3)
        try:
            self._ser.write(str.encode('A')) # the arduino waits for a character to start sending data
            print("lähetys alko?")
        except :
            print("error")
        print("calibrating")
        time.sleep(10) # waits for 10 seconds so that the accelerometer values normalise
        print("done calibrating")

    def checkPorts(self):
        a = []
        while len(a) == 0:
            time.sleep(5)
            a = list(serial.tools.list_ports.comports())
        #print(a)
        if sys.platform.startswith('win'):
            for port in a:
                if "Arduino" in port[1]:
                    return port[0]
        elif sys.platform.startswith('linux'):
            if len(a) > 0:
                for b in a:
                    line = b[0]
                    #print(line)
                #line = a[0]
                #line = line.split(" ")
                #line = line[0]
                print(line)
            return line
        else:
            print("No arduino connected")
            return ""

    def openSerial(self):
        #global ser
        # open serial connection
        line = self.checkPorts()
        self._ser = serial.Serial(line,115200)
        #self._ser = serial.Serial('/dev/ttyACM0',115200)
    def closeSerial(self):
        #global ser
        self._ser.close()

    def run(self):
        self.addBuffer1()

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    limits = bpy.props.IntProperty(default=0)
    _timer = None
    #_ser = None
    
    #_r1 = None
    #_y1 = None
    #_p1 = None
    #_open = None
    #_defA, _defB, _defC = None, None, None
    #_queue = queue.Queue(100)
 
    def rotateObject(self):
        #try:
        obj = bpy.context.active_object
        #print("rota")
        if not p.q.empty():
            #print("ting")
            qlock.acquire()
            line = p.q.get();
            a = float(line[1])
            b = float(line[2])
            c = float(line[3])
            defB = float(line[4])
            defC = float(line[5])
            pi = 3.14159265358979
            qlock.release()
            #obj.rotation_euler = (b , c , a)
            
            
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
            print("done")
            p.do_run = False
            p.closeSerial()
            try:
                qlock.release()
            except RuntimeError:
                print("runtime error")
            p.join()
            return {'FINISHED'}

        if event.type == 'TIMER':
            self.rotateObject()

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
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


# Initialize camera view
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
            bpy.ops.screen.screen_full_area(override, use_hide_panels=True)
            break


def register():
    bpy.utils.register_class(ModalTimerOperator)


def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)


if __name__ == "__main__":
    register()
    #global q
    #global p
    qlock = threading.Lock() # thread lock
    q = queue.Queue() # the queue
    p = serialLink('aasithread',q) # create the thread
    p.start()
    #p.join()
    print("avattu")
    rotateCamera()
    if sys.platform.startswith('win'):
        width, height = getScreenCenter()
        setCursorPosition(width, height)
    # test call
    bpy.ops.wm.modal_timer_operator()