from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class lheWeightsFlattener(Module):
    def __init__(self):
        self.NumNNPDFWeights = 103
        self.NumScaleWeights = 18 # 18 for MiNNLO since it has NNPDF3.0 weights too, 9 for other samples
        self.maxMassShift = 100
        self.massGrid = 10
        self.cenMassWgt = 11

    def beginJob(self):
        pass
    def endJob(self):
        pass
    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        self.initReaders(inputTree)
        for varPair in [("05","05"), ("05","1"), ("05", "2"), ("1", "05"), \
                ("1","1"), ("1","2"), ("2", "05"), ("2", "1"), ("2", "2")]:
            self.out.branch("scaleWeightMuR%sMuF%s" % varPair, "F")

        for i in range(self.NumNNPDFWeights):
            self.out.branch("pdfWeightNNPDF%i" % i, "F")
        # if saving PDFs/alpha as array
        #self.out.branch("npdfWeightNNPDF", "i")
        #self.out.branch("pdfWeightNNPDF", "F", lenVar="npdfWeightNNPDF")

        for i in range(self.massGrid, self.maxMassShift+self.massGrid, self.massGrid):
            self.out.branch("massShift%iMeVUp" % i, "F")
            self.out.branch("massShift%iMeVDown" % i, "F")
        
    def initReaders(self, tree):
        self.LHEScaleWeight = tree.arrayReader("LHEScaleWeight")
        self.LHEPdfWeight = tree.arrayReader("LHEPdfWeight")
        self.MEParamWeight = tree.arrayReader("LHEReweightingWeight")
        self._ttreereaderversion = tree._ttreereaderversion
        pass

    def bwWeight(self,genMass,offset, isW):
        # default mass from the powheg config
        (m0, gamma) = (80351.812293789408, 2090.4310808144846) if isW else (91153.509740726733, 2493.2018986110700)
        newmass = m0 + offset
        s_hat = pow(genMass,2)
        weight = (pow(s_hat - m0*m0,2) + pow(gamma*m0,2)) / (pow(s_hat - newmass*newmass,2) + pow(gamma*newmass,2))
        return weight

    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass
    def analyze(self, event):
        """process event, return True (go to next module) or False (fail, go to next event)"""

        if event._tree._ttreereaderversion > self._ttreereaderversion:
            self.initReaders(event._tree)

        if len(self.LHEScaleWeight) < self.NumScaleWeights:
            raise RuntimeError("Found poorly formed LHE Scale weights")

        for i,varPair in enumerate([("05","05"), ("05","1"), ("05", "2"), ("1", "05"), \
                ("1","1"), ("1","2"), ("2", "05"), ("2", "1"), ("2", "2")]):
            self.out.fillBranch("scaleWeightMuR%sMuF%s" % varPair, self.LHEScaleWeight[i*2])

        for i in range(1, self.maxMassShift/self.massGrid+1):
            val = i*self.massGrid
            # not working (yet) self.out.fillBranch("massShift%iMeVUp" % val, self.MEParamWeight[self.cenMassWgt+i])
            # not working (yet) self.out.fillBranch("massShift%iMeVDown" % val, self.MEParamWeight[self.cenMassWgt-i])
            self.out.fillBranch("massShift%iMeVUp"   % val, self.bwWeight(event.massV*1000.,     val, event.isW))
            self.out.fillBranch("massShift%iMeVDown" % val, self.bwWeight(event.massV*1000., -1.*val, event.isW))

        if len(self.LHEPdfWeight) < self.NumNNPDFWeights:
            raise RuntimeError("Found poorly formed LHE Scale weights")

        pdfWeights = []
        for i in range(self.NumNNPDFWeights):
            self.out.fillBranch("pdfWeightNNPDF%i" % i, self.LHEPdfWeight[i])
        # if saving PDFs/alpha as array
            # pdfWeights.append(self.LHEPdfWeight[i])
        #self.out.fillBranch("npdfWeightNNPDF", self.NumNNPDFWeights)
        self.out.fillBranch("pdfWeightNNPDF" , pdfWeights)

        return True

flattenLheWeightsModule = lambda : lheWeightsFlattener() 
