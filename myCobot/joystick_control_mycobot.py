'''
===================================================================================
This is a practise project of controlling myCobot by Python. The project include 
some design patterns: Observer and Adapter. It also contain mutil thread to  
control myCobot more immediately.

The practise has three goals
- Controlling myCobot
- Usage of design pattern
- Multi-thread programing

The program only can run on Windows due to the dependency of XInput-Python.
I will try to port to Ubuntu or Raspberry Pi.

Auther: Jia-Qi, Song
Date: 2022-03-06
Location: Taichung, Taiwan
-----------------------------------------------------------------------------------
You need to connect a joystrick to controll myCobot. There is a list to show that 
the actions of myCobot can do in the program.

    - `"A"`: go to standing posture.
    - `"B"`: go to sleeping posture.
    - `"X"`: stop the current behavior.
    - `"Y"`: change LED color.
    - `"DPAD_LEFT"`: rotate the selected joint in negative direction.
    - `"DPAD_RIGHT"`: rotate the selected joint in positive direction.
    - `"LEFT_SHOULDER"`: change joint number `i` to `i-1`, change to `6` if `1`. 
    - `"RIGHT_SHOULDER"`: change joint number `i` to `i+1`, change to `1` if `6`.
    
To end the program, press [Ctrl-C] on keyboard or the conbination action
[LEFT_SHOULDER + RIGHT_SHOULDER + START + BACK] on joystrick.
===================================================================================
'''

from pymycobot.mycobot import MyCobot

from threading import Thread
import XInput
import time

class My_Thread(Thread):
    '''An interface inhrit from `threading.Thread`. Add a method `kill()`.'''
    def __init__(self, name):
        super().__init__(name=name)
        
    def kill(self):
        '''Kill the thread.'''
        if self.is_alive():
            if self._tstate_lock.locked():
                self._tstate_lock.release()
            self._stop()
        
class Subject:
    ''' An abstract class used for observer pattern.'''
    def __init__(self):
        self.observers = []
        
    def register(self, *observers):
        '''Make registers of some observers.
        
        Args:
            *observers (Observer, ...):  one or more observers register this subject.
            
        Example:
        ```
        subject = Subject()
        
        register(observer)
        register(observer_1, observer_2, ...)
        ```
        Note:
            If you want to limit some type of observer, try this.
        ```
        class My_Subject(Subject):
            def register(self, *observers):
                accept_types = [Observer_1, Observer_2]
                for o in observers:
                    if type(o) in accept_types:
                        super().register(o)
        ```
        ```
        '''
        self.observers.extend(observers)
    
    def disregister(self, observer):
        '''Make disregister of an observer.

        Args:
            observer (Observer): an observer disregisters this subject.
        '''
        index = self.observers.index(observer)
        self.observers.pop(index)
    
    def notify(self, obj):
        for observer in self.observers:
            observer.update(obj)
            
class Observer:
    '''An interface used for observer pattern.'''
    def __init__(self):
        self.observers = []
    
    def update(self, obj):
        '''The example of implementing the function.

        Args:
            obj (Object): packaged datas.
        '''
        print("Default observer:", obj)
            
class Joystick_Detector(My_Thread, Subject):
    '''
        Subject in observer pattern.
    '''
    def __init__(self, name="Joysticks Detector"):
        My_Thread.__init__(self, name)
        Observer.__init__(self)
        
    def run(self):
        while True:
            for event in XInput.get_events():
                for observer in self.observers:
                    observer.update(event)

class Joystick_Signal_Adapter(My_Thread, Observer, Subject):
    '''An one-way adapter from ``Joystick_Detector` to `Customized_MyCobot`.
    This class gets XInput signals and translates these to notify MyCobot every 0.1 seconds.
    
    The class implements `My_Thread`, `Observer` and `Subject`.
    It is a subject of `Customized_MyCobot`, and an observer of `Joystrick_Detector`.
    '''
    def __init__(self, name="Joystick Signal Adapter"):
        My_Thread.__init__(self, name)
        Observer.__init__(self)
        Subject.__init__(self)
        self.pressed_button = set()
        self.trigger_values = [0, 0]    # L, R
        self.stick_values = [(0, 0), (0, 0)]
        self.observers = []
        self.keyboard_interrupt = None
        
    # Thread interfaces
    def run(self):        
        '''The implementation of `My_Thread.run()`. 
        The sample rate is 10 hz so it notify `MyCobot` every 0.1 seconds.
        '''
        
        try:
            while True:
                self.notify()
                time.sleep(0.1)
        except KeyboardInterrupt as e:
            self.keyboard_interrupt = e
    
    # Observer interfaces
    def update(self, e: XInput.Event):
        '''The implementation of `Observer.update()`.
        Catch the event from `Joystick_Detector` and record the signals.

        Args:
            e (XInput.Event): the event from `Joystrick_Detector`.
        '''

        if e.user_index != 0:
            return
        
        if e.type == XInput.EVENT_BUTTON_PRESSED:
            self.pressed_button.add(e.button)
        elif e.type == XInput.EVENT_BUTTON_RELEASED:
            self.pressed_button.remove(e.button)
        elif e.type == XInput.EVENT_TRIGGER_MOVED:
            i = e.trigger
            self.trigger_values[i] = e.value
        elif e.type == XInput.EVENT_STICK_MOVED:
            i = e.stick
            self.stick_values[i] = e.dir
            
    # Subject interfaces
    def notify(self):
        '''The implementation of `Subject.notify()`. Notify the stored signals.
        
        The structure is like the code below:
        ```
        signals = {
            'buttons': set(),
            'triggers': [LT, RT],
            'sticks': [(xL, yL), (xR, yR)]
        }
        ```
            - `buttons`: a set of pressed buttons.
            - `triggers`: the values of left and right triggers.
            - `stick`: the coordinates `(x, y)` of left and right stick.
        '''
        
        signals = {
            'buttons': self.pressed_button,
            'triggers': self.trigger_values,
            'sticks': self.stick_values
        }
        
        super().notify(signals)
 
class Customized_MyCobot(MyCobot, Observer):
    '''A class which has customized functions of myCobot. This class can control myCobot by a joystrick.

    This class inherits from `pymycobot.mycobot.MyCobot` and implements `Observer`.
    '''
    _MIN_ANGLES = [-160, -100, -150, -150, -160, -180]
    _MAX_ANGLES = [160, 100, 150, 150, 160, 180]
    
    def __init__(self):
        MyCobot.__init__(self, 'COM3')
        Observer.__init__(self)
        
        self.color = (0, 255, 0)    # R, G, B
        self.joint = 1
        
        self.set_color(*self.color)
        print(f"Current Joint Number {self.joint}", end='\r')
    
    def next_color(self):
        '''Change the color of LED on Atom.'''
        r, g, b = self.color
        
        if r == 0 and g > 0:
            g = max(g - 32, 0)
            b = 255 - g
        elif g == 0 and b > 0:
            b = max(b - 32, 0)
            r = 255 - b
        elif b == 0 and r > 0:
            r = max(r - 32, 0)
            g = 255 - r
        
        self.color = (r, g, b)
        self.set_color(r, g, b)
    
    def go_sleep(self):
        '''Make myCobot going to sleeping posture.
        For the safety, call this method before `release_all_servos()`
        '''
        self.send_angles([83, 140, -150, 154, 87, 0], 50)

    def _get_combination_action(self, signals):
        if 'LEFT_SHOULDER' in signals['buttons'] and \
           'RIGHT_SHOULDER' in signals['buttons'] and \
           'START' in signals['buttons'] and \
           'BACK' in signals['buttons']:
               return "end_program"
        
    # Observer interface
    def update(self, signals):
        '''This is the implementation of `Observer.update()`.
        MyCobot gets joystric signals from `Joystick_Signal_Adapter` and dose something by one of those.
        
        The priority of the signal and the behavior from high to low is:
        - `"A"`: go to standing posture.
        - `"B"`: go to sleeping posture.
        - `"X"`: stop the current behavior.
        - `"Y"`: change LED color.
        - `"DPAD_LEFT"`: rotate the selected joint in negative direction.
        - `"DPAD_RIGHT"`: rotate the selected joint in positive direction.
        - `"LEFT_SHOULDER"`: change joint number `i` to `i-1`, change to `6` if `1`. 
        - `"RIGHT_SHOULDER"`: change joint number `i` to `i+1`, change to `1` if `6`.
        
        The conbination `"LEFT_SHOULDER", "RIGHT_SHOULDER", "START", "BACK"` will raise `KeyboardInterrupt` to end the program.

        Args:
            signals (dict): the structure of signals see `Joystrick_Signal_Adapter.notify()`.     
        '''
        if len(signals['buttons']) > 0:
            if self._get_combination_action(signals) == "end_program":
                raise KeyboardInterrupt("")
            elif 'A' in signals['buttons']:
                self.send_angles([0,0,0,0,0,0], 50)
            elif 'B' in signals['buttons']:
                self.send_angles([83, 140, -150, 154, 87, 0], 50)
            elif 'X' in signals['buttons']:
                self.stop()
            elif 'Y' in signals['buttons']:
                self.next_color()
            elif 'DPAD_LEFT' in signals['buttons']:
                theta: float
                if self.joint == 6:
                    theta = self.get_angles()[self.joint - 1] - 179
                    if theta < -180:
                        theta += 360
                else:
                    theta = self._MIN_ANGLES[self.joint - 1]
                self.send_angle(self.joint, theta, 10)
            elif 'DPAD_RIGHT' in signals['buttons']:
                theta: float
                if self.joint == 6:
                    theta = self.get_angles()[self.joint - 1] + 179
                    if theta > 180:
                        theta -= 360
                else:
                    theta = self._MAX_ANGLES[self.joint - 1]
                self.send_angle(self.joint, theta, 10)
            elif 'LEFT_SHOULDER' in signals['buttons']:
                if self.joint == 1:
                    self.joint = 6
                else:
                    self.joint -= 1
            elif 'RIGHT_SHOULDER' in signals['buttons']:
                if self.joint == 6:
                    self.joint = 1
                else:
                    self.joint += 1
            print(f"Current Joint Number {self.joint}", end='\r')
    
def main():
    '''Main procedure of the project.'''
    
    print(__doc__)
    
    mc = Customized_MyCobot()
    sa = Joystick_Signal_Adapter()
    jd = Joystick_Detector()
    
    jd.register(sa)
    sa.register(mc)

    try:
        jd.start()
        sa.start()
        
        # detect KeyboardInterrupt from thread Joystrick Signal Adapter
        # KeyboardInterrupt by keyboard is at main
        while True:
            if sa.keyboard_interrupt is not None:
                raise sa.keyboard_interrupt
        
    except KeyboardInterrupt:
        print('User stopped the program.')
        
    finally:
        jd.disregister(sa)
        sa.disregister(mc)

        jd.kill()
        sa.kill()
        
        mc.go_sleep()
        print('MyCobot is going to sleep, wait for 10 seconds.')
        for i in range(10, 0, -1):
            print(f'\r[{i}] ', end='')
            time.sleep(1)
            
        mc.release_all_servos()
        print('\r[done]')
            
if __name__ =='__main__':
    main()
    