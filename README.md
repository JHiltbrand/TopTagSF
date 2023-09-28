#  TopTagSF

Standalone code to calculate top tagging SFs using template histograms and the tag and probe model in Higgscombine

## Setting up Working Area

The current work flow is based on Combine v9, so the following commands can be followed to setup the working area

```
cmsrel CMSSW_11_3_4
cd CMSSW_11_3_4/src
cmsenv
git clone git@github.com:cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
git clone git@github.com:cms-analysis/CombineHarvester.git

cd HiggsAnalysis/CombinedLimit

git fetch origin
git checkout v9.1.0
scram b clean
scram b -j4

cd ../..

git clone git@github.com:JHiltbrand/TopTagSF.git

cd TopTagSF

cp TagAndProbeExtended.py ../HiggsAnalysis/CombinedLimit/python
```

## Creating Combine Inputs and Data Cards

The `makeInputsAndCards.py` script reads simple TTrees from ROOT files (in this case created by the `MakeTopTagSFTree` analyzer) and performs TTree->Draw() commands to make histograms for input to combine. The sidecar file `makeInputsAndCards_aux.py` is used to customize what variable is histogrammed for which physics processes as well as any selections to apply during the draw. The options to this script are as follows:

```
usage: %makeInputsAndCards [options] [-h] --inputDir INPUTDIR --outputDir
                                     OUTPUTDIR [--tree TREE] [--year YEAR]
                                     [--options OPTIONS] --measure MEASURE
                                     --tagger TAGGER [--ptBin PTBIN]
                                     [--doSysts]

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
  --doSysts             include systs
```

An example running of this script could be:

```
python makeInputsAndCards.py --inputDir /some/dir/to/root/files/ --tree TopTagSkim --year 2016preVFP --outputDir TEST --measure Eff --tagger Res --ptBin 100to200 --doSysts
```

Executing this command will create a subdirectory in the working area called `TEST` with a subfolder `2016preVFP_inputs_Eff_Res_topPt100to200`, which will contain two ROOT files (`top_mass_{pass,fail}.root`) with all relevant input histograms specified in the sidecar file, a data card (sf.txt), and a shell script to wrap all necessary combine commands (`runfits.sh`).

## Generating Final Results

The script `runAllFits.sh` is provided to run the `makeInputsAndCards.py` in bulk as well as run the `runfits.sh` for every combination of tagger, SF measurement type, year, and top pt bin. The first argument to the script is the output directory specified to `makeInputsAndCards.py` while the second and third arguments are switches to allow separating of making inputs and just running combine on pre-existing inputs.

An example of running would be:

``runAllFits.sh --inputDir /some/dir/to/root/files/ --outputDir TEST --makeInputs --runCombine --taggers Mrg Res --measures Mis Eff``

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
 
In this case, referring to the previous example, the input directory to the plotting script would be `TEST`. For each SF measurement, pre- and post-fit plots are created. Additionally, a summary plot is made to show all efficiency scale factors and mistag scale factors.
