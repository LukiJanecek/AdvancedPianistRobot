import time

import PySimpleGUI as sg
import csv
from kukaconn import KUKA_Handler
import Parameters as Parameters
import robinfo
import os
import mouse
robot = KUKA_Handler(Parameters.ip_KUKA, Parameters.port_KUKA, Parameters.KUKA1_defaultPositions)
robot.KUKA_Open()

file = open('../emaily.csv', 'a', newline='')
csv_writer = csv.writer(file)

sg.theme('GrayGrayGray')

layout = [[sg.Text()],
          [sg.Text('Vyber mi skladbu', font=('Drive Book', 80), expand_x=True, justification='center')],
          [sg.Text(font=15)],
          [sg.Push(), sg.Button('REGGAE', font=('Drive Book', 40)), sg.Push(),
           sg.Button('STUPNICE', font=('Drive Book', 40)), sg.Push(),
           sg.Button('BEETHOVEN', font=('Drive Book', 40)), sg.Push()],
          [sg.Text(font=13)],
          [sg.Text('', key='-UpperText-', font=('Drive Book', 30), expand_x=True, justification='center')],
          [sg.Text('', key='-BottomText-', font=('Drive Book', 20), expand_x=True, justification='center'), ],
          [sg.Text()],
          [sg.Text(text='B E Z P E Č N O S T     N A R U Š E N A',key='-varovani-',font=('Drive Book', 30), text_color='red',expand_x=True, justification='center')],
          [sg.Push(), sg.Image('450 FEI-CZ.png'), sg.Push()],
          [sg.Push(), sg.Button('Info'), sg.Text('Je nutno zadat email',key='-Collect-',enable_events=True),sg.Button('<-Zmena', key='-BtnChange-'),sg.Exit()]
          ]

window = sg.Window('Klavirista GUI', layout, no_titlebar=True, size=(1024, 768), finalize=True)
window['-varovani-'].update(visible=True)
needMail = True
robot.client.write('PyEND', str(False))
# window.Maximize()
def disablebuttons(var):
    window['REGGAE'].update(disabled=var)
    window['STUPNICE'].update(disabled=var)
    window['BEETHOVEN'].update(disabled=var)

def openKeyboard():
    os.system("C:\\PROGRA~1\\COMMON~1\\MICROS~1\\ink\\tabtip.exe")


def closeKeyboad():
    mouse.move(760, 626)
    mouse.click("left")
    time.sleep(0.2)
    mouse.click("left")

while True:  # The Event Loop
    event, values = window.read(timeout=20)

    if robot.KUKA_ReadVar('PyEND') == b'TRUE':
        songEnded = True
    else:
        songEnded = False
    if robot.KUKA_ReadVar('$IN[8]') == b'TRUE':
        safety = True
    else:
        safety = False

    if event == '-BtnChange-':
        openKeyboard()
        password = sg.popup_get_text('Pro pokračování zadej heslo', title="Oprávnění k akci", password_char='*')
        closeKeyboad()
        if password == 'vsb':
            needMail = not needMail
        elif password is None:
            pass
        else:
            sg.popup_auto_close('Spatne heslo')

    if needMail:
        window['-Collect-'].update('Je nutno zadat email')
    else:
        window['-Collect-'].update('Není nutno zadat email')

    if safety:
        window['-varovani-'].update(visible=True)
    else:
        window['-varovani-'].update(visible=False)
    if needMail:
        if event in ('REGGAE', 'STUPNICE', 'BEETHOVEN'):
            openKeyboard()
            text = sg.popup_get_text('Napiš svou emailovou adresu', title="Email", font=('Drive Book', 12))
            closeKeyboad()
            if text is not None:
                if '@' in text and len(text) > 5:
                    window['-UpperText-'].update('Právě vám hraji ' + event)
                    window['-BottomText-'].update('Tahle skladba je pro ' + text)
                    csv_writer.writerow([text])
                    disablebuttons(True)
                    match event:
                        case 'REGGAE':
                            robot.Play_REGGAE(True)
                        case 'STUPNICE':
                            robot.Play_STUPNICE(True)
                        case 'BEETHOVEN':
                            robot.Play_BEETHOVEN(True)
                else:
                    window['-UpperText-'].update('Zadejte prosím platnou emailovou adresu')
    else:
        if event in ('REGGAE', 'STUPNICE', 'BEETHOVEN'):
            window['-UpperText-'].update('Právě vám hraji ' + event)
            window['-BottomText-'].update('Užívejte!')
            disablebuttons(True)
            match event:
                case 'REGGAE':
                    robot.Play_REGGAE(True)
                case 'STUPNICE':
                    robot.Play_STUPNICE(True)
                case 'BEETHOVEN':
                    robot.Play_BEETHOVEN(True)
    if songEnded:
        disablebuttons(False)
        robot.Play_REGGAE(False)
        robot.Play_STUPNICE(False)
        robot.Play_BEETHOVEN(False)
        # robot.client.write('PyEND', str(False))
        window['-UpperText-'].update('')
        window['-BottomText-'].update('')

    if event == 'Info':
        robinfo.robotInfo()
        pass

    if event == sg.WIN_CLOSED or event == 'Exit':
        openKeyboard()
        password = sg.popup_get_text('Pro pokračování zadej heslo', title="Oprávnění k akci", password_char='*')
        closeKeyboad()
        if password == 'vsb':
            break
        elif password is None:
            pass
        else:
            sg.popup_auto_close('Špatné heslo')

robot.KUKA_Close()
file.close()
window.close()




