import PySimpleGUI as sg
import csv

from kukaconn import KUKA_Handler
#from KUKALIB import kukaconn
from KUKALIB import Parameters as Parameters
from KUKALIB import robinfo
from KUKALIB import subwindow as sw


robot =KUKA_Handler(Parameters.ip_KUKA, Parameters.port_KUKA, Parameters.KUKA1_defaultPositions)
robot.KUKA_Open()

need_mail = True


file = open('C:\pythonProject\V2\emaily.csv', 'a', newline='')
csv_writer = csv.writer(file)
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
          [sg.Push(), sg.Image(r'C:\pythonProject\V2\450 FEI-CZ.png'), sg.Push()],
          [sg.Push(), sg.Button('Info',font=('Drive Book', 15)), sg.Button('Nastavení',font=('Drive Book', 15))]
          ]

window = sg.Window('Klavirista GUI', layout, no_titlebar=True, size=(1024, 768), finalize=True)
window['-varovani-'].update(visible=False)
window['-ACK-'].update(visible=False)

window.Maximize()
def disablebuttons(var):
    window['REGGAE'].update(disabled=var)
    window['STUPNICE'].update(disabled=var)
    window['HÁDEJ MELODII'].update(disabled=var)




def settings():
    sg.theme('GrayGrayGray')

    layout = [[sg.Checkbox('Pro spustění skladby je nutno zadat email', key='-Vybirame-', font=('Drive Book', 13),
                           enable_events=True,default=True)],
              [sg.Button(button_text='Potvrdit', font=('Drive Book', 15)),
               sg.Button(button_text='Zavřít nastavení', font=('Drive Book', 15)),
               sg.Button(button_text='Ukončit aplikaci', font=('Drive Book', 15),button_color='red')]]

    window = sg.Window("Nastavení", layout,keep_on_top=True,icon='C:\pythonProject\V2\logotyp.ico')
    while True:
        event, values = window.read()
        if event == 'Ukončit aplikaci':
            window.close()
            return 'CloseApp'

        if event == 'Potvrdit':
            global need_mail
            need_mail = values['-Vybirame-']
            break
        if event == 'Zavřít nastavení' or event == sg.WIN_CLOSED:
            break
    window.close()

while True:  # The Event Loop
    event, values = window.read(timeout=5)

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

            if sw.isEmail(text):
                csv_writer.writerow([text])
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
            elif text == '' or text is None:
                pass
            else:
                window['-UpperText-'].update('Zadejte prosím platnou emailovou adresu')
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
            action = settings()
            match action:
                case 'CloseApp':
                    break

    if event == 'Info':
        robinfo.robotInfo()
        pass


file.close()
robot.KUKA_Close()
window.close()




