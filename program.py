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

class SerialLink(threading.Thread):
    # Thread for reading the usb port and adding to the queue 
    _ser = None
    _open = None
    ctr_distance = 0
    distance = 15.0
    def __init__(self,name,q, qlock):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
        self.qlock = qlock
        
    def add_buffer(self):
        try:
            quit = 0
            ctr = 0
            tempB = 0
            tempC = 0
            ctr_zoom = 0
            ctr_sculpt = 0
            defA, defB, defC = None, None, None
            s = threading.currentThread()
            connection = self.open_connection()
            if not connection:
                bpy.context.scene.enable_prop = '0'
            while getattr(s,"do_run", True) and connection: # Waits for the event for the blender window
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
                        if len(line) == 7:
                            self.qlock.acquire()
                            a = float(line[1])
                            b = float(line[2])
                            c = float(line[3])
                            zoom_button = line[4]
                            sculpt_button = line[5]
                            flex_sensor = line[6]
                            if (zoom_button == "0" and float(flex_sensor) > 55):
                                ctr_zoom += 1
                                if (ctr_zoom % 2 == 1):
                                    self.distance = zoom(-1)
                                    self.ctr_distance -= 1
                            elif (zoom_button == "0"):
                                ctr_zoom += 1
                                if (ctr_zoom % 2 == 1):
                                    self.distance = zoom(1)
                                    self.ctr_distance += 1
                            elif (sculpt_button == "0"):
                                ctr_sculpt += 1
                                if (ctr_sculpt % 2 == 1):
                                    click()                              
                            else:
                                ctr_zoom = 0
                                ctr_sculpt = 0
                            if ctr < 5:
                                if (c == tempC and b == tempB):
                                    ctr += 1
                                    print(ctr)
                                else:
                                    ctr = 0
                                tempC = c
                                tempB = b
                                if ctr == 3:
                                    defA, defB, defC = float(a), float(b), float(c)
                                    ctr = 6
                                    print("YAW alustettu")
                            
                            if defA:
                                if a > defA + 30 or a < defA - 30 or b > defB + 30 or b < defB - 30 or c > defC + 30 or c < defC - 30:
                                    line.append(defB)
                                    line.append(defC)
                                    self.q.put(line)
                            self.qlock.release()
                except TypeError:
                    pass
                except UnicodeError:
                    pass
                except ValueError:
                    pass
                except KeyboardInterrupt:
                    pass
        except serial.serialutil.SerialException: # FileNotFoundError
            print("Serial error!!")

    def open_connection(self):
        """Opens the connection to the arduino device and returns TRUE if successful"""
        ports = []
        port = None
        ctr = 0
        while port == None:
            if bpy.context.scene.enable_prop == '0':
                return False
            ctr += 1
            if (ctr > 4):
                print("Couldn't find Arduino in reasonable time exiting program")
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
        while not closed:
            if bpy.context.scene.enable_prop == '0':
                return False
            try:
                self._ser = serial.Serial(port,115200, write_timeout=5) # opens the serial connection
                closed = True
            except SerialException:
                print("Problem opening connection retrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    print("Couldn't find open serial port in reasonable time exiting program")
                    return False
                time.sleep(5)
        write = False
        ctr = 0
        while not write: # Tries to write to the arduino so that the Arduino knows to start sending data
            if bpy.context.scene.enable_prop == '0':
                return False
            try:
                self._ser.write(str.encode('A')) # The Arduino waits for a character to start sending data
                print("Sent character to Arduino")
                print("Calibrating...")
                time.sleep(10) # Waits for 10 seconds so that the accelerometer values normalise
                print("Calibrating finished!")
                write =  True
            except:
                print("Couldn't write to the serial port\nRetrying in 5 seconds")
                ctr += 1
                if (ctr > 4):
                    print("Couldn't find write to the serial port in reasonable time exiting program")
                    return False
        return True

    def close_serial(self):
        self._ser.close()

    def run(self):
        time.sleep(3)
        print("slept")
        self.add_buffer()

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"
    _timer = None
    
    def rotate_object(self):
        obj = bpy.context.active_object #Active object which will be rotated
        if (p.distance < 5):
            rot_angle = radians(p.distance) / 2
        elif (p.distance > 15):
            rot_angle = radians(15.0)
        else:
            rot_angle = radians(p.distance)
       
        mat_rot_x = Matrix.Rotation(rot_angle, 4, 'X') #rotation matrix along global X axis
        mat_rot_y = Matrix.Rotation(rot_angle, 4, 'Z') #rotation matrix along global Z axis
        mat_rot_nx = Matrix.Rotation(-rot_angle, 4, 'X')
        mat_rot_ny = Matrix.Rotation(-rot_angle, 4, 'Z')
        
        if not p.q.empty():
            p.qlock.acquire()
            line = p.q.get();
            a = float(line[1])
            b = float(line[2])
            c = float(line[3])
            defB = float(line[7])
            defC = float(line[8]) 
            pi = 3.14159265358979
            p.qlock.release()
            
            loc, rot, scale = obj.matrix_world.decompose()
            mat_loc = Matrix.Translation(loc)
            mat_rot = rot.to_matrix().to_4x4()
            mat_scale = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
              
            rotation = mat_loc

            """Determines the object rotation directions and if the sensor has moved enough to rotate the object"""
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
        if event.type in {'ESC'} or bpy.context.scene.enable_prop == '0':
            bpy.context.scene.enable_prop = '0'
            self.cancel(context)
            print("Exiting program")
            p.do_run = False
            try:
                p.close_serial() # Try to close the serial
            except:
                pass
            try:
                p.qlock.release() # Release the queue lock if it is locked
            except RuntimeError:
                pass
            p.join()
            
            # Updating panel once after program has stopped            
            context.scene.enable_prop = '0'
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    
            bpy.ops.screen.back_to_previous()
            
            # DISABLE FULLSCREEN HERE
            
            return {'FINISHED'}

        if event.type == 'TIMER':
            self.rotate_object()

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
    
class PanelControl(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_category = "EditObject"  # Name seen in tab
    bl_label = "EditObject" # Caption of the opened panel
    bl_idname = "Paneeli"  # Unique not seen name of each panel
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    #bl_context = "objectmode"  # sculpt?
    
    @classmethod
    def poll(cls, context):
        #print("panel poll")
        return context.active_object is not None
       
    def draw(self, context):
        
        scene = context.scene
        object = context.active_object
        
        layout = self.layout       
        row = layout.row()
        row.label(text="Status")
        
        row = layout.row() 
        row.prop(scene,"enable_prop", expand=True)
        
       
        col = layout.column()
        row = layout.row()
        split = row.split(align=True)
        split.operator("mesh.subdivide")
        split.operator("mesh.unsubdivide", text="Unsubsivide")
        
#        row= layout.row()
#        row.operator("mesh.subdivide") #"mesh.primitive_cube_add"
#        
#        row = layout.row()
#        row.operator("mesh.unsubdivide")
        
        row = layout.row()
        bpy.context.active_object.update_from_editmode()
        row.label(text="Number of vertices: %d" % len(object.data.vertices))
        
        col = layout.column()
        col.label(text= "Mode")
        col.prop(scene,"mode_prop", expand=True)
        
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row.operator("object.location_clear", text="Move object to center")
        

class PanelTimer(bpy.types.Operator):
    """This check if program is enabled in panel"""
    bl_idname = "wm.panel_modal_timer"
    bl_label = "Panel Modal Timer"

    _timer = None
    
    lastMode= None 
    curMode = None 
    

    def modal(self, context, event):
        
        modes =["OBJECT", "EDIT", "SCULPT", "TEXTURE_PAINT", "WEIGHT_PAINT", "VERTEX_PAINT"]
           
        if event.type == 'TIMER':
            # When program is enabled in panel and the other thread doesn't exist
            # run the actual program
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

                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                    
            
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        
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
    # Can cause blender to crash
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas: 
            if area.type == 'VIEW_3D':
                if (area.spaces.active.region_3d.view_distance > 10):
                    value = value*2
                elif (area.spaces.active.region_3d.view_distance < 5):
                    value = value / 10
                area.spaces.active.region_3d.view_distance -= value
                return area.spaces.active.region_3d.view_distance

def rotate_camera():
    #bpy.ops.object.delete(use_global=False)
    #bpy.ops.mesh.primitive_cube_add()
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override['area'] = area
            #bpy.ops.view3d.viewnumpad(override, type = 'FRONT')
            #bpy.ops.view3d.view_orbit(type = 'ORBITUP')
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.screen.screen_full_area(override, use_hide_panels=False)
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
#    # This is executed when program is enabled in panel
    global p
    qlock = threading.Lock()
    q = queue.Queue()
    p = SerialLink('serial thread',q, qlock) #Create the thread
    p.start()
    bpy.app.handlers.scene_update_post.append(my_handler)
    print("Thread made and establishing connecion with Arduino device")
    rotate_camera()
    if sys.platform.startswith('win'):
        width, height = get_screen_center()
        set_cursor_position(width, height)

def register():
    bpy.types.Scene.enable_prop = bpy.props.EnumProperty(items = (('0','Stop', ''),('1','Run','')))
    bpy.types.Scene.mode_prop = bpy.props.EnumProperty(items = (('0','Object', ''),('1','Edit',''), ('2','Sculpt',''), ('3','Texture Paint', ''),('4','Weight Paint',''), ('5','Vertex Paint','')))
    bpy.utils.register_module(__name__)
    bpy.app.handlers.scene_update_post.append(panel_handler)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.enable_prop
    del bpy.types.Scene.mode_prop


if __name__ == "__main__":
    register() #  Running from text editor