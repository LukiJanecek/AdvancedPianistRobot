import PySimpleGUI as sg
import re

import os
import mouse
import time

icon_path=r'C:\Users\Adam Bátrla\PycharmProjects\pythonProject\logotyp.ico'
def getEmail():
    openKeyboard()
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Napiš, prosím,  svou emailovou adresu: ", font=('Drive Book', 20))],
            [sg.InputText(key='-email-', font=('Drive Book', 20))],
            [sg.Text("Ať vím, pro koho hraji :-)", font=('Drive Book', 20))],
            [sg.Button(button_text='Potvrdit', font=('Drive Book', 20)),sg.Button(button_text='Zavřít',font=('Drive Book', 20))]]

    window = sg.Window("Email", layout, keep_on_top=True, icon='C:\pythonProject\V2\logotyp.ico')
    while True:
        event, values = window.read()
        if event == 'Potvrdit':
            if values['-email-'] != '':
                window.close()
                return values['-email-']
        if event == 'Zavřít' or event == sg.WIN_CLOSED:
            break
    window.close()


def logon():
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Pro změnu nastavení zadejte heslo", font=('Drive Book', 12))],
              [sg.InputText(key='-password-', font=('Drive Book', 12),password_char='*')],
              [sg.Button(button_text='Ok', font=('Drive Book', 12)),
               sg.Button(button_text='Zavřít', font=('Drive Book', 12))]]

    window = sg.Window("Přihlášení", layout,keep_on_top=True,icon='C:\pythonProject\V2\logotyp.ico',size=(270,100))
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






def isEmail(var):
    regex = r'[@].*(\.cz|\.com|\.sk)'
    if var is not None: return bool(re.search(regex, var)) and len(var) > 6


def openKeyboard():
    os.system("C:\\PROGRA~1\\COMMON~1\\MICROS~1\\ink\\tabtip.exe")


def closeKeyboad():
    mouse.move(760, 626)
    mouse.click("left")
    time.sleep(0.2)
    mouse.click("left")


# a=isEmail('adam@vsb.cz')
# b=isEmail('adam@vsb.sk')
# c=isEmail('adamvsb.com')
# d=isEmail('adamvsb.com')

# getEmail()




