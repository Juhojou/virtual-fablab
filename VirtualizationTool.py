#
# (C) Juho Kananen, Juuso Sipola, Krista Vilppola, Juhani Wilén
#
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
from bpy.props import EnumProperty
from math import radians
from mathutils import Matrix
from bpy.props import *

class SerialLink(threading.Thread):
    # Thread for reading the usb port and adding to the queue 
    _ser = None
    _open = None
    def __init__(self,name,q, qlock):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
        self.qlock = qlock
        
    def add_buffer(self):
        '''This function listens for Arduino data and saves it to queue '''
        try:
            # These variables are used for initializing the accelometer
            ctr = 0
            tempB = 0
            tempC = 0
            defA, defB, defC = None, None, None
            s = threading.currentThread()
            # Opening connection with Arduino using pyserial
            connection = self.open_connection()
            if not connection:
                # If connection is not estabilished succesfully set program to be stopped in panel
                bpy.context.scene.enable_prop = '0' 
            while getattr(s,"do_run", True) and connection: # Waits for the event for the blender window
                try:                   
                    line = self._ser.readline()
                    line = line.decode('utf-8') 
                    # In case Arduino doesn't initialize properly or there is need to reset the Arduino                   
                    if not line.find("demo") == -1:
                        self._ser.write(str.encode("a"))
                        defA = None
                        ctr = 0
                        continue
                    else:
                        # Reading a line 
                        line = line.strip('\r\n')
                        line = line.split('\t')
                        # Comment this if you don't want to see data sent by Arduino in console
                        print(line)
                        if len(line) == 7:
                            self.qlock.acquire()
                            a = float(line[1])
                            b = float(line[2])
                            c = float(line[3])
                            
                            # Waits for the accelometer data to stabilize. If we get 3 identical sequential values
                            # and then accelometer has stabilized
                            if ctr < 5:
                                if (c == tempC and b == tempB):
                                    ctr += 1
                                    print(ctr)
                                else:
                                    ctr = 0
                                tempC = c
                                tempB = b
                                if ctr == 3:
                                    # Default values are set here
                                    defA, defB, defC = float(a), float(b), float(c)
                                    ctr = 6
                                    bpy.context.scene.status_prop = "Running"
                            
                            # Adds values to queue if accelometer data has changed enough from default values
                            if defA:
                                if a > defA + 30 or a < defA - 30 or b > defB + 30 or b < defB - 30 or c > defC + 30 or c < defC - 30:
                                    line.append(defB)
                                    line.append(defC)
                                    self.q.put(line)
                            self.qlock.release()
                
                # There may be some erroneous lines but since baud rate is high enough we can skip those
                except TypeError:
                    pass
                except UnicodeError:
                    pass
                except ValueError:
                    pass
                except KeyboardInterrupt:
                    pass
        # If Arduino connection disappears when program is running      
        except serial.serialutil.SerialException: 
            print("Serial error!!")

    def open_connection(self):
        """Opens the connection to the arduino device and returns True if successful else False"""
        ports = []
        port = None
        ctr = 0
        bpy.context.scene.status_prop = "Searching COM port"
        # Searching for a COM port with an Arduino device
        while port == None:
            if bpy.context.scene.enable_prop == '0':
                bpy.context.scene.status_prop = "Stopped"
                return False
            ctr += 1
            if (ctr > 4):
                print("Couldn't find Arduino in reasonable time exiting program")
                bpy.context.scene.status_prop = "Could not find Arduino. Program stopped."
                return False
            time.sleep(5)
            print("Checking for Arduino connected to a usb port")
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
        bpy.context.scene.status_prop = "Opening serial connection"
        # Trying open serial connection with Arduino
        while not closed:
            if bpy.context.scene.enable_prop == '0':
                bpy.context.scene.status_prop = "Stopped"
                return False
            try:
                self._ser = serial.Serial(port,115200, write_timeout=5) # opens the serial connection
                closed = True
            except SerialException:
                print("Problem opening connection retrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    bpy.context.scene.status_prop = "Could not open connection. Program stopped."
                    print("Couldn't find open serial port in reasonable time exiting program")
                    return False
                time.sleep(5)
        write = False
        ctr = 0
        bpy.context.scene.status_prop = "Sending first character"
        # Tries to write to the arduino so that the Arduino knows to start sending data
        while not write: 
            if bpy.context.scene.enable_prop == '0':
                bpy.context.scene.status_prop = "Stopped"
                return False
            try:
                # The Arduino waits for a character to start sending data
                self._ser.write(str.encode('A')) 
                print("Sent character to Arduino")
                print("Calibrating...")
                bpy.context.scene.status_prop = "Calibrating"
                # Waits for 10 seconds so that the accelerometer values normalise
                time.sleep(10) 
                write =  True
            except:
                print("Couldn't write to the serial port\nRetrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    bpy.context.scene.status_prop = "Could not write a character. Program stopped."
                    print("Couldn't find write to the serial port in reasonable time exiting program")
                    return False
        return True

    def close_serial(self):
        self._ser.close()

    def run(self):
        time.sleep(3)
        self.add_buffer()

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs itself from a timer and is used to edit the object using data from queue"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"
    _timer = None
    _ctr_zoom = 0
    _ctr_sculpt = 0
    
    def rotate_object(self):
        # Active object which will be rotated
        obj = bpy.context.active_object 
        if (get_distance() < 4):
            rot_angle = radians(get_distance()) / 2
        elif (get_distance() > 8):
            rot_angle = radians(8.0)
        else:
            rot_angle = radians(get_distance())
       
        # rotation matrix along global X axis
        mat_rot_x = Matrix.Rotation(rot_angle, 4, 'X') 
        # rotation matrix along global Z axis
        mat_rot_y = Matrix.Rotation(rot_angle, 4, 'Z') 
        mat_rot_nx = Matrix.Rotation(-rot_angle, 4, 'X')
        mat_rot_ny = Matrix.Rotation(-rot_angle, 4, 'Z')
        
        # If the data thread's queue is not empty, execute the rotation
        if not p.q.empty():
            # Queue is locked and data values saved in variables
            p.qlock.acquire()
            line = p.q.get();
            a = float(line[1])
            b = float(line[2])
            c = float(line[3])
            zoom_button = line[4]
            sculpt_button = line[5]
            flex_sensor = line[6]
            defB = float(line[7])
            defC = float(line[8]) 
            pi = 3.14159265358979
            
            if (zoom_button == "0" and float(flex_sensor) > 55):
                # Checks if the zoom and scultp buttons are pressed
                self._ctr_zoom += 1
                 # Waits that 2 sequential cycles where zoom button is pressed occurs
                if (self._ctr_zoom % 2 == 1):
                    zoom(-1)
            elif (zoom_button == "0"):
                self._ctr_zoom += 1
                if (self._ctr_zoom % 2 == 1):
                    zoom(1)
            elif (sculpt_button == "0"):
                self._ctr_sculpt += 1
                if (self._ctr_sculpt % 2 == 1):
                    click()                              
            else:
                self._ctr_zoom = 0
                self._ctr_sculpt = 0
            # Lock is released to allow Arduino add more data to queue
            p.qlock.release()
            
            loc, rot, scale = obj.matrix_world.decompose()
            mat_loc = Matrix.Translation(loc)
            mat_rot = rot.to_matrix().to_4x4()
            mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
              
            rotation = mat_loc

            # Determines the object rotation directions and if the sensor has moved enough to rotate the object
            if b > defB + 30: 
                bpy.context.scene.update()
                loc, rot, scale = obj.matrix_world.decompose()
                mat_loc = Matrix.Translation(loc)
                mat_rot = rot.to_matrix().to_4x4()
                mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
                obj.matrix_world = mat_loc * mat_rot_x * mat_rot * mat_scale

            if b < defB - 30:
                bpy.context.scene.update()
                loc, rot, scale = obj.matrix_world.decompose()
                mat_loc = Matrix.Translation(loc)
                mat_rot = rot.to_matrix().to_4x4()
                mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
                obj.matrix_world = mat_loc * mat_rot_nx * mat_rot * mat_scale
                    
            if c > defC + 70:
                bpy.context.scene.update()
                loc, rot, scale = obj.matrix_world.decompose()
                mat_loc = Matrix.Translation(loc)
                mat_rot = rot.to_matrix().to_4x4()
                mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
                obj.matrix_world = mat_loc * mat_rot_ny * mat_rot * mat_scale
    
            if c < defC - 70:
                bpy.context.scene.update()
                loc, rot, scale = obj.matrix_world.decompose()
                mat_loc = Matrix.Translation(loc)
                mat_rot = rot.to_matrix().to_4x4()
                mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
                obj.matrix_world = mat_loc * mat_rot_y * mat_rot * mat_scale

    def modal(self, context, event):
        # This condition executed when program stopped
        if event.type in {'ESC'} or bpy.context.scene.enable_prop == '0':
            if bpy.context.scene.enable_prop == '0' and bpy.context.scene.status_prop == 'Running':
                bpy.context.scene.status_prop = 'Stopped'
            bpy.context.scene.enable_prop = '0'
            self.cancel(context)
            print("Exiting program")
            p.do_run = False
            try:
                # Closing the serial connection 
                p.close_serial() 
            except:
                pass
            try:
                # Release the queue lock if it is locked
                p.qlock.release() 
            except RuntimeError:
                pass
            
            # Waiting the data thread to finish
            p.join()
            
            # Updating panel once after program has stopped            
            context.scene.enable_prop = '0'
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    
            # Return to previous view of blender
            try:        
                bpy.ops.screen.back_to_previous()
            except RuntimeError:
                pass
                    
            return {'FINISHED'}

        # This is the normal timer operation, rotating the object
        if event.type == 'TIMER':            
            self.rotate_object()

        return {'PASS_THROUGH'}

    def execute(self, context):
        # This is executed on timer launch
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # When stopping the timer
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
    
class PanelControl(bpy.types.Panel):
    """Creates a Panel in the 3D-View tools window"""
    bl_category = "VirtualizationTool"  # Name seen in tab
    bl_label = "VirtualizationTool" # Caption of the opened panel
    bl_idname = "controlpanel"  # Unique object name
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
       
    def draw(self, context):
        # This function draws everything that is seen in the panel
        
        scene = context.scene
        object = context.active_object
        layout = self.layout

        row = layout.row()
        row.label(text="Status")
        
        row = layout.row()
        status= bpy.context.scene.status_prop 
        row.label(text=status) 

        row = layout.row() 
        row.prop(scene,"enable_prop", expand=True)

        row = layout.row()
        row = layout.row()
        row = layout.row()        
       
        col = layout.column()
        row = layout.row()
        split = row.split(align=True)
        split.operator("mesh.subdivide")
        split.operator("mesh.unsubdivide", text="Unsubdivide")
        
        row = layout.row()
        bpy.context.active_object.update_from_editmode()
        row.label(text="Number of vertices: %d" % len(object.data.vertices))
        
        row = layout.row()
        row = layout.row()

        col = layout.column()
        col.label(text= "Mode")
        col.prop(scene,"mode_prop", expand=True)
        
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row.operator("object.location_clear", text="Move object to center")
        
        row = layout.row()
        row.operator("object.rotateview", text="Rotate view")

class PanelTimer(bpy.types.Operator):
    """This modal timer check if propertes are changed in panel by user"""
    bl_idname = "wm.panel_modal_timer"
    bl_label = "Panel Modal Timer"

    _timer = None
    
    lastMode= None 
    curMode = None 
    

    def modal(self, context, event):
        
        modes =["OBJECT", "EDIT", "SCULPT", "TEXTURE_PAINT", "WEIGHT_PAINT", "VERTEX_PAINT"]
           
        if event.type == 'TIMER':
            # When program is enabled in panel and the other thread doesn't exist run the actual program
            if bpy.context.scene.enable_prop == '1' and len(threading.enumerate()) == 1:
                run()
                           
            # Updating current mode to panel changing mode if changed in panel
            self.lastMode = self.curMode
            self.curMode = bpy.context.active_object.mode 
            m = modes.index(self.curMode)
            if self.lastMode != self.curMode:
                if str(m) != bpy.context.scene.mode_prop:
                    bpy.context.scene.mode_prop = str(m)
            else:
                if  bpy.context.scene.mode_prop == '0':
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                elif bpy.context.scene.mode_prop == '1':
                    bpy.ops.object.mode_set(mode = 'EDIT') 
                elif bpy.context.scene.mode_prop == '2':
                    bpy.ops.object.mode_set(mode = 'SCULPT') 
                elif  bpy.context.scene.mode_prop == '3':
                    bpy.ops.object.mode_set(mode = 'TEXTURE_PAINT')
                elif bpy.context.scene.mode_prop == '4':
                    bpy.ops.object.mode_set(mode = 'WEIGHT_PAINT') 
                elif bpy.context.scene.mode_prop == '5':
                    bpy.ops.object.mode_set(mode = 'VERTEX_PAINT')      
                
                # Redraw to see mode change
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()                    
            
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        # This is executed on launch of modal timer
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

class rotateView(bpy.types.Operator):
    ''' Class for rotate view button on the panel. Rotates camera to default sculpting position '''
    bl_idname = "object.rotateview"
    bl_label = "Camera Rotation"

    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas: 
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = {'blend_data': bpy.context.blend_data,'mode': 'SCULPT','active_object': bpy.context.scene.objects.active,'scene': bpy.context.scene,'window': window, 'screen': screen, 'area': area, 'region': region}
                            bpy.ops.view3d.viewnumpad(override, type = 'FRONT')
                            break
        return {'FINISHED'}

    
# Definition of point structure - Windows
class POINT(Structure):
    _fields_ = [("x", c_ulong), ("y", c_ulong)]

# Get cursor position - Windows
def get_cursor_position():
   point = POINT()
   windll.user32.GetCursorPos(byref(point))
   return point.x, point.y

# Set cursor position - Windows
def set_cursor_position(x, y):
   windll.user32.SetCursorPos(x, y)

# Left mouse button click - Windows
def click():
    if (bpy.context.scene.mode_prop == '1'):
        ctypes.windll.user32.mouse_event(0x8,0,0,0,0)
        ctypes.windll.user32.mouse_event(0x10,0,0,0,0)
        print("right")
    else:
        ctypes.windll.user32.mouse_event(0x2, 0,0,0,0)    # MouseLeft clicked Down
        ctypes.windll.user32.mouse_event(0x4, 0,0,0,0)    # MouseLeft clicked Up
    
# Get coordinates for center of screen - Windows
def get_screen_center():
    user32 = ctypes.windll.user32
    x = int(user32.GetSystemMetrics(0)/2)
    y = int(user32.GetSystemMetrics(1)/2)
    return x, y
       
def zoom(value):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas: 
            if area.type == 'VIEW_3D':
                if (area.spaces.active.region_3d.view_distance > 10):
                    value = value*2
                elif (area.spaces.active.region_3d.view_distance < 5):
                    value = value / 10
                area.spaces.active.region_3d.view_distance -= value
                
def get_distance():
    # Gets the user perspctive distance to the object
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas: 
            if area.type == 'VIEW_3D':
                return area.spaces.active.region_3d.view_distance

def set_fullscreen():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override['area'] = area
            bpy.ops.screen.screen_full_area(override, use_hide_panels=False)
            break



"""https://blenderartists.org/forum/showthread.php?340820-How-to-start-a-Modal-Timer-at-launch-in-an-addon
was used as a guideline how to implement modal timer operator in a blender addon"""

# These handlers are used to launch modal timer for object rotation
@persistent
def my_handler2(scene):
    bpy.ops.wm.modal_timer_operator()
    bpy.app.handlers.frame_change_post.remove(my_handler2)

@persistent
def my_handler(scene):
    bpy.app.handlers.frame_change_post.append(my_handler2)
    bpy.context.scene.frame_current=bpy.context.scene.frame_current
    bpy.app.handlers.scene_update_post.remove(my_handler)


# These handlers are used to lauch modal timer for panel
@persistent
def panel_handler2(scene):
    bpy.ops.wm.panel_modal_timer()
    bpy.app.handlers.frame_change_post.remove(panel_handler2)

@persistent
def panel_handler(scene):
    bpy.app.handlers.frame_change_post.append(panel_handler2)
    bpy.context.scene.frame_current=bpy.context.scene.frame_current
    bpy.app.handlers.scene_update_post.remove(panel_handler)

def run():
    # This is executed when program is enabled in panel
    
    # This is thread which is connected to Arduino and listens for data
    global p    
    qlock = threading.Lock()
    
    # Data from Arduino is stored to this queue
    q = queue.Queue()
    p = SerialLink('serial thread',q, qlock) 
    p.start()
    
    # Lauch modal timer for object rotation
    bpy.app.handlers.scene_update_post.append(my_handler)
    print("Thread made and establishing connection with Arduino device")
    bpy.context.scene.status_prop = "Connecting to Arduino"
    set_fullscreen()

def register():
    # This property is used to lauch program in panel
    bpy.types.Scene.enable_prop = bpy.props.EnumProperty(items = (('0','Stop', ''),('1','Run','')))
    # Property for switching modes
    bpy.types.Scene.mode_prop = bpy.props.EnumProperty(items = (('0','Object','Object mode', 'OBJECT_DATAMODE', 0),('1','Edit','Edit mode', 'EDITMODE_HLT', 1), ('2','Sculpt','Sculpt mode', 'SCULPTMODE_HLT', 2), ('3','Texture Paint', 'Texture paint mode', 'TPAINT_HLT', 3),('4','Weight Paint','Weight paint mode', 'WPAINT_HLT',4), ('5','Vertex Paint','Vertex paint mode', 'VPAINT_HLT' ,5)))
    # This property shows program status in panel
    bpy.types.Scene.status_prop = bpy.props.StringProperty(default="Stopped")
    bpy.utils.register_module(__name__)
    # Launch modal timer for panel
    bpy.app.handlers.scene_update_post.append(panel_handler)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.enable_prop
    del bpy.types.Scene.mode_prop
    del bpy.types.Scene.status_prop


if __name__ == "__main__":
    #  Running from text editor
    register() 