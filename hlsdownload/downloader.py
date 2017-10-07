# Copyright 2016 Eyevinn Technology. All rights reserved
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.
# Author: Jonas Birme (Eyevinn Technology)
import argparse
import logging
from hlsdownload import debug
from hlsdownload import HLSDownloader

def main():
    parser = argparse.ArgumentParser(description='Download HLS and convert to MP4 files')
    parser.add_argument('hlsuri', metavar='HLSURI', default=None, help='URI to HLS master manifest')
    parser.add_argument('output', metavar='OUTPUT', default='out', help='Output name')
    parser.add_argument('--debug', dest='debug', action='store_true', default=False, help='Write debug info to stderr')
    parser.add_argument('--nocleanup', dest='nocleanup', action='store_true', default=False, help='Do not remove temp files')
    parser.add_argument('--nodownload', dest='nodownload', action='store_true', default=False, help='Do not download any segments')
    parser.add_argument('--singlebitrate', dest='bitrate', default=None, help='Download only one bitrate')
    args = parser.parse_args()
    debug.doDebug = args.debug

    logger = logging.getLogger('hlsdownload')
    hdlr = logging.FileHandler('hls-downloader.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

    debug.log('Downloading HLS: %s' % args.hlsuri)
    logger.info("------------------------ NEW SESSION -------------------------")
    try:
        downloader = HLSDownloader(args.hlsuri, '.', not args.nocleanup)    
        downloader.writeDiscontinuityFile(args.output)
        downloader.toMP4(args.output, args.bitrate, not args.nodownload)
    except Exception as e:
        logger.error('Unrecoverable error: ' + str(e))

if __name__ == '__main__':
    try:
        main()
    except Exception, err:
        raise

