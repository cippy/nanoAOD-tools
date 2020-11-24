import ROOT
import math
ROOT.PyConfig.IgnoreCommandLineOptions = True

from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection 
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

#global definition of CS angles
def getCSangles(muon, neutrino):
    	
    	m = ROOT.TLorentzVector()
    	n = ROOT.TLorentzVector()
    	w = ROOT.TLorentzVector()
    	
    	m.SetPtEtaPhiM(muon.pt, muon.eta, muon.phi, 0.105)
        n.SetPtEtaPhiM(neutrino.pt, neutrino.eta, neutrino.phi, 0.)
  		
        w = m + n

        sign  = abs(w.Z())/w.Z()
        
        ProtonMass = 0.938
        BeamEnergy = 6500.000
        
        p1 = ROOT.TLorentzVector()
        p2 = ROOT.TLorentzVector()
        
        p1.SetPxPyPzE(0, 0, sign*BeamEnergy, math.sqrt(BeamEnergy*BeamEnergy+ProtonMass*ProtonMass)) 
        p2.SetPxPyPzE(0, 0, -1*sign*BeamEnergy, math.sqrt(BeamEnergy*BeamEnergy+ProtonMass*ProtonMass))
        
        p1.Boost(-w.BoostVector())
        p2.Boost(-w.BoostVector())
        
        CSAxis = (p1.Vect().Unit()-p2.Vect().Unit()).Unit() #quantise along axis that bisects the boosted beams
        
        yAxis = (p1.Vect().Unit()).Cross((p2.Vect().Unit())) #other axes
        yAxis = yAxis.Unit()
        xAxis = yAxis.Cross(CSAxis)
        xAxis = xAxis.Unit()

        m.Boost(-w.BoostVector())

        phi = math.atan2((m.Vect()*yAxis),(m.Vect()*xAxis))
        if phi<0: phi = phi + 2*math.pi
        
        return math.cos(m.Angle(CSAxis)), phi


class CSVariables(Module):
    def __init__(self):
        pass
    def beginJob(self):
        pass
    def endJob(self):
        pass
    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree

        self.out.branch("CStheta_preFSR", "F")
        self.out.branch("CSphi_preFSR", "F")
        
        
    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass

    def analyze(self, event):
        """process event, return True (go to next module) or False (fail, go to next event)"""

        genParticles = Collection(event, "GenPart")

        # reobtain the indices of the good muons and the neutrino
        
        preFSRLepIdx1 = event.GenPart_preFSRLepIdx1
        preFSRLepIdx2 = event.GenPart_preFSRLepIdx2
        
        if preFSRLepIdx1 >= 0 and preFSRLepIdx2 >= 0:
            CStheta_preFSR, CSphi_preFSR = getCSangles(genParticles[preFSRLepIdx1], genParticles[preFSRLepIdx2])
        else: 
            CStheta_preFSR, CSphi_preFSR = -99., -99.

        self.out.fillBranch("CStheta_preFSR",CStheta_preFSR)
        self.out.fillBranch("CSphi_preFSR",CSphi_preFSR)

        return True


# define modules using the syntax 'name = lambda : constructor' to avoid having them loaded when not needed

CSAngleModule = lambda : CSVariables() 
