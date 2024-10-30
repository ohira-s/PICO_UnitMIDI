###############################################
# Unit-MIDI synthesizer with Raspberry Pi PICO
###############################################
from machine import Pin, UART, I2C
import time, utime, os, json
import random
import _thread
from micropython import const

# Class objects
sdcard_obj         = None   # SD Card
device_manager_obj = None   # Device manager
thread_manager_obj = None   # Thread manager
joystick_obj       = None   # Joy Stick
midi_obj           = None   # MIDI
sequencer_obj      = None   # Sequencer
application        = None   # Application


########################
# Device Manager Class
########################
class device_manager_class():
    # Constructor
    def __init__(self):
        self.devices = []

    # Add a device
    def add_device(self, device):
        self.devices.append(device)

    # Call device controller in each device
    def device_control(self):
        for device in self.devices:
            device.controller()

    # Call device controller in a thread
    def device_control_thread(self, thread_manager, timer=10):
        while not thread_manager.exit_thread():
            self.device_control()
            utime.sleep_ms(timer)
            
        thread_manager.exit_thread(True)
        
################# End of Device Controller Class Definition #################


########################
# Thread Manager Class
########################
class thread_manager_class():
    # Constructor
    def __init__(self):
        self.working = False
        self.stop = False
        
    # Get thread working status
    def is_working(self):
        return self.working
        
    # Get thread stop status
    def will_be_stopped(self):
        return self.stop
        
    # Set / Get thread stop flag, nust be called when a thread is terminated in the thread process.
    def exit_thread(self, flag=None):
        if not flag is None:
            self.working = False

        return self.stop

    # Stop thread
    def stop_thread(self):
        self.stop = True
        while self.is_working():
            utime.sleep_ms(10)
            
        self.stop = False

    # Start thread
    def start(self, func, args):
        if self.is_working() or self.will_be_stopped():
            return False
        
        try:
            _thread.start_new_thread(func, args)
            self.working = True
            return True
        except:
            self.working = False
            self.stop = False
            return False


###################
### SD card class
###   Use internal file system in PICO.
###################
class sdcard_class:
    # Constructor
    def __init__(self):
        self.file_opened = None

    # Initialize SD Card device
    def setup(self):
        pass

    # Opened file
    def file_opened(self):
        return self.file_opened

    # File open, needs to close the file
    def file_open(self, path, fname, mode = 'r'):
        try:
            if not self.file_opened is None:
                self.file_opened.close()
                self.file_opened = None

            self.file_opened = open(path + fname, mode)
            return self.file_opened

        except Exception as e:
            self.file_opened = None
            print('sccard_class.file_open Exception:', e, path, fname, mode)

        return None

    # Close the file opened currently
    def file_close(self):
        try:
            if not self.file_opened is None:
                self.file_opened.close()

        except Exception as e:
            print('sdcard_class.file_open Exception:', e, path, fname, mode)

        self.file_opened = None

    # Read JSON format file, then retun JSON data
    def json_read(self, path, fname):
        json_data = None
        try:
            with open(path + fname, 'r') as f:
                json_data = json.load(f)

        except Exception as e:
            print('sccard_class.json_read Exception:', e, path, fname)

        return json_data

    # Write JSON format file
    def json_write(self, path, fname, json_data):
        try:
            with open(path + fname, 'w') as f:
                json.dump(json_data, f)

            return True

        except Exception as e:
            print('sccard_class.json_write Exception:', e, path, fname)

        return False

################# End of SD Card Class Definition #################


########################
### LCD AQM0802A class
########################
class aqm0802a_lcd_class:
    def __init__(self, address=0x3e, unit=1, scl_pin=7, sda_pin=6):
        self._ST7032  = address
        self._SETTING = const(0x00)
        self._DISPLAY = const(0x40)
        
        self.screen = ['        ', '        ']
        
        self.lcd = I2C(unit, scl=Pin(scl_pin), sda=Pin(sda_pin))
        device_list = self.lcd.scan()
        print('I2C DEVICES:', unit, device_list)

        orders = [b'\x38', b'\x39', b'\x14', b'\x73', b'\x56', b'\x6C',
                  b'\x38', b'\x0C', b'\x01']
        utime.sleep_ms(40)
        for order in orders[:6]:
            self.lcd.writeto_mem(self._ST7032, self._SETTING, order)
            utime.sleep_ms(1)
        utime.sleep_ms(200)
        for order in orders[6:]:
            self.lcd.writeto_mem(self._ST7032, self._SETTING, order)
            utime.sleep_ms(1)
        utime.sleep_ms(1)

    def _writeCMD(self, cmd):
        buf = bytearray([self._SETTING, cmd])
        self.lcd.writeto(self._ST7032, buf)

    def clear(self):
        buf = bytearray([self._SETTING, 0x01])
        self.lcd.writeto(self._ST7032, buf)
        utime.sleep_ms(1)

    def setContrast(self, contrast):
        if contrast < 0:
            contrast = 0
        if contrast > 0x0f:
            contrast = 0x0f
        self._writeCMD(0x39)
        self._writeCMD(0x70 + contrast)

    def home(self):
        self._writeCMD(0x02)
        utime.sleep_ms(10)

    def setCursor(self, x, y):
        if x < 0: x = 0
        if y < 0: y = 0
        addr = y * 0x40 + x
        self._writeCMD(0x80 + addr)
        utime.sleep_ms(2)

    # Show text immediately
    def clearScreen(self):
        self.screen = ['        ', '        ']
        
    # Show text immediately
    def dispText(self, str_show, x=None, y=None):
        if not x is None and not x is None:
            self.setCursor(x, y)

        for ch in str_show:
            self.lcd.writeto_mem(self._ST7032, self._DISPLAY, ch.encode())

    # Set text on the screen buffer
    def setText(self, str_show, x=None, y=None):
        if x is None:
            x = 0
            
        if y is None:
            y = 0

        elif x < 0 or x > 7 or y < 0 or y > 1:
            return
        
        str_show = str_show[: (8 - x)]
        line = list(self.screen[y])
        for ch in str_show:
            line[x] = ch
            x = x + 1
            
        self.screen[y] = ''.join(line)

    # Show the screen buffer
    def show(self):
        self.setCursor(0, 0)
        for row_str in self.screen:
            for ch in row_str:
                self.lcd.writeto_mem(self._ST7032, self._DISPLAY, ch.encode())

            self.setCursor(0, 1)

################# End of LCD AQM0802A Class Definition #################


#####################
### Unit-MIDI class
#####################
class MIDIUnit:
    # Constructor
    #   uart_unit: PICO UART unit number 0 or 1
    #   port     : A tuple of (Tx, Rx)
    #              This argument is NOT USED, to keep compatibility with M5Stack CORE2.
    def __init__(self, uart_unit=0, port=None):
        self._uart = UART(uart_unit, 31250)
        
    def midi_out(self, midi_msg):
        self._uart.write(midi_msg)
    
    def set_master_volume(self, vol):
        midi_msg = bytearray([0xF0, 0x7F, 0x7F, 0x04, 0x01, 0, vol & 0x7f, 0xF7])
        self.midi_out(midi_msg)

    def set_instrument(self, gmbank, channel, prog):
        midi_msg = bytearray([0xC0 + channel, prog])
        self.midi_out(midi_msg)

    def set_note_on(self, channel, note_key, velosity):
        midi_msg = bytearray([0x90 + channel, note_key, velosity])
        self.midi_out(midi_msg)

    def set_note_off(self, channel, note_key):
        midi_msg = bytearray([0x90 + channel, note_key, 0])
        self.midi_out(midi_msg)

    def set_all_notes_off(self, channel = None):
        midi_msg = bytearray([0xB0 + channel, 0x78, 0])
        self.midi_out(midi_msg)

    def set_reverb(self, channel, prog, level, feedback):
        status_byte = 0xB0 + channel
        midi_msg = bytearray([status_byte, 0x50, prog, status_byte, 0x5B, level])
        self.midi_out(midi_msg)
        if feedback > 0:
            midi_msg = bytearray([0xF0, 0x41, 0x00, 0x42, 0x12, 0x40, 0x01, 0x35, feedback, 0, 0xF7])
            self.midi_out(midi_msg)
            
    def set_chorus(self, channel, prog, level, feedback, delay):
        status_byte = 0xB0 + channel
        midi_msg = bytearray([status_byte, 0x51, prog, status_byte, 0x5D, level])
        self.midi_out(midi_msg)
        if feedback > 0:
            midi_msg = bytearray([0xF0, 0x41, 0x00, 0x42, 0x12, 0x40, 0x01, 0x3B, feedback, 0, 0xF7])
            self.midi_out(midi_msg)

        if delay > 0:
            midi_msg = bytearray([0xF0, 0x41, 0x00, 0x42, 0x12, 0x40, 0x01, 0x3C, delay, 0, 0xF7])
            self.midi_out(midi_msg)

    def set_vibrate(self, channel, rate, depth, delay):
        status_byte = 0xB0 + channel
        midi_msg = bytearray([status_byte, 0x63, 0x01, 0x62, 0x08, 0x06, rate, status_byte, 0x63, 0x01, 0x62, 0x09, 0x06, depth, status_byte, 0x63, 0x01, 0x62, 0x0A, 0x06, delay])
        self.midi_out(midi_msg)

    def set_pitch_bend(self, channel, value):
        status_byte = 0xE0 + channel
        lsb = value & 0x7f					# Least
        msb = (value >> 7) & 0x7f			# Most
#        print('PITCH BEND value=', channel, value, lsb, msb) 
        midi_msg = bytearray([status_byte, lsb, msb])
#        midi_msg = bytearray([status_byte, value & 0xef, (value >> 7) & 0xff])		# Original
        self.midi_out(midi_msg)

    def set_pitch_bend_range(self, channel, value):
        status_byte = 0xB0 + channel
        midi_msg = bytearray([status_byte, 0x65, 0x00, 0x64, 0x00, 0x06, value & 0x7f])
        self.midi_out(midi_msg)

################# End of Unit-MIDI Class Definition #################
        

################
### MIDI class
################
class midi_class:
    def __init__(self, synthesizer_obj, sdcard_obj):
        self.synth = synthesizer_obj
        self.midi_uart = self.synth._uart
        self.sdcard_obj = sdcard_obj
        self.master_volume = 127
        self.key_trans = 0
        self.key_names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        self.USE_GMBANK = 0                              # GM bank number (normally 0, option is 127)
        #self.USE_GMBANK = 127
        self.GM_FILE_PATH = '/SYNTH/MIDIFILE/'       # GM program names list file path

    # Setup
    def setup(self, uart = None):
        if not uart is None:
            self.midi_uart = uart

    # Set/Get GM bank
    def gmbank(self, bank = None):
        if bank is None:
            return self.USE_GMBANK
    
        self.USE_GMBANK = bank

    # Native synthesize object
    def synthesizer_obj(self):
        return self.shynth

    # Native UART object
    def uart_obj(self):
        return self.midi_uart

    # Set/Get GM_FILE_PATH
    def gm_file_path(self, path = None):
        if path is None:
            return self.GM_FILE_PATH

        self.GM_FILE_PATH = path

    # Get GM prgram name
    #   gmbank: GM bank number
    #   program: GM program number
    def get_gm_program_name(self, gmbank, program):
        f = self.sdcard_obj.file_open(self.GM_FILE_PATH, 'GM' + str(gmbank) + '.TXT')
        if not f is None:
            for mf in f:
                mf = mf.strip()
                if len(mf) > 0:
                    if program == 0:
                        self.sdcard_obj.file_close()
                        return mf

                program = program - 1

            self.sdcard_obj.file_close()

        return 'UNKNOWN'

    # Get key name of key number
    #   key_num: MIDI note number
    def key_name(self, key_num):
        octave = int(key_num / 12) - 1
        return self.key_names[key_num % 12] + ('' if octave < 0 else str(octave))

    # MIDI OUT
    def midi_out(self, midi_bytes):
        self.midi_uart.write(midi_bytes)

    # MIDI IN
    def midi_in(self):
        midi_rcv_bytes = self.midi_uart.any()
        if midi_rcv_bytes > 0:
            return self.midi_uart.read()

        return None

    # MIDI IN --> OUT
    # Receive MIDI IN data (UART), then send it to MIDI OUT (UART)
    def midi_in_out(self):
        midi_bytes = self.midi_in()
        if not midi_bytes is None:
            self.midi_out(midi_bytes)
            return True

        return False

    # Set key transopose
    def key_transpose(self, trans = None):
        if not trans is None:
            self.key_trans = trans
  
        return self.key_trans

    # Master volume
    def set_master_volume(self, vol):
        self.master_volume = vol
        self.synth.set_master_volume(vol)

    # Get master volume
    def get_master_volume(self):
        return self.master_volume

    # Set instrument
    def set_instrument(self, gmbank, channel, prog):
        self.synth.set_instrument(gmbank, int(channel), int(prog))

    # Note on
    def set_note_on(self, channel, note_key, velosity, transpose = False):
        self.synth.set_note_on(channel, note_key + (self.key_trans if transpose else 0), velosity)
  
    # Note off
    def set_note_off(self, channel, note_key, transpose = False):
        self.synth.set_note_off(channel, note_key + (self.key_trans if transpose else 0))

    # Notes off
    def notes_off(self, channel, note_keys, transpose = False):
        for nk in note_keys:
            self.set_note_off(channel, nk, transpose)

    # All notes off
    def set_all_notes_off(self, channel = None):
        if channel is None:
            for ch in range(16):
                self.set_all_notes_off(ch)
        else:
            self.synth.set_all_notes_off(channel)

    # Reverb
    def set_reverb(self, channel, prog, level, feedback):
        self.synth.set_reverb(channel, prog, level, feedback)

    # Chorus
    def set_chorus(self, channel, prog, level, feedback, delay):
        self.synth.set_chorus(channel, prog, level, feedback, delay)

    # Vibrate
    def set_vibrate(self, channel, rate, depth, delay):
        self.synth.set_vibrate(channel, rate, depth, delay)

    # Pitch Bend
    def set_pitch_bend(self, channel, value):
        self.synth.set_pitch_bend(channel, value)

    # Pitch Bend Range
    def set_pitch_bend_range(self, channel, value):
        self.synth.set_pitch_bend_range(channel, value)

################# End of MIDI Class Definition #################


########################
# MIDI-IN Player class
########################
class midi_in_player_class():
  def __init__(self, midi_obj, sdcard_obj):
    self.sdcard_obj = sdcard_obj
    self.midi_obj = midi_obj
    self.midi_in_ch = 0                               # MIDI IN channel to edit
    self.midi_in_set_num = 0                          # MIDI IN setting file number to load/save
    self.MIDI_IN_FILE_PATH = '/SYNTH/MIDIUNIT/' 	  # MIDI IN setting files path
    self.MIDI_SET_FILES_MAX = 1000                    # Maximum MIDI IN setting files

    # MIDI-IN player
    self.midi_in_settings = []                        # MIDI IN settings for each channel, see setup()
                                                      # Each channel has following data structure
                                                      #     {'program':0, 'gmbank':0, 'reverb':[0,0,0], 'chorus':[0,0,0,0], 'vibrate':[0,0,0]}
                                                      #     {'program':PROGRAM, 'gmbank':GM BANK, 'reverb':[PROGRAM,LEVEL,FEEDBACK], 'chorus':[PROGRAM,LEVEL,FEEDBACK,DELAY], 'vibrate':[RATE,DEPTH,DELAY]}

    # SYNTH settings
    for ch in range(16):
      self.midi_in_settings.append({'program':0, 'gmbank':0, 'reverb':[0,0,0], 'chorus':[0,0,0,0], 'vibrate':[0,0,0]})

  # Set midi_in_setting
  def set_midi_in_setting(self, val):
    self.midi_in_settings = val

  def set_midi_in_setting3(self, channel, key_str, val):
    self.midi_in_settings[channel][key_str] = val

  def set_midi_in_setting4(self, channel, key_str, idx, val):
    self.midi_in_settings[channel][key_str][idx] = val

  # Get midi_in_setting
  def get_midi_in_setting(self, channel = None, key_str = None):
    if channel is None:
      return self.midi_in_settings
    
    if key_str is None:
      return self.midi_in_settings[channel]

    return self.midi_in_settings[channel][key_str]

  # Set/Get the current MIDI-IN channel
  def midi_in_channel(self, channel = None):
    if channel is None:
      return self.midi_in_ch
    
    self.midi_in_ch = channel
    return self.midi_in_ch

  # Set/Get midi_in_set_num
  def set_midi_in_set_num(self, num = None):
    if num is None:
      return self.midi_in_set_num
    
    self.midi_in_set_num = num % self.MIDI_SET_FILES_MAX
    return self.midi_in_set_num

  # Set/Get MIDI_IN_FILE_PATH
  def set_midi_in_file_path(self, path = None):
    if path is None:
      return self.MIDI_IN_FILE_PATH
    
    self.MIDI_IN_FILE_PATH = path
    return self.MIDI_IN_FILE_PATH

  # Set/Get MIDI_SET_FILES_MAX
  def set_midi_set_files_max(self, num = None):
    if num is None:
      return self.MIDI_SET_FILES_MAX
    
    self.MIDI_SET_FILES_MAX = num
    return self.MIDI_SET_FILES_MAX

  # Write MIDI IN settings to SD card
  #   num: File number (0..999)
  def write_midi_in_settings(self, num):
    # Write MIDI IN settings as JSON file
    self.sdcard_obj.json_write(self.MIDI_IN_FILE_PATH, 'MIDISET{:0=3d}.json'.format(num), self.midi_in_settings)

  # Read MIDI IN settings from SD card
  #   num: File number (0..999)
  def read_midi_in_settings(self, num):
    # Read MIDI IN settings JSON file
    rdjson = None
    rdjson = self.sdcard_obj.json_read(self.MIDI_IN_FILE_PATH, 'MIDISET{:0=3d}.json'.format(num))
    if not rdjson is None:
      # Default values
      for ch in range(16):
        kys = rdjson[ch]
        if not 'program' in kys:
          rdjson[ch]['program'] = 0
        if not 'gmbank' in kys:
          rdjson[ch]['gmbank'] = 0
        if not 'reverb' in kys:
          rdjson[ch]['reverb'] = [0,0,0]
        if not 'chorus' in kys:
          rdjson[ch]['chorus'] = [0,0,0,0]
        if not 'vibrate' in kys:
          rdjson[ch]['vibrate'] = [0,0,0]
    
    return rdjson

  # Send a MIDI channel settings to Unit-MIDI
  #   ch: MIDI channel
  def send_midi_in_settings(self, ch):
    self.midi_obj.set_instrument(self.midi_in_settings[ch]['gmbank'], ch, self.midi_in_settings[ch]['program'])
    self.midi_obj.set_reverb(ch, self.midi_in_settings[ch]['reverb'][0], self.midi_in_settings[ch]['reverb'][1], self.midi_in_settings[ch]['reverb'][2])
    self.midi_obj.set_chorus(ch, self.midi_in_settings[ch]['chorus'][0], self.midi_in_settings[ch]['chorus'][1], self.midi_in_settings[ch]['chorus'][2], self.midi_in_settings[ch]['chorus'][3])
    self.midi_obj.set_vibrate(ch, self.midi_in_settings[ch]['vibrate'][0], self.midi_in_settings[ch]['vibrate'][1], self.midi_in_settings[ch]['vibrate'][2])

  # Send all MIDI channel settings
  def send_all_midi_in_settings(self):
    for ch in range(16):
      self.send_midi_in_settings(ch)

  # Set and show new MIDI channel for MIDI-IN player
  #   dlt: MIDI channel delta value added to the current MIDI IN channel to edit.
  def set_midi_in_channel(self, dlt):
    self.midi_in_ch = (self.midi_in_ch + dlt) % 16
    self.set_midi_in_program(0)

    midi_in_reverb = self.midi_in_settings[self.midi_in_ch]['reverb']
    self.set_midi_in_reverb(midi_in_reverb[0], midi_in_reverb[1], midi_in_reverb[2])

    midi_in_chorus = self.midi_in_settings[self.midi_in_ch]['chorus']
    self.set_midi_in_chorus(midi_in_chorus[0], midi_in_chorus[1], midi_in_chorus[2], midi_in_chorus[3])

    midi_in_vibrate = self.midi_in_settings[self.midi_in_ch]['vibrate']
    self.set_midi_in_vibrate(midi_in_vibrate[0], midi_in_vibrate[1], midi_in_vibrate[2])

    return self.midi_in_ch

  # Set and show new program to the current MIDI channel for MIDI-IN player
  #   dlt: GM program delta value added to the current MIDI IN channel to edit.
  def set_midi_in_program(self, dlt):
    self.midi_in_settings[self.midi_in_ch]['program'] = (self.midi_in_settings[self.midi_in_ch]['program'] + dlt) % 128
    midi_in_program = self.midi_in_settings[self.midi_in_ch]['program']
    self.midi_obj.set_instrument(self.midi_in_settings[self.midi_in_ch]['gmbank'], self.midi_in_ch, midi_in_program)


  # Set and show new master volume value
  #   dlt: Master volume delta value added to the current value.
  def set_synth_master_volume(self, dlt):
    master_volume = self.midi_obj.get_master_volume() + dlt
    if master_volume < 1:
      master_volume = 0
    elif master_volume > 127:
      master_volume = 127

    self.midi_obj.set_master_volume(master_volume)


  # Set reverb parameters for the current MIDI IN channel
  #   prog : Reverb program
  #   level: Reverb level
  #   fback: Reverb feedback
  def set_midi_in_reverb(self, prog=None, level=None, fback=None):
    disp = None
    if not prog is None:
      self.midi_in_settings[self.midi_in_ch]['reverb'][0] = prog
      disp = prog

    if not level is None:
      self.midi_in_settings[self.midi_in_ch]['reverb'][1] = level
      disp = level
      
    if not fback is None:
      self.midi_in_settings[self.midi_in_ch]['reverb'][2] = fback
      disp = fback

    midi_in_reverb = self.midi_in_settings[self.midi_in_ch]['reverb']
    if not disp is None:
      self.midi_obj.set_reverb(self.midi_in_ch, midi_in_reverb[0], midi_in_reverb[1], midi_in_reverb[2])


  # Set chorus parameters for the current MIDI-IN channel
  #   prog : Chorus program
  #   level: Chorus level
  #   fback: Chorus feedback
  #   delay: Chorus delay
  def set_midi_in_chorus(self, prog=None, level=None, fback=None, delay=None):
    send = False
    if not prog is None:
      self.midi_in_settings[self.midi_in_ch]['chorus'][0] = prog
      send = True

    if not level is None:
      self.midi_in_settings[self.midi_in_ch]['chorus'][1] = level
      send = True
      
    if not fback is None:
      self.midi_in_settings[self.midi_in_ch]['chorus'][2] = fback
      send = True
      
    if not delay is None:
      self.midi_in_settings[self.midi_in_ch]['chorus'][3] = delay
      send = True

    midi_in_chorus = self.midi_in_settings[self.midi_in_ch]['chorus']
    if send:
      self.midi_obj.set_chorus(self.midi_in_ch, midi_in_chorus[0], midi_in_chorus[1], midi_in_chorus[2], midi_in_chorus[3])


  # Set vibrate parameters for the current MIDI-IN channel
  #   level: Vibrate level
  #   depth: Vibrate depth
  #   delay: Vibrate delay
  def set_midi_in_vibrate(self, rate=None, depth=None, delay=None):
    send = False
    if not rate is None:
      self.midi_in_settings[self.midi_in_ch]['vibrate'][0] = rate
      send = True

    if not depth is None:
      self.midi_in_settings[self.midi_in_ch]['vibrate'][1] = depth
      send = True
      
    if not delay is None:
      self.midi_in_settings[self.midi_in_ch]['vibrate'][2] = delay
      send = True

    midi_in_vibrate = self.midi_in_settings[self.midi_in_ch]['vibrate']
    if send:
      self.midi_obj.set_vibrate(self.midi_in_ch, midi_in_vibrate[0], midi_in_vibrate[1], midi_in_vibrate[2])

################# End of MIDI-IN Player Class Definition #################


###################
# Sequencer Class
###################
class sequencer_class():
  # self.seq_channel: Sequencer channel data
  #   [{'gmbank': <GM bank>, 'program': <GM program>, 'volume': <Volume ratio>}, ..]

  # self.seq_score: Sequencer score data
  #   [
  #     {
  #       'time': <Note on time>,
  #       'max_duration': <Maximum duration in note off times>
  #       'notes': [
  #                  {
  #                   'channel': <MIDI channel>,
  #                   'note': <Note number>, 'velocity': <Velocity>, 'duration': <Note on duration>
  #                  }
  #                ]
  #     }
  #   ] 

  # self.seq_score_sign: Signs on the score
  # [
  #    {
  #       'time': <Signs on time>,
  #       'loop' <True/False>       Repeat play from here
  #       'skip' <True/False>       Bar to skip in repeat play, skip to next to repeat bar
  #       'repeat' <True/False>     Repeat here, go back to loop
  #    }
  # ]

  # Sequencer controls
  #   'tempo': Play a quoter note 'tempo' times per a minutes 
  #   'mini_note': Minimum note length (4,8,16,32,64: data are 2,3,4,5,6 respectively) 
  #   'time_per_bar': Times (number of notes) per bar
  #   'disp_time': Time span to display on sequencer
  #   'disp_key': Key spans to display on sequencer each track
  #   'time_cursor': Time cursor to edit note
  #   'key_cursor': Key cursors to edit note each track
  #   'program': Program number for each MIDI channel

  # self.seq_parm_repeat: Current time cursor position or None

  # Constructor
  def __init__(self, midi_obj, sdcard_obj):
    self.midi_obj = midi_obj
    self.sdcard_obj = sdcard_obj
    self.seq_channel = None
    self.seq_score = None
    self.seq_score_sign = None
    self.seq_parm_repeat = None
    self.seq_control = {'tempo': 120, 'mini_note': 4, 'time_per_bar': 4, 'disp_time': [0,12], 'disp_key': [[57,74],[57,74]], 'time_cursor': 0, 'key_cursor': [60,60], 'program':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], 'gmbank':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}

    # View method delegation
    self.view_delegate_obj = self

    # Sequencer file
    self.SEQ_FILE_LOAD = 0
    self.SEQ_FILE_SAVE = 1
    self.SEQ_FILE_NOP  = 2

    # Sequencer file
    self.seq_file_number = 0                               # Sequencer file number
    self.seq_file_ctrl = self.SEQ_FILE_NOP                 # Currnet MIDI IN setting file operation id
    self.seq_file_ctrl_label = ['L', 'S', '-']             # Load / Save / nop

    # Sequencer parameter
    #   Sequencer parameter strings to show
    self.SEQUENCER_PARM_CHANNEL = 0                        # Change a track MIDI channel
    self.SEQUENCER_PARM_PROGRAM = 1                        # Change program of MIDI channel
    self.SEQUENCER_PARM_CHANNEL_VOL = 2                    # Change volume ratio of MIDI channel
    self.SEQUENCER_PARM_TIMESPAN = 3                       # Change times to display
    self.SEQUENCER_PARM_STRETCH_ONE = 4                    # Insert/Delete a time in the current MIDI channel
    self.SEQUENCER_PARM_STRETCH_ALL = 5                    # Insert/Delete a time in all MIDI channels
    self.SEQUENCER_PARM_VELOCITY = 6                       # Change note velocity
    self.SEQUENCER_PARM_NOTES_BAR = 7                      # Change number of notes in a bar
    self.SEQUENCER_PARM_RESOLUTION = 8                     # Resolution up
    self.SEQUENCER_PARM_CLEAR_ONE = 9                      # Clear all notes in the current MIDI channel
    self.SEQUENCER_PARM_CLEAR_ALL = 10                     # Clear all notes in all MIDI channels
    self.SEQUENCER_PARM_PLAYSTART = 11                     # Start and end time to play with sequencer
    self.SEQUENCER_PARM_PLAYEND = 12                       # End time to play with sequencer
    self.SEQUENCER_PARM_TEMPO = 13                         # Change tempo to play sequencer
    self.SEQUENCER_PARM_MINIMUM_NOTE = 14                  # Change minimum note length
    self.SEQUENCER_PARM_REPEAT = 15                        # Set repeat signs (NONE/LOOP/SKIP/REPEAT)
    self.seq_parm = self.SEQUENCER_PARM_CHANNEL                 # Current sequencer parameter index (= initial)

    # Sequencer parameter
    #   Sequencer parameter strings to show
    self.seq_parameter_names = ['MDCH', 'MDPG', 'CHVL', 'TIME', 'STR1', 'STRA', 'VELO', 'NBAR', 'RESL', 'CLR1', 'CLRA', 'PLYS', 'PLYE', 'TMP', 'MIN', 'REPT']
    self.seq_total_parameters = len(self.seq_parameter_names)   # Number of seq_parm

    # Editor/Player settings
    self.seq_edit_track = 0                  # The track number to edit (0 or 1, 0 is Track1 as display)
    self.seq_track_midi = [0,1]              # MIDI channels for the two tracks on the display
    self.seq_play_time = [0,0]               # Start and end time to play with sequencer
    self.seq_cursor_note = None              # The score and note data on the cursor (to highlite the note)

    # Backup the cursor position
    self.time_cursor_bk = None
    self.key_cursor0_bk = None
    self.key_cursor1_bk = None
    self.seq_disp_time0_bk  = None
    self.seq_disp_time1_bk  = None
    self.master_volume_bk = None

    # Display mode to draw note on sequencer
    self.SEQ_NOTE_DISP_NORMAL = 0
    self.SEQ_NOTE_DISP_HIGHLIGHT = 1
    self.seq_note_color = [[0x00ff88,0x8888ff], [0xff4040,0xffff00]]   # Note colors [frame,fill] for each display mode
    self.seq_draw_area = [[20,40,319,129],[20,150,319,239]]      # Display area for each track

    # Maximum number of sequence files
    self.SEQ_FILE_MAX = 1000

    # Sequencer file path
    self.SEQUENCER_FILE_PATH = '/SYNTH/SEQFILE/'

  # Set delegation class for graphics
  def delegate_graphics(self, view_delegate_obj):
    self.view_delegate_obj = view_delegate_obj

  # Set up the sequencer
  def setup_sequencer(self):
    # Initialize the sequencer channels
    self.seq_channel = []
    for ch in range(16):
      self.seq_channel.append({'gmbank': self.midi_obj.gmbank(), 'program': ch, 'volume': 100})

    # Clear score
    self.seq_score = []
    self.seq_score_sign = []

  # Set/Get sequencer file path
  def set_sequencer_file_path(self, path = None):
    if path is None:
      return self.SEQUENCER_FILE_PATH
    
    self.SEQUENCER_FILE_PATH = path
    return self.SEQUENCER_FILE_PATH

  # Set/Get edit track
  def edit_track(self, trknum = None):
    if not trknum is None:
      self.seq_edit_track = trknum

    return self.seq_edit_track

  # Set MIDI channel of each tracks
  def set_track_midi(self, channel, trknum = None):
    if trknum is None:
      trknum = self.seq_edit_track

    self.seq_track_midi[trknum] = channel
  
  # Get MIDI channel of each tracks
  def get_track_midi(self, trknum = None):
    if trknum is None:
      trknum = self.seq_edit_track

    return self.seq_track_midi[trknum]

  # Set/Get start and end time to play
  def play_time(self, side = None, val = None):
    if side is None:
      return self.seq_play_time

    if val is None:
      return self.seq_play_time[side]

    self.seq_play_time[side] = val
    return val

  # Set the cursor note in sequencer
  def set_cursor_note(self, val):
    self.seq_cursor_note = val

  # Get the cursor note in sequencer
  def get_cursor_note(self, side = None):
    if side is None:
      return self.seq_cursor_note

    return self.seq_cursor_note[side]

  # Clear seq_score
  def clear_seq_score(self):
    self.seq_score = []

  # Get seq_score
  def get_seq_score(self):
    return self.seq_score

  # Set seq_channel
  def set_seq_channel(self, channel, key_str, val):
    self.seq_channel[channel][key_str] = val
    return val

  # Get seq_channel
  def get_seq_channel(self, channel, key_str):
    return self.seq_channel[channel][key_str]

  # Set seq_parm_repeat
  def set_seq_parm_repeat(self, time_cursor):
    self.seq_parm_repeat = time_cursor
    return self.seq_parm_repeat

  # Get seq_parm_repeat
  def get_seq_parm_repeat(self):
    return self.seq_parm_repeat

  # Set time cursor
  def set_seq_time_cursor(self, cursor):
    self.seq_control['time_cursor'] = cursor if cursor >= 0 else 0

  # Get time cursor
  def get_seq_time_cursor(self):
    return self.seq_control['time_cursor']

  # Set key cursor
  def set_seq_key_cursor(self, trknum, cursor):
    if cursor < 0:
      cursor = 0
    elif cursor > 127:
      cursor = 127

    self.seq_control['key_cursor'][trknum] = cursor

  # Get key cursor
  def get_seq_key_cursor(self, trknum = None):
    if trknum is None:
      return self.seq_control['key_cursor']
    else:
      return self.seq_control['key_cursor'][trknum]

  # Set display key
  def set_seq_disp_key(self, trknum, key_from, key_to):
    self.seq_control['disp_key'][trknum][0] = key_from
    self.seq_control['disp_key'][trknum][1] = key_to

  # Get display key
  def get_seq_disp_key(self, trknum, side = None):
    if side is None:
      return self.seq_control['disp_key'][trknum]
    else:
      return self.seq_control['disp_key'][trknum][side]

  # Set display time
  def set_seq_disp_time(self, time_from, time_to):
    self.seq_control['disp_time'][0] = time_from
    self.seq_control['disp_time'][1] = time_to

  # Get display time
  def get_seq_disp_time(self, side = None):
    if side is None:
      return self.seq_control['disp_time']
    else:
      return self.seq_control['disp_time'][side]

  # Set time per bar
  def set_seq_time_per_bar(self, tpb):
    self.seq_control['time_per_bar'] = tpb if tpb > 2 else 2

  # Get time per bar
  def get_seq_time_per_bar(self):
    return self.seq_control['time_per_bar']

  # Set tempo
  def set_seq_tempo(self, tempo):
    if tempo < 6:
      tempo = 6
    elif tempo > 999:
      tempo = 999

    self.seq_control['tempo'] = tempo

  # Get tempo
  def get_seq_tempo(self):
    return self.seq_control['tempo']

  # Set minimum note length
  def set_seq_mini_note(self, length):
    if length < 2:
      length = 2
    elif length > 5:
      length = 5

    self.seq_control['mini_note'] = length

  # Get minimum note length
  def get_seq_mini_note(self):
    return self.seq_control['mini_note']

  # Set GM bank for a channel
  def set_seq_gmbank(self, channel, bank):
    self.seq_control['gmbank'][channel] = bank

  # Get GM bank for a channel
  def get_seq_gmbank(self, channel):
    return self.seq_control['gmbank'][channel]

  # Set program for a channel
  def set_seq_program(self, channel, prog):
    prog = prog % 128
    self.seq_control['program'][channel] = prog

  # Get program for a channel
  def get_seq_program(self, channel):
    return self.seq_control['program'][channel]

  # Save sequencer file
  def sequencer_save_file(self, path, num):
    # Write MIDI IN settings as JSON file
    if self.sdcard_obj.json_write(path, 'SEQSC{:0=3d}.json'.format(num), {'channel': self.seq_channel, 'control': self.seq_control, 'score': self.seq_score, 'sign': self.seq_score_sign}):
      print('SAVED')

  # Load sequencer file
  def sequencer_load_file(self, path, num):
    # Read MIDI IN settings JSON file
    seq_data = self.sdcard_obj.json_read(path, 'SEQSC{:0=3d}.json'.format(num))
    if not seq_data is None:
      if 'score' in seq_data.keys():
        if seq_data['score'] is None:
          self.seq_score = []
        else:
          self.seq_score = seq_data['score']
      else:
        seq_data = []
      
      if 'sign' in seq_data.keys():
        if seq_data['sign'] is None:
          self.seq_score_sign = []
        else:
          self.seq_score_sign = seq_data['sign']
      else:
        self.seq_score_sign = []

      if 'control' in seq_data.keys():
        if seq_data['control'] is None:
          self.seq_control = {'tempo': 120, 'mini_note': 4, 'time_per_bar': 4, 'disp_time': [0,12], 'disp_key': [[57,74],[57,74]], 'time_cursor': 0, 'key_cursor': [60,60], 'program':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], 'gmbank':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}
        else:
          for ky in seq_data['control'].keys():
            if ky == 'tempo':
              self.seq_control[ky] = int(seq_data['control'][ky])
            else:
              self.seq_control[ky] = seq_data['control'][ky]
      else:
        self.seq_control = {'tempo': 120, 'mini_note': 4, 'time_per_bar': 4, 'disp_time': [0,12], 'disp_key': [[57,74],[57,74]], 'time_cursor': 0, 'key_cursor': [60,60], 'program':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], 'gmbank':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}

      if 'channel' in seq_data.keys():
        if not seq_data['channel'] is None:
          self.seq_channel = seq_data['channel']
          for ch in range(16):
            if not 'gmbank' in self.seq_channel[ch]:
              self.seq_channel[ch]['gmbank'] = 0
            if not 'program' in self.seq_channel[ch]:
              self.seq_channel[ch]['program'] = 0
            if not 'volume' in self.seq_channel[ch]:
              self.seq_channel[ch]['volume'] = 100

      self.seq_cursor_note = self.sequencer_find_note(self.seq_edit_track, self.seq_control['time_cursor'], self.seq_control['key_cursor'][self.seq_edit_track])
      self.send_all_sequencer_settings()


  # Get key name of key number
  #   key_num: MIDI note number
  def seqencer_key_name(self, key_num):
    return self.midi_obj.key_name(key_num)

  # Find note
  def sequencer_find_note(self, track, seq_time, seq_note):
    channel = self.seq_track_midi[track]
    for score in self.seq_score:
      note_on_tm = score['time']
      note_off_max = note_on_tm + score['max_duration']
      if note_on_tm <= seq_time and seq_time <= note_off_max:
        for note_data in score['notes']:
          if note_data['channel'] == channel and note_data['note'] == seq_note:
            if note_on_tm + note_data['duration'] > seq_time:
              return (score, note_data)

    return None

  # Update maximum duration
  def sequencer_duration_update(self, score):
    max_dur = 0
    for note_data in score['notes']:
      max_dur = max(max_dur, note_data['duration'])

    score['max_duration'] = max_dur

  # Delete a note
  def sequencer_delete_note(self, score, note_data):
    score['notes'].remove(note_data)
    if len(score['notes']) == 0:
      self.seq_score.remove(score)
    else:
      self.sequencer_duration_update(score)

  # Add new note
  def sequencer_new_note(self, channel, note_on_time, note_key, velocity = -1, duration = 1):
    sc = 0
    scores = len(self.seq_score)
    while sc < scores:
      # Add the note to the existing score
      current = self.seq_score[sc]
      if current['time'] == note_on_time:
        # Inset new note at sorted order by key
        nt = 0
        notes_len = len(current['notes'])
        for nt in range(notes_len):
          if current['notes'][nt]['note'] > note_key:
            current['notes'].insert(nt, {'channel': channel, 'note': note_key, 'velocity': max(velocity, current['notes'][nt]['velocity']), 'duration': duration})
            self.seq_cursor_note = current['notes'][nt]
            if duration > self.seq_score[sc]['max_duration']:
              self.seq_score[sc]['max_duration'] = duration

            return (current, self.seq_cursor_note)

        # New note is the highest tone
        current['notes'].append({'channel': channel, 'note': note_key, 'velocity': max(velocity, current['notes'][notes_len-1]['velocity']), 'duration': duration})
        self.seq_cursor_note = current['notes'][len(current['notes']) - 1]
        if duration > self.seq_score[sc]['max_duration']:
          self.seq_score[sc]['max_duration'] = duration

        return (current, self.seq_cursor_note)

      # Insert the note as new score at new note-on time
      elif current['time'] > note_on_time:
        self.seq_score.insert(sc, {'time': note_on_time, 'max_duration': duration, 'notes': [{'channel': channel, 'note': note_key, 'velocity': max(velocity, 127), 'duration': duration}]})
        current = self.seq_score[sc]
        self.seq_cursor_note = current['notes'][0]
        return (current, self.seq_cursor_note)

      # Next note on time
      sc = sc + 1

    # Append the note as new latest note-on time
    self.seq_score.append({'time': note_on_time, 'max_duration': duration, 'notes': [{'channel': channel, 'note': note_key, 'velocity': max(velocity, 127), 'duration': duration}]})
    current = self.seq_score[len(self.seq_score) - 1]
    self.seq_cursor_note = current['notes'][0]
    return (current, self.seq_cursor_note)

  # Change MIDI channel
  def sequencer_change_midi_channel(self, delta):
    channel = (self.seq_track_midi[self.seq_edit_track] + delta) % 16
    self.seq_track_midi[self.seq_edit_track] = channel
    self.sequencer_draw_track(self.seq_edit_track)

  # Change time span to display score
  def sequencer_timespan(self, delta):
    end = self.seq_control['disp_time'][1] + delta
    if end - self.seq_control['disp_time'][0] <= 3:
      return
    
    self.seq_control['disp_time'][1] = end
    self.sequencer_draw_track(0)
    self.sequencer_draw_track(1)

  # Change a note velocity
  def sequencer_velocity(self, delta):
    # No note is selected
    if self.seq_cursor_note is None:
      return False

    # Change velocity of a note selected
    note_data = self.seq_cursor_note[1]
    note_data['velocity'] = note_data['velocity'] + delta
    if note_data['velocity'] < 1:
      note_data['velocity'] = 1
    elif note_data['velocity'] > 127:
      note_data['velocity'] = 127

    return True

  # Insert time at the time cursor on a MIDI channel
  def sequencer_insert_time(self, channel, time_cursor, ins_times):
    affected = False
    for sc_index in list(range(len(self.seq_score)-1,-1,-1)):
      score = self.seq_score[sc_index]

      # Note-on time is equal or larger than the origin time to insert --> move forward
      if score['time'] >= time_cursor:
        note_on_time = score['time'] + ins_times
        to_delete = []
        for note_data in score['notes']:
          if note_data['channel'] == channel:
            # Delete a note
            to_delete.append(note_data)

            # Move the note as new note
            self.sequencer_new_note(channel, note_on_time, note_data['note'], note_data['velocity'], note_data['duration'])
            affected = True

        # Delete notes moved
        for note_data in to_delete:
          self.sequencer_delete_note(score, note_data)

      # Note-on time is less than the origin time to insert
      else:
        # Notes over the origin time to insert --> stretch duration toward forward
        # Not include note-off time
        if score['time'] + score['max_duration'] > time_cursor:
          for note_data in score['notes']:
            if note_data['channel'] == channel:
              if score['time'] + note_data['duration'] > time_cursor:
                note_data['duration'] = note_data['duration'] + ins_times
                affected = True

    return affected

  # Delete time at the time cursor on the all MIDI channels
  def sequencer_delete_time(self, channel, time_cursor, del_times):
    # Can not delete
    if time_cursor <= 0:
      return False
    
    # Adjust times to delete
    times_to_delete = time_cursor - del_times
    if times_to_delete < 0:
      del_times = time_cursor

    affected = False
    notes_moved = []
    to_delete = []
    for score in self.seq_score:
      note_on_time = score['time']

      # Note-on time is equal or larger than the delete time
      if note_on_time >= time_cursor:
        for note_data in score['notes']:
          if note_data['channel'] == channel:
            affected = True

            # Delete a note
            to_delete.append((score, note_data))

            # Move the note as new note
            notes_moved.append((note_on_time - del_times, note_data['note'], note_data['velocity'], note_data['duration']))

      # Note-on time is less than the delete time, and there are some notes acrossing the delete time
      elif note_on_time + score['max_duration'] >= time_cursor:
        for note_data in score['notes']:
          if note_data['channel'] == channel:

            # Accross the time range to delete
            if note_on_time + note_data['duration'] >= time_cursor - del_times:
              affected = True
              note_data['duration'] = note_data['duration'] - del_times

              # Zero length note
              if note_data['duration'] <= 0:
                to_delete.append((score, note_data))

    # Delete notes without duration
    for score, note_data in to_delete:
      self.sequencer_delete_note(score, note_data)

    # Add notes moved
    for note_time, note_key, velosity, duration in notes_moved:
      self.sequencer_new_note(channel, note_time, note_key, velosity, duration)

    return affected

  # Up or Down time resolution
  def sequencer_resolution(self, res_up):
    # Reolution up
    if res_up:
      for score in self.seq_score:
        score['time'] = score['time'] * 2

      for score in self.seq_score_sign:
        score['time'] = score['time'] * 2

    # Resolution down
    else:
      for score in self.seq_score:
        if score['time'] % 2 != 0:
          return

      for score in self.seq_score_sign:
        if score['time'] % 2 != 0:
          return

      for score in self.seq_score:
        score['time'] = int(score['time'] / 2)

      for score in self.seq_score_sign:
        score['time'] = int(score['time'] / 2)

  # Get signs on score at tc(time cursor)
  def sequencer_get_repeat_control(self, tc):
    if not self.seq_score_sign is None:
      for sc_sign in self.seq_score_sign:
        if sc_sign['time'] == tc:
          return sc_sign

    return None

  # Add or change score signs at a time
  def sequencer_edit_signs(self, sign_data):
#    print('REPEAT SIGNS:', sign_data)
    if not sign_data is None:
      tm = sign_data['time']
      sc_sign = self.sequencer_get_repeat_control(tm)

      # Insert new sign data
      if sc_sign is None:
        # Sign status check
        flg = False
        for ky in sign_data.keys():
          if ky != 'time':
            flg = flg or sign_data[ky]
        
        # No sign is True
        if flg == False:
          return

        idx = 0
        for idx in range(len(self.seq_score_sign)):
          if self.seq_score_sign[idx]['time'] > tm:
            self.seq_score_sign.insert(idx, sign_data)
            return
          else:
            idx = idx + 1
        
        self.seq_score_sign.append(sign_data)

      # Change sign parameters
      else:
        for ky in sign_data.keys():
          sc_sign[ky] = sign_data[ky]

        # Sign status check
        flg = False
        for ky in sign_data.keys():
          if ky != 'time':
            flg = flg or sign_data[ky]
        
        # No sign is True
        if flg == False:
          self.seq_score_sign.remove(sign_data)

  # Backup the cursor position
  def pre_play_sequencer(self):
    self.time_cursor_bk = self.seq_control['time_cursor']
    self.key_cursor0_bk = self.seq_control['key_cursor'][0]
    self.key_cursor1_bk = self.seq_control['key_cursor'][1]
    self.seq_disp_time0_bk  = self.seq_control['disp_time'][0]
    self.seq_disp_time1_bk  = self.seq_control['disp_time'][1]

    # Backup master volume
    self.master_volume_bk = self.midi_obj.get_master_volume()

  # Retrieve the backuped cursor position
  def post_play_sequencer(self):
    self.seq_control['time_cursor'] = self.time_cursor_bk
    self.seq_control['key_cursor'][0] = self.key_cursor0_bk
    self.seq_control['key_cursor'][1] = self.key_cursor1_bk
    self.seq_control['disp_time'][0] = self.seq_disp_time0_bk
    self.seq_control['disp_time'][1] = self.seq_disp_time1_bk
    self.sequencer_draw_track(0)
    self.sequencer_draw_track(1)

    # Set master volume (for pause/stop)
    self.midi_obj.set_master_volume(self.master_volume_bk)

  # Play sequencer score
  def play_sequencer(self, func_pause_or_stop = None, func_pause_to_stop = None, func_pre_move_cursor = None, func_post_move_cursor = None):
    print('SEQUENCER STARTS.')
    note_off_events = []

    # Insert a note off event in the notes off list
    def insert_note_off(time, channel, note_num):
      len_evt = len(note_off_events)
      if len_evt == 0:
        note_off_events.append({'time': time, 'notes': [{'channel': channel, 'note': note_num}]})
        return

      for evt_index in range(len_evt):
        evt = note_off_events[evt_index]
        if   evt['time'] == time:
          evt['notes'].append({'channel': channel, 'note': note_num})
          return

        elif evt['time'] > time:
          note_off_events.insert(evt_index,{'time': time, 'notes': [{'channel': channel, 'note': note_num}]})
          return

      note_off_events.append({'time': time, 'notes': [{'channel': channel, 'note': note_num}]})


    # Notes off the first event in the notes off event list
    def sequencer_notes_off():
      for note_data in note_off_events[0]['notes']:
        self.midi_obj.notes_off(note_data['channel'], [note_data['note']])

      note_off_events.pop(0)


    # Move play cursor
    def move_play_cursor(tc):
      if not func_pre_move_cursor is None:
        func_pre_move_cursor()
      tc = tc + 1
      self.seq_control['time_cursor'] = tc

      # Slide score
      if self.seq_control['time_cursor'] < self.seq_control['disp_time'][0] or self.seq_control['time_cursor'] > self.seq_control['disp_time'][1]:
        width = self.seq_control['disp_time'][1] - self.seq_control['disp_time'][0]
        self.seq_control['disp_time'][0] = self.seq_control['time_cursor']
        self.seq_control['disp_time'][1] = self.seq_control['disp_time'][0] + width
        self.sequencer_draw_track(0)
        self.sequencer_draw_track(1)

      if not func_post_move_cursor is None:
        func_post_move_cursor()
      return tc

    ##### CODE: play_sequencer

    # Play parameter
    next_note_on = 0
    next_note_off = 0
    time_cursor = self.seq_play_time[0]
    end_time = self.seq_play_time[1] if self.seq_play_time[0] < self.seq_play_time[1] else -1

    # Repeat controls
    loop_play_time = 0
    loop_play_slot = 0
    repeating_bars = False
    repeat_time = -1
    repeat_slot = -1

    # Sequencer play loop
    self.seq_control['time_cursor'] = time_cursor
    score_len = len(self.seq_score)
    play_slot = 0
    while play_slot < score_len:
      print('SEQ POINT:', time_cursor, play_slot)
      score = self.seq_score[play_slot]
      print('SCORE:', play_slot, score)

      # Scan stop button (PLAY-->PAUSE-->STOP)
      if not (func_pause_or_stop is None or func_pause_to_stop is None):
        if func_pause_or_stop():
          self.midi_obj.set_master_volume(0)
          count = func_pause_to_stop()
          if count >= 0:    # Stop playing (push the button long)
            self.midi_obj.set_master_volume(self.master_volume_bk)
            if count > 0:
              break

      # Play4,8,16,32,64--1,2,3,4,5--1,2,4,8,16
      skip_continue = False
      repeat_continue = False
      tempo = int((60.0 / self.seq_control['tempo'] / (2**self.seq_control['mini_note']/4)) * 1000000)
      next_notes_on = score['time']
      while next_notes_on > time_cursor:
  #      print('SEQUENCER AT0:', time_cursor)
        time0 = time.ticks_us()
        if len(note_off_events) > 0:
          if note_off_events[0]['time'] == time_cursor:
            sequencer_notes_off()

        # Get MIDI-IN and send data to Unit-MIDI
        self.midi_obj.midi_in_out()
        
        time1 = time.ticks_us()
        timedelta = time.ticks_diff(time1, time0)
        time.sleep_us(tempo - timedelta)
        time_cursor = move_play_cursor(time_cursor)

        # Loop/Skip/Repeat
        repeat_ctrl = self.sequencer_get_repeat_control(time_cursor)
  #      print('REPEAT CTRL0:', time_cursor, repeat_ctrl)
        if not repeat_ctrl is None:
          # Skip bar point
          if repeat_ctrl['skip']:
            # During repeat play, skip to next play slot
            if repeating_bars and repeat_time != -1 and repeat_slot != -1:
              time_cursor = repeat_time
              play_slot = repeat_slot
              repeat_time = -1
              repeat_slot = -1
              repeating_bars = False
              loop_play_time = -1
              loop_play_slot = -1
              skip_continue = True
              break

          # Repeat bar point
          if repeat_ctrl['repeat'] and repeating_bars == False and loop_play_time >= 0:
            repeat_time = repeat_ctrl['time']
            repeat_slot = play_slot
            time_cursor = loop_play_time
            play_slot = loop_play_slot
            loop_play_time = -1
            loop_play_slot = -1
            repeating_bars = True
            repeat_continue = True
            break

          # Loop bar point
          if repeat_ctrl['loop']:
            loop_play_time = repeat_ctrl['time']
            loop_play_slot = play_slot

        if end_time != -1 and time_cursor >= end_time:
          break

      # Note off
  #    print('SEQUENCER AT1:', time_cursor)
      time0 = time.ticks_us()
      if len(note_off_events) > 0:
        if note_off_events[0]['time'] == time_cursor:
          sequencer_notes_off()

      # Skip to next play slot
      if skip_continue:
        skip_continue = False
  #      print('SEQ SKIP TO 0:', time_cursor, play_slot)
        continue

      # Repeat
      if repeat_continue:
        repeat_continue = False
  #      print('SEQ REPEAT TO 0:', time_cursor, play_slot, repeat_time, repeat_slot)
        continue

      # Loop/Skip/Repeat
      repeat_ctrl = self.sequencer_get_repeat_control(time_cursor)
  #    print('REPEAT CTRL1:', time_cursor, repeat_ctrl)
      if not repeat_ctrl is None:
        # Loop bar point
        if repeat_ctrl['loop']:
          loop_play_time = repeat_ctrl['time']
          loop_play_slot = play_slot

        # Skip bar point
        if repeat_ctrl['skip']:
          # During repeat play
          if repeating_bars and repeat_time != -1 and repeat_slot != -1:
            time_cursor = repeat_time
            play_slot = repeat_slot
            repeat_time = -1
            repeat_slot = -1
            repeating_bars = False
  #          print('SEQ SKIP TO 1:', time_cursor, play_slot)
            continue

        # Repeat bar point
        if repeat_ctrl['repeat'] and repeating_bars == False and loop_play_time >= 0:
          repeat_time = repeat_ctrl['time']
          repeat_slot = play_slot
          time_cursor = loop_play_time
          play_slot = loop_play_slot
          loop_play_time = -1
          loop_play_slot = -1
          repeating_bars = True
  #        print('SEQ REPEAT TO 1:', time_cursor, play_slot, repeat_time, repeat_slot)
          continue

      if end_time != -1 and time_cursor >= end_time:
        break

      # Notes on
      for note_data in score['notes']:
        channel = note_data['channel']
  #      print('SEQ NOTE ON:', time_cursor, note_data['note'])
        self.midi_obj.set_note_on(channel, note_data['note'], int(note_data['velocity'] * self.seq_channel[channel]['volume'] / 100))
        note_off_at = time_cursor + note_data['duration']
        insert_note_off(note_off_at, channel, note_data['note'])

      self.midi_obj.midi_in_out()

      time1 = time.ticks_us()
      timedelta = time.ticks_diff(time1, time0)
      time.sleep_us(tempo - timedelta)

      time_cursor = move_play_cursor(time_cursor)

      if end_time != -1 and time_cursor >= end_time:
        break

      # Next time slot
      play_slot = play_slot + 1

    # Notes off (final process)
    print('SEQUENCER: Notes off process =', len(note_off_events))
    while len(note_off_events) > 0:
      score = note_off_events[0]
      timedelta = 0
      while score['time'] > time_cursor:
        time.sleep_us(tempo - timedelta)
        time0 = time.ticks_us()
        time_cursor = move_play_cursor(time_cursor)

        time1 = time.ticks_us()
        timedelta = time.ticks_diff(time1, time0)

      time0 = time.ticks_us()
      sequencer_notes_off()
      self.midi_obj.midi_in_out()

      time1 = time.ticks_us()
      timedelta = time.ticks_diff(time1, time0)
      time.sleep_us(tempo - timedelta)
      time_cursor = move_play_cursor(time_cursor)

    print('SEQUENCER: Finished.')

  # Draw a note on the sequencer
  def sequencer_draw_note(self, trknum, note_num, note_on_time, note_off_time, disp_mode):
    # Delegation
    if not self.view_delegate_obj is self:
      self.view_delegate_obj.sequencer_draw_note(trknum, note_num, note_on_time, note_off_time, disp_mode)
      return

    print('sequencer_draw_note IN SEQUENCER: TO BE IMPLEMENT IN DELEGATE CLASS FUNCTION')
    pass

  # Draw velocity
  def sequencer_draw_velocity(self, trknum, channel, note_on_time, notes):
    # Delegation
    if not self.view_delegate_obj is self:
      self.view_delegate_obj.sequencer_draw_velocity(trknum, channel, note_on_time, notes)
      return

    print('sequencer_draw_velocity IN SEQUENCER: TO BE IMPLEMENT IN DELEGATE CLASS FUNCTION')
    pass

  # Draw start and end time line to play in sequencer
  def sequencer_draw_playtime(self, trknum):
    # Delegation
    if not self.view_delegate_obj is self:
      self.view_delegate_obj.sequencer_draw_playtime(trknum)
      return

    print('sequencer_draw_playtime IN SEQUENCER: TO BE IMPLEMENT IN DELEGATE CLASS FUNCTION')
    pass

  # Draw sequencer track
  #   trknum: The track number to draw (0 or 1)
  def sequencer_draw_track(self, trknum):
    # Delegation
    if not self.view_delegate_obj is self:
      self.view_delegate_obj.sequencer_draw_track(trknum)
      return

    print('sequencer_draw_track IN SEQUENCER: TO BE IMPLEMENT IN DELEGATE CLASS FUNCTION')
    pass

  # Draw keyboard
  def sequencer_draw_keyboard(self, trknum):
    # Delegation
    if not self.view_delegate_obj is self:
      self.view_delegate_obj.sequencer_draw_keyboard(trknum)
      return

    print('sequencer_draw_keyboard IN SEQUENCER: TO BE IMPLEMENT IN DELEGATE CLASS FUNCTION')
    pass

    # Draw a keyboard of the track
    key_s = self.seq_control['disp_key'][trknum][0]
    key_e = self.seq_control['disp_key'][trknum][1]
    area = self.seq_draw_area[trknum]
    xscale = area[0] - 1
    black_scale = int(xscale / 2)
    yscale = int((area[3] - area[1] + 1) / (key_e - key_s  + 1))
    black_key = [1,3,6,8,10]
    for note_num in range(key_s, key_e + 1):
      # Display a key
      y = area[3] - (note_num - key_s + 1) * yscale
      M5.Lcd.drawRect(0, y, xscale, yscale, 0x888888)
      M5.Lcd.fillRect(1, y + 1, xscale - 2, yscale - 2, 0xffffff)

      # Black key on piano
      key_is_black = ((note_num % 12) in black_key) == True
      if key_is_black:
        M5.Lcd.fillRect(1, y + 1, black_scale, yscale - 2, 0x000000)

  # Send all sequencer MIDI settings
  def send_all_sequencer_settings(self):
    for ch in range(16):
      self.midi_obj.set_instrument(self.seq_control['gmbank'][ch], ch, self.seq_control['program'][ch])
      self.midi_obj.set_reverb(ch, 0, 0, 0)
      self.midi_obj.set_chorus(ch, 0, 0, 0, 0)
      self.midi_obj.set_vibrate(ch, 0, 0, 0)


  # Send the current MIDI channel settings to MIDI channel 1
  # Normally, MIDI-IN instruments send MIDI channel1 message.
  def send_sequencer_current_channel_settings(self, ch):
    self.midi_obj.set_instrument(self.seq_control['gmbank'][ch], 0, self.seq_control['program'][ch])
    self.midi_obj.set_reverb(0, 0, 0, 0)
    self.midi_obj.set_chorus(0, 0, 0, 0, 0)
    self.midi_obj.set_vibrate(0, 0, 0, 0)

################# End of Sequencer Class Definition #################


def notes_on(midi_obj, notes):
    for note in notes:
        print("NOTE ON :", midi_obj.key_name(note))
        midi_obj.set_note_on(0, note, 127)


def notes_off(midi_obj, notes):
    for note in notes:
        print("NOTE ON :", midi_obj.key_name(note))
        midi_obj.set_note_off(0, note)


######################
### Joy Stick Device
######################
class device_joystick_class:
    def __init__(self, device_manager, address=82, unit=0, scl_pin=9, sda_pin=8, frequency=400000):
        self.callback_delegate = self.callback_values
        self.i2c = I2C(unit, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=frequency)
        device_list = self.i2c.scan()
        print('I2C DEVICES:', device_list)
        
        if address in device_list:
            device_manager.add_device(self)
        else:
            print('CAN NOT FIND I2C DEVICE AT THE ADDRESS:', address)

    def delegate(self, callback_function):
        self.callback_delegate = self.callback_values = callback_function

    def callback_values(self, joys_x, joys_y, joys_b):
        print('JOY STICK x, y, b:', joys_x, joys_y, joys_b)
        
    def controller(self):
        try:
            joystick = self.i2c.readfrom(82, 3)
            joys_x = int.from_bytes(joystick[0:1], 'little', True)
            joys_y = int.from_bytes(joystick[1:2], 'little', True)
            joys_b = int.from_bytes(joystick[2:3], 'little', True)
            self.callback_delegate(joys_x, joys_y, joys_b)
        except:
            print('I2C ERROR.')
            
################# End of Joy Stick Device Class Definition #################

class midi_in_instrument_class:
    def __init__(self, device_manager, midi_obj):
        self.midi_obj = midi_obj
        device_manager.add_device(self)
    
    def controller(self):
        self.midi_obj.midi_in_out()


#######################
### Application class
#######################
class unipico_application_class:
    # Constructor
    def __init__(self):
        self.lock = False
        self.order_queuer = []

        self.midi_in_player_controller = False

        self.midi_channel = -1
        self.sequencer_file = 0

        self.sequencer_playing = False
        self.sequencer_pause = False
        self.sequencer_stop = False

        self.joystick_x = -1
        self.joystick_y = -1
        self.joystick_b = False
        
        self.MENU_SEQ_FILE = 0
        self.MENU_MIN_SAVE = 1
        self.MENU_MIN_PLAY_MVOL     = 2
        self.MENU_MIN_PLAY_CTRL     = 3
        self.MENU_MIN_MIDI_SET      = 4
        self.MENU_MIN_LOAD          = 5
        self.MENU_MIN_CH01_CHN_INST = 6
        self.MENU_MIN_CH01_REV_PROG = 7
        self.MENU_MIN_CH01_REV_LEVL = 8
        self.MENU_MIN_CH01_REV_FDBK = 9
        self.MENU_MIN_CH01_CHR_PROG = 10
        self.MENU_MIN_CH01_CHR_LEVL = 11
        self.MENU_MIN_CH01_CHR_FDBK = 12
        self.MENU_MIN_CH01_CHR_DELY = 13
        self.MENU_MIN_CH01_VIB_RATE = 14
        self.MENU_MIN_CH01_VIB_DEPT = 15
        self.MENU_MIN_CH01_VIB_DELY = 16
        
        self.menu_change_dir = 0
        self.value_change_dir = 0
        self.VALUE_CHANGE_SENSE_MAX = 15
        self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX
        self.menu_selected = self.MENU_MIN_MIDI_SET
        self.menu = [
                [('SEQ:PLAY',    '', None), ('FILE:', '{:03d}', self.get_seq_file)],
                [('MIN:SAVE',    '', None),              ('OK?:',        '', None)],
                [('PLAY:', '{:03d}', self.get_midi_set), ('MVOL:', '{:03d}', self.get_master_volume)],
                [('PLAY:', '{:03d}', self.get_midi_set), ('CTRL:', '{:s}'  , self.get_min_play_ctrl)],
                [('PLAY:', '{:03d}', self.get_midi_set), ('SET:',  '{:03d}', self.get_midi_set)],
                [('MIN:LOAD',    '', None),              ('OK?',         '', None)]
            ]
        for ch in list(range(1,17)):
            ch_str = 'CH{:02d}'.format(ch)
            self.menu.append([(ch_str + ':CHN', '', None), ('INST:', '{:03d}', self.get_chn_inst)])
            self.menu.append([(ch_str + ':REV', '', None), ('PROG:', '{:03d}', self.get_rev_prog)])
            self.menu.append([(ch_str + ':REV', '', None), ('LEVL:', '{:03d}', self.get_rev_levl)])
            self.menu.append([(ch_str + ':REV', '', None), ('FDBK:', '{:03d}', self.get_rev_fdbk)])
            self.menu.append([(ch_str + ':CHR', '', None), ('PROG:', '{:03d}', self.get_chr_prog)])
            self.menu.append([(ch_str + ':CHR', '', None), ('LEVL:', '{:03d}', self.get_chr_levl)])
            self.menu.append([(ch_str + ':CHR', '', None), ('FDBK:', '{:03d}', self.get_chr_fdbk)])
            self.menu.append([(ch_str + ':CHR', '', None), ('DELY:', '{:03d}', self.get_chr_dely)])
            self.menu.append([(ch_str + ':VIB', '', None), ('RATE:', '{:03d}', self.get_vib_rate)])
            self.menu.append([(ch_str + ':VIB', '', None), ('DEPT:', '{:03d}', self.get_vib_dept)])
            self.menu.append([(ch_str + ':VIB', '', None), ('DELY:', '{:03d}', self.get_vib_dely)])

    def get_seq_file(self, delta=0):
        if delta != 0:
            if delta < 0:
                delta = -1
            elif delta > 0:
                delta = 1

            self.sequencer_file = (self.sequencer_file + delta) % 1000

        return self.sequencer_file

    def get_midi_set(self, delta=0):
        if delta != 0:
            if delta < 0:
                delta = -1
            elif delta > 0:
                delta = 1
                
            set_num = midi_in_player_obj.set_midi_in_set_num()
            print('MIDI SET DELTA:', set_num, delta)
            set_num = (set_num + delta) % 1000
            midi_in_player_obj.set_midi_in_set_num(set_num)
            set_number = midi_in_player_obj.set_midi_in_set_num()

            midi_in_set = midi_in_player_obj.read_midi_in_settings(set_number)
            if not midi_in_set is None:
                print('LOAD MIDI-IN SET:', set_number, midi_in_set)
                midi_in_player_obj.set_midi_in_setting(midi_in_set)
                midi_in_player_obj.send_all_midi_in_settings()

        return midi_in_player_obj.set_midi_in_set_num()
    
    def get_master_volume(self, delta=0):
        vol = midi_obj.get_master_volume() + delta
        if vol < 0:
            vol = 0
            
        if vol > 127:
            vol = 127
            
        midi_obj.set_master_volume(vol)
        return vol
    
    def get_min_play_ctrl(self, delta=0):
        if delta != 0:
            self.midi_in_player_controller = not self.midi_in_player_controller
        return 'MOD' if self.midi_in_player_controller else '---'
    
    def get_chn_inst(self, delta=0):
        if delta != 0:
            prog = midi_in_player_obj.get_midi_in_setting(self.midi_channel, 'program')
            prog = (prog + delta) % 128
            midi_in_player_obj.set_midi_in_setting3(self.midi_channel, 'program', prog)
            midi_in_player_obj.send_midi_in_settings(self.midi_channel)
            
        return midi_in_player_obj.get_midi_in_setting(self.midi_channel, 'program')
    
    def get_rev_prog(self, delta=0):
        return 11
    
    def get_rev_levl(self, delta=0):
        return 12
    
    def get_rev_fdbk(self, delta=0):
        return 13
    
    def get_chr_prog(self, delta=0):
        return 21
    
    def get_chr_levl(self, delta=0):
        return 22
    
    def get_chr_fdbk(self, delta=0):
        return 23
    
    def get_chr_dely(self, delta=0):
        return 24
    
    def get_vib_rate(self, delta=0):
        return 31
    
    def get_vib_dept(self, delta=0):
        return 32
    
    def get_vib_dely(self, delta=0):
        return 33
    
    # Make an order to the application, orders come from other functions including thread process.
    #   order: A string text of the order
    #   args : Arguments tuple
    def make_order(self, order, args):
        while self.lock:
            utime.sleep_ms(50)
            
        self.lock = True
        self.order_queuer.append((order, args))
        self.lock = False
    
    # Get a first order and do it
    def get_order(self):
        while self.lock:
            utime.sleep_ms(50)
            
        self.lock = True
        if len(self.order_queuer) > 0:
            order = self.order_queuer.pop()

        else:
            order = None

        self.lock = False
        return order

    # Get an order to pause or stop sequncer
    def sequencer_pause_or_stop(self):
        return self.sequencer_stop

    # Get an order to pause to stop sequncer
    def sequencer_pause_to_stop(self):
        return 1

    # Show the current menu on the LCD
    def show_menu(self, delta=0):
        display.clearScreen()
        menu_item  = self.menu[self.menu_selected][0]
        menu_value = self.menu[self.menu_selected][1]
        
        # MIDI channel related parameters
        if self.menu_selected >= self.MENU_MIN_CH01_CHN_INST:
            self.midi_channel = int((self.menu_selected - self.MENU_MIN_CH01_CHN_INST) / 11)
        else:
            self.midi_channel = -1
    
        if menu_item[2] is None:
            show_str = menu_item[0]
        else:
            show_str = menu_item[0] + menu_item[1].format(menu_item[2]())
        display.setText(show_str, 0, 0)
        
        if menu_value[2] is None:
            show_str = menu_value[0]
        else:
            show_str = menu_value[0] + menu_value[1].format(menu_value[2](delta))
        display.setText(show_str, 0, 1)

        display.show()

    # Joy Stick delegateion of device controller
    def device_joystick_controller(self, joy_x, joy_y, joy_b):
        # Opertion: MIDI-IN PLAYER CONTROLLER
#        if self.midi_in_player_controller:
            # Sequencer player
#            if joy_b == 1:
#                # Stop trigger
#                if self.sequencer_playing:
#                    self.sequencer_pause = True
#                
                # Play
#                else:
#                    self.sequencer_playing = True
#                    self.make_order('play sequencer', (977,))
#                    utime.sleep_ms(1000)
#               
            # Stop playing
#            elif self.sequencer_pause:
#                self.sequencer_stop =True
#                self.sequencer_pause = False
#                utime.sleep_ms(1000)
                
        # Joystick button clicked
        if joy_b == True and self.joystick_b == False:
            # Menu: MIDI-IN PLAYER CONTROLLER
            if self.menu_selected == self.MENU_MIN_PLAY_CTRL:
                self.midi_in_player_controller = not self.midi_in_player_controller
                self.show_menu()

            elif self.menu_selected == self.MENU_SEQ_FILE:
                # Stop trigger
                if self.sequencer_playing:
                    self.sequencer_stop = True
                    self.sequencer_pause = False
                    utime.sleep_ms(1000)
                
                # Play
                else:
                    self.sequencer_playing = True
                    self.make_order('play sequencer', (self.sequencer_file,))
                    utime.sleep_ms(1000)
                
            self.joystick_b = True

        else:
            self.joystick_b = False

        # Joystick-Y moved
        if self.joystick_y != joy_y:
            # Opertion: MIDI-IN PLAYER CONTROLLER
            if self.midi_in_player_controller:
#                print('MASTRE VOLUME:', int(joy_y / 255 * 127))
                midi_obj.set_master_volume(int(joy_y / 255 * 127))
                
            # Menu change
            else:
                affected = False
                if joy_y <= 50 and self.menu_change_dir != -1:
                    self.menu_selected = (self.menu_selected - 1) % len(self.menu)
                    self.menu_change_dir = -1
                    affected = True
                    
                elif joy_y >= 205 and self.menu_change_dir != 1:
                    self.menu_selected = (self.menu_selected + 1) % len(self.menu)
                    self.menu_change_dir = 1
                    affected = True
                
                elif 50 < joy_y and joy_y < 205:
                    self.menu_change_dir = 0

                # Change menu
                if affected:
                    print('MENU CHANGE:', joy_y, self.joystick_y)
                    self.show_menu()
                    
            self.joystick_y = joy_y

        # Joystick-X moved
        if self.joystick_x != joy_x:
            # Opertion: MIDI-IN PLAYER CONTROLLER
            if self.midi_in_player_controller:
                if joy_x <= 100:
#                    print('PITCH BEND -:', joy_x)
                    midi_obj.set_pitch_bend(0, 0x1fff - int(0x1fff * (100 - joy_x) / 100))
                elif joy_x >= 155:
#                    print('PITCH BEND +:', joy_x)
                    midi_obj.set_pitch_bend(0, 0x1fff + int(0x1fff * (joy_x - 155) / 100))
                else:
                    midi_obj.set_pitch_bend(0, 0x1fff)
                    
            # Value change
            else:
                affected = False
                if joy_x <= 50:
                    if self.value_change_dir != -1:
                        delta = min(int((50 - joy_x) / -10), -1)
                        self.value_change_dir = -1
                        self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX
                        affected = True
                    else:
                        self.value_change_sense = self.value_change_sense - 1
                        if self.value_change_sense == 0:
                            self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX
                            self.value_change_dir = 0
                            
                elif joy_x >= 205:
                    if self.value_change_dir != 1:
                        delta = max(int((255 - joy_x) / 10), 1)
                        self.value_change_dir = 1
                        self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX
                        affected = True
                    else:
                        self.value_change_sense = self.value_change_sense - 1
                        if self.value_change_sense == 0:
                            self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX
                            self.value_change_dir = 0
                
                elif 50 < joy_x and joy_x < 205:
#                    self.value_change_dir = 0
                    self.value_change_sense = self.VALUE_CHANGE_SENSE_MAX

                # Change menu
                if affected:
                    print('VALUE CHANGE:', joy_x, delta)
                    self.show_menu(delta)

            self.joystick_x = joy_x

    # ORDER: play sequencer
    def order_play_sequencer(self, file_num):
        self.sequencer_playing = True
        self.sequencer_pause = False
        self.sequencer_stop = False
        sequencer_obj.sequencer_load_file(sequencer_obj.set_sequencer_file_path(), 997)
        sequencer_obj.send_all_sequencer_settings()
        sequencer_obj.pre_play_sequencer()
        sequencer_obj.play_sequencer(self.sequencer_pause_or_stop, self.sequencer_pause_to_stop, None, None)

        # Retrieve the cursor position
        sequencer_obj.post_play_sequencer()
        self.sequencer_playing = False
        self.sequencer_pause = False
        self.sequencer_stop = False

    # Application main loop
    def app_loop(self):     
        # PICO settings
        led = Pin("LED", Pin.OUT, value=0)
        led.value(0)
        
        # Play UnitMIDI with flashing a LED on PICO board
        self.show_menu()
        while True:
            # Order to the application
            order = self.get_order()
            if not order is None:
                if order[0] == 'play sequencer':
                    self.order_play_sequencer(order[1])

            utime.sleep_ms(200)
            
################# End of Application class #################


# Main program
if __name__ == '__main__':
    try:
        # Appication
        application = unipico_application_class()

        # SD cars (Internal memory file for PICO)
        sdcard_obj = sdcard_class()

        # Device Manager
        device_manager_obj = device_manager_class()
        
        # Joy Stick
        # __init__(self, device_manager, address=82, unit=0, scl_pin=9, sda_pin=8, frequency=400000):
        joystick_obj = device_joystick_class(device_manager_obj)
        joystick_obj.delegate(application.device_joystick_controller)
        
        # Synthesizer objects
        unit_midi_obj = MIDIUnit(0)
        midi_obj = midi_class(unit_midi_obj, sdcard_obj)
        midi_obj.set_pitch_bend_range(0, 5)

        # External MIDI-IN instrument
        midi_in_instrument = midi_in_instrument_class(device_manager_obj, midi_obj)

        # MIDI-IN Player object
        midi_in_player_obj = midi_in_player_class(midi_obj, sdcard_obj)
        midi_in_player_obj.set_midi_in_program(0)

        # Sequencer object
        sequencer_obj = sequencer_class(midi_obj, sdcard_obj)

        # Device control in a thread
        thread_manager_obj = thread_manager_class()
        thread_manager_obj.start(device_manager_obj.device_control_thread, (thread_manager_obj, 5,))

        # LCD
        display = aqm0802a_lcd_class(62, 1, 7, 6)
        display.setContrast(0)
        display.clear()
        
        # Application loop
        application.app_loop()
        
    except Exception as e:
        print('Catch exception at main loop:', e)
        
    finally:
        print('All notes off to quit the application.')
        midi_obj.set_all_notes_off()
        
        print('Terminate device controller.')
        while thread_manager_obj.is_working():
            thread_manager_obj.stop_thread()
            utime.sleep_ms(1000)
            
        print('Exit.')
