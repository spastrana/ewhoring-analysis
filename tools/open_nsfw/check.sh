#!/usr/local/bin/bash

# This script processes the images from a directory and obtains its NSFW score and OCR using Yahoo open_nsfw and tesseract respectively
# Path to images
datasetDir='../../files/images/proofOfEarnings/'

# Desired output file
outputFile='../../files/proofOfEarnings_nsfw_word_detection.csv'

# Path to the Yahoo open_nsfw code/model 
pathOpenNSFW='../../tools/open_nsfw/'

#Gets the directories
subdirs=$( ls ${datasetDir})

for dir in $subdirs; do
	
	cd ${datasetDir}/${dir}
	find . -type f > tmpfile
	IFS=$'\r\n' GLOBIGNORE='*' command eval  'files=($(cat tmpfile))'
	rm tmpfile
	for file in "${files[@]}"; do
		completePath="${datasetDir}/${dir}/${file:2}"
		compare=`echo ${completePath} | sed 's/\[/\\\[/g' | sed 's/\]/\\\]/g'`
		grep "${compare}" ${outputFile} &> /dev/null
		if (( $? > 0 ));then
			fileType=`file "${completePath}" | cut -d ":" -f 2 | cut -d " " -f 2`
			if [ "${fileType}" == "JPEG" ] || [ "${fileType}" == "PNG" ] || [ "${fileType}" == "GIF" ];then
				
				# Get the NSFW score
				python ${pathOpenNSFW}classify_nsfw.py --model_def  ${pathOpenNSFW}nsfw_model/deploy.prototxt --pretrained_model ${pathOpenNSFW}nsfw_model/resnet_50_1by2_nsfw.caffemodel "${completePath}" &> tmp 
				nsfw_score=`tail -n 1 tmp | cut -d ":" -f 2`
				
				# Get the OCR value
				tesseract "${completePath}" tmp &> /dev/null
				numWords=`wc -w tmp.txt | cut -d 't' -f 1`
				echo "${completePath}",${nsfw_score//[[:blank:]]/},${numWords//[[:blank:]]/} >> ${outputFile}

				rm tmp.txt
			else
				echo "${completePath}","NOT_IMAGE_FILE","${fileType}" >> ${outputFile}
			fi
		fi
	done
done
