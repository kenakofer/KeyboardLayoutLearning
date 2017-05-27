#!/usr/bin/env python3
import curses
from curses import wrapper, textpad
from time import sleep, strftime, mktime, gmtime
import subprocess
import _thread
import random
from sys import argv
from datetime import datetime

WORDS_FILE = '10000words.txt' #File to draw random words from
WORDS_SAMPLE_SIZE = 1000
LINE_CHARACTER_WIDTH = 70
TIME_LIMIT = 15*60  #Time out after 15 minutes
BACKSPACE_ENABLED = False

layouts = {
    #LAYOUT   TOP ROW      HOME ROW     BOTTOM ROW
    #------   -----------  -----------  -----------
    'qwerty': 'qwertyuiop'+'asdfghjkl;'+'zxcvbnm,./',
    '0':'\',.pyfgcrl'+'aoeuidhtns'+';qjkxbmwvz', #Dvorak
    '1': 'gljz,x.uvk'+'oidhtnears'+'pw;b/ycmfq', #10 most common letter in home row, otherwise random
    '2': 'fjh,.;dvli'+'bostunprmz'+'exaqwy/gck', #Fewer than 5 most common letters in home row (4 to be exact), otherwise random
    }

LAYOUT_TO_USE = argv[1]
PRETEST_LAYOUT = 'qwerty'
SYSTEM_LAYOUT = 'qwerty'
assert LAYOUT_TO_USE in layouts and SYSTEM_LAYOUT in layouts

SURVEY_QUESTIONS = [
    'Do you normally look at the keyboard while you type? (Yes/No/Sometimes)',
    'How many fingers do you normally use to type? (1-10)',
    'How many different keyboard layouts (including different languages) have you learned to use? (0-10)',
    'List them below, separated by commas:',
    'If you would like the opportunity to receive a $20 Java card for achieving the highest score in this study, enter your email below. Leave blank to opt-out.'
]

PRETEST_INSTRUCTIONS = 'You will now take a short typing test to adjust to how the interface works.' 

MAIN_INSTRUCTIONS = 'You will now begin to learn to type in the keyboard layout which is displayed below. The program will show one line of common english words, and you will type them as quickly as you can. All words are lowercase. Backspace is disabled. The test will end after 15 minutes have passed. You can see your current CPM (characters per minute) in the lefthand panel.'

GOODBYE = 'You have finished! If you filled out your email and have the highest score out of all experiment subjects, we will contact you to receive the gift card. Please tell the experiment coordinator that you have finished.\n\nThank you for your time and mental effort!'

INCORRECT_COLOR = (1,curses.COLOR_RED, curses.COLOR_BLACK)
CORRECT_COLOR = (2, curses.COLOR_GREEN, curses.COLOR_BLACK)
INCORRECT_KEY = (3,curses.COLOR_BLACK, curses.COLOR_RED)
CORRECT_KEY = (4, curses.COLOR_BLACK, curses.COLOR_GREEN)
MODEL_COLOR = (5,curses.COLOR_BLACK,curses.COLOR_WHITE)
GRAPH_COLOR = (6,curses.COLOR_YELLOW,curses.COLOR_BLACK)

def load_words():
    words = []
    count = 0
    for line in open(WORDS_FILE, 'r'):
        if count > WORDS_SAMPLE_SIZE:
            break
        words.append(line.strip())
        count += 1
    return words

def get_line_of_text(word_choices, character_length):
    line = ""
    while len(line) <= character_length:
        to_add = random.choice(word_choices)
        if len(line) + 1 + len(to_add) > character_length:
            break
        line += ' '+to_add
    return line.strip()

def display_information(string, terminate_with_key=True, terminate_at_time=9, show_keyboard_layout = None):
    main_pad.clear()
    main_pad.addstr(0,0,string)
    if show_keyboard_layout in layouts:
        draw_keyboard(layouts[show_keyboard_layout], None)

    if terminate_with_key:
        main_pad.addstr(5,3, 'Press any key to continue...')
        main_pad.refresh( 0,0, 0,0, 25,width+20)
        stdscr.getch()
    else:
        if terminate_at_time <= 0:
            return
        else:
            main_pad.addstr(5,3, 'We will continue in '+str(terminate_at_time)+' seconds...')
            main_pad.refresh( 0,0, 0,0, 25,width+20)
            sleep(1)
            display_information(string, terminate_with_key=False, terminate_at_time=terminate_at_time-1, show_keyboard_layout = show_keyboard_layout)

def survey():
    curses.echo()
    out_file = id_str+'.results'
    answers = []
    with open(out_file, 'a+') as f:
        f.write('id: '+id_str+'\r\n')
        for question in SURVEY_QUESTIONS:
            main_pad.clear()
            main_pad.addstr(0,0, question)
            main_pad.addstr(1,1,'')
            main_pad.refresh( 0,0, 0,0, 25,width+20)

            f.write(question)
            f.write( str(stdscr.getstr(1,1, 80)) )
            f.write('\r\n')

def display_stats(layout, time, model_line, typed_line, mistake_count):
    main_pad.clear()
    cpm = len(model_line)/time*60
    accuracy = max(0, 1-mistake_count/len(model_line))
    score = accuracy * cpm
    display_string = \
        'CPM (chars / minute): '+str(int(cpm))+'\n'+\
        'Mistakes:             '+str(mistake_count)+'\n'+\
        'Accuracy:             '+str(int(accuracy*100))+'%\n'+\
        'Score on this line:   '+str(int(score))+'\n'

    #Write results
    out_file = id_str+'.results'
    with open(out_file, 'a+') as f:
        strings = ['id: '+id_str,
                'layout: '+layout,
                'time: '+strftime("%c"),
                'elapsed: '+str(time),
                'length: '+str(len(model_line)), 
                'cpm: '+str(cpm),
                'mistakes: '+str(mistake_count),
                'accuracy: '+str(accuracy),
                'score: '+str(score),
                'model_line: '+model_line,
                'typed_line: '+typed_line]
        for string in strings:
             f.write(string)
             f.write('\r\n')
        f.write('\r\n')

        display_information(display_string, terminate_with_key=False, show_keyboard_layout = layout)

#TODO make keys flash green and red when pressed.
def draw_keyboard(char_list, pressed_char, is_correct = True):
    KEY_WIDTH = 6
    KEY_HEIGHT = 4
    start_y = 6
    char_list = char_list.upper()
    #FIRST ROW
    x = 0; y = start_y
    for k in range(0, 10):
        textpad.rectangle(main_pad, y, x, y + KEY_HEIGHT, x + KEY_WIDTH)
        char = char_list[0+k]
        style = curses.A_BOLD
        if pressed_char == char.lower():
            if is_correct:
                style = curses.color_pair(CORRECT_KEY[0])
            else:
                style = curses.color_pair(INCORRECT_KEY[0])
        if not char.isalpha():
            char=' '
        main_pad.addstr(y + 1, x+1, ' '*(KEY_WIDTH - 1), style)
        main_pad.addstr(y + 2, x+1, (' '*(KEY_WIDTH//2 - 1)) + char + (' '*(KEY_WIDTH//2 - 1)), style)
        main_pad.addstr(y + 3, x+1, ' '*(KEY_WIDTH - 1), style)
        x += KEY_WIDTH
    y += KEY_HEIGHT
    x = 2
    #SECOND ROW
    for k in range(0, 10):
        textpad.rectangle(main_pad, y, x, y + KEY_HEIGHT, x + KEY_WIDTH)
        char = char_list[10+k]
        style = curses.A_BOLD
        if pressed_char == char.lower():
            if is_correct:
                style = curses.color_pair(CORRECT_KEY[0])
            else:
                style = curses.color_pair(INCORRECT_KEY[0])
        if not char.isalpha():
            char=' '
        main_pad.addstr(y + 1, x+1, ' '*(KEY_WIDTH - 1), style)
        main_pad.addstr(y + 2, x+1, (' '*(KEY_WIDTH//2 - 1)) + char + (' '*(KEY_WIDTH//2 - 1)), style)
        main_pad.addstr(y + 3, x+1, ' '*(KEY_WIDTH - 1), style)
        if (k in [3,6]):
            main_pad.addstr(y + KEY_HEIGHT//2+1, x+KEY_WIDTH//2, '_', style)
        x += KEY_WIDTH
    y += KEY_HEIGHT
    x = 5
    #THIRD ROW
    for k in range(0, 10):
        textpad.rectangle(main_pad, y, x, y + KEY_HEIGHT, x + KEY_WIDTH)
        char = char_list[20+k]
        style = curses.A_BOLD
        if pressed_char == char.lower():
            if is_correct:
                style = curses.color_pair(CORRECT_KEY[0])
            else:
                style = curses.color_pair(INCORRECT_KEY[0])
        if not char.isalpha():
            char=' '
        main_pad.addstr(y + 1, x+1, ' '*(KEY_WIDTH - 1), style)
        main_pad.addstr(y + 2, x+1, (' '*(KEY_WIDTH//2 - 1)) + char + (' '*(KEY_WIDTH//2 - 1)), style)
        main_pad.addstr(y + 3, x+1, ' '*(KEY_WIDTH - 1), style)
        x += KEY_WIDTH
    main_pad.refresh( start_y, 0, start_y, 0, start_y + KEY_HEIGHT*3 , 0 + 4 + 10*KEY_WIDTH)


def convert(char, from_layout, to_layout):
    from_string = layouts[from_layout]
    to_string = layouts[to_layout]
    try:
        key_position = from_string.index(char)
    except ValueError:
        return None
    return to_string[key_position]


def run_test(stdscr, choices, layout):
    #Start of new line of the test
    curses.noecho()
    main_pad.clear()
    draw_keyboard(layouts[layout], None)
    model_line = get_line_of_text(choices, LINE_CHARACTER_WIDTH)
    typed_line = ''
    line_num = 1; x = 0
    mistakes = 0
    start = datetime.now()

    main_pad.addstr(0,x,model_line)
    main_pad.addstr(1,x,'') #Move cursor to next line
    main_pad.refresh( 0,0, 0,0, 25,width+20)


    while x < len(model_line):
        #start of character fetch/process cycle
        typed_char_code = stdscr.getch()
        typed_char = chr(typed_char_code)

        #Convert char to the new layout if not space or backspace
        if not typed_char in [curses.KEY_BACKSPACE, ' ']:
            typed_char = convert( typed_char, SYSTEM_LAYOUT, layout )

        model_char = model_line[x]

        if typed_char: #Conversion may have returned None
            typed_line += typed_char

        if typed_char == model_char: #CORRECT LETTER
            main_pad.addstr(1, x, typed_char, curses.color_pair(CORRECT_COLOR[0]) | curses.A_BOLD)
            x+=1
            is_correct = True
        elif typed_char == curses.KEY_BACKSPACE: #BACKSPACE
            if BACKSPACE_ENABLED:
                if x !=0:
                    x-=1
                    main_pad.addstr(line_num, x, ' ')
                    main_pad.addstr(line_num, x, '')
            is_correct = False
        else: #WRONG LETTER
            #TODO this should be a separate option
            if BACKSPACE_ENABLED:
                main_pad.addstr(1, x, typed_char, curses.color_pair(INCORRECT_COLOR[0]) | curses.A_BOLD) 
                x += 1
            mistakes += 1
            is_correct = False

        draw_keyboard(layouts[layout], typed_char, is_correct = is_correct)
        main_pad.refresh( 0,0, 0,0, 25,width+20)
    
    #Finished with a line, show the status page
    now = datetime.now()
    time = now - start
    time = time.total_seconds()
    display_stats(layout, time, model_line, typed_line, mistakes)

def run(stdscr):

    choices = load_words()

    survey()

    #PRETEST
    display_information(PRETEST_INSTRUCTIONS, show_keyboard_layout = PRETEST_LAYOUT)
    run_test(stdscr, choices, PRETEST_LAYOUT)

    #MAIN TEST
    display_information(MAIN_INSTRUCTIONS, show_keyboard_layout = LAYOUT_TO_USE)
    very_start = datetime.now()
    while True:

        run_test(stdscr, choices, LAYOUT_TO_USE)

        #Check if we have exceeded the time limit
        if (datetime.now() - very_start).total_seconds() >= TIME_LIMIT:
            break
    display_information(GOODBYE)


def init_curses():
    global stdscr, main_pad, ref_pad, width
    stdscr = curses.initscr()
    curses.echo()
    curses.cbreak()
    curses.start_color()
    curses.init_pair(*INCORRECT_COLOR)
    curses.init_pair(*CORRECT_COLOR)
    curses.init_pair(*INCORRECT_KEY)
    curses.init_pair(*CORRECT_KEY)
    curses.init_pair(*MODEL_COLOR)
    curses.init_pair(*GRAPH_COLOR)
    stdscr.attron(curses.A_BOLD)
    stdscr.keypad(True)

    width=curses.COLS
    main_pad = curses.newpad(70, width)

def cleanup_curses():
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()

def set_id():
    global id_str
    id_str = str(int(mktime(gmtime()))) + str(random.randint(100,999))

if __name__ == '__main__':
    set_id()
    init_curses()
    wrapper(run) #main method
    cleanup_curses() #Exiting
