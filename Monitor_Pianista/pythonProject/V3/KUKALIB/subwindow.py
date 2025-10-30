import PySimpleGUI as sg
import re
import csv
import os
import mouse
import time

#icon_path=r'C:\Users\Adam Bátrla\PycharmProjects\pythonProject\logotyp.ico'
icon_path='C:\pythonProject\V3\logotyp.ico'
# emaily_path = 'C:\pythonProject\V3\emaily.csv'
emaily_path = r'C:\Users\FEI\Desktop\emaily.csv'
def getEmail():
    openKeyboard()
    file = open(emaily_path, 'a', newline='')
    csv_writer = csv.writer(file)
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Napiš, prosím,  svou emailovou adresu: ",key='-title-', font=('Drive Book', 20))],
            [sg.InputText(key='-email-', font=('Drive Book', 20), enable_events=True)],
            [sg.Text("Ať vím, pro koho hraji :-)", font=('Drive Book', 20))],
            [sg.Button(button_text='Potvrdit', font=('Drive Book', 20)),sg.Button(button_text='Zavřít',font=('Drive Book', 20))]]

    window = sg.Window("Email", layout, keep_on_top=True, icon=icon_path)
    while True:
        event, values = window.read()
        if event == 'Potvrdit':
            in_text = values['-email-']
            if isEmail(in_text):
                csv_writer.writerow([in_text])
                window.close()
                return values['-email-']
            else:
                window['-title-'].update('Zadejte prosím platnou emailovou adresu',text_color='red')

        if event == '-email-':
            window['-title-'].update('Napiš, prosím, svou emailovou adresu:',text_color='black')

        if event == 'Zavřít' or event == sg.WIN_CLOSED:
            break

    file.close()
    window.close()


def settings():
    sg.theme('GrayGrayGray')
    layout = [[sg.Checkbox('Pro spustění skladby je nutno zadat email', key='-Vybirame-', font=('Drive Book', 13),
                           enable_events=True,default=True)],
              [sg.Button(button_text='Potvrdit', font=('Drive Book', 15)),
               sg.Button(button_text='Zavřít nastavení', font=('Drive Book', 15)),
               sg.Button(button_text='Ukončit aplikaci', font=('Drive Book', 15),button_color='red')]]

    window = sg.Window("Nastavení", layout,keep_on_top=True,icon=icon_path)
    while True:
        event, values = window.read()
        if event == 'Ukončit aplikaci':
            window.close()
            return 'CloseApp'

        if event == 'Potvrdit':
            window.close()
            if values['-Vybirame-']:
                return 'CollectMail'
            else:
                return 'NoMailNeeded'

        if event == 'Zavřít nastavení' or event == sg.WIN_CLOSED:
            break
    window.close()


def isEmail(var):
    regex = r'[@].*(\.cz|\.com|\.sk|\.eu)'
    if var is not None: return bool(re.search(regex, var)) and len(var) > 6


def logon():
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Pro změnu nastavení zadejte heslo", font=('Drive Book', 12))],
              [sg.InputText(key='-password-', font=('Drive Book', 12),password_char='*')],
              [sg.Button(button_text='Ok', font=('Drive Book', 12)),
               sg.Button(button_text='Zavřít', font=('Drive Book', 12))]]

    window = sg.Window("Přihlášení", layout,keep_on_top=True,icon=icon_path,size=(270,100))
    while True:
        event, values = window.read()
        if event == 'Ok':
            if values['-password-'] == 'vsb':
                window.close()
                return True
            elif values['-password-'] == '':
                pass
            else:
                sg.popup_auto_close('Špatné heslo',keep_on_top=True)
                window.close()
                return False
        if event == 'Zavřít' or event == sg.WIN_CLOSED:
            break
    window.close()


def openKeyboard():
    os.system("C:\\PROGRA~1\\COMMON~1\\MICROS~1\\ink\\tabtip.exe")


def closeKeyboad():
    mouse.move(760, 626)
    mouse.click("left")
    time.sleep(0.2)
    mouse.click("left")






