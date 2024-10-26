from machine import Pin, UART
import utime

###################
# Unit-MIDI class
###################
class MIDIUnit:
    # Constructor
    #   uart_unit: PICO UART unit number 0 or 1
    #   port     : A tuple of (Tx, Rx)
    #              This argument is NOT USED, to keep compatibility with M5Stack CORE2.
    def __init__(self, uart_unit=0, port=None):
        self._uart = UART(uart_unit, 31250)
        
    def midi_out(self, midi_msg):
        self._uart.write(midi_msg)

    def set_note_on(self, channel, note_key, velosity):
        midi_msg = bytearray([0x90 + channel, note_key, velosity])
        self.midi_out(midi_msg)

    def set_note_off(self, channel, note_key):
        midi_msg = bytearray([0x90 + channel, note_key, 0])
        self.midi_out(midi_msg)
        
        
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
        self.GM_FILE_PATH = '/sd//SYNTH/MIDIFILE/'       # GM program names list file path
 
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

    # Get key name of key number
    #   key_num: MIDI note number
    def key_name(self, key_num):
        octave = int(key_num / 12) - 1
        return self.key_names[key_num % 12] + ('' if octave < 0 else str(octave))

    # Note on
    def set_note_on(self, channel, note_key, velosity, transpose = False):
        self.synth.set_note_on(channel, note_key + (self.key_trans if transpose else 0), velosity)
  
    # Note off
    def set_note_off(self, channel, note_key, transpose = False):
        self.synth.set_note_off(channel, note_key + (self.key_trans if transpose else 0))


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
        while True:
            notes = score[play_at]
            led.value(1)
            notes_on(midi_obj, notes)
            utime.sleep_ms(500)

            led.value(0)
            notes_off(midi_obj, notes)
            utime.sleep_ms(500)
            
            play_at = (play_at + 1) % steps
            
    except Exception as e:
        print('Catch exception at main loop:', e)
