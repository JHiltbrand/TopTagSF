#! /bin/env/python
import copy

from collections import OrderedDict as odict

def initHistos(year, measurement, tagger, ptbin, doSysts):

    # Define working points for merged and resolved tagger per year
    WPs = {}
    if   "2016" in year:
        WPs["Res"] = 0.950
        WPs["Mrg"] = 0.937
    elif "2017" in year:
        WPs["Res"] = 0.950
        WPs["Mrg"] = 0.895
    elif "2018" in year:
        WPs["Res"] = 0.950
        WPs["Mrg"] = 0.895

    # Get the exact working point based on tagger
    WP = WPs[tagger]

    # Relevant top tagger variables contain R or M based on which tagger they refer to
    topType = "R"
    if tagger == "Mrg":
        topType = "M"

    # Four main selections, efficiency and mistag, and pass or fail categories
    selections = {"Eff_pass" : "pass_TTCR${SYST}&&best%sTopDisc${SYST}>${WP}"%(topType),
                  "Eff_fail" : "pass_TTCR${SYST}&&best%sTopDisc${SYST}<=${WP}"%(topType),
                  "Mis_pass" : "pass_QCDCR${SYST}&&best%sTopDisc${SYST}>${WP}"%(topType),
                  "Mis_fail" : "pass_QCDCR${SYST}&&best%sTopDisc${SYST}<=${WP}"%(topType)
    }

    histosInfo = {"${TOP}TopCandMass" : {"weight" : "weight${PROC}${SYST}", "selection" : "${SELECTION}", "variable" : "best%sTopMass${SYST}"%(topType), "xbins" : 30, "xmin" : 100, "xmax" : 250}}

    # Match process names to generic name used for naming ROOT files
    # Also, for efficiency, split TT into GEN matched and unmatched categories
    # Ordered dictionary is to keep process which SF will be applied to as process 0
    processes = odict()
    if measurement == "Eff":
        processes["TTmatch"]   = "TT"
        processes["TTunmatch"] = "TT"
        processes["QCD"]       = "QCD"
    elif measurement == "Mis":
        processes["QCD"]   = "QCD"
        processes["TT"]    = "TT"
    processes["Boson"]  = "Boson"
    processes["TTX"]    = "TTX"
    processes["ST"]     = "ST"

    # Depending on type of measurement, pick the correct data sample
    if   measurement == "Eff": processes["SingleMuon"] = "Data_SingleMuon"
    elif measurement == "Mis": processes["JetHT"]      = "Data_JetHT"

    # Empty string "systematic" ensures baseline histograms that are always needed
    systematics = [""]
    if doSysts:
        systematics.append("pu")
        systematics.append("scale")
        systematics.append("pdf")
        systematics.append("JEC")
        systematics.append("JER")
        if measurement == "Eff":
            systematics.append("btag")
            systematics.append("lep")

    histograms = {}

    for syst in systematics:
        for variation in ["Up", "Down"]:

            systematic = ""
            systTreeStub = ""
            if syst != "":
                systematic = syst + variation
                # Need to get different TTree for JEC and JER systs, which follows particular capitalization
                if "JE" in syst:
                    systTreeStub = syst + variation.lower()

            for process, stub in processes.items():

                # Skip doing systs for data
                if "Data" in stub and systematic != "": continue

                # Split TT into whether GEN matched or not
                extraSel = ""
                if   process == "TTmatch":   extraSel = "&&best%sTopMassGenMatch%s==1"%(topType, systTreeStub)
                elif process == "TTunmatch": extraSel = "&&best%sTopMassGenMatch%s==0"%(topType, systTreeStub)
            
                for cat in ["pass", "fail"]:

                    selStr = "%s_%s"%(measurement, cat)
                    selExp = selections[selStr]

                    for histoName, histoOps in histosInfo.items():
                        hopsCopy = copy.copy(histoOps)

                        if   tagger == "Res":
                            if "1200" in ptbin and measurement == "Eff":
                                hopsCopy["xbins"] = 15
                        elif tagger == "Mrg":
                            if measurement == "Eff": 
                                hopsCopy["xbins"] = range(100, 220, 10) + [220., 285., 350.]
                            else:
                                hopsCopy["xbins"] = [0., 100.] + range(110, 250, 10) + [250., 275., 300., 500.] 

                        # Decide which event weight to use based on the desired measurement
                        proc = ""
                        if   "Mis" in selStr: proc = "QCD"
                        elif "Eff" in selStr: proc = "TTbar"
                        else: continue

                        # Resolved string "100to150" to make selection on top pt
                        ptSel = ""
                        if "to" in ptbin:
                            ptSel = "&&best%sTopPt%s>%s&&best%sTopPt%s<=%s"%(topType, systTreeStub, ptbin.split("to")[0], topType, systTreeStub, ptbin.split("to")[-1])

                        hopsCopy["selection"] = selExp.replace("${WP}", str(WP)).replace("${SYST}", systTreeStub) + extraSel + ptSel

                        if "Data" in stub: hopsCopy["weight"] = "Weight"
                        else:              hopsCopy["weight"] = hopsCopy["weight"].replace("${PROC}", proc).replace("${SYST}", systTreeStub)

                        # Divide out b tag SF from total event weight for QCD CR
                        if proc == "QCD" and syst == "" and "Data" not in stub:
                            hopsCopy["weight"] += "/bTagSF_EventWeightSimple_Central"
                       
                        hopsCopy["variable"] = hopsCopy["variable"].replace("${SYST}", systTreeStub)

                        if   systematic == "puUp":      hopsCopy["weight"] += "*puSysUpCorr/puWeightCorr"
                        elif systematic == "puDown":    hopsCopy["weight"] += "*puSysDownCorr/puWeightCorr"
                        elif systematic == "scaleUp":   hopsCopy["weight"] += "*scaleWeightUp"
                        elif systematic == "scaleDown": hopsCopy["weight"] += "*scaleWeightDown"
                        elif systematic == "pdfUp":     hopsCopy["weight"] += "*PDFweightUp"
                        elif systematic == "pdfDown":   hopsCopy["weight"] += "*PDFweightDown"
                        elif systematic == "btagUp":    hopsCopy["weight"] += "*bTagSF_EventWeightSimple_Down/bTagSF_EventWeightSimple_Central"
                        elif systematic == "btagDown":  hopsCopy["weight"] += "*bTagSF_EventWeightSimple_Up/bTagSF_EventWeightSimple_Central"
                        elif systematic == "lepUp":     hopsCopy["weight"] += "*totGoodMuonSF_Up/totGoodMuonSF"
                        elif systematic == "lepDown":   hopsCopy["weight"] += "*totGoodMuonSF_Down/totGoodMuonSF"

                        histograms["%s_%s_%s_%s"%(process, histoName.replace("${TOP}", tagger), selStr, systematic)] = hopsCopy

    # Do not need empty syst before returning the list
    systematics.pop(0) 
    
    return processes, histograms, systematics
