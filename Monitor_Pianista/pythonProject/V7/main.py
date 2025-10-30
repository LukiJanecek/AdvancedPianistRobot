import PySimpleGUI as sg
from kukaconn import KUKA_Handler
from KUKALIB import Parameters as Parameters
from KUKALIB import subwindow as sw

global Online
Online = True


def disablebuttons(var):
    window['-play_song_1-'].update(disabled=var)
    window['-play_song_2-'].update(disabled=var)
    window['-play_song_3-'].update(disabled=var)


robot = KUKA_Handler(Parameters.ip_KUKA, Parameters.port_KUKA, Parameters.KUKA1_defaultPositions)
if Online:
    robot.KUKA_Open()

need_mail = False
lc_deactivate = False
if Online:
    robot.client.write('PyLCoff', str(lc_deactivate))
    robot.client.write('PyEND', str(False))
    logo_path = r'C:\pythonProject\V2\450 FEI-CZ.png'
    # logo_path = 'C:/Users/Adam Bátrla/Documents/GitHub/Klavirista_GUI/V7/450 FEI-CZ.png'
else:
    logo_path = '450 FEI-CZ.png'
    # logo_path = 'C:/Users/Adam Bátrla/Documents/GitHub/Klavirista_GUI/V7/450 FEI-CZ.png'

sg.theme('GrayGrayGray')

layout = [[sg.Text()],
          [sg.Text('Uhodneš, co hraju?', font=('Drive Book', 80), expand_x=True, justification='center')],
          [sg.Text('Vyber si obtížnost:', font=('Drive Book', 20), expand_x=True, justification='center')],
          [sg.Text(font=15)],
          [sg.Push(), sg.Button('LEHKÁ',key='-play_song_1-' ,font=('Drive Book', 35)), sg.Push(),
           sg.Button('STŘEDNÍ',key='-play_song_2-' , font=('Drive Book', 35)), sg.Push(),
           sg.Button(button_text='TĚŽKÁ',key='-play_song_3-' , font=('Drive Book', 35)), sg.Push()],
          [sg.Text(font=13)],
          [sg.Text('', key='-UpperText-', font=('Drive Book', 30), expand_x=True, justification='center')],
          # [sg.Text('', key='-BottomText-', font=('Drive Book', 20), expand_x=True, justification='center'), ],
          [sg.Text()],
          [sg.Text(text='B E Z P E Č N O S T     N A R U Š E N A', key='-varovani-', font=('Drive Book', 30),
                   background_color='yellow', text_color='red', expand_x=True, justification='center'),
           sg.Button('Potvrzení', key='-ACK-', font=('Drive Book', 20), button_color='yellow')],
          [sg.Push(), sg.Image(logo_path), sg.Push()],
          [sg.Push(), sg.Text('', key='-LC_State-', font=('Drive Book', 15)),
           sg.Button('Parametry', font=('Drive Book', 15)), sg.Button('Nastavení', font=('Drive Book', 15))]
          ]

window = sg.Window('Klavirista GUI', layout, no_titlebar=True, keep_on_top=True, size=(1024, 768), finalize=True)
window['-varovani-'].update(visible=False)
window['-ACK-'].update(visible=False)

while True:  # The Event Loop
    event, values = window.read(timeout=50)
    robot.client.write('TEST_BOOL', str(True))
    if robot.KUKA_ReadVar('PyLCoff', False) == b'TRUE':
        lc_deactivate = True
    else:
        lc_deactivate = False

    if robot.KUKA_ReadVar('PyEND', False) == b'TRUE':
        songEnded = True
    else:
        songEnded = False

    if robot.KUKA_ReadVar('$OUT[8]', False) == b'TRUE':  # robot se nachazi v safetystopu
        window['-varovani-'].update(visible=True)
        window['-ACK-'].update(visible=True)
    else:
        window['-varovani-'].update(visible=False)
        window['-ACK-'].update(visible=False)

    if event == '-ACK-':
        robot.client.write('PyACK', str(True))

    if event in ('-play_song_1-', '-play_song_2-', '-play_song_3-'):
        if need_mail:
            text = sw.questionnaire()
        else:
            text = 'Užívejte!'
        if text != 'Rollback':
            window['-UpperText-'].update('Pozorně poslouchej... Už tušíš, co je to za melodii?')
            #window['-BottomText-'].update(text)
            disablebuttons(True)
            match event:
                case '-play_song_1-':
                    robot.Play_REGGAE(True)
                case '-play_song_2-':
                    robot.Play_STUPNICE(True)
                case '-play_song_3-':
                    robot.Play_BEETHOVEN(True)

    else:
        if event in ('REGGAE', 'STUPNICE', 'HÁDEJ MELODII'):
            window['-UpperText-'].update('Právě vám hraji ' + event)
            #window['-BottomText-'].update()
            disablebuttons(True)
            match event:
                case 'REGGAE':
                    robot.Play_REGGAE(True)
                case 'STUPNICE':
                    robot.Play_STUPNICE(True)
                case 'HÁDEJ MELODII':
                    robot.Play_BEETHOVEN(True)

    if robot.KUKA_ReadVar('PyEND', False) == b'TRUE':  # pokud je PyEND true, coz nastavi robot na konci pisnicky
        disablebuttons(False)
        robot.Play_REGGAE(False)
        robot.Play_STUPNICE(False)
        robot.Play_BEETHOVEN(False)

        window['-UpperText-'].update('')
        #window['-BottomText-'].update('')

    if event == 'Nastavení':
        sw.openKeyboard()
        accessGranted = sw.logon()
        sw.closeKeyboad()
        if accessGranted == 'Pass':
            if robot.KUKA_ReadVar('PyMAX_VOLUME', False) == b'TRUE':
                max_volume = True
            else:
                max_volume = False
            settings_out = sw.settings(need_mail, lc_deactivate, max_volume)
            if settings_out == 'CloseApp':
                robot.Play_REGGAE(False)
                robot.Play_STUPNICE(False)
                robot.Play_BEETHOVEN(False)
                break
            elif type(settings_out) is tuple:
                need_mail = settings_out[0]
                lc_deactivate = settings_out[1]
                max_volume = settings_out[2]
                robot.client.write('PyLCoff', str(lc_deactivate))
                robot.client.write('PyMAX_VOLUME', str(max_volume))
        elif type(accessGranted) is str:
            sg.popup_no_buttons('Špatné heslo, fakt to není: "' + accessGranted + '" :-)', font=('Drive Book', 15),
                                modal=True, auto_close=True, auto_close_duration=2,
                                icon='C:\pythonProject\V2\logotyp.ico', title='Mě nepřečůráš')

    if lc_deactivate:
        window['-LC_State-'].update('Světelná závora neaktivní', text_color='red')
    else:
        window['-LC_State-'].update('Světelná závora aktivní', text_color='black')

    if event == 'Parametry':
        sw.robotinfo(robot)

robot.KUKA_Close()
window.close()
