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
import re
from Queue import Queue
from threading import Thread
from urlparse import urlparse

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
        listlengths = []
        for mediaplaylist in m3u8_obj.playlists:
            url = urlparse(self.manifesturi)
            mediauri = mediaplaylist.uri
            if mediaplaylist.uri[0] == "/":
                mediauri = url.scheme + "://" + url.hostname + mediaplaylist.uri
            debug.log('Building segment list from %s' % mediauri)
            segmentlist = SegmentList(mediauri, mediaplaylist.stream_info.average_bandwidth, self.tmpdir)
            self.bitrates.append(segmentlist)
            listlengths.append(segmentlist.getLength())

        # This is to handle the edge case where the segmentlists differs in length and start segment
        # A special case that actually should not happened
        debug.log('Shortest list length %d' % min(listlengths))
        debug.log('Longest list length %d' % max(listlengths))
        if min(listlengths) != max(listlengths):
            debug.log('Segment list lengths differs')
            for segmentlist in self.bitrates:
                while segmentlist.getLength() > min(listlengths):
                    segmentlist.removeFirstSegment()
        for segmentlist in self.bitrates:
            debug.log('First segment: %s of (%d)' % (segmentlist.getFirstSegment(), segmentlist.getLength()))

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

    def toMP4(self, output, bitrate=None, download=True):
        if download:
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
        self.cq = Queue()
        self.num_worker_threads = 10

    def getFirstSegment(self):
        p = re.compile('.*/(.*?)\.ts$')
        m = p.match(self.m3u8_obj.segments[0].uri)
        if m:
            return m.group(1)
        return None
    
    def getLength(self):
        return len(self.m3u8_obj.segments)

    def getBitrate(self):
        return self.bitrate

    def removeFirstSegment(self):
        self.m3u8_obj.segments.pop(0)

    def downloadWorker(self):
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
            t = Thread(target=self.downloadWorker)
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
            mp4fname = localfname + '.mp4'
            self.mp4segs.append(mp4fname)
        self.q.join()

    def convertWorker(self):
        while True:
            item = self.cq.get()
            debug.log('Converting %s%s to %s%s' % (item['downloaddir'], item['localfname'], item['downloaddir'], item['mp4fname']))
            if not os.path.isfile(item['downloaddir'] + item['mp4fname']):
                FFMpegCommand(item['downloaddir'] + item['localfname'], item['downloaddir'] + item['mp4fname'], '-acodec copy -bsf:a aac_adtstoasc -vcodec copy')
            self.cq.task_done()

    def convert(self):
        for i in range(self.num_worker_threads):
            t = Thread(target=self.convertWorker)
            t.daemon = True
            t.start()

        for segfname in self.downloadedsegs:
            mp4fname = segfname + '.mp4'
            item = {
                'downloaddir': self.downloaddir,
                'localfname': segfname,
                'mp4fname': mp4fname
            }
            self.cq.put(item)
        self.cq.join()

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
