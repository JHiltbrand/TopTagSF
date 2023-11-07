#!/bin/bash

INPUTDIR=FAIL
OUTPUTDIR=FAIL
MAKEINPUTS=0
RUNCOMBINE=0
RUNIMPACTS=0
OVERWRITE=0
TREENAME=TopTagSFSkim
YEARS=("2016preVFP" "2016postVFP" "2017" "2018")
TAGGERS=("Mrg" "Res")
MEASURES=("Eff" "Mis")
PTBINS=()
DOSYSTS=0

RUNTIME=`date +"%Y%m%d_%H%M%S"`

while [[ $# -gt 0 ]]
do
    case "$1" in
        --treeName)
            TREENAME="$2"
            shift 2
            ;;
        --inputDir)
            INPUTDIR="$2"
            shift 2
            ;;
        --outputDir)
            OUTPUTDIR="$2"
            shift 2
            ;;
        --doImpacts)
            RUNIMPACTS=1
            shift
            ;;
        --makeInputs)
            MAKEINPUTS=1
            shift
            ;;
        --runCombine)
            RUNCOMBINE=1
            shift
            ;;
        --years)
            YEARS=()
            while [[ "$2" == *"20"* && $# -gt 1 ]]
            do
                YEARS+=("$2")
                shift
            done
            shift
            ;;
        --taggers)
            TAGGERS=()
            while [[ $2 != *"--"* && $# -gt 1 ]]
            do
                TAGGERS+=("$2")
                shift
            done
            shift
            ;;
        --measures)
            MEASURES=()
            while [[ $2 != *"--"* && $# -gt 1 ]]
            do
                MEASURES+=("$2")
                shift
            done
            shift
            ;;
        --ptBins)
            PTBINS=()
            while [[ $2 == *"to"* && $# -gt 1 ]]
            do
                PTBINS+=("$2")
                shift
            done
            shift
            ;;
        --doSysts)
            DOSYSTS=1
            shift
            ;;
        --overwrite)
            OVERWRITE=1
            shift
            ;;
        *)
            echo "Unknown option \"$1\""
            exit 1
            ;;
    esac
done

if [[ ${INPUTDIR} == "FAIL" && ${MAKEINPUTS} == 1 ]]
then
    echo "User must designate input directory to make inputs !"
    exit 1 
fi

if [[ ${OUTPUTDIR} == "FAIL" ]]
then
    echo "User must designate where outputs are located !"
    exit 1
fi

UNIQUEPTBINS=("${PTBINS[@]}")
if [[ ${MAKEINPUTS} == 1 ]]
then
    mkdir -p ${OUTPUTDIR}

    for YEAR in "${YEARS[@]}"
    do
        for TAGGER in "${TAGGERS[@]}"
        do 
            # If no pt bins are spec'd on the command line, assume standards based on tagger
            if [[ ${#PTBINS[@]} -eq 0 ]]
            then
                if [[ ${TAGGER} == "Mrg" ]]
                then
                    UNIQUEPTBINS=("400to480" "480to600" "600toInf")
                elif [[ ${TAGGER} == "Res" ]]
                then
                    UNIQUEPTBINS=("0to200" "200to400" "400toInf")
                fi
            fi

            for PTBIN in "${UNIQUEPTBINS[@]}"
            do
                for MEASURE in "${MEASURES[@]}"
                do
                    echo "Making input histograms and data cards for year:${YEAR}, measure:${MEASURE}, tagger:${TAGGER}, pt:${PTBIN}..."

                    SYSTSTR=""
                    if [[ ${DOSYSTS} == 1 ]]
                    then
                        SYSTSTR="--doSysts"
                    fi
                    
                    OVERWRITESTR=""
                    if [[ ${OVERWRITE} == 1 ]]
                    then
                        OVERWRITESTR="--overwrite"
                    fi

                    python makeInputsAndCards.py --inputDir ${INPUTDIR} --outputDir ${OUTPUTDIR} --tree ${TREENAME} --year ${YEAR} --measure ${MEASURE} --tagger ${TAGGER} --ptBin ${PTBIN} ${SYSTSTR} ${OVERWRITESTR} >> ${OUTPUTDIR}/makeInputsAndCards_${RUNTIME}.log 2>&1
                done
            done
        done
    done
fi

if [[ ${RUNCOMBINE} == 1 ]]
then
    STARTDIR=`pwd`
    for JOBDIR in ${OUTPUTDIR}/*
    do
        # Ignore any files, they are not a candidate job folder
        if [[ -f ${JOBDIR} ]]
        then
            continue
        fi
        for YEAR in "${YEARS[@]}"
        do
            for TAGGER in "${TAGGERS[@]}"
            do
                if [[ ${#PTBINS[@]} -eq 0 ]]
                then
                    if [[ ${TAGGER} == "Mrg" ]]
                    then
                        UNIQUEPTBINS=("400to480" "480to600" "600toInf")
                    elif [[ ${TAGGER} == "Res" ]]
                    then
                        UNIQUEPTBINS=("0to200" "200to400" "400toInf")
                    fi
                fi
                for MEASURE in "${MEASURES[@]}"
                do
                    for PTBIN in "${UNIQUEPTBINS[@]}"
                    do
                        if [[ ${JOBDIR} != *"${YEAR}"* || ${JOBDIR} != *"${TAGGER}"* || ${JOBDIR} != *"${MEASURE}"* || ${JOBDIR} != *"${PTBIN}"* ]]
                        then
                            continue
                            echo ${JOBDIR}
                        fi
                        cd ${JOBDIR}
                        echo "Running combine fits for ${JOBDIR}..."
                        ./runfits.sh ${RUNIMPACTS} >> combine.log 2>&1
                        cd ${STARTDIR}
                    done
                done
            done
        done
    done
fi
