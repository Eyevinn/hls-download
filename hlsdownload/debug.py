from __future__ import print_function
import sys
# Copyright 2016 Eyevinn Technology. All rights reserved
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.
# Author: Jonas Birme (Eyevinn Technology)


global doDebug
doDebug = False

def log(*args, **kwargs):
    if doDebug:
        print(*args, file=sys.stderr, **kwargs)

