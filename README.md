#  TopTagSF

Code to calculate top tagging SFs using templates and combine

## Setting up Working Area

The current work flow is based on Combine v9, so the following commands can be followed to setup the working area

```
cmsrel CMSSW_11_3_4
cd CMSSW_11_3_4/src
cmsenv
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
cd HiggsAnalysis/CombinedLimit

git fetch origin
git checkout v9.1.0
scram b clean
scram b -j4
```

## Creating Combine Inputs and Data Cards

The script `makeInputsAndCards.py` script reads simple TTrees from ROOT files (in this case created by the `MakeTopTagTree` analyzer) and performs TTree->Draw() commands to make histograms to be input to combine. The sidecar file `makeInputsAndCards.py` is used to customize what variable is histogrammed as well as any selections to apply during the draw. The options to this script are as follows:

```
usage: %makeInputsAndCards [options] [-h] --inputDir INPUTDIR --outputDir
                                     OUTPUTDIR [--tree TREE] [--year YEAR]
                                     [--options OPTIONS] --measure MEASURE
                                     --tagger TAGGER [--ptBin PTBIN]

optional arguments:
  -h, --help            show this help message and exit
  --inputDir INPUTDIR   Path to ntuples
  --outputDir OUTPUTDIR
                        storing combine
  --tree TREE           TTree name to draw
  --year YEAR           which year
  --options OPTIONS     options file
  --measure MEASURE     Eff or mis measure
  --tagger TAGGER       Which tagger
  --ptBin PTBIN         top pt bin
```

An example running of this script could be

```
python makeInputsAndCards.py --inputDir /some/dir/to/root/files/ --tree TopTagSkim --year 2016preVFP --outputDir TEST --measure Eff --tagger Res --ptBin 100to200
```

Executing this command will create a subdirectory in the working area called `TEST` with a subfolder `2016preVFP_inputs_Eff_Res_ptBin100to200`, which will contain two ROOT files (`top_mass_{pass,fail}.root`) with all relevant input histograms, a datacard (sf.txt), and a shell script to run necessary combine commands (runfits.sh).

## Generating Final Results

The script `runAllFits.sh` is provided to run the `makeInputAndCards.py` in bulk as well as run the `runfits.sh` for combination of tagger, SF measurement, year, and top pt bin. The first argument to the script is the directory specified to `makeInputsAndCards.py` while the second and third arguments are switches to allow separating of making inputs and just running combine.

An example of running would be

``runAllFits.sh TEST 0 1``

Where the arguments denote that combine inputs are located in the `TEST` folder already (no need to make them) and to run the combine wrapper script in each of the individual combine directories inside `TEST`

## Plotting Results

The main plotting script is `makeSummaryPlots.py` with the following arguments

```
usage: usage: %makeSummaryPlots [options] [-h] --year YEAR --inputDir INPUTDIR
                                   --outputDir OUTPUTDIR [--approved]

optional arguments:
  -h, --help            show this help message and exit
  --year YEAR           year to process
  --inputDir INPUTDIR   area with fit results
  --outputDir OUTPUTDIR
                        where to put plots
  --approved            plots approved
```
 
In this case, referring to the previous example, the input directory to the plotting script would be `TEST`.
