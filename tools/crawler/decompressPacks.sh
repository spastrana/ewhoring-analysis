#!/usr/local/bin/bash

datasetDir='../../files/images/packs/'
subdirs=$( ls ${datasetDir})
for dir in $subdirs; do
	files=$( ls ${datasetDir}/${dir})
	cd ${datasetDir}/${dir}
	for file in $files; do
		fileType=`file $file | cut -d " " -f 2`
		if [[ "${fileType}" == "RAR" ]];then
			echo "Unpacking RAR ${dir}/${file}"
			unrar x -ad ${file} 
		elif [[ "${fileType}" == "Zip" ]];then
	        	echo "Unpacking ZIP ${dir}/${file}"
			unzip $file -d "${file%.*}"
		elif [[ "${fileType}" == "7-zip" ]];then
			echo "Unpacking 7-zip ${dir}/${file}"
			7z x $file -o"${file%.*}"
		else
			echo "No pack: ${dir}/${file},[${fileType}]"
		fi;

	done
done
