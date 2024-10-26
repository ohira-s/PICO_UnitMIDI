###############################################
# Unit-MIDI synthesizer with Raspberry Pi PICO
###############################################
from machine import Pin, UART
import utime

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
        midi_msg = bytearray([0xF0, 0x7F, 0x7F, 0x04, 0x01, 0, vol, 0xF7])
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

################# End of MIDI Class Definition #################


def notes_on(midi_obj, notes):
    for note in notes:
        print("NOTE ON :", midi_obj.key_name(note))
        midi_obj.set_note_on(0, note, 127)


def notes_off(midi_obj, notes):
    for note in notes:
        print("NOTE ON :", midi_obj.key_name(note))
        midi_obj.set_note_off(0, note)
        
# Main program
if __name__ == '__main__':
    try:
        # Synthesizer objects
        unit_midi_obj = MIDIUnit(0)
        midi_obj = midi_class(unit_midi_obj, None)

        # PICO settings
        led = Pin("LED", Pin.OUT, value=0)
        
        # Play UnitMIDI with flashing a LED on PICO board
        score = [(60,), (64,), (67,), (60, 64, 67)]
        steps = len(score)
        play_at = 0
        effect = -1
        while True:
            # Master volume test
#            midi_obj.set_master_volume(int(127 / (play_at + 1)))

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
            midi_obj.set_instrument(0, 0, play_at * 5 + 20)
            
            # Note-on / Note-off
            notes = score[play_at]
            led.value(1)
            notes_on(midi_obj, notes)
            utime.sleep_ms(1000)

            led.value(0)
            notes_off(midi_obj, notes)
            utime.sleep_ms(500)
            
            # Next notes on the score
            play_at = (play_at + 1) % steps
            
    except Exception as e:
        print('Catch exception at main loop:', e)
        
    finally:
        midi_obj.set_all_notes_off()
        print('All notes off to quit the application.')
