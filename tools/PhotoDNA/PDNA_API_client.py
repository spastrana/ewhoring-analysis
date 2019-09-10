########### Python 2.7 #############

"""
This script serve as client for the PhotoDNA API Client
"""



import httplib, urllib, base64
import imghdr
from datetime import datetime
import json
import os
import time
import csv
import sys

tsFormat='%Y%m%d_%H%M%S'

# -------------GLOBAL VARIABLES-----------------
INPUT_DIR='write/here/the/path/to/the/images'
OUTPUT_FILE='write/here/the/output/file/in/csv/format.csv'
SUBSCRIPTION_KEY='REPLACE_WITH_PDNA_SUBSCRIPTION_KEY'



def queryImage(filename,imgType,conn):
	"""
	Sends a request to the API from PhotoDNA for a given file and a given imgType. 
	The connection is passed as arguments
	"""
	f = open(filename, "rb")
	body = f.read()
	f.close()
	headers = {
		# Request headers
		'Content-Type': 'image/%s'%imgType,
		'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY
	}
	params = urllib.urlencode({
		# Request parameters
		'enhance': 'true',
	})
	try:
		conn.request("POST", "/photodna/v1.0/Match?%s" % params, body, headers)
		response = conn.getresponse()
		data = response.read()
		return data
	except Exception as e:
		print("%s ERROR Requesting %s: %s-%s"%(datetime.now().strftime(tsFormat),filename,e.__class__.__name__,str(e)))
		return None


def queryImagesFromDirectory(dirName,outputFile,verbose=True):
	"""
	Queries the PhotoDNA API for all the images in dirName (and its subdirectories).
	Outputs a CSV file with the following fields:
		path,image_type,response_code,trackingID,isMatch,matchString

		here matchString will contain all the labels for matched images in form source(violation), separated by a /. E.g. IWF(B2)/NMEC(B1)

	To avoid re-quering the API, it does not process twice images that have been already processed
	"""
	try:
		conn = httplib.HTTPSConnection('uk-api.microsoftmoderator.com')
	except:
		print("%s ERROR Connecting to API (%s-%s)"%(datetime.now().strftime(tsFormat),e.__class__.__name__,str(e)))
	alreadyProcessed=[]
	if os.path.exists(outputFile):
		reader = csv.reader(open(outputFile, 'r'), dialect='excel', delimiter=',', quotechar='"')
		for row in reader:
			alreadyProcessed.append(row[0])
	for root,subdirs,files in os.walk(dirName):
		for filename in files:
			path=root+"/"+filename
			if not path.replace('"','[DQ]') in alreadyProcessed:
				if verbose: print "%s INFO Processing File %s"%(datetime.now().strftime(tsFormat),path)
				fd=open(outputFile,'a+')
				imgType=imghdr.what(path)
				totaltime=0
				# imghdr sometimes fails to fetch the image type. In these cases, we use the extension
				if not imgType and (not 'MACOS' in filename and ('jpeg' in filename or 'png' in filename or 'jpg' in filename or 'bmp' in filename or 'gif' in filename)):
					imgType=path[path.rfind('.')+1:]
					if imgType=='jpg': imgType='jpeg'
				if imgType:
					try:
						response=queryImage(path,imgType,conn)
						if not response: continue
						jResponse=json.loads(response)
						code=jResponse['Status']['Code']
						isMatch=bool(jResponse['IsMatch'])
						trackingID=jResponse['TrackingId']
						if isMatch:
							matches=jResponse['MatchDetails']['MatchFlags']
							matchString=""
							for match in matches:
								source=match["Source"]
								violations='/'.join(match['Violations'])
								matchString+="%s(%s)/"%(source,violations)
							# For the CSV format, replace all double quotes from the path with the [DQ] keyword
							fd.write('"%s",%s,%s,%s,TRUE,"%s"\n'%(path.replace('"','[DQ]'),imgType,code,trackingID,matchString))
						else:
							# For the CSV format, replace all double quotes from the path with the [DQ] keyword
							fd.write('"%s",%s,%s,%s,FALSE\n'%(path.replace('"','[DQ]'),imgType,code,trackingID))
						# Rate limit is 5 queries per second, so sleep between queries
						time.sleep(0.12)
					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
						if verbose: print "%s ERROR Processing file %s. %s:%s (%s, line %s)"%(datetime.now().strftime(tsFormat),path,e.__class__.__name__,str(e),fname,exc_tb.tb_lineno)
						fd.write('"%s",ERROR\n'%(path.replace('"','[DQ]')))
				else:
					fd.write('"%s",NOT_IMAGE\n'%(path.replace('"','[DQ]')))
				fd.close()
			else:
				if verbose: print "%s INFO File %s already processed"%(datetime.now().strftime(tsFormat),path)
		for subdir in subdirs:
			queryImagesFromDirectory(subdir,outputFile)			




queryImagesFromDirectory(INPUT_DIR,OUTPUT_FILE)

