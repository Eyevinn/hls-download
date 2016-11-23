# Copyright 2016 Eyevinn Technology. All rights reserved
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.
# Author: Jonas Birme (Eyevinn Technology)
import argparse
from hlsdownload import debug
from hlsdownload import HLSDownloader

def main():
    parser = argparse.ArgumentParser(description='Download HLS and convert to MP4 files')
    parser.add_argument('hlsuri', metavar='HLSURI', default=None, help='URI to HLS master manifest')
    parser.add_argument('output', metavar='OUTPUT', default='out', help='Output name')
    parser.add_argument('--debug', dest='debug', action='store_true', default=False, help='Write debug info to stderr')
    parser.add_argument('--nocleanup', dest='nocleanup', action='store_true', default=False, help='Do not remove temp files')
    args = parser.parse_args()
    debug.doDebug = args.debug

    debug.log('Downloading HLS: %s' % args.hlsuri)
    downloader = HLSDownloader(args.hlsuri, '.', not args.nocleanup)    
    downloader.writeDiscontinuityFile(args.output)
    downloader.toMP4(args.output)

if __name__ == '__main__':
    try:
        main()
    except Exception, err:
        raise


