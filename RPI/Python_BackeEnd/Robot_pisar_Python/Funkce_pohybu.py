#Needed functions 
#pip install pandas openpyxl
import pandas as pd

from time import sleep


def draw_A(robot,offset):

    print("DRAW_A")

    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[0:].isnull().any(axis=1).idxmax()
    df = df.iloc[0:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    
    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")  

    print("Function_A done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return


def draw_B(robot,offset):

    print("DRAW_B")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[20:].isnull().any(axis=1).idxmax()
    df = df.iloc[20:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)

    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    
    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")  

    print("Function_B done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return


def draw_C(robot,offset):

    print("DRAW_C")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[40:].isnull().any(axis=1).idxmax()
    df = df.iloc[40:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_C done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_D(robot,offset):

    print("DRAW_D")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[60:].isnull().any(axis=1).idxmax()
    df = df.iloc[60:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_D done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_E(robot,offset):

    print("DRAW_E")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[80:].isnull().any(axis=1).idxmax()
    df = df.iloc[80:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_E done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_F(robot,offset):

    print("DRAW_F")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[100:].isnull().any(axis=1).idxmax()
    df = df.iloc[100:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_F done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_G(robot,offset):

    print("DRAW_G")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[120:].isnull().any(axis=1).idxmax()
    df = df.iloc[120:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_G done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_H(robot,offset):

    print("DRAW_H")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[140:].isnull().any(axis=1).idxmax()
    df = df.iloc[140:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_H done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_I(robot,offset):
    
    print("DRAW_I")

    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[160:].isnull().any(axis=1).idxmax()
    df = df.iloc[160:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_I done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_J(robot,offset):
    
    print("DRAW_J")

    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[180:].isnull().any(axis=1).idxmax()
    df = df.iloc[180:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_J done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_K(robot,offset):
    
    print("DRAW_K")

    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[200:].isnull().any(axis=1).idxmax()
    df = df.iloc[200:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_K done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_L(robot,offset):

    print("DRAW_L")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[220:].isnull().any(axis=1).idxmax()
    df = df.iloc[220:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_L done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_M(robot,offset):

    print("DRAW_M")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[240:].isnull().any(axis=1).idxmax()
    df = df.iloc[240:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_M done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_N(robot,offset):

    print("DRAW_N")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[260:].isnull().any(axis=1).idxmax()
    df = df.iloc[260:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_N done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_O(robot,offset):

    print("DRAW_O")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[280:].isnull().any(axis=1).idxmax()
    df = df.iloc[280:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_O done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_P(robot,offset):

    print("DRAW_P")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[300:].isnull().any(axis=1).idxmax()
    df = df.iloc[300:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_P done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_Q(robot,offset):

    print("DRAW_Q")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[320:].isnull().any(axis=1).idxmax()
    df = df.iloc[320:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_Q done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_R(robot,offset):

    print("DRAW_R")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[340:].isnull().any(axis=1).idxmax()
    df = df.iloc[340:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_R done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_S(robot,offset):

    print("DRAW_S")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[360:].isnull().any(axis=1).idxmax()
    df = df.iloc[360:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_S done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_T(robot,offset):
    
    print("DRAW_T")

    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[380:].isnull().any(axis=1).idxmax()
    df = df.iloc[380:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_T done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_U(robot,offset):

    print("DRAW_U")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[400:].isnull().any(axis=1).idxmax()
    df = df.iloc[400:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_U done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_V(robot,offset):

    print("DRAW_V")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[420:].isnull().any(axis=1).idxmax()
    df = df.iloc[420:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_V done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_W(robot,offset):

    print("DRAW_W")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[440:].isnull().any(axis=1).idxmax()
    df = df.iloc[440:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_W done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_X(robot,offset):

    print("DRAW_X")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[460:].isnull().any(axis=1).idxmax()
    df = df.iloc[460:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_X done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_Y(robot,offset):

    print("DRAW_Y")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[480:].isnull().any(axis=1).idxmax()
    df = df.iloc[480:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_Y done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return

def draw_Z(robot,offset):

    print("DRAW_Z")
    
    # Načtení dat z CSV souboru
    df = pd.read_csv('Body_Abeceda.csv', delimiter=';')

    # řádky jsou co 20 kde řádek 21 má index 20
    prazdny_radek_index = df.iloc[500:].isnull().any(axis=1).idxmax()
    df = df.iloc[500:prazdny_radek_index]

    print(df)
    NumberOfPoints = len(df)

    print("NumberOfPoints:")
    print(NumberOfPoints)
    
    robot.KUKA_WriteVar('PyNumIter', NumberOfPoints)
    
    robot.KUKA_WriteVar('PyPsani', True)


    for index, row in df.iterrows():
        print(index)

        x = float(row['x'].replace(',', '.'))
        y = float(row['y'].replace(',', '.'))
        z = float(row['z'].replace(',', '.'))
        a = float(row['a'].replace(',', '.'))
        b = float(row['b'].replace(',', '.'))
        c = float(row['c'].replace(',', '.'))

        x = offset + x

        print("Dalsi bod:")
        print(x)
        print(y)
        print(z)
        print(a)
        print(b)
        print(c)
        print(" ")

        robot.KUKA_WriteVar('PyX', x)
        robot.KUKA_WriteVar('PyY', y)
        robot.KUKA_WriteVar('PyZ', z)
        robot.KUKA_WriteVar('PyA', a)
        robot.KUKA_WriteVar('PyB', b)
        robot.KUKA_WriteVar('PyC', c)

        sleep(1)
        robot.KUKA_WriteVar('PyOK', False)
        robot.KUKA_WriteVar('PyDalsiBod', True)

        while not robot.KUKA_ReadVar('PyBodDopsan'):
            sleep(0.5)
        robot.KUKA_WriteVar('PyOK', True)

        sleep(0.5)

        print("BOD DOPSAN")
        print(" ")

    print("BODY DOPSANY?")
    while not robot.KUKA_ReadVar('PyDopsano'):
        sleep(0.5)
    print("BODY DOPSANY")     

    print("Function_Z done.")

    sleep(1)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    return
