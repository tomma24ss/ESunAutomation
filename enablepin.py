import RPi.GPIO as GPIO       
GPIO.setmode(GPIO.BOARD)
GPIO.setup(29, GPIO.OUT)
#GPIO.output(29, GPIO.LOW)
input = GPIO.input(29)
print(input)
