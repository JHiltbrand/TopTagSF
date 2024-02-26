import os
import glob
import argparse

import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.TH1.SetDefaultSumw2()

ttprocs  = ["TTmatch", "TTunmatch", "Other"]
#"QCD", "Boson", "TTX", "ST"]
qcdprocs = ["QCD", "TT", "Other"]
#"Boson", "TTX", "ST"]

ttsysts = ["", "_JECUp", "_JECDown", "_JERUp", "_JERDown", "_pdfUp", "_pdfDown", "_puUp", "_puDown", "_scaleUp", "_scaleDown", "_btagUp", "_btagDown", "_lepUp", "_lepDown"]
qcdsysts = ["", "_JECUp", "_JECDown", "_JERUp", "_JERDown", "_pdfUp", "_pdfDown", "_puUp", "_puDown", "_scaleUp", "_scaleDown"]

colors = [ROOT.kBlack, ROOT.kCyan+1, ROOT.kCyan+2, ROOT.kBlue-7, ROOT.kBlue-5, ROOT.kPink-9, ROOT.kPink-8, ROOT.kOrange+4, ROOT.kOrange+5, ROOT.kOrange, ROOT.kOrange-6, ROOT.kMagenta+3, ROOT.kRed, ROOT.kGreen-6, ROOT.kGreen+2]

names = ["nominal", "JEC Up", "JEC Down", "JER Up", "JER Down", "PDF Up", "PDF Down", "PU Up", "PU Down", "Scl. Up", "Scl. Down", "b tag Up", "b tag Down", "Lep. Up", "Lep. Down"]

class SystPlotter:

    def __init__(self, inputDir, outputDir):

        self.TopMargin    = 0.06
        self.BottomMargin = 0.12
        self.RightMargin  = 0.04
        self.LeftMargin   = 0.16

        self.outputDir = outputDir

        self.fitDirs = glob.glob(inputDir + "/*") 
    
        if not os.path.isdir(outputDir):
            os.makedirs(outputDir)
    
    def run(self):
        for fitDir in self.fitDirs:
    
            if os.path.isfile(fitDir):
                continue
    
            fpass = ROOT.TFile.Open(fitDir + "/top_mass_pass.root", "READONLY")
            ffail = ROOT.TFile.Open(fitDir + "/top_mass_fail.root", "READONLY")
    
            newName = fitDir.rpartition("/")[-1].replace("_inputs", "")
    
            procs = None
            systs = None
            if "Eff" in fitDir:
                procs = ttprocs
                systs = ttsysts
            else:
                procs = qcdprocs
                systs = qcdsysts
    
            for proc in procs:
                self.makeSystPlot(newName, proc, fpass, systs, "_pass")
                self.makeSystPlot(newName, proc, ffail, systs, "_fail")
           
    def makeCanvas(self, name, noRatio=False):
    
        canvas = ROOT.TCanvas(name, name, 900, 900)
    
        # Split the canvas 70 / 30 by default if doing ratio
        # scale parameter keeps text sizes in ratio panel the
        # same as in the upper panel
        self.split      = 0.5
        self.upperSplit = 1.0
        self.lowerSplit = 1.0
        self.scale      = 1.0
    
        if not noRatio:
            self.upperSplit = 1.0-self.split
            self.lowerSplit = self.split
            self.scale = self.upperSplit / self.lowerSplit
    
            canvas.Divide(1,2)
    
            canvas.cd(1)
            ROOT.gPad.SetPad(0.0, self.split, 1.0, 1.0)
            ROOT.gPad.SetTopMargin(self.TopMargin / self.upperSplit)
            ROOT.gPad.SetBottomMargin(0)
            ROOT.gPad.SetLeftMargin(self.LeftMargin)
            ROOT.gPad.SetRightMargin(self.RightMargin)
    
            canvas.cd(2)
            ROOT.gPad.SetPad(0.0, 0.0, 1.0, self.split)
            ROOT.gPad.SetTopMargin(0)
            ROOT.gPad.SetBottomMargin(self.BottomMargin / self.lowerSplit)
            ROOT.gPad.SetLeftMargin(self.LeftMargin)
            ROOT.gPad.SetRightMargin(self.RightMargin)
    
        else:
            ROOT.gPad.SetTopMargin(self.TopMargin)
            ROOT.gPad.SetBottomMargin(self.BottomMargin)
            ROOT.gPad.SetLeftMargin(self.LeftMargin)
            ROOT.gPad.SetRightMargin(self.RightMargin)
    
        return canvas

    def prepHisto(self, histogram, scale=1.0):

        histogram.GetXaxis().SetTitleSize(0.04 * scale / self.upperSplit); histogram.GetYaxis().SetTitleSize(0.04 * scale / self.upperSplit)
        histogram.GetXaxis().SetLabelSize(0.04 * scale / self.upperSplit); histogram.GetYaxis().SetLabelSize(0.04 * scale / self.upperSplit)
        histogram.GetXaxis().SetTitleOffset(1.2);                          histogram.GetYaxis().SetTitleOffset(1.0 * scale)
        histogram.GetXaxis().SetTitle("Top Candidate Mass [GeV]");         histogram.GetYaxis().SetTitle("# Weighted Events")    

    def makeSystPlot(self, nameStub, proc, file, systs, tag, normalize=False):
    
        dumpster = []
        nominal = None
        for isyst in range(1, len(systs), 2):

            syst = systs[isyst]
            syst2 = systs[isyst+1]

            theName = proc + syst
    
            canvas = self.makeCanvas(theName.replace("Down","").replace("Up","").replace("down","").replace("up",""))
    
            canvas.cd(1)

            if isyst == 1:
                nominal = file.Get(proc)
                self.prepHisto(nominal)
                if normalize and nominal.Integral() > 0.0:
                    nominal.Scale(1.0/nominal.Integral())
                    nominal.GetYaxis().SetRangeUser(0, 0.25)
                else:
                    nominal.GetYaxis().SetRangeUser(-0.05*nominal.GetMaximum(), nominal.GetMaximum()*1.5)
    
                nominal.SetLineWidth(3)
                nominal.SetLineColor(colors[systs.index("")])
                nominal.SetMarkerSize(0)
                nominal.SetMarkerStyle(20)

            nominal.Draw("EHIST")
        
            iamLegend = ROOT.TLegend(self.LeftMargin, 0.7, 0.96, 1.0-self.RightMargin)
            iamLegend.SetNColumns(4)
            iamLegend.AddEntry(nominal, names[systs.index("")], "L")
            
            for s in [syst, syst2]:
                theName = proc + s
                systematic = file.Get(theName)
                if "TObject" in systematic.__class__.__name__:
                    continue
    
                self.prepHisto(systematic)
                systematic.SetDirectory(0)
                systematic.SetLineWidth(3)
                systematic.SetMarkerSize(0)
                systematic.SetMarkerStyle(20)
                if normalize and systematic.Integral() > 0.0:
                    systematic.Scale(1.0/systematic.Integral())
                systematic.SetLineColor(colors[systs.index(s)])
                iamLegend.AddEntry(systematic, names[systs.index(s)], "L")
    
                canvas.cd(1)
                systematic.Draw("SAME EHIST")
                dumpster.append(systematic)
    
                canvas.cd(2)
                systRatio = systematic.Clone(systematic.GetName() + "_ratio")
                systRatio.SetDirectory(0)
                self.prepHisto(systRatio, self.scale)
                systRatio.Divide(nominal)
                systRatio.GetYaxis().SetRangeUser(0.3, 1.7)
                systRatio.GetYaxis().SetNdivisions(5, 5, 0)
                systRatio.GetYaxis().SetTitle("Syst. / Nom.")
                systRatio.Draw("SAME EHIST")
                dumpster.append(systRatio)
    
            canvas.cd(1)
            nominal.Draw("SAME")
            iamLegend.Draw("SAME")
    
            canvas.SaveAs("%s/%s_%s%s%s.pdf"%(self.outputDir, nameStub, proc, syst.replace("Down", "").replace("Up",""), tag))

if __name__ == "__main__":
    usage = "%plotSystematics [options]"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("--inputDir",  dest="inputDir",  help="Path to ntuples",    required=True                     )
    parser.add_argument("--outputDir", dest="outputDir", help="storing combine",    required=True                     )

    args = parser.parse_args()

    systPlotter = SystPlotter(args.inputDir, args.outputDir)
    
    systPlotter.run()
