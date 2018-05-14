#http://effbot.org/tkinterbook/tkinter-classes.htm
from tkinter import *


class App:
    def __init__(self, master):
        
        row1 = Frame(master)
        row1.pack()

        row_status = Frame(master)
        row_status.pack()
        
        row_memory = Frame(master)
        row_memory.pack()

        row_led = Frame(master)
        row_led.pack()

        row_logging = Frame(master)
        row_logging.pack()

        self.label1 = StringVar()
        self.label = Label(row1, textvariable=self.label1)
        self.label.pack(side=LEFT)

        self.get_name = Button(row_status, text='GET NAME', command=self.get_name)
        self.get_name.pack(side=LEFT)

        self.get_id = Button(row_status, text='GET ID', command=self.get_id)
        self.get_id.pack(side=LEFT)

        self.get_vbatt = Button(row_status, text='READ BATTERY VOLTAGE', command=self.get_vbatt)
        self.get_vbatt.pack(side=LEFT)

        self.read_sensors = Button(row_status, text='READ SENSORS', command=self.read_sensors)
        self.read_sensors.pack(side=LEFT)

        self.read_memory = Button(row_memory, text='EXTRACT DATA', command=self.read_memory)
        self.read_memory.pack(side=LEFT)

        self.clear_memory = Button(row_memory, text='CLEAR MEMORY', command=self.clear_memory)
        self.clear_memory.pack(side=LEFT)

        self.red_led_on = Button(row_led, text='RED ON', fg='red', command=self.red_led_on)
        self.red_led_on.pack(side=LEFT)

        self.red_led_off = Button(row_led, text='RED OFF', command=self.red_led_off)
        self.red_led_off.pack(side=LEFT)

        self.green_led_on = Button(row_led, text='GREEN ON', fg='green', command=self.green_led_on)
        self.green_led_on.pack(side=LEFT)

        self.green_led_off = Button(row_led, text='GREEN OFF', command=self.green_led_off)
        self.green_led_off.pack(side=LEFT)

        self.blue_led_on = Button(row_led, text='BLUE ON', fg='blue', command=self.blue_led_on)
        self.blue_led_on.pack(side=LEFT)

        self.blue_led_off = Button(row_led, text='BLUE OFF', command=self.blue_led_off)
        self.blue_led_off.pack(side=LEFT)


        self.v = IntVar()
        self.v.set(2)
        self.radio1 = Radiobutton(row_logging, text='0.2 second', variable=self.v, value=1)
        self.radio1.pack(anchor=W)
        self.radio2 = Radiobutton(row_logging, text='1 second', variable=self.v, value=2)
        self.radio2.pack(anchor=W)
        self.radio3 = Radiobutton(row_logging, text='60 second', variable=self.v, value=3)
        self.radio3.pack(anchor=W)
        
        self.set_rtc = Button(row_logging, text='SET CLOCK', command=self.set_rtc)
        self.set_rtc.pack(side=LEFT)

        self.start_logging = Button(row_logging, text='START Logging', command=self.start_logging)
        self.start_logging.pack(side=LEFT)

        self.stop_logging = Button(row_logging, text='STOP Logging', command=self.stop_logging)
        self.stop_logging.pack(side=LEFT)

        #self.button = Button(row_status, text='QUIT', fg='red', command=row.quit)
        #self.button.pack(side=LEFT)

        #self.text = Text(row_logging)
        #self.text.pack(side=LEFT)

    def get_name(self):
        self.label1.set('一人前')

    def get_id(self):
        print('awake')
    
    def read_memory(self):
        print('avast')

    def clear_memory(self):
        print('hold')

    def start_logging(self):
        print('tight')

    def stop_logging(self):
        print('your')

    def get_vbatt(self):
        print('bun')

    def read_sensors(self):
        print('for')

    def set_rtc(self):
        print('bun')

    def red_led_on(self):
        print('you')

    def red_led_off(self):
        print('do')

    def green_led_on(self):
        print('hold')

    def green_led_off(self):
        print('dear')

    def blue_led_on(self):
        print('wut')

    def blue_led_off(self):
        print('wut')


root = Tk()

app = App(root)

root.mainloop()
root.destroy()




