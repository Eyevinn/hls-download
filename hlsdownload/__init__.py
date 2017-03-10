# Copyright 2016 Eyevinn Technology. All rights reserved
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.
# Author: Jonas Birme (Eyevinn Technology)

import m3u8
import shutil
import shlex
import ntpath
import os
import pycurl
import subprocess
from Queue import Queue
from threading import Thread

class HLSDownloader:
    def __init__(self, manifesturi, tmpdir, cleanup=True):
        self.manifesturi = manifesturi
        self.tmpdir = tmpdir
        self.bitrates = []
        self.cleanup = cleanup
        self._collectSegments()

    def _collectSegments(self):
        m3u8_obj = m3u8.load(self.manifesturi)
        if not m3u8_obj.is_variant:
            raise Exception('%s is not a master manifest' % self.manifesturi) 
        for mediaplaylist in m3u8_obj.playlists:
            debug.log('Building segment list from %s' % mediaplaylist.uri)
            segmentlist = SegmentList(mediaplaylist.uri, mediaplaylist.stream_info.average_bandwidth, self.tmpdir)
            self.bitrates.append(segmentlist)

    def _downloadSegments(self, bitrate=None):
        for segmentlist in self.bitrates:
            if bitrate:
                if segmentlist.getBitrate() == bitrate:
                    segmentlist.download()
            else:
                segmentlist.download()

    def _convertSegments(self, bitrate=None):
        for segmentlist in self.bitrates:
            if bitrate:
                if segmentlist.getBitrate() == bitrate:
                    segmentlist.convert()
            else:
                segmentlist.convert()

    def _concatSegments(self, output, bitrate=None):
        for segmentlist in self.bitrates:
            if bitrate:
                if segmentlist.getBitrate() == bitrate:
                    segmentlist.concat(output)
            else:
                segmentlist.concat(output)

    def _cleanup(self):
        for segmentlist in self.bitrates:
            segmentlist.cleanup()

    def writeDiscontinuityFile(self, output):
        # We can assume that all bitrates are aligned so we only
        # need to look at one of the bitrates
        segmentlist = self.bitrates[0]
        with open(output + '.txt', 'w') as f:
            for d in segmentlist.getDiscontinuities():
                f.write(str(d) + '\n')
        f.close()

    def toMP4(self, output, bitrate=None):
        self._downloadSegments(bitrate)
        self._convertSegments(bitrate)
        self._concatSegments(output, bitrate)
        if self.cleanup:
            self._cleanup()

class SegmentList:
    def __init__(self, mediaplaylisturi, bitrate, downloaddir):
        self.mediaplaylisturi = mediaplaylisturi
        self.bitrate = bitrate
        if not downloaddir == '.':
            self.downloaddir = downloaddir + '/' + str(self.bitrate) + '/'
        else:
            self.downloaddir = str(self.bitrate) + '/'
        self.downloadedsegs = []
        self.mp4segs = []
        self.m3u8_obj = m3u8.load(self.mediaplaylisturi)
        self.q = Queue()
        self.num_worker_threads = 10

    def getBitrate(self):
        return self.bitrate

    def worker(self):
        while True:
            item = self.q.get()
            debug.log('Downloading %s to %s%s' % (item['remoteurl'], item['downloaddir'], item['localfname']))
            fp = open(item['downloaddir'] + item['localfname'], 'wb')
            c = pycurl.Curl()
            c.setopt(c.URL, item['remoteurl'])
            c.setopt(c.WRITEDATA, fp)
            c.perform()
            c.close()
            fp.close()
            self.downloadedsegs.append(item['localfname'])
            self.q.task_done()

    def download(self):
        if not os.path.exists(self.downloaddir):
            os.mkdir(self.downloaddir)
        print "Downloading segments from %s" % self.mediaplaylisturi
        for i in range(self.num_worker_threads):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()
        for seg in self.m3u8_obj.segments:
            head, tail = ntpath.split(self.downloaddir + seg.uri)
            localfname = tail
            if not os.path.isfile(self.downloaddir + localfname):
                item = { 
                    'remoteurl': self.m3u8_obj.base_uri + seg.uri,
                    'localfname': localfname,
                    'downloaddir': self.downloaddir
                }
                self.q.put(item)        
        self.q.join()

    def convert(self):
        for segfname in self.downloadedsegs:
            mp4fname = segfname + '.mp4'
            if not os.path.isfile(self.downloaddir + mp4fname):
                debug.log('Converting %s%s to %s%s' % (self.downloaddir, segfname, self.downloaddir, mp4fname)) 
                FFMpegCommand(self.downloaddir + segfname, self.downloaddir + mp4fname, '-acodec copy -bsf:a aac_adtstoasc -vcodec copy')
            self.mp4segs.append(mp4fname)

    def concat(self, outputname):
        output = outputname + '-' + str(self.bitrate) + '.mp4'
        print "Converting segments and writing to %s" % output
        if not os.path.isfile(output):
            lstfile = open(self.downloaddir + output + '.lst', 'w')
            for mp4fname in self.mp4segs:
                lstfile.write("file '%s'\n" % mp4fname)      
            lstfile.close()
            FFMpegConcat(self.downloaddir + output + '.lst', output)

    def getDiscontinuities(self):
        discont = []
        position = 0.0
        for seg in self.m3u8_obj.segments: 
            if seg.discontinuity:
                discont.append(position)
            position += float(seg.duration)
        return discont

    def cleanup(self):
        if os.path.exists(self.downloaddir):
            shutil.rmtree(self.downloaddir)

def runcmd(cmd, name):
    debug.log('COMMAND: %s' % cmd)
    try:
        FNULL = open(os.devnull, 'w')
        if debug.doDebug:
            return subprocess.call(cmd)
        else:
            return subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        message = "binary tool failed with error %d" % e.returncode
        raise Exception(message)
    except OSError as e:
        raise Exception('Command %s not found, ensure that it is in your path' % name)

def FFMpegCommand(infile, outfile, opts):
    cmd = [os.path.basename('ffmpeg')]
    cmd.append('-i')
    cmd.append(infile)
    args = shlex.split(opts)
    cmd += args
    cmd.append(outfile)
    runcmd(cmd, 'ffmpeg')

def FFMpegConcat(lstfile, outfile):
    cmd = [os.path.basename('ffmpeg')]
    cmd.append('-f')
    cmd.append('concat')
    cmd.append('-safe')
    cmd.append('0')
    cmd.append('-i')
    cmd.append(lstfile) 
    cmd.append('-c')
    cmd.append('copy')
    cmd.append(outfile)
    runcmd(cmd, 'ffmpeg')
