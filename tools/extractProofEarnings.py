import getpass
import psycopg2
import socket
import pickle
import sys
import csv
import os
import re
from datetime import datetime
import operator
import random

reload(sys)  
sys.setdefaultencoding('utf-8')


tsFormat='%Y%m%d_%H%M%S'

DB_NAME='crimebb'
OUTPUT_DIR ='../files/'



image_sites=['imgur',
			'gyazo',
			'postimg',
			'postimage',
			'photobucket',
			'imageshack',
			'imagebanana',
			'prnt',
			'sendspace',
			'screencloud',
			'minus',
			'directupload',					
			'auplod',
			'imagetwist',
			'imgup',
			'imagezilla',
			'noelshack',
			'imgbox',
			'imagebam',
			'imgchili']

keywords_content=['earn',
				  'profit',
				  'money',
				  'gain']
def isImageURL(url):
	for s in image_sites:
		if s in url.lower():
			return True
	return (".jpg" in url.lower() or ".png" in url.lower() or ".gif" in url.lower() or ".tiff" in url.lower())

def checkDuplicate(url,processedURLs):
	for processedURL,post,position in processedURLs:
		if url==processedURL:
			return(post,position)
	return (-1,-1)
# This method tries to infer the site being encoded in a URL. e.g. s30.#.org/el35uskyp/32152161.png"
def get_url_encoded(url,content):
	for s in image_sites:
		if s in content.lower():
			return url.replace('.#.',".%s."%s)
	return url

filename=OUTPUT_DIR+'proofEarnings.csv'
filenameDuplicates=OUTPUT_DIR+'proofEarnings_duplicates.pickle'
processedPosts=[]
if os.path.exists(filename):
	lines=open(filename,'r').readlines()
	for line in lines:
		processedPosts.append(int(line.split(',')[1]))

orclauseImageSites='lower("Content") LIKE '
for i in range(0,len(image_sites)-1):
	orclauseImageSites+='\'%%%s%%\' OR lower("Content") LIKE '%image_sites[i]
orclauseImageSites+='\'%%%s%%\''%image_sites[i+1]

orclauseKeywordsContent='lower("Content") LIKE '
for i in range(0,len(keywords_content)-1):
	orclauseKeywordsContent+='\'%%%s%%\' OR lower("Content") LIKE '%keywords_content[i]
orclauseKeywordsContent+='\'%%%s%%\''%keywords_content[i+1]

connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
print ("%s Querying DB for URLs"%(datetime.now().strftime(tsFormat)))



filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
if not os.path.exists(filenameThreads):
	print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
	exit(-1)
data=pickle.load(open(filenameThreads))
posts=[]
for site in data:
	forums=[f for f in data[site] if not 'total' in str(f)]
	for forum in forums:
		for idThread in data[site][forum]:
			if not 'total' in str(idThread):
				heading=data[site][forum][idThread]
				if 'you make' in heading or 'earn' in heading or (forum==12 and site==0):
					query=('SELECT "Content","Thread","Author","IdPost","Site","Timestamp",(SELECT array_agg(i) FROM (SELECT (regexp_matches("Content",\'.://([^* \"\\[\\]\\n]*)\',\'g\'))[1] i) t) FROM "Post" WHERE "Thread"=%s AND (%s) AND "Site"=%s ORDER BY "IdPost" ASC'%(idThread,orclauseImageSites,site))	
				else:
					query=('SELECT "Content","Thread","Author","IdPost","Site","Timestamp",(SELECT array_agg(i) FROM (SELECT (regexp_matches("Content",\'.://([^* \"\\[\\]\\n]*)\',\'g\'))[1] i) t) FROM "Post" WHERE "Thread"=%s AND (%s) AND lower("Content") LIKE \'%%proof%%\' AND (%s) AND "Site"=%s ORDER BY "IdPost" ASC'%(idThread,orclauseImageSites,orclauseKeywordsContent,site))		
				cursor=connector.cursor()
				cursor.execute(query)
				postsForum=cursor.fetchall()
				if len(postsForum)>0:
					posts.extend(postsForum)
				cursor.close()
		print ("%s Processed Forum:%s from site:%s. Total Posts:%s"%(datetime.now().strftime(tsFormat),forum,site,len(posts)))




print ("%s Obtained %s posts in total"%(datetime.now().strftime(tsFormat),len(posts)))
print ("%s Already processed previously %s posts"%(datetime.now().strftime(tsFormat),len(processedPosts)))
fd=open(filename,'a+')
totalURLs=0
if not os.path.exists(filenameDuplicates):
	duplicates={}
else:
	duplicates=pickle.load(open(filenameDuplicates))
for content,idThread,author,idPost,site,Timestamp,URLs in posts:
	if not "%s-%s"%(site,idPost) in processedPosts:
		processedPosts.append("%s-%s"%(site,idPost))
		if URLs:
			urlsToPrint=[]
			for url in URLs:
				if ".#." in url:
					url=get_url_encoded(url,content)
				if (not url in urlsToPrint) and isImageURL(url) and (not "..." in url):
					urlsToPrint.append(url)		
						
			if len(urlsToPrint)>0:
				stringToPrint="%s,%s,%s,%s,%s,%s,"%(idThread,idPost,site,Timestamp.strftime("%Y-%m-%d"),author,len(urlsToPrint))
				for n,url in enumerate(urlsToPrint):
					if not url in duplicates.keys():
						totalURLs+=1
						fd.write(stringToPrint+"%s,\"%s\"\n"%(n+1,url))
						#duplicates[url]=[(idPost,n)]
						duplicates[url]=[("%s-%s"%(site,idPost),n+1)]
					else:
						duplicates[url].append(("%s-%s"%(site,idPost),n+1))
	
pickle.dump(duplicates,open(filenameDuplicates,'wb'))
fd.close()
outputFile=OUTPUT_DIR+'proofEarnings_duplicates.csv'
fd=open(outputFile,'w+')
totalDuplicates=0
for url in duplicates.keys():
	stringToPrint='"%s",'%url
	sites=[]
	if len(duplicates[url])>1:
		totalDuplicates+=1
		for (postSite,n) in duplicates[url][:-1]:
			site=postSite.split("-")[0]
			if len(sites)>0 and not site in sites:
				sites.append(site)
				print ("%s URL %s found in various sites: %s"%(datetime.now().strftime(tsFormat),url,duplicates[url]))
			else:
				sites.append(site)
			stringToPrint+="%s_%s/"%(postSite,n)
		(postSite,n) = duplicates[url][-1]
		site=postSite.split("-")[0]
		if len(sites)>0 and not site in sites:
			sites.append(site)
			print ("%s URL %s found in various sites: %s"%(datetime.now().strftime(tsFormat),url,duplicates[url]))
		else:
			sites.append(site)			
		stringToPrint+="%s_%s\n"%duplicates[url][-1]
		fd.write(stringToPrint)
fd.close()
print ("%s Extracted %s urls"%(datetime.now().strftime(tsFormat),totalURLs))
print ("%s Found %s duplicates"%(datetime.now().strftime(tsFormat),totalDuplicates))
