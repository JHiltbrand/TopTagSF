#!/bin/bash

INPUTDIR=
OUTPUTDIR=
MAKEINPUTS=true
RUNCOMBINE=true
YEARS=("2016preVFP" "2016postVFP" "2017" "2018")
TAGGERS=("Mrg" "Res")
MEASURES=("Eff" "Mis")
PTBINS=()
DOSYST=true

while [[ $# -gt 0 ]]
do
    case "$1" in
        --inputDir)
            INPUTDIR="$2"
            shift 2
            ;;
        --outputDir)
            OUTPUTDIR="$2"
            shift 2
            ;;
        --doImpacts)
            RUNIMPACTS=true
            shift
            ;;
        --makeInputs)
            MAKEINPUTS=true
            shift
            ;;
        --runCombine)
            RUNCOMBINE=true
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
            DOSYSTS=true
            shift
            ;;
        *)
            exit 1
            ;;
    esac
done

if [ "${MAKEINPUTS}" == true ]
then
    echo "Making combine inputs..."
    mkdir -p ${OUTPUTDIR}

    for YEAR in "${YEARS[@]}"
    do
        for TAGGER in "${TAGGERS[@]}"
        do 
            UNIQUEPTBINS=()
            if [ ${#PTBINS[@]} -eq 0 ]
            then
                if [ ${TAGGER} == "Mrg" ]
                then
                    UNIQUEPTBINS=("400to480" "480to600" "600to1200")
                elif [ ${TAGGER} == "Res" ]
                then
                    UNIQUEPTBINS=("0to200" "200to400" "400to1200")
                else
                    UNIQUEPTBINS=("${PTBINS[@]}")
                fi
            fi

            for PTBIN in "${UNIQUEPTBINS[@]}"
            do
                for MEASURE in "${MEASURES[@]}"
                do
                    echo "Making input histograms and data cards for year:${YEAR}, measure:${MEASURE}, tagger:${TAGGER}, pt:${PTBIN}..."
                    if [ "${DOSYSTS}" == true ]
                    then
                        python makeInputsAndCards.py --inputDir ${INPUTDIR}/${YEAR} --outputDir ${OUTPUTDIR} --tree TopTagSkim --year ${YEAR} --measure ${MEASURE} --tagger ${TAGGER} --ptBin ${PTBIN} --doSysts >> ${OUTPUTDIR}/makeInputsAndCards.log 2>&1
                    else
                        python makeInputsAndCards.py --inputDir ${INPUTDIR}/${YEAR} --outputDir ${OUTPUTDIR} --tree TopTagSkim --year ${YEAR} --measure ${MEASURE} --tagger ${TAGGER} --ptBin ${PTBIN} >> ${OUTPUTDIR}/makeInputsAndCards.log 2>&1
                    fi                      
                done
            done
        done
    done
fi

if [ "${RUNCOMBINE}" == true ]
then
    STARTDIR=`pwd`
    for JOBDIR in ${OUTPUTDIR}/*
    do
        if [[ -f ${JOBDIR} ]]
        then
            continue
        fi

        cd ${JOBDIR}
        echo "Running combine fits for ${JOBDIR}..."
        if [[ "${RUNIMPACTS}" == true ]]
        then
            ./runfits.sh 1 >> combine.log 2>&1
        else
            ./runfits.sh 0 >> combine.log 2>&1
        fi
        cd ${STARTDIR}
    done
fi
