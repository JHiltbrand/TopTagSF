#! /bin/env/python
import copy

from collections import OrderedDict as odict

def initHistos(year, measurement, tagger, ptbin):

    WPs = {}
    if "2016" in year:
        WPs["Res"] = 0.95
        WPs["Mrg"] = 0.937
    elif "2017" in year:
        WPs["Res"] = 0.95
        WPs["Mrg"] = 0.895
    elif "2018" in year:
        WPs["Res"] = 0.95
        WPs["Mrg"] = 0.895

    ptSel = ""
    if "to" in ptbin:
        ptSel = "&&bestTopPt>%s&&bestTopPt<=%s"%(ptbin.split("to")[0], ptbin.split("to")[-1])

    selections = {"Eff_pass" : "pass_TTCR${SYST}&&bestTopDisc${SYST}>${WP}",
                  "Eff_fail" : "pass_TTCR${SYST}&&bestTopDisc${SYST}>=0&&bestTopDisc${SYST}<=${WP}",
                  "Mis_pass" : "pass_QCDCR${SYST}&&bestTopDisc${SYST}>${WP}",
                  "Mis_fail" : "pass_QCDCR${SYST}&&bestTopDisc${SYST}>=0&&bestTopDisc${SYST}<=${WP}",
    }

    histosInfo = {"${TOP}TopCandMass" : {"weight" : "weight${PROC}${SYST}", "selection" : "${SELECTION}", "variable" : "bestTopMass${SYST}", "xbins" : 20, "xmin" : 100, "xmax" : 250}, 
    }

    processes = odict()

    if measurement == "Eff":
        processes["TTmatch"]    = "TT"
        processes["TTunmatch"]  = "TT"
        processes["QCD"]        = "QCD"
    elif measurement == "Mis":
        processes["QCD"]   = "QCD"
        processes["TT"]    = "TT"
        processes["WJets"]  = "WJets"
        processes["DYJets"] = "DYJetsToLL_M-50"

    processes["Boson"]  = "Boson"
    processes["TTX"]    = "TTX"
    processes["ST"]     = "ST"

    if measurement == "Eff":
        processes["SingleMuon"] = "Data_SingleMuon"
    elif measurement == "Mis":
        processes["JetHT"]      = "Data_JetHT"

    histograms = {}

    systematics = ["", "puUp", "puDown"]#, "JECUp", "JECDown", "JERUp", "JERDown"]:

    for syst in systematics:

        for process, stub in processes.items():

            # Skip doing systs for data
            if "Data" in stub and syst != "": continue

            systVar = ""
            if "JE" in syst:
                systVar = syst.replace("U", "u").replace("D", "d")

            # Split TT into whether GEN matched or not
            extraSel = ""
            if process == "TTmatch":
                extraSel = "&&bestTopMassGenMatch%s==1"%(systVar)
            elif process == "TTunmatch":
                extraSel = "&&bestTopMassGenMatch%s==0"%(systVar)
        
            for top, WP in WPs.items():

                # Only pick out one of the taggers based on passed argument
                if top != tagger: continue

                for selStr, selExp in selections.items():

                    # Only pick efficiency or mistag measurement, not both
                    if measurement not in selStr: continue

                    selExpCopy = copy.copy(selExp)
                    for histoName, histoOps in histosInfo.items():
                        histoNameCopy = copy.copy(histoName)
                        hopsCopy = copy.copy(histoOps)
            
                        # Decide which event weight to use based on the desired measurement
                        proc = ""
                        if   "Mis" in selStr:
                            proc = "QCD"
                        elif "Eff" in selStr:   
                            proc = "TTbar"
                        else:
                            continue

                        # Need to add a requirement on number of constituents
                        constSel = "&&bestTopNconst%s==3"%(systVar)
                        if tagger == "Mrg":
                            constSel = "&&bestTopNconst%s==1"%(systVar)

                        extraWeights = ""
                        if proc == "TTbar":
                            extraWeights = "*totGoodMuonSF"
                        elif proc == "QCD":
                            extraWeights = "*jetTrigSF"
            
                        hopsCopy["selection"] = selExpCopy.replace("${WP}", str(WP)).replace("${SYST}", systVar) + extraSel + constSel + ptSel

                        if "Data" in stub:
                            hopsCopy["weight"] = "Weight"
                        else:
                            hopsCopy["weight"] = hopsCopy["weight"].replace("${PROC}", proc).replace("${SYST}", systVar) + extraWeights
                       
                        hopsCopy["variable"]  = hopsCopy["variable"].replace("${SYST}", systVar)

                        if syst == "puUp":
                            hopsCopy["weight"] += "*puSysUpCorr/puWeightCorr"
                        elif syst == "puDown":
                            hopsCopy["weight"] += "*puSysDownCorr/puWeightCorr"

                        if "Mrg" in top:
                            hopsCopy["xmin"] = 105
                            hopsCopy["xmax"] = 210

                        histograms["%s_%s_%s_%s"%(process, histoNameCopy.replace("${TOP}", top), selStr, syst)] = hopsCopy
    
    return processes, histograms, systematics
