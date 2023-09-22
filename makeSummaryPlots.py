#! /bin/env/python

import os
import re
import array
import argparse

import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.TH1.SetDefaultSumw2()
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)
ROOT.gStyle.SetPalette(1)

class SFresult:

    def __init__(self, SF, SFHiErr, SFLoErr, tagger, measurement, ptBin):

        self.SF          = SF
        self.SFHiErr     = SFHiErr
        self.SFLoErr     = SFLoErr
        self.tagger      = tagger
        self.measurement = measurement
        self.ptBin       = ptBin

    def uniqueId(self):
        return self.tagger + self.measurement + self.ptBin

class Plotter:
    
    def __init__(self, year, approved, inputDir, outputDir):

        self.year      = year
        self.inputDir  = os.path.realpath(inputDir)
        self.outputDir = os.path.realpath(outputDir)
        self.approved  = approved
    
        self.LeftMargin = 0.1
        self.RightMargin = 0.04
        self.TopMargin = 0.08

        self.colors = {
            "data"             : 1,
            "total"            : ROOT.kBlue+2,
            "TTmatch"          : ROOT.kMagenta-5,
            "TTunmatch"        : 40,
            "TT"               : 40,
            "QCD"              : 30,
            "Boson"            : ROOT.TColor.GetColor("#ffcc33"),
            "TTX"              : 38,
            "ST"               : ROOT.TColor.GetColor("#fb8072"),
            "Rare"             : ROOT.TColor.GetColor("#fdb462"),
            "DYJets"           : ROOT.TColor.GetColor("#80b1d3"),
            "WJets"            : 41
        }

        self.names = {
            "data"             : "Data",
            "total"            : "Total SM",
            "TTmatch"          : "t#bar{t} (matched)",
            "TTunmatch"        : "t#bar{t} (unmatched)",
            "TT"               : "t#bar{t} + jets",
            "QCD"              : "QCD multijet",
            "Boson"            : "Boson",
            "TTX"              : "t#bar{t} + X",
            "ST"               : "Single top",
            "Rare"             : "Rare",
            "DYJets"           : "Z/#gamma^{*} + jets",
            "WJets"            : "W + jets"
        }

        self.lumis = {
            "2016preVFP"  : 19.52,
            "2016postVFP" : 16.81,
            "2017"        : 41.48,
            "2018"        : 59.83
        }

        if not os.path.isdir(self.outputDir):
            os.system("mkdir -p " + self.outputDir)

    def run(self):

        results = {}

        fitDirs = os.listdir(self.inputDir)

        for fitDir in fitDirs:
        
            chunks = fitDir.split("_")

            if self.year != chunks[0]: continue

            if "topPt" not in chunks[-1]: continue

            ptBin = chunks[-1].split("topPt")[-1]

            aResult = self.makePrePostFitPlot("%s/%s"%(self.inputDir,fitDir), ptBin, chunks[2], chunks[3], "pass")
            _       = self.makePrePostFitPlot("%s/%s"%(self.inputDir,fitDir), ptBin, chunks[2], chunks[3], "fail")

            results[aResult.uniqueId()] = aResult

        self.getSFSummary(results, "Eff")
        self.getSFSummary(results, "Mis")

    def remapAxis(self, obj, tagger):

        minimum = None
        maximum = None
        if   tagger == "Mrg":
            minimum = 105.0
            maximum = 210.0
        elif tagger == "Res":
            minimum = 100.0
            maximum = 250.0

        if "TH1" in obj.ClassName():
            nbins = obj.GetNbinsX()
            name  = obj.GetName()
            newHisto = ROOT.TH1F(name,name,nbins,minimum,maximum)
            newHisto.SetDirectory(0)

            for iBin in range(1, nbins+1):
                newHisto.SetBinContent(iBin,obj.GetBinContent(iBin))
                newHisto.SetBinError(iBin,obj.GetBinError(iBin))
    
            return newHisto

        elif "TGraph" in obj.ClassName():

            N = obj.GetN()
            xval = obj.GetX()
            yval = obj.GetY()
            xvalerrhi = obj.GetEXhigh()
            xvalerrlo = obj.GetEXlow()
            yvalerrhi = obj.GetEYhigh()
            yvalerrlo = obj.GetEYlow()

            scaleX = (maximum - minimum) / float(N)
            for iPoint in range(0, N):
                xval[iPoint] = minimum + xval[iPoint]*scaleX

            newGraph = ROOT.TGraphAsymmErrors(N,xval,yval,xvalerrlo,xvalerrhi,yvalerrlo,yvalerrhi)

            return newGraph

    def getDataMCratio(self, data, fit):
    
        tempData = fit.Clone("tempData")
        tempData.SetName("tempData")
        for iBin in range(0, tempData.GetNbinsX()):
            tempData.SetBinContent(iBin+1, data.GetY()[iBin])
            tempData.SetBinError(iBin+1, (data.GetEYlow()[iBin]+data.GetEYhigh()[iBin])/2.0)
    
        ratio = tempData.Clone("ratio")
        ratio.Divide(tempData, fit)
        ratio.SetMarkerStyle(20)
        ratio.SetMarkerSize(1)
        ratio.SetLineWidth(2)
        ratio.SetLineStyle(1)
    
        return ratio
    
    def addCMSlogo(self, canvas, topMargin = None, rightMargin = None, leftMargin = None):

        if topMargin == None:
            topMargin = self.TopMargin
        if rightMargin == None:
            rightMargin = self.RightMargin
        if leftMargin == None:
            leftMargin = self.LeftMargin
    
        canvas.cd()
    
        mark = ROOT.TLatex()
        mark.SetNDC(True)

        CMSsize = 0.095
    
        mark.SetTextAlign(13)
        mark.SetTextSize(CMSsize)
        mark.SetTextFont(61)
        mark.DrawLatex(leftMargin + 0.04, 1.0 - (topMargin + 0.01), "CMS")
    
        mark.SetTextFont(52)
        mark.SetTextSize(0.055)
    
        if self.approved:
            mark.DrawLatex(leftMargin + 0.04, 1 - (topMargin + 0.01 + CMSsize * 1.05), "")
        else:
            mark.DrawLatex(leftMargin + 0.04, 1 - (topMargin + 0.01 + CMSsize * 1.05), "Work in Progress")
    
        mark.SetTextFont(42)
        mark.SetTextAlign(31)
        mark.DrawLatex(1 - rightMargin, 1 - (topMargin - 0.017), "%.1f fb^{-1} (13 TeV)"%(self.lumis[self.year]))

    def extractHistos(self, folder, tagger):

        histos = {}
        for key in folder.GetListOfKeys():
    
            if "TH1" not in key.GetClassName() and "TGraph" not in key.GetClassName(): continue
    
            if "total" in key.GetName() and "_" in key.GetName(): continue
    
            histo = key.ReadObj()
            if "TH1" in key.GetClassName():
                histo.SetDirectory(0)
    
            process = histo.GetName()
            histos[process] = self.remapAxis(histo, tagger)
        
        return histos
   
    def makePrePostFitPlot(self, fitpath, ptBin, measurement, tagger, category):

        orderedNames = None
        if   measurement == "Eff":
            orderedNames = ["TTmatch", "TTunmatch", "QCD", "WJets", "DYJets", "Boson", "TTX", "ST", "total", "data"]
        elif measurement == "Mis":
            orderedNames = ["QCD", "TT", "WJets", "DYJets", "Boson", "TTX", "ST", "total", "data"]
   
        fdiag = ROOT.TFile.Open("%s/fitDiagnosticsTest.root"%(fitpath), "READONLY")
    
        prefitFolder = fdiag.Get("shapes_prefit/%s"%(category))
        prefitHistos = self.extractHistos(prefitFolder, tagger)
    
        postfitFolder = fdiag.Get("shapes_fit_s/%s"%(category))
        postfitHistos = self.extractHistos(postfitFolder, tagger)

        ttree = fdiag.Get("tree_fit_sb")
        ttree.GetEntry(0)

        SF      = ttree.SF
        SFLoErr = ttree.SFLoErr
        SFHiErr = ttree.SFHiErr
    
        for hname in prefitHistos.keys():
            prefitHistos[hname].SetTitle("")
            postfitHistos[hname].SetTitle("")
            if "data" in hname:
                prefitHistos[hname].SetLineColor(1)
                prefitHistos[hname].SetLineWidth(3)
                prefitHistos[hname].SetMarkerSize(1.2)
                prefitHistos[hname].SetMarkerStyle(20)
                prefitHistos[hname].SetMarkerColor(1)

                postfitHistos[hname].SetLineColor(1)
                postfitHistos[hname].SetLineWidth(3)
                postfitHistos[hname].SetMarkerSize(1.2)
                postfitHistos[hname].SetMarkerStyle(20)
                postfitHistos[hname].SetMarkerColor(1)
            else:
                prefitHistos[hname].SetLineColor(self.colors[hname])
                prefitHistos[hname].SetLineStyle(2)
                prefitHistos[hname].SetLineWidth(3)
                prefitHistos[hname].SetMarkerSize(0)
    
                postfitHistos[hname].SetLineColor(self.colors[hname])
                postfitHistos[hname].SetLineStyle(1)
                postfitHistos[hname].SetLineWidth(4)
                postfitHistos[hname].SetMarkerSize(0)
    
        h_r_postfit = self.getDataMCratio(prefitHistos["data"], postfitHistos["total"])
        h_r_postfit.SetName("h_r_postfit")
        h_r_postfit.SetMarkerColor(1)
        h_r_postfit.SetLineColor(1)
        
        leg = ROOT.TLegend(0.73,0.50,0.95,0.90)
        leg.SetFillStyle(0)
        leg.SetFillColor(0)
        leg.SetLineWidth(0)
        leg.SetTextSize(0.04)
        for hname in orderedNames:
            try:
                if "data" in hname:
                    leg.AddEntry(postfitHistos[hname], "Data", "ELP")
                else:
                    leg.AddEntry(postfitHistos[hname], self.names[hname], "L")
            except:
                pass
        
        legfit = ROOT.TLegend(0.73,0.35,0.95,0.45)
        legfit.SetFillStyle(0)
        legfit.SetFillColor(0)
        legfit.SetLineWidth(0)
        legfit.SetTextSize(0.04)
        legfit.AddEntry(prefitHistos["total"],"Pre-fit","L")
        legfit.AddEntry(postfitHistos["total"],"Post-fit","L")
        
        canvas = ROOT.TCanvas("canvas","canvas",600,600) 

        split = 0.35
        scale = (1.0 - 0.35) / 0.35
        
        pMain = ROOT.TPad("pMain", "pMain", 0.0, split, 1.0, 1.0)
        pMain.SetRightMargin(self.RightMargin)
        pMain.SetLeftMargin(self.LeftMargin)
        pMain.SetBottomMargin(0.00)
        pMain.SetTopMargin(self.TopMargin)
        
        pRatio = ROOT.TPad("pRatio", "pRatio", 0.0, 0.0, 1.0, split)
        pRatio.SetRightMargin(self.RightMargin)
        pRatio.SetLeftMargin(self.LeftMargin)
        pRatio.SetTopMargin(0.00)
        pRatio.SetBottomMargin(0.23)
    
        pMain.Draw()
        pRatio.Draw()
        
        pMain.cd()
        
        maxHeight = 0
        if postfitHistos["total"].GetMaximum() > prefitHistos["total"].GetMaximum():
            maxHeight = postfitHistos["total"].GetMaximum()
        else:
            maxHeight = prefitHistos["total"].GetMaximum()

        prefitHistos["total"].GetYaxis().SetRangeUser(-0.05*maxHeight, 1.08*maxHeight)

        titleSize = 0.12
        labelSize = 0.09
    
        prefitHistos["total"].GetXaxis().SetLabelSize(0.)
        prefitHistos["total"].GetYaxis().SetTitle("Events / bin")
        prefitHistos["total"].GetXaxis().SetTitle("Top Candidate Mass [GeV]")
        prefitHistos["total"].GetYaxis().SetTitleOffset(0.8)
        prefitHistos["total"].GetYaxis().SetTitleSize(titleSize / scale)
        prefitHistos["total"].GetYaxis().SetLabelSize(labelSize / scale)
        prefitHistos["total"].GetXaxis().SetTitleSize(0.0)
        prefitHistos["total"].GetXaxis().SetLabelSize(0.0)
        prefitHistos["total"].SetMinimum(-6)

        prefitHistos["total"].Draw("HIST E0")
       
        for hname in prefitHistos.keys():
    
            if "total" in hname:
                postfitHistos[hname].Draw("HIST E0 sames")
            elif "data" in hname:
                prefitHistos[hname].Draw("P sames")
            else:
                prefitHistos[hname].Draw("HIST E0 sames")
                postfitHistos[hname].Draw("HIST E0 sames")
    
        leg.Draw("sames")
        legfit.Draw("sames")

        self.addCMSlogo(pMain)

        mark = ROOT.TLatex()
        mark.SetNDC(True)
    
        mark.SetTextAlign(13)
        mark.SetTextSize(0.055)
        mark.SetTextFont(61)

        taggerName = ""
        if tagger == "Res":
            taggerName = "Resolved"
        elif tagger == "Mrg":
            taggerName = "Merged"

        mark.DrawLatex(self.LeftMargin + 0.04, 0.73, taggerName)
    
        mark.SetTextFont(42)
        mark.SetTextSize(0.045)
    
        mark.DrawLatex(self.LeftMargin + 0.04, 0.66, "SF = %.2f^{+%.2f}_{-%.2f}"%(SF, SFHiErr, SFLoErr))

        canvas.RedrawAxis()
        
        pRatio.cd()
        h_r_postfit.GetYaxis().SetTitleOffset(0.4)
        h_r_postfit.GetXaxis().SetTitleOffset(0.8)
        h_r_postfit.GetYaxis().SetNdivisions(5,5,0)
        h_r_postfit.GetYaxis().SetTitleSize(titleSize)
        h_r_postfit.GetYaxis().SetLabelSize(labelSize)
        h_r_postfit.GetXaxis().SetTitleSize(titleSize)
        h_r_postfit.GetXaxis().SetLabelSize(labelSize)
        h_r_postfit.GetXaxis().SetTitle("Top Candidate Mass [GeV]")
        h_r_postfit.GetYaxis().SetTitle("Data / Post-fit")
        h_r_postfit.GetYaxis().SetRangeUser(0.01,1.99)
        h_r_postfit.Draw("P E0")
        canvas.RedrawAxis()
        
        canvas.Print(self.outputDir + "/%s_%s_%s_%s.pdf"%(self.year, tagger, measurement, category))

        return SFresult(SF, SFHiErr, SFLoErr, tagger, measurement, ptBin)
    
    def getSFSummary(self, results, measurement):
      
        sfGraphs = []
        ptrange = []

        dummy = None

        leg = ROOT.TLegend(0.60, 0.66, 0.95, 0.89)
        leg.SetFillStyle(0)
        leg.SetFillColor(0)
        leg.SetLineWidth(0)
        leg.SetTextSize(0.03)
    
        ialgo = 0
        for algo in ["Res", "Mrg"]:

            names = []
            names.append("0-100")
            names.append("100-150") 
            names.append("150-200")
            names.append("200-300")
            names.append("300-400")
            names.append("400-480")
            names.append("480-600")
            names.append("600-1200")

            legname = None
            color = None
            if algo == "Res":
                legname = "Resolved Top Tagger"
                color = ROOT.TColor.GetColor("#88258C")

                dummy = ROOT.TH1F("dummy","dummy",len(names),0.,len(names))
                for name in names:
                    dummy.GetXaxis().SetBinLabel(names.index(name)+1, name)
                dummy.GetYaxis().SetRangeUser(0.5,2.)
                dummy.GetYaxis().SetTitleOffset(0.8)
                dummy.GetYaxis().SetLabelSize(0.04)
                dummy.GetYaxis().SetTitleSize(0.05)
                dummy.GetYaxis().SetTitle("#epsilon_{  DATA} / #epsilon_{  MC}")
                dummy.GetXaxis().SetLabelSize(0.06)
                dummy.GetXaxis().SetTitleSize(0.05)
                dummy.GetXaxis().SetTitle("Top Candidate p_{T} [GeV]")
                dummy.GetXaxis().SetTitleOffset(1.2)
                dummy.SetTitle("")

            elif algo == "Mrg":
                legname = "Merged Top Tagger (DeepAK8)"
                color = ROOT.TColor.GetColor("#5CB4E8")
   
            xval      = array.array('d', [-1.0 for i in range(len(names))])
            xvalerr   = array.array('d', [-1.0 for i in range(len(names))])
            yval      = array.array('d', [-1.0 for i in range(len(names))])
            yvalerrlo = array.array('d', [-1.0 for i in range(len(names))])
            yvalerrhi = array.array('d', [-1.0 for i in range(len(names))])
            
            for name in names:
    
                iname = names.index(name)

                SF      = -1.0
                SFLoErr = 0.0
                SFHiErr = 0.0
                for result in results.values():

                    nameToUse = name
                    if algo == "Res" and float(name.split("-")[0]) >= 400.0:
                        nameToUse = "400-1200"
                        
                    if algo in result.tagger and measurement in result.measurement and nameToUse.replace("-", "to") in result.ptBin:
                        SF = result.SF
                        SFHiErr = result.SFHiErr
                        SFLoErr = result.SFLoErr
                        break
    
                xval[iname]      = (iname+0.5) + 0.03*(ialgo)
                xvalerr[iname]   = 0.
                yval[iname]      = SF 
                yvalerrlo[iname] = SFLoErr
                yvalerrhi[iname] = SFHiErr
    
            sfGraph = ROOT.TGraphAsymmErrors(len(names),xval,yval,xvalerr,xvalerr,yvalerrlo,yvalerrhi)
            sfGraph.SetLineColor(color)
            sfGraph.SetMarkerColor(color)
            sfGraph.SetMarkerStyle(8)
            sfGraph.SetMarkerSize(1)
            sfGraph.SetLineWidth(2)

            leg.AddEntry(sfGraph, legname, "PE2")
            sfGraphs.append(sfGraph)

            ialgo += 1
    
        canvas = ROOT.TCanvas("c_sf_%s"%(measurement), "c_sf_%s"%(measurement), 700, 500)
        canvas.SetLeftMargin(0.08)
        canvas.SetBottomMargin(0.14)
        canvas.SetTopMargin(0.08)
        canvas.SetRightMargin(0.03)
    
        dummy.Draw("HIST")

        for sfGraph in sfGraphs:
            sfGraph.Draw("EP SAMES")
    
        leg.Draw("SAME")

        self.addCMSlogo(canvas, 0.08, 0.03, 0.08)
    
        canvas.SaveAs("%s/%s_SF_%s.pdf"%(self.outputDir, self.year, measurement))

if __name__ == "__main__":

    usage = "usage: %makePlots [options]"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("--year",      dest="year",      help="year to process",       required=True)
    parser.add_argument("--inputDir",  dest="inputDir",  help="area with fit results", required=True)
    parser.add_argument("--outputDir", dest="outputDir", help="where to put plots",    required=True)
    parser.add_argument("--approved",  dest="approved",  help="plots approved",        default=False, action="store_true")
    args = parser.parse_args()

    thePlotter = Plotter(args.year, args.approved, args.inputDir, args.outputDir)

    thePlotter.run()
