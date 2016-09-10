'''The TXS Catalog.
Data files are in tab-separated format from Vizier.
To download in the correct format, open a catalog online in Vizier,
select'Tab-Separated-Values' as the Output layout in the drop-down box, set
the maximum entries to 'unlimited', and click 'Sexagesimal' under the box
for 'Target Name or Position'.  Submit the query, and copy the output to a
txt file.  Copy this file to "txs.txt" in the _src directory of your AIPY
installation.'''
import aipy as a, numpy as np, os

class TXSCatalog(a.fit.SrcCatalog):
    def fromfile(self,filename):
        f = open(filename)
        addsrcs = []
        for L in [L for L in f.readlines() if not L.startswith('#')]:
            text = L.split('\t')
            if len(text) <= 4: continue
            try: int(text[0][0])
            except(ValueError): continue
            ra = text[0].replace(' ',':')
            dec = text[1].replace(' ',':')
            name = text[2].strip()
            jys = float(text[7])
            try: index = float(text[10])
            except(ValueError): index = 0
            addsrcs.append(a.fit.RadioFixedBody(ra, dec, name=name,
                jys=jys, index=index, mfreq=0.365))
        self.add_srcs(addsrcs)

TXSFILE = os.path.dirname(__file__) + os.sep + 'txs.txt'
_txscat = None

def get_srcs(srcs=None, cutoff=None):
    global _txscat
    if _txscat is None:
        _txscat = TXSCatalog()
        _txscat.fromfile(TXSFILE)
    if srcs is None:
        if cutoff is None: srcs = _txscat.keys()
        else:
            cut, fq = cutoff
            fq = np.array([fq])
            for s in _txscat.keys(): _txscat[s].update_jys(fq)
            srcs = [s for s in _txscat.keys() if _txscat[s].jys[0] > cut]
    srclist = []
    for s in srcs:
        try: srclist.append(_txscat[s])
        except(KeyError): pass
    return srclist
