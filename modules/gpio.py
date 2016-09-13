

#!/usr/bin/env python3

import shlex
import subprocess

cmd = 'gpioctl -f /dev/gpioc0 17'
args = shlex.split(cmd)
process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

pin17 = int(stdout.decode('utf-8'))

if pin17 == 1:
    print('ALARM')
else:
    print('OK')
