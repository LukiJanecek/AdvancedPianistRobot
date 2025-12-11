import PySimpleGUI as sg
from kukaconn import KUKA_Handler
from KUKALIB import Parameters as Parameters
from KUKALIB import robinfo
from KUKALIB import subwindow as sw

robot =KUKA_Handler(Parameters.ip_KUKA, Parameters.port_KUKA, Parameters.KUKA1_defaultPositions)
robot.KUKA_Open()



need_mail=True
logo_path = r'C:\pythonProject\V3\450 FEI-CZ.png'
#logo_path = '450 FEI-CZ.png'


sg.theme('GrayGrayGray')

layout = [[sg.Text()],
          [sg.Text('Vyber mi skladbu', font=('Drive Book', 80), expand_x=True, justification='center')],
          [sg.Text(font=15)],
          [sg.Push(), sg.Button('REGGAE', font=('Drive Book', 35)), sg.Push(),
           sg.Button('STUPNICE', font=('Drive Book', 35)), sg.Push(),
           sg.Button(button_text='HÁDEJ MELODII', font=('Drive Book', 35)), sg.Push()],
          [sg.Text(font=13)],
          [sg.Text('', key='-UpperText-', font=('Drive Book', 30), expand_x=True, justification='center')],
          [sg.Text('', key='-BottomText-', font=('Drive Book', 20), expand_x=True, justification='center'), ],
          [sg.Text()],
          [sg.Text(text='B E Z P E Č N O S T     N A R U Š E N A',key='-varovani-',font=('Drive Book', 30),background_color='yellow', text_color='red',expand_x=True, justification='center'),
           sg.Button('Potvrzení',key='-ACK-',font=('Drive Book', 20),button_color='yellow')],
          [sg.Push(), sg.Image(logo_path), sg.Push()],
          [sg.Push(), sg.Button('Info',font=('Drive Book', 15),disabled=True), sg.Button('Nastavení',font=('Drive Book', 15))]
          ]

window = sg.Window('Klavirista GUI', layout, no_titlebar=True, size=(1024, 768), finalize=True)
window['-varovani-'].update(visible=False)
window['-ACK-'].update(visible=False)

def disablebuttons(var):
    window['REGGAE'].update(disabled=var)
    window['STUPNICE'].update(disabled=var)
    window['HÁDEJ MELODII'].update(disabled=var)






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

    if safety:
        window['-varovani-'].update(visible=True)
        window['-ACK-'].update(visible=True)

    if event == '-ACK-':
        robot.client.write('PyACK', str(True))
        window['-varovani-'].update(visible=False)
        window['-ACK-'].update(visible=False)

    if robot.KUKA_ReadVar('$OUT[8]') == b'FALSE':
        window['-varovani-'].update(visible=False)
        window['-ACK-'].update(visible=False)



    if need_mail:
        if event in ('REGGAE', 'STUPNICE', 'HÁDEJ MELODII'):
            sw.openKeyboard()
            text = sw.getEmail()
            sw.closeKeyboad()
            if text is not None:
                window['-UpperText-'].update('Právě vám hraji ' + event)
                window['-BottomText-'].update('Tahle skladba je pro ' + text)
                disablebuttons(True)
                match event:
                    case 'REGGAE':
                        robot.Play_REGGAE(True)
                    case 'STUPNICE':
                        robot.Play_STUPNICE(True)
                    case 'HÁDEJ MELODII':
                        robot.Play_BEETHOVEN(True)

    else:
        if event in ('REGGAE', 'STUPNICE', 'HÁDEJ MELODII'):
            window['-UpperText-'].update('Právě vám hraji ' + event)
            window['-BottomText-'].update('Užívejte!')
            disablebuttons(True)
            match event:
                case 'REGGAE':
                    robot.Play_REGGAE(True)
                case 'STUPNICE':
                    robot.Play_STUPNICE(True)
                case 'HÁDEJ MELODII':
                    robot.Play_BEETHOVEN(True)
    if songEnded:
        disablebuttons(False)
        robot.Play_REGGAE(False)
        robot.Play_STUPNICE(False)
        robot.Play_BEETHOVEN(False)

        window['-UpperText-'].update('')
        window['-BottomText-'].update('')

    if event == 'Nastavení':
        sw.openKeyboard()
        accessGranted = sw.logon()
        sw.closeKeyboad()
        if accessGranted:
            action = sw.settings()
            match action:
                case 'CollectMail':
                    need_mail = True
                case 'NoMailNeeded':
                    need_mail = False
                case 'CloseApp':
                    break

    if event == 'Info':
        robinfo.robotInfo()
        pass

robot.KUKA_Close()
window.close()




