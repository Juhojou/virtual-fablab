import bpy
import random
import serial
import time
import queue
import multiprocessing
import threading
import sys
"""
# are we running inside Blender?
bpy = sys.modules.get("bpy")
if bpy is not None:
    sys.executable = bpy.app.binary_path_python
    # get the text-block's filepath
    __file__ = bpy.data.texts[__file__[1:]].filepath
del bpy, sys
"""
class myThread(threading.Thread):
    def __init__(self,name,q):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
    def run(self):
        addBuffer1()
    
def setup1():
    openSerial()
    time.sleep(3)
    try:
        ser.write(str.encode('A'))
        print("lähetys alko?")
    except :
        print("error")
    print("calibrating")
    time.sleep(10)
    print("done calibrating")

def openSerial():
    global ser
    ser = serial.Serial('/dev/ttyACM4',115200)
    
def closeSerial():
    #global ser
    ser.close()
    
def addBuffer1():
    try:
        if open1 == 0:
            setup1()
            open = 1
            print("opened ser")
        #print("add buffer")
        quit = 0
        ctr = 0
        tempA = 0
        defA, defB, defC = None, None, None
        s = threading.currentThread()
        while getattr(s,"do_run", True):
            try:
                line = ser.readline()
                line = line.decode('utf-8')
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
                        if (a == tempA):
                            ctr += 1
                            print(ctr)
                        else:
                            #print("else ctr")
                            ctr = 0
                        tempA = a
                        if ctr == 5:
                            defA, defB, defC = float(a), float(b), float(c)
                            ctr = 6
                            print("YAW alustettu")
                    if defA:
                        if a > defA + 30 or a < defA - 30 or b > defB + 30 or b < defB - 30 or c > defC + 30 or c < defC - 30:
                            #print(line)
                            q.put(line)
                #print(line)
                #q.put(line)
                    qlock.release()
            except UnicodeError:
                print("unicode error")
                continue
            except ValueError:
                print("value error")
                continue
            except KeyboardInterrupt:
                print("KeyboardInterrupt!!!!")
                #threading.Thread.exit()
                #ser.close()
                quit = 1
            #finally:
            #    ser.close()
    except serial.serialutil.SerialException: # FileNotFoundError
        #closeSerial()
        #ser.close()
        print("Serial error!!")
    #ser.close()
        

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    limits = bpy.props.IntProperty(default=0)
    _timer = None
    _ser = None
    
    _r1 = None
    _y1 = None
    _p1 = None
    _open = None
    _defA, _defB, _defC = None, None, None
    _queue = queue.Queue(100)
 
    def rotateObject(self):
        #try:
        obj = bpy.context.active_object
        #print("rota")
        if not q.empty():
            #print("ting")
            qlock.acquire()
            line = q.get();
            a = float(line[1])
            b = float(line[2])
            c = float(line[3])

            #y = float(line[1])
            #p = float(line[2])
            #roll = float(line[3])
            #print(y)
    #rotate (45 degrees: value=6.283/8)
            #bpy.ops.transform.rotate(value=y*0.0174533, axis=(0,0,1))
            #bpy.ops.transform.rotate(value=p*0.0174533, axis=(1,0,0)) 
            #bpy.ops.transform.rotate(value=roll*0.0174533, axis=(0,1,0))
            pi = 3.14159265358979
            qlock.release()
            #obj.rotation_euler = (b , c , a)
            
            
            if a > obj.rotation_euler.z + 30:
     #           rotation.append("+a")
                obj.rotation_euler.z -= pi/16
                #pass
                           
            if a < obj.rotation_euler.z - 30:
    #            rotation.append("-a")       
                obj.rotation_euler.z += pi/16
                #pass
                    
            if b > obj.rotation_euler.x + 30:
                #rotation.append("+b") 
                obj.rotation_euler.x += pi/16
                #pass     
            if b < obj.rotation_euler.x - 30:
                #rotation.append("-b")
                obj.rotation_euler.x -= pi/16
                #pass
                    
            if c > obj.rotation_euler.y + 30:
                #rotation.append("+c") 
                obj.rotation_euler.y += pi/16     
                #pass
            if c < obj.rotation_euler.y - 30:
                #rotation.append("-c")
                obj.rotation_euler.y -= pi/16
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
            p.join()
            quit = 1
            return {'FINISHED'}

        if event.type == 'TIMER':
            
            #time.sleep(3)
            #try:
            #    self._ser.write(str.encode('A'))
                #print("lähetys alko 2 ?")
            #except :
            #   print("some error")
                #time.sleep(300)
            self.rotateObject()
            #time.sleep(15)

        return {'PASS_THROUGH'}

    def execute(self, context):
        #self.openSerial()
        #self.setup1()
        #_thread.start_new_thread(self.addBuffer,())

        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
        #threading.Thread(target=wm.modal_handler_add())
        #multiprocessing.Process(target=wm.modal_handler_add,args=(self,))
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        #self.closeSerial()
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        


def register():
    bpy.utils.register_class(ModalTimerOperator)


def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)


if __name__ == "__main__":
    register()
    global open1
    open1 = 0
    global q
    global p
    global quit
    quit = 0
    qlock = threading.Lock()
    #q = multiprocessing.Queue()
    q = queue.Queue()
    #p = multiprocessing.Process(target=addBuffer1)
    p = myThread('aasithread',q)
    p.start()
    #p.join()
    print("avattu")
    # test call
    #threading.Thread(bpy.ops.wm.modal_timer_operator()).start()
    bpy.ops.wm.modal_timer_operator()