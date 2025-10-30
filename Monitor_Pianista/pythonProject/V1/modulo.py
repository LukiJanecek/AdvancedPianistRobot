import time
def modulo(N,M):
    if (N == 0) or (M == 0):
        return 0
    else:
        temp = N % M
        return temp



def myModulo(N,M):
    if (N == 0) or (M == 0):
        return 0
    else:
        podil = N/M
        podilint=int(podil)
        precision=podil - podilint
        return precision*M



myresult = myModulo(N=3250, M=2500)
x = 1
while True:

    myresult = myModulo(N=x, M=2000)

    if x < 8000:
        x = x+1
    else:
        break
    if myresult == 0:
        print('ubehlo 2s ')
    time.sleep(0.001)
