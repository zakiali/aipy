#! /usr/bin/env python
"""
A script for removing stable crosstalk from UV files.

Author: Aaron Parsons
Date: 6/03/07
Revisions: None
"""

import aipy.miriad, numpy, os, sys, aipy.ant, aipy.src
from optparse import OptionParser

p = OptionParser()
p.set_usage('rm_src.py [options] *.uv')
p.set_description(__doc__)
p.add_option('-f', '--fng_w', dest='fng_w', 
    type=int, default=1,
    help='The number of fringe bins to null.')
p.add_option('-d', '--dly_w', dest='dly_w',
    type=float, default=5,
    help='The number of delay bins to null.')
p.add_option('-s', '--src', dest='src',
    help='The source to remove.')
p.add_option('-l', '--loc', dest='loc', default='pwa303',
    help='Use location-specific info for this location (default pwa303).')
opts, args = p.parse_args(sys.argv[1:])

exec('from aipy.%s import get_aa' % opts.loc)
aa = get_aa()

src = aipy.src.get_src(opts.src, type='ant')

# Group files into 1/10 of a julian day for processing in batches.
groups = {}
for uvfile in args:
    uv = aipy.miriad.UV(uvfile)
    p, d = uv.read_data()
    t = p[-2]
    t = int(t*10) / 2
    if not groups.has_key(t): groups[t] = [uvfile]
    else: groups[t].append(uvfile)
    del(uv)

for g in groups:
    phs_dat = {}
    cnt = {}
    files = groups[g]
    files.sort()
    print 'Processing group', files
    flag = 0
    for uvfile in files:
        uvofile = uvfile+'.'+opts.src
        if os.path.exists(uvofile):
            print uvofile, 'exists, skipping group.'
            flag = 1
            break
    if flag: continue
    for uvfile in files:
        print 'Reading', uvfile
        uvi = aipy.miriad.UV(uvfile)
        uvi.select_data('auto', 0, 0, include_it=0)
        # Gather all data
        while True:
            p, d = uvi.read_data()
            if d.size == 0: break
            bl = p[-1]
            aa.set_jultime(p[-2])
            src.compute(aa)
            try:
                d = aa.phs2src(d, src, bl)
                cnt[bl] = cnt.get(bl, 0) + d.mask.sum()
                d = numpy.fft.ifft(d.filled(0))
            except(aipy.ant.PointingError): d = numpy.zeros_like(d.data)
            try: phs_dat[bl].append(d)
            except(KeyError): phs_dat[bl] = [d]
        del(uvi)

    # Perform fringe rate transform
    for bl in phs_dat:
        d = numpy.array(phs_dat[bl])
        d /= float(d.size - cnt.get(bl,0)) / d.size
        d = numpy.fft.fft(d, axis=0)
        x1, x2 = opts.fng_w, -opts.fng_w+1
        if x2 == 0: x2 = d.shape[0]
        y1, y2 = opts.dly_w, -opts.dly_w
        if y2 == 0: y2 = d.shape[1]
        d[x1:x2,:] = 0
        d[:,y1:y2] = 0
        d = numpy.fft.ifft(d, axis=0)
        d = numpy.fft.fft(d, axis=1)
        phs_dat[bl] = d

    cnt = {}
    for bl in phs_dat: cnt[bl] = 0

    # Generate a pipe for removing average phase bias from data
    def rm_mfunc(uv, p, d):
        bl = p[-1]
        i, j = aipy.miriad.bl2ij(bl)
        if i == j: return p, d
        aa.set_jultime(p[-2])
        src.compute(aa)
        data = phs_dat[bl][cnt[bl],:]
        try: data = aa.unphs2src(data, src, bl)
        except(aipy.ant.PointingError): data = 0
        cnt[bl] += 1
        return p, d - data

    for uvfile in files:
        # Apply the pipe to the data
        print 'Working on', uvfile
        uvofile = uvfile+'.'+opts.src
        uvi = aipy.miriad.UV(uvfile)
        uvo = aipy.miriad.UV(uvofile, status='new')
        aipy.miriad.pipe_uv(uvi, uvo, mfunc=rm_mfunc)
        del(uvo)
        del(uvi)