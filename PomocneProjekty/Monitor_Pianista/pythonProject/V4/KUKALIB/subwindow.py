import PySimpleGUI as sg
import re
import csv
import os
import mouse
import time
from datetime import datetime

#icon_path = r'C:\Users\Adam Bátrla\PycharmProjects\pythonProject\logotyp.ico'
icon_path='C:\pythonProject\V2\logotyp.ico'

now = datetime.now()
date = now.strftime("%Y-%m-%d")
# emaily_path = (date + '-emaily.csv')

emaily_path =('C:/Users/FEI/Desktop/Emaily/' + date + '.csv')
def getEmail():
    openKeyboard()
    file = open(emaily_path, 'a', newline='')
    csv_writer = csv.writer(file)
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Napiš, prosím, svou emailovou adresu: ", key='-title-', font=('Drive Book', 20))],
              [sg.InputText(default_text='@',key='-email-', font=('Drive Book', 20), enable_events=True)],
              [sg.Text("Ať vím, pro koho hraji :-)", font=('Drive Book', 20))],
              [sg.Button(button_text='Potvrdit', font=('Drive Book', 20)),
               sg.Button(button_text='Zavřít', font=('Drive Book', 20))]]

    window = sg.Window("Email", layout, keep_on_top=True, finalize=True, modal=True, icon=icon_path)
    window['-email-'].set_focus()
    while True:
        event, values = window.read()
        if event == 'Potvrdit':
            in_text = values['-email-']
            if isEmail(in_text):
                now = datetime.now()
                dt_string = now.strftime("%H:%M:%S")
                csv_writer.writerow([dt_string + ';' + in_text])
                window.close()
                return values['-email-']
            else:
                window['-title-'].update('Zadejte prosím platnou emailovou adresu', text_color='red')

        if event == '-email-':
            window['-title-'].update('Napiš, prosím, svou emailovou adresu:', text_color='black')

        if event == 'Zavřít' or event == sg.WIN_CLOSED:
            break

    file.close()
    window.close()


def settings(need_mail,lc_off):
    sg.theme('GrayGrayGray')
    layout = [[sg.Checkbox('Pro spustění skladby je nutno zadat email', key='-Vybirame-', font=('Drive Book', 13),
                           enable_events=True, default=need_mail)],
              [sg.Checkbox(text='Deaktivace světelných závor',key='-zavoryOff-',font=('Drive Book', 13),
                           default=lc_off)],
              [sg.Button(button_text='Potvrdit', font=('Drive Book', 15)),
               sg.Button(button_text='Zavřít nastavení', font=('Drive Book', 15)),
               sg.Button(button_text='Ukončit aplikaci', font=('Drive Book', 15), button_color='red')]]

    window = sg.Window("Nastavení", layout, keep_on_top=True, icon=icon_path, finalize=True, modal=True)

    while True:
        event, values = window.read()
        if event == 'Potvrdit':
            window.close()
            return values['-Vybirame-'],values['-zavoryOff-']

        if event == 'Ukončit aplikaci':
            window.close()
            return 'CloseApp'

        if event == 'Zavřít nastavení' or event == sg.WIN_CLOSED:
            break
    window.close()


def isEmail(var):
    regex = r'[@].*(\.cz|\.com|\.sk|\.eu)'
    if var is not None: return bool(re.search(regex, var)) and len(var) > 10

def logon():
    sg.theme('GrayGrayGray')
    layout = [[sg.Text("Pro změnu nastavení zadejte heslo", font=('Drive Book', 12))],
              [sg.InputText(key='-password-', font=('Drive Book', 12), password_char='*')],
              [sg.Button(button_text='Ok', font=('Drive Book', 12)),
               sg.Button(button_text='Zavřít', font=('Drive Book', 12))]]

    window = sg.Window("Přihlášení", layout, keep_on_top=True, finalize=True, modal=True, icon=icon_path, size=(270, 100))
    window['-password-'].set_focus()
    while True:
        event, values = window.read()
        if event == 'Ok':
            if values['-password-'] == 'vsb':
                window.close()
                return 'Pass'
            elif values['-password-'] == '':
                pass
            else:
                window.close()
                return values['-password-']
        if event == 'Zavřít' or event == sg.WIN_CLOSED:
            break
    window.close()


def robotinfo(robot_instance):
    freeze = False
    sg.theme('GrayGrayGray')
    f=('Drive Book', 20)
    mezera=' '*30
    tab1 = [[sg.Text(key="-position_X-", font=f, size=(8, 1)), sg.Text('mm'+mezera), sg.Text(key="-position_A-",font=f,size=(7, 1)),sg.Text('°  ')],
            [sg.Text(key="-position_Y-", font=f, size=(8, 1)), sg.Text('mm'+mezera), sg.Text(key="-position_B-",font=f,size=(7, 1)),sg.Text('°  ')],
            [sg.Text(key="-position_Z-", font=f, size=(8, 1)), sg.Text('mm'+mezera), sg.Text(key="-position_C-",font=f,size=(7, 1)),sg.Text('°  ')]]

    tab2 = [[sg.Text(key="-mot_temp_A1-", font=f, size=(5, 1)), sg.Text('°C'+mezera), sg.Text(key="-mot_temp_A4-",font=f,size=(5, 1)), sg.Text('°C         ')],
            [sg.Text(key="-mot_temp_A2-", font=f, size=(5, 1)), sg.Text('°C'+mezera), sg.Text(key="-mot_temp_A5-",font=f,size=(5, 1)), sg.Text('°C         ')],
            [sg.Text(key="-mot_temp_A3-", font=f, size=(5, 1)), sg.Text('°C'+mezera), sg.Text(key="-mot_temp_A6-",font=f,size=(5, 1)), sg.Text('°C         ')]]

    tab3 = [[sg.Text(key="-mot_tq_A1-", size=(8, 1),font=f), sg.Text('Nm'+mezera), sg.Text(key="-mot_tq_A4-", size=(8, 1),font=f),
             sg.Text('Nm')],
            [sg.Text(key="-mot_tq_A2-", size=(8, 1),font=f), sg.Text('Nm'+mezera), sg.Text(key="-mot_tq_A5-", size=(8, 1),font=f),
             sg.Text('Nm')],
            [sg.Text(key="-mot_tq_A3-", size=(8, 1),font=f), sg.Text('Nm'+mezera), sg.Text(key="-mot_tq_A6-", size=(8, 1),font=f),
             sg.Text('Nm')]]

    layout = [[sg.TabGroup(
        [[sg.Tab('Aktuální pozice', tab1,font=('Drive Book', 25)),
          sg.Tab('Teplota motorů', tab2),
          sg.Tab('Točivý moment motorů', tab3)]])],
        [sg.Checkbox('Zmrazit', key='-freeze-',font=('Drive Book', 15),enable_events=True),sg.Push(),
        sg.Button(button_text='Zavřít', font=('Drive Book', 15))]]

    window = sg.Window("Aktuální parametry robotu",layout,modal=True,  keep_on_top=True,grab_anywhere=True,font=('Drive Book', 15),icon=icon_path)
    try:
        while True:
    
            event, values = window.read(timeout=50)

            if robot_instance.KUKA_ReadVar('$OUT[8]', False) == b'TRUE': # v pripade naruseni bezpecnosti se okno zavre
                break

            pos_raw = robot_instance.KUKA_ReadVar('$POS_ACT', False)
            pos_str = pos_raw.decode('utf-8').strip('{}')
            pos_list = re.split(', |: ', pos_str)[1:]

            # Inicializace proměnných pro X, Y a Z
            X = None
            Y = None
            Z = None
            A = None
            B = None
            C = None

            # Procházení seznamu a hledání hodnot pro X, Y a Z
            for item in pos_list[0:]:
                if item.startswith('X'):
                    X = float(item.split(' ')[1])
                elif item.startswith('Y'):
                    Y = float(item.split(' ')[1])
                elif item.startswith('Z'):
                    Z = float(item.split(' ')[1])
                elif item.startswith('A'):
                    A = float(item.split(' ')[1])
                elif item.startswith('B'):
                    B = float(item.split(' ')[1])
                elif item.startswith('C'):
                    C = float(item.split(' ')[1])

            # vycteni hodnot teplot motoru
            mot_temp_1 = robot_instance.KUKA_ReadVar('$MOT_TEMP[1]', False)
            mot_temp_2 = robot_instance.KUKA_ReadVar('$MOT_TEMP[2]', False)
            mot_temp_3 = robot_instance.KUKA_ReadVar('$MOT_TEMP[3]', False)
            mot_temp_4 = robot_instance.KUKA_ReadVar('$MOT_TEMP[4]', False)
            mot_temp_5 = robot_instance.KUKA_ReadVar('$MOT_TEMP[5]', False)
            mot_temp_6 = robot_instance.KUKA_ReadVar('$MOT_TEMP[6]', False)

            # vycteni hodnot tocivych momentu motoru
            mot_tq_1 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[1]', False)
            mot_tq_2 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[2]', False)
            mot_tq_3 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[3]', False)
            mot_tq_4 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[4]', False)
            mot_tq_5 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[5]', False)
            mot_tq_6 = robot_instance.KUKA_ReadVar('$TORQUE_AXIS_ACT[6]', False)

            if not freeze:
                # Výpis hodnot X, Y a Z
                window['-position_X-'].update('X: ' + str(round(X, 1)))
                window['-position_Y-'].update('Y: ' + str(round(Y, 1)))
                window['-position_Z-'].update('Z: ' + str(round(Z, 1)))
                window['-position_A-'].update('A: ' + str(round(A, 1)))
                window['-position_B-'].update('B: ' + str(round(B, 1)))
                window['-position_C-'].update('C: ' + str(round(C, 1)))

                # vypis teplot s prevodem z K na °C
                window['-mot_temp_A1-'].update('A1: ' + str(int(mot_temp_1) - 273))
                window['-mot_temp_A2-'].update('A2: ' + str(int(mot_temp_2) - 273))
                window['-mot_temp_A3-'].update('A3: ' + str(int(mot_temp_3) - 273))
                window['-mot_temp_A4-'].update('A4: ' + str(int(mot_temp_4) - 273))
                window['-mot_temp_A5-'].update('A5: ' + str(int(mot_temp_5) - 273))
                window['-mot_temp_A6-'].update('A6: ' + str(int(mot_temp_6) - 273))

                # vypis teplot s prevodem z K na °C
                window['-mot_tq_A1-'].update('A1: ' + str(round(float(mot_tq_1), 1)))
                window['-mot_tq_A2-'].update('A2: ' + str(round(float(mot_tq_2), 1)))
                window['-mot_tq_A3-'].update('A3: ' + str(round(float(mot_tq_3), 1)))
                window['-mot_tq_A4-'].update('A4: ' + str(round(float(mot_tq_4), 1)))
                window['-mot_tq_A5-'].update('A5: ' + str(round(float(mot_tq_5), 1)))
                window['-mot_tq_A6-'].update('A6: ' + str(round(float(mot_tq_6), 1)))

            if event == '-freeze-':
                freeze = values['-freeze-']

            if event == 'Zavřít' or event == sg.WIN_CLOSED:
                break
        window.close()
    except Exception as e:
        print(e)
def openKeyboard():
    os.system("C:\\PROGRA~1\\COMMON~1\\MICROS~1\\ink\\tabtip.exe")


def closeKeyboad():
    mouse.move(760, 626)
    mouse.click("left")
    time.sleep(0.2)
    mouse.click("left")
