# Description
This package contains a script that with the help of ffmpeg download segments in an 
HLS stream and convert and concatenate the video segments to MP4 files. HLS with
discontinuities are supported.

# Installation

    pip install hlsdownload

# Usage

    hls-downloader "http://example.com/event/master.m3u8?t=2016-11-21T10:35:00Z-2016-11-21T10:45:00Z" outfile

# Contribution
We welcome contributions to this project. Just follow the normal procedures by forking 
this repository, create a topic branch for your fix and then submit a pull request.

# License
See LICENSE for details
