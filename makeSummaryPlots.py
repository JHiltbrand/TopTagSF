#! /bin/env/python

import os
import json
import array
import shutil
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

    def increaseUnc(self, impactsJson):

        if self.measurement != "Mis":
            return

        payload = json.load(open(impactsJson))

        self.SF = payload["POIs"][0]["fit"][1]
        self.SFHiErr = payload["POIs"][0]["fit"][2] - self.SF
        self.SFLoErr = self.SF - payload["POIs"][0]["fit"][0]

        print(self.SFHiErr, self.SFLoErr)
        paramResults = payload["params"]

        totalErrHi = 0.0
        totalErrLo = 0.0

        proc = "TTmatch"
        if self.measurement == "Mis":
            proc = "QCD"

        for paramResult in paramResults:
            name      = paramResult["name"]

            if name != "JEC":
                continue

            tempImpHi = paramResult["SF_%s"%(proc)][2] - paramResult["SF_%s"%(proc)][1]
            tempImpLo = paramResult["SF_%s"%(proc)][1] - paramResult["SF_%s"%(proc)][0]
   
            pullErrHi = paramResult["fit"][2] - paramResult["fit"][1]
            pullErrLo = paramResult["fit"][1] - paramResult["fit"][0]
       
            factorHi = 1.0
            factorLo = 1.0
            if pullErrHi != 0.0: factorHi = 1.0/pullErrHi
            if pullErrLo != 0.0: factorLo = 1.0/pullErrLo
            print(factorHi, factorLo)

            tempErrHi = self.SFHiErr**2.0 - tempImpHi**2.0
            tempErrLo = self.SFLoErr**2.0 - tempImpLo**2.0

            self.SFHiErr = (tempErrHi + (factorHi * tempImpHi)**2.0)**0.5
            self.SFLoErr = (tempErrLo + (factorLo * tempImpLo)**2.0)**0.5

        print(self.SFHiErr, self.SFLoErr)

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
            "Other"            : ROOT.TColor.GetColor("#fb8072"),
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
            "Other"            : "Other",
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

        doEff = False
        doMis = False
        for fitDir in fitDirs:
        
            chunks = fitDir.split("_")

            if self.year != chunks[0]: continue

            if "topPt" not in chunks[-1]: continue

            ptBin   = chunks[-1].split("topPt")[-1].replace("Inf", "1200")
            tagger  = chunks[2]
            measure = chunks[3]

            fitPath = self.inputDir + "/" + fitDir
            aResult = self.makePrePostFitPlot(fitPath, ptBin, measure, tagger, "pass")
            _       = self.makePrePostFitPlot(fitPath, ptBin, measure, tagger, "fail")

            if   measure == "Eff":
                doEff = True
            elif measure == "Mis":
                doMis = True

            if aResult != None:
                results[aResult.uniqueId()] = aResult

            impactsFile = fitDir.replace("/", "").replace("_inputs", "").replace("topPt", "") + "_impacts.pdf"
            impactsPath = fitPath + "/" + impactsFile 
            impactsJson = fitPath + "/impacts.json"
            if os.path.exists(impactsPath):
                shutil.copyfile(impactsPath, self.outputDir + "/" + impactsFile.replace("Inf", "1200"))

            aResult.increaseUnc(impactsJson)

        if doEff:
            self.getSFSummary(results, "Eff")
        if doMis:
            self.getSFSummary(results, "Mis")

    def remapAxis(self, obj, objRef):

        nbins = objRef.GetNbinsX()
        edges = []
        for iBin in range(1, nbins+1):
            edges.append(objRef.GetXaxis().GetBinLowEdge(iBin))
        edges.append(objRef.GetXaxis().GetBinUpEdge(nbins))

        name  = obj.GetName()
        newHisto = ROOT.TH1F(name, name, nbins, array.array('d', edges))
        newHisto.SetDirectory(0)

        if "TH1" in obj.ClassName():
            for iBin in range(1, nbins+1):
                newHisto.SetBinContent(iBin, obj.GetBinContent(iBin))
                newHisto.SetBinError(iBin, obj.GetBinError(iBin))
        elif "TGraph" in obj.ClassName():
             for iBin in range(1, nbins+1):
                newHisto.SetBinContent(iBin, objRef.GetBinContent(iBin))
                newHisto.SetBinError(iBin, objRef.GetBinError(iBin))
   
        return newHisto

    def getDataMCratio(self, data, fit):
    
        ratio = data.Clone("ratio")
        ratio.Divide(data, fit)
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

    def extractHistos(self, folder, inputs):

        histos = {}
        histoRef = inputs.Get("data_obs")
        for key in folder.GetListOfKeys():
    
            if "TH1" not in key.GetClassName() and "TGraph" not in key.GetClassName(): continue
    
            if "total" in key.GetName() and "_" in key.GetName(): continue
    
            histo = key.ReadObj()
            if "TH1" in key.GetClassName():
                histo.SetDirectory(0)
    
            process = histo.GetName()

            histos[process] = self.remapAxis(histo, histoRef)
        
        return histos
   
    def makePrePostFitPlot(self, fitpath, ptBin, measurement, tagger, category):

        orderedNames = None
        if   measurement == "Eff":
            orderedNames = ["TTmatch", "TTunmatch", "Other", "QCD", "WJets", "DYJets", "Boson", "TTX", "ST", "total", "data"]
        elif measurement == "Mis":
            orderedNames = ["QCD", "TT", "Other", "WJets", "DYJets", "Boson", "TTX", "ST", "total", "data"]

        finputs = ROOT.TFile.Open("%s/top_mass_%s.root"%(fitpath, category), "READONLY")
        if finputs == None:
            return None
   
        fdiag = ROOT.TFile.Open("%s/fitDiagnosticsTest.root"%(fitpath), "READONLY")
        if fdiag == None:
            return None
    
        prefitFolder = fdiag.Get("shapes_prefit/%s"%(category))
        if prefitFolder == None:
            return None

        prefitHistos = self.extractHistos(prefitFolder, finputs)
    
        postfitFolder = fdiag.Get("shapes_fit_s/%s"%(category))
        if postfitFolder == None:
            return None

        postfitHistos = self.extractHistos(postfitFolder, finputs)

        SF      = -1.0
        SFLoErr = 0.
        SFHiErr = 0.

        ttree = fdiag.Get("tree_fit_sb")
        if ttree != None:
            ttree.GetEntry(0)
        
            if   measurement == "Eff":
                SF      = ttree.SF_TTmatch
                SFLoErr = ttree.SF_TTmatchLoErr
                SFHiErr = ttree.SF_TTmatchHiErr
            elif measurement == "Mis":
                SF      = ttree.SF_QCD
                SFLoErr = ttree.SF_QCDLoErr
                SFHiErr = ttree.SF_QCDHiErr
    
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

        nLegItems = 0
        for hname in orderedNames:
            if hname in postfitHistos:
                nLegItems += 1
        
        legTopStart = 0.9
        legBottomStart = legTopStart-nLegItems*0.06
        leg = ROOT.TLegend(0.70,legBottomStart,0.95,legTopStart)
        leg.SetFillStyle(0)
        leg.SetFillColor(0)
        leg.SetLineWidth(0)
        leg.SetTextSize(0.05)
        for hname in orderedNames:
            try:
                if "data" in hname:
                    leg.AddEntry(postfitHistos[hname], "Data", "ELP")
                else:
                    leg.AddEntry(postfitHistos[hname], self.names[hname], "L")
            except:
                pass
        
        legfit = ROOT.TLegend(self.LeftMargin+0.04,0.45,self.LeftMargin+0.24,0.57)
        legfit.SetFillStyle(0)
        legfit.SetFillColor(0)
        legfit.SetLineWidth(0)
        legfit.SetTextSize(0.05)
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
        pRatio.SetBottomMargin(0.25)
    
        pMain.Draw()
        pRatio.Draw()
        
        pMain.cd()
        
        maximums = []
        for hname in postfitHistos.keys():
            maximums.append(postfitHistos[hname].GetMaximum() + postfitHistos[hname].GetBinError(postfitHistos[hname].GetMaximumBin()))
            maximums.append(prefitHistos[hname].GetMaximum() + prefitHistos[hname].GetBinError(prefitHistos[hname].GetMaximumBin()))

        maxHeight = max(maximums)

        prefitHistos["total"].GetYaxis().SetRangeUser(-0.05*maxHeight, 1.25*maxHeight)

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
        prefitHistos["total"].GetYaxis().SetMaxDigits(4)

        xMax = 250.0
        if tagger == "Mrg":
            if measurement == "Eff":
                xMax = 250.0
            elif measurement == "Mis":
                xMax = 250.0

        prefitHistos["total"].GetXaxis().SetRangeUser(100.0, 250.0)

        prefitHistos["total"].Draw("HIST E0")
       
        for hname in prefitHistos.keys():
    
            if "total" in hname:
                postfitHistos[hname].Draw("HIST E0 sames")
            elif "data" in hname:
                prefitHistos[hname].Draw("EP sames")
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

        mark.DrawLatex(self.LeftMargin + 0.04, 0.73, taggerName + " | %s"%(category.replace("f", "F").replace("p", "P")))
    
        if category == "pass":
            mark.SetTextFont(42)
            mark.SetTextSize(0.045)
    
            mark.DrawLatex(self.LeftMargin + 0.04, 0.66, "SF = %.2f^{+%.2f}_{-%.2f}"%(SF, SFHiErr, SFLoErr))

        canvas.RedrawAxis()
        
        pRatio.cd()
        h_r_postfit.GetYaxis().SetTitleOffset(0.4)
        h_r_postfit.GetXaxis().SetTitleOffset(0.9)
        h_r_postfit.GetYaxis().SetNdivisions(5,5,0)
        h_r_postfit.GetYaxis().SetTitleSize(titleSize)
        h_r_postfit.GetYaxis().SetLabelSize(labelSize)
        h_r_postfit.GetXaxis().SetTitleSize(titleSize)
        h_r_postfit.GetXaxis().SetLabelSize(labelSize)
        h_r_postfit.GetXaxis().SetTitle("Top Candidate Mass [GeV]")
        h_r_postfit.GetYaxis().SetTitle("Data / Post-fit")
        h_r_postfit.GetYaxis().SetRangeUser(0.01,1.99)
        h_r_postfit.GetXaxis().SetRangeUser(100.0, 250.0) 

        beginX = h_r_postfit.GetXaxis().GetXmin()
        endX   = h_r_postfit.GetXaxis().GetXmax()

        h_r_postfit.Draw("P E0 SAME")

        l = ROOT.TLine(100.0, 1.0, 250.0, 1.0) 
        l.SetLineWidth(2)
        l.SetLineColor(ROOT.kBlack)
        l.SetLineStyle(7)
        l.Draw("SAME")

        canvas.RedrawAxis()
        
        canvas.Print(self.outputDir + "/%s_%s_%s_%s_%s.pdf"%(self.year, tagger, measurement, ptBin, category))

        return SFresult(SF, SFHiErr, SFLoErr, tagger, measurement, ptBin)
    
    def getSFSummary(self, results, measurement):
      
        sfGraphs = []
        ptrange = []

        names = []
        for result in results.values():
            if result.measurement != measurement:
                continue
            if result.tagger == "Res" and int(result.ptBin.split("to")[0]) >= 400:
                continue
            names.append(result.ptBin.replace("to", "-"))

        names.sort()

        dummy = None

        leg = ROOT.TLegend(0.55, 0.66, 0.95, 0.89)
        leg.SetFillStyle(0)
        leg.SetFillColor(0)
        leg.SetLineWidth(0)
        leg.SetTextSize(0.035)
    
        ialgo = 0
        for algo in ["Res", "Mrg"]:

            legname = None
            color = None
            if algo == "Res":
                legname = "Resolved Top Tagger"
                color = ROOT.TColor.GetColor("#88258C")

                dummy = ROOT.TH1F("dummy","dummy",len(names),0.,len(names))
                for name in names:
                    dummy.GetXaxis().SetBinLabel(names.index(name)+1, name)
                dummy.GetYaxis().SetRangeUser(0.2,2.4)
                dummy.GetYaxis().SetTitleOffset(0.9)
                dummy.GetYaxis().SetLabelSize(0.04)
                dummy.GetYaxis().SetTitleSize(0.05)
                dummy.GetYaxis().SetTitle("#epsilon_{  Data} / #epsilon_{  MC}")
                dummy.GetXaxis().SetLabelSize(0.06)
                dummy.GetXaxis().SetTitleSize(0.05)
                dummy.GetXaxis().SetTitle("Top Candidate p_{T} [GeV]")
                dummy.GetXaxis().SetTitleOffset(1.25)
                dummy.SetTitle("")

            elif algo == "Mrg":
                legname = "Merged Top Tagger (DeepAK8)"
                color = ROOT.TColor.GetColor("#5CB4E8")
   
            xval      = array.array('d', [-1.0 for i in range(len(names))])
            xvalerr   = array.array('d', [-1.0 for i in range(len(names))])
            yval      = array.array('d', [-1.0 for i in range(len(names))])
            yvalerrlo = array.array('d', [-1.0 for i in range(len(names))])
            yvalerrhi = array.array('d', [-1.0 for i in range(len(names))])
            
            sfNaming = "%s_%s_vs_topPt_%s"%(self.year, measurement.replace("Mis", "MisTagSF").replace("Eff", "TagRateSF"), algo.replace("Res", "Resolved").replace("Mrg", "Merged"))
            sfFile = ROOT.TFile.Open("%s_SF.root"%(self.year), "UPDATE")

            binEdges = []
            for name in names:
    
                binEdges.append(float(name.split("-")[0]))

                if name == names[-1]:
                    binEdges.append(float(name.split("-")[1]))

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
    
                xval[iname]      = (iname+0.5) + 0.08*(ialgo)
                xvalerr[iname]   = 0.
                yval[iname]      = SF 
                yvalerrlo[iname] = SFLoErr
                yvalerrhi[iname] = SFHiErr
    
            sfHist = ROOT.TH1F(sfNaming, sfNaming, len(binEdges)-1, array.array('d', binEdges))
            for i in range(len(yval)):
                val = 1.0
                err = 0.0
                if yval[i] > 0.0:
                    val = yval[i]
                    err = max(yvalerrlo[i], yvalerrhi[i])
                sfHist.SetBinContent(i+1, val)
                sfHist.SetBinError(i+1, err)

            sfFile.cd()
            sfHist.Write()
            sfFile.Close()

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
        canvas.SetLeftMargin(0.10)
        canvas.SetBottomMargin(0.14)
        canvas.SetTopMargin(0.08)
        canvas.SetRightMargin(0.03)
    
        dummy.Draw("HIST")

        for sfGraph in sfGraphs:
            sfGraph.Draw("EP0 SAMES")
    
        leg.Draw("SAME")

        self.addCMSlogo(canvas, 0.08, 0.03, 0.10)
    
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
