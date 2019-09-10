from pytineye import *
from collections import defaultdict
import pickle
from datetime import datetime
import os
import sys
import psycopg2
import socket
import operator

tsFormat='%Y%m%d_%H%M%S'

## Use these for testing purposes ###
## From Tineye: "The key used is the sandbox key, so you can copy and paste these examples to try them without using up your own searches"
PUBLIC_KEY='requestToTineye'
PRIVATE_KEY='requestToTineye'

IMAGE_DIR='../files/images/tineyeRequests/packs/'
# IMAGE_DIR='../files/PhotoDNA_matched/'
METADATA_PACKS_FILE='../files/images/tineyeRequests/metadataPacks.pickle'

# GET ONLY 10 MATCHES IS THEIR SCORE IS LESS THAN 20
THRESHOLD_SCORE_MATCHES=20
MAX_MATCHES=10

api = TinEyeAPIRequest('http://api.tineye.com/rest/', PUBLIC_KEY, PRIVATE_KEY)


def searchImageByPath(path):
	print "%s INFO Searching for image %s"%(datetime.now().strftime(tsFormat),path)
	try:
		fp = open(path, 'rb')
	except IOError as err:
		return "%s ERROR Reading image %s from disk . %s"%(datetime.now().strftime(tsFormat),path,str(err).replace('\n',' '))
	data = fp.read()
	try:
		response=api.search_data(data=data,limit=-1)
	except TinEyeAPIError as err:
		fp.close()
		return "%s ERROR Searching for image %s. %s"%(datetime.now().strftime(tsFormat),path,str(err).replace('\n',' '))
	fp.close()
	return response

def processResponse(responsePath,outputFileText,showScreen=False,verbose=False):
	if not showScreen:
		fd=open(outputFileText,'wb')
	else:
		fd=sys.stdout
	if verbose:
		print "%s INFO Reading response from file %s "%(datetime.now().strftime(tsFormat),responsePath)
	response=pickle.load(open(responsePath))
	if isinstance(response,TinEyeResponse):
		#fd.write("Response report for %s. Found %s matches\n"%(responsePath[responsePath.rfind('/')+1:],len(response.matches)))
		fileName=responsePath[responsePath.rfind('/')+1:]
		numMatches=0
		domains=[]
		numDomains=0
		for c,match in enumerate(response.matches):
			if numMatches<MAX_MATCHES or match.score>THRESHOLD_SCORE_MATCHES:
				numMatches+=1
				if not match.domain.encode('utf-8') in domains:
					numDomains+=1
					domains.append(match.domain.encode('utf-8'))
				fd.write("-----MATCH %s/%s ----\n"%(c+1,len(response.matches)))
				fd.write("URL: %s\n"%match.image_url.encode('utf-8'))
				fd.write("Overlay: %s\n"%match.overlay.encode('utf-8'))
				fd.write("Score: %s\n"%match.score)
				fd.write("File %s Domain %s N=%s\n"%(responsePath.replace(" ","_"),match.domain.encode('utf-8'),numDomains))
				fd.write("Found %s LINKS:\n"%len(match.backlinks))
				for cl,link in enumerate(match.backlinks):
					fd.write("\t[%s/%s] URL: %s\n"%(cl+1,len(match.backlinks),link.url.encode('utf-8')))
					fd.write("\t[%s/%s] BACKLINK: %s\n"%(cl+1,len(match.backlinks),link.backlink.encode('utf-8')))
					fd.write("\t[%s/%s] CRAWL DATE:%s\n"%(cl+1,len(match.backlinks),link.crawl_date))
				fd.write("\n")
		#fd.write("Showed %s matches that were above the threshold %s\n"%(numMatches,THRESHOLD_SCORE_MATCHES))
	else:
		if verbose:
			print "%s INFO Erroneous response. Log message was [%s] "%(datetime.now().strftime(tsFormat),response)
	if not showScreen:
		fd.close()

def processImage(inputFile):
	response=searchImageByPath(inputFile)
	outputFileRaw=inputFile[:inputFile.rfind('.')]+'.trespraw'
	outputFileText=inputFile[:inputFile.rfind('.')]+'.tresptxt'
	pickle.dump(response,open(outputFileRaw,'wb'))
	if isinstance(response,TinEyeResponse):
		print "%s INFO Response received. Found %s matches. Saving raw to %s and text info to %s"%(datetime.now().strftime(tsFormat),len(response.matches),outputFileRaw,outputFileText)
		processResponse(outputFileRaw,outputFileText,verbose=False)
	else:
		print response
	
def queryImagesFromDirectory(dirName):
	files=os.listdir(dirName)
	for f in files:
		path=dirName+f
		if not f.endswith('.trespraw') and not f.endswith('.tresptxt'):
			if not f[:f.rfind('.')]+'.trespraw' in files:
				processImage(path)
			else:
				print "%s INFO Image %s already processed by TineEye"%(datetime.now().strftime(tsFormat),path)
def processResponsesFromDirectory(dirName,showScreen=True):
	files=os.listdir(dirName)
	for f in files:
		path=dirName+f
		if f.endswith('.trespraw'):
			processResponse(path,None,showScreen=True)

queryImagesFromDirectory(IMAGE_DIR)
