###############################################
# Unit-MIDI synthesizer with Raspberry Pi PICO
###############################################
import os

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

      print('PATH:', '[' + path + ']', ' [' + fname + ']')
      print('FILE:', path + fname)
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
        
# Main program
if __name__ == '__main__':
    try:
        # SD cars (Internal memory file for PICO)
        sdcard_obj = sdcard_class()
        
#        os.mkdir('/SYNTH')
#        os.mkdir('/SYNTH/MIDIUNIT')
#        os.mkdir('/SYNTH/SEQFILE')
        gm_list = [
'Acostic Grand Piano    ',
'Bright Acostic Piano   ',
'Electric Grand Piano   ',
'Honky-Tonk Piano       ',
'Electric Piano 1       ',
'Electric Piano 2       ',
'Harpsicord             ',
'Clavi                  ',
'Celesta                ',
'Glockenspiel           ',
'Music Box              ',
'Vibraphone             ',
'Marimba                ',
'Xylophone              ',
'Tubular Bells          ',
'Dulcimer               ',
'Drawber Organ          ',
'Percussive Organ       ',
'Rock Organ             ',
'Church Organ           ',
'Reed Organ             ',
'Accordion              ',
'Harmonica              ',
'Tango Accordion        ',
'Acostic Guitar (nylon) ',
'Acostic Guitar (steel) ',
'Electric Guitar (jazz) ',
'Electric Guitar (clean)',
'Electric Guitar (muted)',
'Overdriven Guitar      ',
'Distortion Guitar      ',
'Guitar Harmonics       ',
'Acosic Bass            ',
'Electric Bass (finger) ',
'Electric Bass (pick)   ',
'Fretless Bass          ',
'Slap Bass 1            ',
'Slap Bass 2            ',
'Synth Bass 1           ',
'Synth Bass 2           ',
'Violin                 ',
'Viola                  ',
'Cello                  ',
'Contrabass             ',
'Tremoro Strings        ',
'Pizzicato Strings      ',
'Orchestral Harp        ',
'Timpani                ',
'String Ensamble 1      ',
'String Ensamble 2      ',
'Synth Strings 1        ',
'Synth Strings 2        ',
'Choir Aahs             ',
'Voice Oohs             ',
'Synth Voice            ',
'Orchestra Hit          ',
'Trumpet                ',
'Trombone               ',
'Tuba                   ',
'Muted Trumpet          ',
'French Horn            ',
'Brass Section          ',
'Synth Brass 1          ',
'Synth Brass 2          ',
'Soprano Sax            ',
'Alto Sax               ',
'Tenor Sax              ',
'Baritone Sax           ',
'Oboe                   ',
'English Horn           ',
'Bassoon                ',
'Clarinet               ',
'Piccolo                ',
'Flute                  ',
'Recorder               ',
'Pan Flute              ',
'Bottle Blow            ',
'Shakuhachi             ',
'Whistle                ',
'Ocarina                ',
'Lead 1 (square)        ',
'Lead 2 (sawtooth)      ',
'Lead 3 (caliope)       ',
'Lead 4 (chiff)         ',
'Lead 5 (charang)       ',
'Lead 6 (voice)         ',
'Lead 7 (fifth)         ',
'Lead 8 (bass+lead)     ',
'Pad 1 (new age)        ',
'Pad 2 (warm)           ',
'Pad 3 (polysynth)      ',
'Pad 4 (choir)          ',
'Pad 5 (bowed)          ',
'Pad 6 (metalic)        ',
'Pad 7 (halo)           ',
'Pad 8 (sweep)          ',
'FX (rain)              ',
'FX (soundtrack)        ',
'FX (crystal)           ',
'FX (atmosphere)        ',
'FX (brightness)        ',
'FX (goblins)           ',
'FX (echoes)            ',
'FX (sci-fi)            ',
'Sitar                  ',
'Banjo                  ',
'Shamisen               ',
'Koto                   ',
'Kalimba                ',
'Bagpipe                ',
'Fiddle                 ',
'Shanai                 ',
'Tinkle Bell            ',
'Agogo                  ',
'Steel Drums            ',
'Woodblock              ',
'Taiko Drum             ',
'Melodic Tom            ',
'Synth Drum             ',
'Reverse Cymbal         ',
'Guitar Fret Noise      ',
'Breath Noise           ',
'Seashore               ',
'Bird Tweet             ',
'Telephone Ring         ',
'Helicopter             ',
'Applause               ',
'Gun Shot               ',
        ]
        f = sdcard_obj.file_open('/SYNTH/MIDIFILE/', 'GM0.TXT', 'w')
        f.write('')
        f.close()

        f = sdcard_obj.file_open('/SYNTH/MIDIFILE/', 'GM0.TXT', 'a')
        for gm_name in gm_list:
            print(gm_name, file=f)
        f.close()

        f = sdcard_obj.file_open('/SYNTH/MIDIFILE/', 'GM0.TXT', 'r')
        print(f.read())
        f.close()
            
    except Exception as e:
        print('Catch exception at main loop:', e)
        
