###############################################
# Unit-MIDI synthesizer with Raspberry Pi PICO
###############################################
from machine import Pin, UART, I2C
import time, utime, os, json
import random
import _thread

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


#######################
### Application class
#######################
class unipico_application_class:
    # Constructor
    def __init__(self):
        self.lock = False
        self.order_queuer = []

        self.sequencer_playing = False
        self.sequencer_pause = False
        self.sequencer_stop = False

        self.joystick_x = -1
        self.joystick_y = -1
        self.joystick_b = False

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

    # Joy Stick delegateion of device controller
    def device_joystick_controller(self, joy_x, joy_y, joy_b):
        # Sequencer player
        if joy_b == 1:
            # Stop trigger
            if self.sequencer_playing:
                self.sequencer_pause = True
            
            # Play
            else:
                self.sequencer_playing = True
                self.make_order('play sequencer', (977,))
                utime.sleep_ms(1000)
        
        # Stop playing
        elif self.sequencer_pause:
            self.sequencer_stop =True
            self.sequencer_pause = False
            utime.sleep_ms(1000)

        # Master volume
        if self.joystick_y != joy_y:
#            print('MASTRE VOLUME:', int(joy_y / 255 * 127))
            midi_obj.set_master_volume(int(joy_y / 255 * 127))
            self.joystick_y = joy_y

        # Pitch Bend
        if self.joystick_x != joy_x:
            if joy_x <= 100:
#                print('PITCH BEND -:', joy_x)
                midi_obj.set_pitch_bend(0, 0x1fff - int(0x1fff * (100 - joy_x) / 100))
            elif joy_x >= 155:
#                print('PITCH BEND +:', joy_x)
                midi_obj.set_pitch_bend(0, 0x1fff + int(0x1fff * (joy_x - 155) / 100))
            else:
                midi_obj.set_pitch_bend(0, 0x1fff)

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

        # Play test data
        score = [(60,), (64,), (67,), (60, 64, 67)]
        steps = len(score)
        play_at = 0
        effect = -1
        
        # Play UnitMIDI with flashing a LED on PICO board
        while True:
            # Order to the application
            order = self.get_order()
            if not order is None:
                if order[0] == 'play sequencer':
                    self.order_play_sequencer(order[1])
                
            # Effector test
            if play_at == 0:
                effect = (effect + 1) % 6
                if effect == 1:
                    print('REVERB')
                    midi_obj.set_reverb(0, 3, 120, 80)
                elif effect == 3:
                    print('CHORUS')
                    midi_obj.set_chorus(0, 3, 120, 120, 120)
                elif effect == 5:
                    print('VIBRATE')
                    midi_obj.set_vibrate(0, 60, 120, 0)
                else:
                    print('NO EFFECT')
                    midi_obj.set_reverb(0, 0, 0, 0)
                    midi_obj.set_chorus(0, 0, 0, 0, 0)
                    midi_obj.set_vibrate(0, 0, 0, 0)

            # Instrument test
            gm_program_no = random.randint(0,127)
            gm_program_name = midi_obj.get_gm_program_name(midi_obj.gmbank(), gm_program_no)
            print('INSTRUMENT:', gm_program_name)
            midi_obj.set_instrument(0, 0, gm_program_no)
            
            # Note-on
            notes = score[play_at]
            led.value(1)
            notes_on(midi_obj, notes)
            utime.sleep_ms(1000)

            # Note-off
            led.value(0)
            notes_off(midi_obj, notes)
            utime.sleep_ms(500)
            
            # Next notes on the score
            play_at = (play_at + 1) % steps
            
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
        joystick_obj = device_joystick_class(device_manager_obj)
        joystick_obj.delegate(application.device_joystick_controller)
        
        # Synthesizer objects
        unit_midi_obj = MIDIUnit(0)
        midi_obj = midi_class(unit_midi_obj, sdcard_obj)
        midi_obj.set_pitch_bend_range(0, 5)

        # Sequencer object
        sequencer_obj = sequencer_class(midi_obj, sdcard_obj)

        # Device control in a thread
        thread_manager_obj = thread_manager_class()
        thread_manager_obj.start(device_manager_obj.device_control_thread, (thread_manager_obj, 5,))

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
