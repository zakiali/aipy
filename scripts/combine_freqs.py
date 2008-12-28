#! /usr/bin/env python
import aipy.miriad, sys, os, numpy
from optparse import OptionParser

p = OptionParser()
p.set_usage('combine_freqs.py [options] *.uv')
p.set_description(__doc__)
p.add_option('-n', '--nchan', dest='nchan', default=256, type='int',
    help='Reduce the number of channels in a spectrum to this number.')
p.add_option('-c', '--careful_flag', dest='careful_flag', action='store_true',
    help='Flag resultant bin if any component bins are flagged (otherwise, flags only when there are more flagged bins than unflagged bins).')
p.add_option('-u', '--unify', dest='unify', action='store_true',
    help='Output to a single UV file.')
opts, args = p.parse_args(sys.argv[1:])

uvo = None
for uvfile in args:
    print uvfile
    uvi = aipy.miriad.UV(uvfile)
    sfreq = uvi['sfreq']
    sdf = uvi['sdf']
    nchan = uvi['nchan']
    newsfreq = sfreq + ((nchan/opts.nchan) * sdf) / 2
    newsdf = sdf * (nchan/opts.nchan)
    
    if uvo is None:
        uvofile = uvfile+'m'
        if os.path.exists(uvofile):
            print uvofile, 'exists, skipping.'
            continue
        uvo = aipy.miriad.UV(uvofile, status='new')
        aipy.miriad.init_from_uv(uvi, uvo, append2hist='Miniaturized...\n',
            override={'nchan':opts.nchan, 'sfreq':newsfreq, 'sdf':newsdf,
                'nschan':opts.nchan, 'freq':newsfreq, 'nchan0':opts.nchan, })

    def f(uv, p, d):
        d.shape = (opts.nchan, nchan/opts.nchan)
        m = d.mask.sum(axis=1)
        if opts.careful_flag: m = numpy.where(m > 0, 1, 0)
        else: m = numpy.where(m >= nchan/opts.nchan/2, 1, 0)
        d = numpy.ma.average(d, axis=1)
        d = numpy.ma.array(d.data, mask=m)
        return p, d
    # Pipe data, but don't track variables that we overrode, so they don't
    # get clobbered
    aipy.miriad.pipe_uv(uvi, uvo, mfunc=f, init=False, 
        notrack=['nchan', 'sfreq', 'sdf', 'nschan', 'freq', 'nchan0'])
    del(uvi)
    if not opts.unify:
        del(uvo)
        uvo = None
    