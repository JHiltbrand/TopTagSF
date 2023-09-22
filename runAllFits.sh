#!/bin/bash

OUTPUTDIR=$1

mkdir -p ${OUTPUTDIR}

MAKEINPUTS=$2

RUNCOMBINE=$3

if [ ${MAKEINPUTS} -eq 1 ]
then
    YEARS=("2016preVFP")
    #"2016postVFP" "2017" "2018")
    
    #TAGGERS=("Mrg" "Res")
    TAGGERS=("Res")
    
    MEASURES=("Eff" "Mis")

    for YEAR in "${YEARS[@]}"
    do
        for TAGGER in "${TAGGERS[@]}"
        do 
            PTBINS=("inclusive")
            if [ ${TAGGER} == "Mrg" ]
            then
                PTBINS=("400to480" "480to600" "600to1200")
            elif [ ${TAGGER} == "Res" ]
            then
                #PTBINS=("0to100" "100to150" "150to200" "200to300" "300to400" "400to1200")
                PTBINS=("0to100")
            fi

            for PTBIN in "${PTBINS[@]}"
            do
                for MEASURE in "${MEASURES[@]}"
                do
                    echo "Making input histograms and data cards for year:${YEAR}, measure:${MEASURE}, tagger:${TAGGER}..."
                    python makeInputsAndCards.py --inputDir /uscmst1b_scratch/lpc1/3DayLifetime/jhiltbra/TopTagSkims_hadd/ --outputDir ${OUTPUTDIR} --tree TopTagSkim --year ${YEAR} --measure ${MEASURE} --tagger ${TAGGER} --ptBin ${PTBIN} >> ${OUTPUTDIR}/makeInputsAndCards.log 2>&1
                done
            done
        done
    done
fi

if [ ${RUNCOMBINE} -eq 1 ]
then
    STARTDIR=`pwd`
    for JOBDIR in ${OUTPUTDIR}/*
    do
        if [ -f ${JOBDIR} ]
        then
            continue
        fi

        cd ${JOBDIR}
        echo "Running combine fits for ${JOBDIR}..."
        ./runfits.sh >> combine.log 2>&1 &
        cd ${STARTDIR}
    done
fi
