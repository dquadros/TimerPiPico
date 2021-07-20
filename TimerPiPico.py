"""
    TimerPiPico - Timer construido com um Raspberry Pi Pico
    (C) 2021, Daniel Quadros
"""

from machine import Pin
from time import sleep
from time import sleep_ms
from utime import ticks_ms, ticks_diff
import array
import rp2

# Conexões
PIN_SW1 = 16
PIN_SW2 = 17
PIN_BUZZER = 19
PIN_SENSORMOV = 20
PIN_LED = 21

# Número de LEDs nos aneis
NLEDS_EXT = 12
NLEDS_INT = 7

# Mapeia os LEDs em ordem
posLED = {
    0:1, 1:2, 2:3, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9, 9:10, 10:11, 11:0, # Anel externo
    12:14, 13:15, 14:16, 15:17, 16:18, 17:13, 18:12 # Anel interno
    }

# Programa para o PIO controlar os aneis de LED
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT,
             autopull=True, pull_thresh=24) # PIO configuration
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

# Classe para controlar os LEDs
class AnelLED(object):
    
    sm = None
    pixel_array = None # pixel_array guarda o estado de cada LED
    nLeds = 0          # número de LEDs
    mudou = False      # indica se chamou set depois de atualiza
    
    # iniciacao
    def __init__(self, pino, nLeds):
        # inicia o array dos LEDs
        self.nLeds = nLeds
        self.pixel_array = array.array("I", [0 for _ in range(nLeds)])
        # inicia a máquina de estado que controla os LEDs
        self.sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(pino))
        self.sm.active(1)
        
    # atualiza os LEDs
    def atualiza(self,intensidade = 0.2):
        dimmer_array = array.array("I", [0 for _ in range(self.nLeds)])
        for ii,cc in enumerate(self.pixel_array):
            # acerta as cores conforme a intensidade
            r = int(((cc >> 8) & 0xFF) * intensidade)
            g = int(((cc >> 16) & 0xFF) * intensidade)
            b = int((cc & 0xFF) * intensidade)
            dimmer_array[ii] = (g<<16) + (r<<8) + b
        self.sm.put(dimmer_array, 8)
        self.mudou = False
    
    # muda a cor de um LED
    def set_rgb(self,iLed, cor):
        self.pixel_array[iLed] = (cor[1]<<16) + (cor[0]<<8) + cor[2] # set 24-bit color
        self.mudou = True
    
    # apaga todos os LEDs
    def limpa(self):
        for i in range(0, self.nLeds):
            self.pixel_array[i] = 0
        self.atualiza()
        
# Controle do Buzzer
class Buzzer(object):
    def __init__(self, pino):
        self.buzzer = Pin(pino, Pin.OUT)
        self.buzzer.on()
    def liga(self):
        self.buzzer.off()
    def desliga(self):
        self.buzzer.on()
    def bip(self, nbeeps=1, duracao=0.1, intervalo=0.4):
        for i in range(0, nbeeps):
            self.liga()
            sleep(duracao)
            self.desliga()
            sleep(intervalo)

# Tratamento de botão
class Botao(object):
    atual = 1
    lido = 1
    qdo = 0
    
    def __init__(self, pino):
        self.btn = Pin(pino, Pin.IN, Pin.PULL_UP)
    
    def apertado(self):
        novo = self.btn.value()
        if novo != self.lido:
            self.lido = novo
            self.qdo = ticks_ms()
        elif (novo != self.atual) and (ticks_diff(ticks_ms(), self.qdo) > 20):
            self.atual = novo
        return self.atual == 0

    def clique(self):
        if self.apertado():
            while self.apertado():
                pass
            return True
        return False

# inicia o buzzer
buzzer = Buzzer(PIN_BUZZER)
buzzer.bip(3)

# inicia botoes
btn1 = Botao(PIN_SW1)
btn2 = Botao(PIN_SW2)

# Inicia sensor movimento
sensor = Pin(PIN_SENSORMOV, Pin.IN)

# inicia o anel de LEDs
leds = AnelLED(PIN_LED, NLEDS_EXT+NLEDS_INT)
leds.limpa()

# Rotina de explosão
def explode():
    leds.limpa()
    while (True):
        if btn1.apertado() or btn2.apertado():
            while btn1.apertado() or btn2.apertado():
                pass
            break
        buzzer.liga()
        for i in range(0, NLEDS_EXT):
            leds.set_rgb(posLED[i], (255,255,255))
        leds.atualiza()
        sleep(0.1)
        for i in range(0, NLEDS_EXT):
            leds.set_rgb(posLED[i], (0,0,0))
        for i in range(NLEDS_EXT, NLEDS_EXT+NLEDS_INT-1):
            leds.set_rgb(posLED[i], (255,255,255))
        leds.atualiza()
        sleep(0.1)
        for i in range(NLEDS_EXT, NLEDS_EXT+NLEDS_INT-1):
            leds.set_rgb(posLED[i], (0,0,0))
        leds.set_rgb(posLED[NLEDS_EXT+NLEDS_INT-1], (255,255,255))
        leds.atualiza()
        sleep(0.1)
        buzzer.desliga()
        leds.set_rgb(posLED[NLEDS_EXT+NLEDS_INT-1], (0,0,0))
        leds.atualiza()
        sleep(0.5)

# mostra o tempo selecionado
def MostraTempo(tempo, cor=(0,255,0)):
    for i in range(tempo, NLEDS_EXT+NLEDS_INT-1):
        leds.set_rgb(posLED[i], (0,0,0))
    for i in range(0, tempo):
        leds.set_rgb(posLED[i], cor)
    leds.atualiza()
    
# Seleção do Tempo: BTN1 avança, BTN2 confirma
def SelTempo(tempo):
    MostraTempo(tempo, (0,0,255))
    while True:
        # Verifica se apertou o botão 2
        if btn2.clique():
            return tempo
        # Verifica se apertou o botão 1
        if btn1.clique():
            tempo = tempo+1
            if tempo > NLEDS_EXT:
                leds.limpa()
                tempo = 1
            leds.set_rgb(posLED[tempo-1], (0,0,255))
            leds.atualiza()

# Efetua a função de timer
def Roda(tempo):
    moveu = False
    cont1 = 0
    agora1 = ticks_ms()
    delay1 = 500
    agora2 = ticks_ms()
    delay2 = 60000
    MostraTempo(tempo)
    while True:
        # Botão 2 aborta
        if btn2.clique():
            return
        # Botão 1 pausa
        if btn1.clique():
            while not btn1.clique():
                pass
        # Teste se moveu
        if not moveu and (sensor.value() == 1):
            delay1 = 100
            delay2 = 20000
            leds.set_rgb(posLED[NLEDS_EXT+NLEDS_INT-1], (255,0,0))
            moveu = True
            print("MOVEU!")
        # Atualiza anel interno
        if ticks_diff(ticks_ms(), agora1) > delay1:
            agora1 = ticks_ms()
            leds.set_rgb(posLED[NLEDS_EXT+cont1], (0,0,0))
            if cont1 < NLEDS_INT-2:
                cont1 = cont1+1
            else:
                cont1 = 0
            leds.set_rgb(posLED[NLEDS_EXT+cont1], (255,0,0))
        # Atualiza anel externo
        if ticks_diff(ticks_ms(), agora2) > delay2:
            agora2 = ticks_ms()
            if tempo > 0:
                tempo = tempo-1
                leds.set_rgb(posLED[tempo], (0,0,0))
            if tempo == 0:
                explode()
                return
        # Atualiza os LEDs
        if leds.mudou:
            leds.atualiza()

# Inicia o tempo com o valor padrão
tempo = 5
MostraTempo(tempo)

# Eterno enquanto dure!
while True:
    if btn2.clique():
        tempo = SelTempo(tempo)
    if btn1.clique():
        Roda(tempo)
        MostraTempo(tempo)
