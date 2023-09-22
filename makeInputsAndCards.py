#! /bin/env/python

import os
import re
import argparse
import multiprocessing as mp

import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.TH1.SetDefaultSumw2()
ROOT.TH2.SetDefaultSumw2()

# Routine that is called for each individual histogram that is to be 
# drawn from the input tree. All information about what to draw, selections,
# and weights is contained in the histOps dictionary
def makeNDhisto(year, histName, histOps, outfile, tree, isData):

    # To efficiently TTree->Draw(), we will only "activate"
    # necessary branches. So first, disable all branches
    tree.SetBranchStatus("*", 0)

    selection = histOps["selection"]
    variable  = histOps["variable"]
    weight    = histOps["weight"]
    
    # Make one big string to extract all relevant branch names from
    concatStr = selection + "," + variable
    if not isData:
        concatStr = concatStr + "," + weight

    # The idea is to turn the concatStr into a comma separated list of branches
    # Parenthesis can simply be removed, operators are simply replace with a comma
    # After all replacements, the string is split on the comma and filtered for empty strings
    expressions = re.findall(r'(\w+::\w+)', concatStr)
    for exp in expressions:
        concatStr = concatStr.replace(exp, "")
    concatStr = re.sub("[()]", "", concatStr)
    for replaceStr in ["&&", "||", "==", "<=", ">=", ">", "<", "*", ".", "/", "+", "-", ":"]:
        concatStr = concatStr.replace(replaceStr, ",")
    branches = list(filter(bool, concatStr.split(",")))

    # Here, the branches list will be names of branches and strings of digits
    # The digits are residual cut expressions like NGoodJets_pt30>=7 ==> "NGoodJets_pt30", "7"
    # So if a supposed branch name can be turned into an int, then it is not a legit branch name
    for branch in branches:
        try:
            int(branch)
            continue
        except:
            tree.SetBranchStatus(branch, 1)

    is2D = False
    if re.search(r'^[^:]*:[^:]*$', variable):
        is2D = True

    outfile.cd()

    htemp = None
    if not is2D:
        temph = ROOT.TH1F(histName, "", histOps["xbins"], histOps["xmin"], histOps["xmax"])
    else:
        temph = ROOT.TH2F(histName, "", histOps["xbins"], histOps["xmin"], histOps["xmax"], histOps["ybins"], histOps["ymin"], histOps["ymax"])

    # For MC, we multiply the selection string by our chosen weight in order
    # to fill the histogram with an event's corresponding weight
    drawExpression = "%s>>%s"%(variable, histName)
    if isData:
        tree.Draw(drawExpression, selection)
    else:
        tree.Draw(drawExpression, "(%s)*(%s)"%(weight,selection))
      
    temph = ROOT.gDirectory.Get(histName)
    temph.Sumw2()

    temph.Write(histName, ROOT.TObject.kOverwrite)

# Main function that a given pool process runs, the input TTree is opened
# and the list of requested histograms are drawn to the output ROOT file
def processFile(outputDir, inputDir, year, proc, stub, histograms, treeName):

    try:
        inFileName = "%s/%s_%s.root"%(inputDir, year, stub)
        infile = ROOT.TFile.Open(inFileName.replace("/eos/uscms/", "root://cmseos.fnal.gov///"),  "READ"); infile.cd()
        if infile == None:
            print("Could not open input ROOT file \"%s\""%(inFileName))
            return

        trees = {""        : infile.Get(treeName),
                 "JECUp"   : infile.Get(treeName + "JECup"),
                 "JECDown" : infile.Get(treeName + "JECdown"),
                 "JERUp"   : infile.Get(treeName + "JERup"),
                 "JERDown" : infile.Get(treeName + "JERdown"),
        }

        for flag in ["pass", "fail"]:

            outfile = ROOT.TFile.Open("%s/%s_%s.root"%(outputDir, proc, flag), "RECREATE")

            isData = "Data" in proc
            for histName, histOps in histograms.items():
                if proc not in histName: continue
                if flag not in histName: continue

                syst = histName.split("_")[-1]

                treeSyst = ""
                if "JE" in syst:
                    treeSyst = syst

                nameToPass = proc
                if syst != "":
                    nameToPass = proc + "_" + syst
                elif proc == "JetHT" or proc == "SingleMuon":
                    nameToPass = "data_obs"

                makeNDhisto(year, nameToPass, histOps, outfile, trees[treeSyst], isData)

            outfile.Close()
    except Exception as e:
        print(e)

def makeDatacard(outputDir, processes, systematics, measure, year):

    card = open("%s/sf.txt"%(outputDir), "w")

    # Do not need data in this list
    if "JetHT"      in processes: processes.pop("JetHT")
    if "SingleMuon" in processes: processes.pop("SingleMuon")

    nprocesses = len(processes.keys())

    fpass = ROOT.TFile.Open("%s/top_mass_pass.root"%(outputDir), "READ")
    ffail = ROOT.TFile.Open("%s/top_mass_fail.root"%(outputDir), "READ")

    hobs_pass = fpass.Get("data_obs")
    hobs_fail = ffail.Get("data_obs")

    card.write("imax 2  number of channels\n")
    card.write("jmax %d  number of backgrounds\n"%(nprocesses-1))
    card.write("kmax *  number of nuisance parameters (sources of systematical uncertainties)\n\n")
    card.write("------------\n\n")
    card.write("shapes  *  pass   " + "top_mass_pass.root  $PROCESS $PROCESS_$SYSTEMATIC\n")
    card.write("shapes  *  fail   " + "top_mass_fail.root  $PROCESS $PROCESS_$SYSTEMATIC\n\n")
    card.write("------------\n\n")
    card.write("bin             pass           fail\n")
    card.write("observation     " + str(hobs_pass.Integral(1,hobs_pass.GetNbinsX())).ljust(15) + str(hobs_fail.Integral(1,hobs_fail.GetNbinsX())) + "\n\n")
    card.write("------------\n\n")

    adjustlead = 16
    adjust = 12

    passfailspace = "    "

    binline   = ["bin".ljust(adjustlead)]
    pnameline = ["process".ljust(adjustlead)]
    pinstline = ["process".ljust(adjustlead)]
    rateline  = ["rate".ljust(adjustlead)]
    pinst = 0
    for proc in processes.keys():
        hpass = fpass.Get(proc)
        pnameline.append(proc.ljust(adjust))
        pinstline.append(str(pinst).ljust(adjust))
        rateline.append(str("%.3f"%hpass.Integral(1,hpass.GetNbinsX())).ljust(adjust))
        binline.append("pass".ljust(adjust))
        pinst += 1
    pnameline.append(passfailspace)
    pinstline.append(passfailspace)
    rateline.append(passfailspace)
    binline.append(passfailspace)
    pinst = 0
    for proc in processes.keys():
        hfail = ffail.Get(proc)
        pnameline.append(proc.ljust(adjust))
        pinstline.append(str(pinst).ljust(adjust))
        rateline.append(str("%.3f"%hfail.Integral(1,hfail.GetNbinsX())).ljust(adjust))
        binline.append("fail".ljust(adjust))
        pinst += 1
    
    binline.append("\n")
    pnameline.append("\n")
    pinstline.append("\n")
    rateline.append("\n")

    card.write("".join(binline))
    card.write("".join(pnameline))
    card.write("".join(pinstline))
    card.write("".join(rateline))
    card.write("\n------------\n\n")

    lumiSystVal = 1.012
    if year == 2017:
        lumiSystVal = 1.023
    elif year == 2018:
        lumiSystVal = 1.025

    lumiline = ["lumi".ljust(adjustlead/2), "lnN".ljust(adjustlead/2)]
    
    for iproc in range(len(processes.keys())):
        lumiline.append(str(lumiSystVal).ljust(adjust))
    lumiline.append(passfailspace)
    for iproc in range(len(processes.keys())):
        lumiline.append(str(lumiSystVal).ljust(adjust))
    lumiline.append("\n")
    card.write("".join(lumiline))

    for syst in systematics:
        if syst == "": continue

        # Use Up version as syst name while stripping up/down
        if "Down" in syst: continue

        systName = syst.replace("Up", "")

        systline = [systName.ljust(adjustlead/2), "shape".ljust(adjustlead/2)]

        for iproc in range(len(processes.keys())):
            systline.append(str(1).ljust(adjust))
        systline.append(passfailspace)
        for iproc in range(len(processes.keys())):
            systline.append(str(1).ljust(adjust))
        systline.append("\n")
        card.write("".join(systline))

    card.write("\n*  autoMCStats  0\n")

def makeCombineScript(outputDir, processes, year):

    script = open("%s/runfits.sh"%(outputDir), "w")

    categories = ",".join(processes.keys())

    script.write("echo \"Do tag and probe\"\n")
    script.write("text2workspace.py -m 173.2 -P HiggsAnalysis.CombinedLimit.TagAndProbeModel:tagAndProbe sf.txt --PO categories=%s\n\n"%(categories))
    script.write("echo \"Do the MultiDimFit\"\n")
    script.write("combine -M MultiDimFit -m 173.2 sf.root --algo=singles --robustFit=1 --cminDefaultMinimizerTolerance 5.\n\n")
    script.write("echo \"Run the FitDiagnostics\"\n")
    script.write("combine -M FitDiagnostics -m 173.2 sf.root --saveShapes --saveWithUncertainties --robustFit=1 --cminDefaultMinimizerTolerance 5.\n\n")

    script.close()

    os.system("chmod +x %s/runfits.sh"%(outputDir))

if __name__ == "__main__":
    usage = "%makeInputsAndCards [options]"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument("--inputDir",  dest="inputDir",  help="Path to ntuples",    required=True                   )
    parser.add_argument("--outputDir", dest="outputDir", help="storing combine",    required=True                   )
    parser.add_argument("--tree",      dest="tree",      help="TTree name to draw", default="AnaSkim"               )
    parser.add_argument("--year",      dest="year",      help="which year",         default="Run2UL"                )
    parser.add_argument("--options",   dest="options",   help="options file",       default="makeInputsAndCards_aux")
    parser.add_argument("--measure",   dest="measure",   help="Eff or mis measure", required=True)
    parser.add_argument("--tagger",    dest="tagger",    help="Which tagger",       required=True)
    parser.add_argument("--ptBin",     dest="ptBin",     help="top pt bin",         default="inclusive")

    args = parser.parse_args()
    
    # The auxiliary file contains many "hardcoded" items
    # describing which histograms to get and how to draw
    # them. These things are changed often by the user
    # and thus are kept in separate sidecar file.
    importedGoods = __import__(args.options)

    processes, histograms, systematics = importedGoods.initHistos(args.year, args.measure, args.tagger, args.ptBin)
    
    for hname, ops in histograms.items():
        print(hname, ops)

    inputDir  = args.inputDir
    treeName  = args.tree
    year      = args.year
    
    base = os.getenv("PWD")
    
    # The draw histograms and their host ROOT files are kept in the output
    # folder in the user's condor folder. This then makes running a plotter
    # on the output exactly like running on histogram output from an analyzer

    ptBinStr = ""
    if args.ptBin != "inclusive":
        ptBinStr = "_topPt%s"%(args.ptBin)
            
    outputDir = "%s/%s/%s_inputs_%s_%s%s/"%(base,args.outputDir,args.year,args.measure,args.tagger,ptBinStr)
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    # For speed, histogramming for each specified physics process, e.g. TT, QCD
    # is run in a separate pool process. This is limited to 4 at a time to avoid abuse
    manager = mp.Manager()
    pool = mp.Pool(processes=min(4, len(processes)))
    
    # The processFile function is attached to each process
    for proc, stub in processes.items():
        pool.apply_async(processFile, args=(outputDir, inputDir, year, proc, stub, histograms, treeName))
    
    pool.close()
    pool.join()

    os.system("hadd -f %s/top_mass_pass.root %s/*_pass.root >> %s/python.log 2>&1"%(outputDir, outputDir, outputDir))
    os.system("hadd -f %s/top_mass_fail.root %s/*_fail.root >> %s/python.log 2>&1"%(outputDir, outputDir, outputDir))
    os.system("rm %s/[A-Z]*_{fail,pass}.root >> %s/python.log"%(outputDir, outputDir))

    makeDatacard(outputDir, processes, systematics, args.measure, year)

    makeCombineScript(outputDir, processes, year)
