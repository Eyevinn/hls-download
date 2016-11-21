# Description
This package contains a script that with the help of ffmpeg download segments in an 
HLS stream and convert and concatenate the video segments to MP4 files. HLS with
discontinuities are supported.

# Usage

```
hls-downloader "http://example.com/event/master.m3u8?t=2016-11-21T10:35:00Z-2016-11-21T10:45:00Z"
```
