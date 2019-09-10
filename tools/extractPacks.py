# coding=utf-8
import psycopg2
import pickle
import sys
import csv
import os
from urlparse import urlparse
from datetime import datetime
import getpass
import operator
import random
from collections import defaultdict
import pandas as pd

reload(sys)  # Reload does the trick!
sys.setdefaultencoding('utf-8')

# Format of timestamp
tsFormat='%Y%m%d_%H%M%S'


OUTPUT_DIR='../files/'


# This code requires a connection to the CrimeBB database
DB_NAME='crimebb'
connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)

image_sites=['imgur',
			'gyazo',
			'postimg',
			'postimage',
			'photobucket',
			'imageshack',
			'directupload',			
			'imagebanana',
			'prnt',
			'sendspace',
			'screencloud',
			'minus',
			'auplod',
			'imagetwist',
			'imgup',
			'imagezilla',
			'noelshack',
			'imgbox',
			'imagebam',
			'imgchili']

file_sharing_sites=['megabitload',
					'megafileupload',
					'mega',
					'filezilla',
					'mediafire',
					'2shared',
					'zippyshare',
					'gratisupload',
					'ge.tt',
					'wikisend',
					'dropbox',
					'drive.google',
					'googledrive',
					'uploadee',
					'filefactory',
					'filedropper',
					'depositfiles',
					'datafilehost',
					'file-upload',
					'fileups',
					'oron',
					'filesonic',
					'uploading',
					'rapidgator',
					'speedyshare',
					'uppit']


# Uses heuristics to determine whether a heading is offering a tutorial or not
def isTutorial(heading,content=None):
	tutorialKeywords=('tutorial', '[tut]','howto','definite guide','guide]','how-to')
	for k in tutorialKeywords:
		if k in heading.lower():
			return True
	return False

# Given a text, returns the number of key words/phrases related to questions and info requests
def checkKeyPhrasesQuestions(text):
	key_phrases=['[question]',
	'[help]',
	'need advice',
	'need',
	'needed',
	'wtb',
	'want to buy',
	'req',
	'request',
	'question',
	'looking for',
	'give me advice',
	'quick question',
	'question for',
	'i wonder whether',
	'i wonder if',
	'i\'m asking for',
	'general query',
	'general question',
	'i have a question',
	'i have a doubt',
	'help requested',
	'how to',
	'help please',
	'help with',
	'need help',
	'need a',
	'need some help',
	'help needed',
	'i want help',
	'help me',
	'seeking'
	]
	keyCount=0;
	for k in key_phrases:
		if k in text.lower():
			keyCount+=1
	return keyCount				

#Uses heuristics to estimate a score indicating whether this thread looks like a question
def getQuestionScore (text):
	questionScore=0
	questionScore+=checkKeyPhrasesQuestions(text)*2
	questionScore+=text.count('?')*2
	if 'question' in text:
		questionScore+=1	
	return questionScore


# Compares T.O.P. obtained through heuristics with those obtained from the ML classifier for a given site
# Then, combines both in a single file for each site and writes to disk
def compareTOP_Heuristics_Classifier(site,verbose=False):
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	cursor = connector.cursor()
	if site==0:
		siteName="HackfForums"
	else:
		query=('SELECT "Name" FROM "Site" WHERE "IdSite"=%s'%site)
		cursor.execute(query)
		siteName=cursor.fetchone()[0]
		cursor.close()	
	classifier=pickle.load(open('../files/TOP_Classifier_%s.pickle'%site))
	heuristics=pickle.load(open('../files/TOP_Heuristics_%s.pickle'%(site)))
	TOP_combined=[]
	heurNoClas=[t for t in heuristics if not t in classifier]
	classNoHeur=[t for t in classifier if not t in heuristics]
	both=[t for t in classifier if t in heuristics]
	totalClassifier=len(classifier)
	if verbose: 
		print ("%s. %s TOP obtained from heuristics"%(siteName,len(heuristics)))
		print ("%s. %s TOP obtained from classifier"%(siteName,totalClassifier))
		print ("%s. %s TOP obtained from heuristics but not from classifier"%(siteName,len(heurNoClas)))
		print ("%s. %s TOP obtained from classifier but not from heuristics"%(siteName,len(classNoHeur)))
		print ("%s. %s TOP obtained from both classifier and heuristics"%(siteName,len(both)))
	classifier.extend(heuristics)
	combined=list(set(classifier))
	if verbose: print ("%s. %s TOP obtained in total per site\n"%(siteName,len(combined)))

	pickle.dump(combined,open(OUTPUT_DIR+"TOP_%s.pickle"%site,'wb'))
	return totalClassifier,len(heuristics),len(both),len(combined)

# Compares T.O.P. obtained through heuristics with those obtained from the ML classifier for all the sites
# Then, combines both in a single file for each site and writes to disk
def combine_TOP_ML(verbose=False):
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	sites = [s for s in data.keys() in not 'total' in str(s)]

	classifier=0
	heuristics=0
	combined=0
	both=0
	for site in sites:
		totalClassifier,totalHeuristics,totalBoth,totalCombined=compareTOP_Heuristics_Classifier(site,verbose=verbose)
		classifier+=totalClassifier
		heuristics+=totalHeuristics
		combined+=totalCombined
		both+=totalBoth
	if verbose:
		print ("TOTAL THREADS BY CLASSIFIER %s"%classifier)
		print ("TOTAL THREADS BY HEURISTICS %s"%heuristics)
		print ("TOTAL THREADS BY BOTH %s"%both)
		print ("TOTAL THREADS COMBINED %s"%combined)


# Get the first post from all the TOP
def getPostsFromTOP(site,verbose=False):
	if os.path.exists(OUTPUT_DIR+'postsFromTOP_%s.pickle'%site):
		if verbose: print ("%s Reading TOP posts of site %s from disk"%(datetime.now().strftime(tsFormat),site))
		postsFromTOP=pickle.load(open(OUTPUT_DIR+'postsFromTOP_%s.pickle'%site))
	else:
		if verbose: print ("%s Querying DB to get the first post of each TOP in site %s"%(datetime.now().strftime(tsFormat),site))
		threads=pickle.load(open(OUTPUT_DIR+'TOP_%s.pickle'%site))
		count=0
		connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
		cursor=connector.cursor()
		postsFromTOP={}
		for thread in threads:
			# FOR SOME REASON, THESE THREADS BLOCK THE QUERY, AS THEY TAKE SO MUCH TIME
			#if not thread==5298214 and not thread==5640111:
			count+=1
			# Be Verbose
			if verbose and (count%1 == 0 or count==len(threads)):
				progress = round(count*100.0/len(threads),2)
				sys.stdout.write("%s Processing thread (ID: %s) %s/%s (%s %s) \r"%(datetime.now().strftime(tsFormat), thread,count,len(threads),progress,'%'))
				#sys.stdout.write("%s Processing thread %s/%s (%s %s) \r"%(datetime.now().strftime(tsFormat),count,len(threads),progress,'%'))
				sys.stdout.flush()			
			query=('SELECT "Post"."Content","Thread"."Heading","Thread"."Author","Post"."Author","IdPost","Timestamp",(SELECT array_agg(i) FROM (SELECT (regexp_matches("Content",\'.://([^* \"\\[\\]\\n]*)\',\'g\'))[1] i) t) FROM "Post","Thread" WHERE "Thread"=%s AND "IdThread"="Thread" AND "Post"."Site"=%s AND "Thread"."Site"="Post"."Site" ORDER BY "IdPost" ASC'%(thread,site))
			cursor.execute(query)
			post=cursor.fetchone()
			postsFromTOP[thread]=post
		if verbose:
			print (" ")
			print ()
			print ("%s Writing posts of site %s to disk"%(datetime.now().strftime(tsFormat),site))
		pickle.dump(postsFromTOP,open(OUTPUT_DIR+'postsFromTOP_%s.pickle'%site,'wb'))
		cursor.close()
		connector.close()	
	return postsFromTOP


# Extract URLS from T.O.P. that correspond with file sharing sites or has the an extension related to compression formats (e.g. .rar or .zip)
def extractPackLinksFromTOP(site,getTotal=True):
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	cursor=connector.cursor()
	query=('SELECT "URL" FROM "Site" WHERE "IdSite"=%s'%(site))
	cursor.execute(query)
	url=cursor.fetchone()[0]
	cursor.close()
	connector.close()
	netloc=urlparse(url).netloc
	postsFromTOP=getPostsFromTOP(site)
	sortedPosts=sorted(postsFromTOP.items(),key=operator.itemgetter(0))
	numUrls=0
	outputFile=OUTPUT_DIR+'fileLink_list_%s.csv'%site
	if os.path.exists(outputFile):
		print ("WARNING. Pack Links from TOP of site %s already processed"%site)
		return
	fd=open(outputFile,'wb')
	fd.write("Thread,Post,Timestamp,Author,totalURLsPost,urlPosition,URL\n")
	registry=dict((filesite,defaultdict(int)) for filesite in file_sharing_sites)
	if not os.path.exists(OUTPUT_DIR+'duplicatesFileLinks.pickle'):
		duplicates={}
	else:
		duplicates=pickle.load(open(OUTPUT_DIR+'duplicatesFileLinks.pickle'))
	for thread,post in sortedPosts:
		if post:
			content,heading,OPAuthor,author,idPost,Timestamp,URLs=post
			printedURLs=0
			year=int(Timestamp.strftime("%Y"))
			if URLs:
				URLs=set(URLs)
				urlsToPrint=[]
				for url in URLs:
					url=url.strip()
					if (not url in urlsToPrint) and (not netloc in url) and (not "..." in url):
						fileLink=False
						for fileSite in file_sharing_sites:
							if fileSite in url:
								fileLink=True
								registry[fileSite][year]+=1
								break;
						if (fileLink and not (".jpg" in url or ".png" in url or ".gif" in url)) or ('.zip' in url or '.rar' in url or 'tar.gz' in url or '.7z' in url):
							urlsToPrint.append(url)		
							
				if len(urlsToPrint)>0:
					stringToPrint="%s,%s,%s,%s,%s,%s,"%(site,thread,idPost,Timestamp.strftime("%Y-%m-%d"),author,len(urlsToPrint))
					for n,url in enumerate(urlsToPrint):
						if not url in duplicates.keys():
							fd.write(stringToPrint+"%s,\"%s\"\n"%(n+1,url))
							duplicates[url]=[(site,idPost,n+1)]
							numUrls+=1
						else:
							duplicates[url].append((site,idPost,n+1))
	fd.close()
	pickle.dump(duplicates,open(OUTPUT_DIR+'duplicatesFileLinks.pickle','wb'))
	outputFile=OUTPUT_DIR+'fileLink_duplicates.csv'
	fd=open(outputFile,'wb')
	totalDuplicates=0
	for url in duplicates.keys():
		stringToPrint="%s,"%url
		if len(duplicates[url])>1:
			totalDuplicates+=1
			for (s,post,n) in duplicates[url][:-1]:
				stringToPrint+="%s-%s-%s,"%(s,post,n)
			stringToPrint+="%s-%s-%s\n"%duplicates[url][-1]
			fd.write(stringToPrint)
	fd.close()

	if getTotal:			
		print ("%s Site %s: Extracted a total of %s pack urls from %s posts"%(datetime.now().strftime(tsFormat),site,numUrls,len(postsFromTOP)))
		print ("%s Site %s: Found %s duplicates"%(datetime.now().strftime(tsFormat),site,totalDuplicates))

# Extract URLS from T.O.P. that correspond with image sharing sites or has the image-related extensions (e.g. .jpg or .gif)
def extractImageLinksFromTOP(site,countPerYear=True,getTotal=True):
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	cursor=connector.cursor()
	query=('SELECT "URL" FROM "Site" WHERE "IdSite"=%s'%(site))
	cursor.execute(query)
	url=cursor.fetchone()[0]
	cursor.close()
	connector.close()
	netloc=urlparse(url).netloc	
	postsFromTOP=getPostsFromTOP(site)
	sortedPosts=sorted(postsFromTOP.items(),key=operator.itemgetter(0))
	numUrls=0
	outputFile=OUTPUT_DIR+'imageLink_list_%s.csv'%site
	if os.path.exists(outputFile):
		print ("WARNING. Image links from TOP of site %s already processed"%site)
		return
	fd=open(outputFile,'wb')
	fd.write("Thread,Post,Timestamp,Author,totalURLsPost,urlPosition,URL\n")
	registry=dict((imsite,defaultdict(int)) for imsite in image_sites)
	if not os.path.exists(OUTPUT_DIR+'duplicatesImageLinks.pickle'):
		duplicates={}
	else:
		duplicates=pickle.load(open(OUTPUT_DIR+'duplicatesImageLinks.pickle'))
	for thread,post in sortedPosts:
		if post:
			content,heading,OPAuthor,author,idPost,Timestamp,URLs=post
			printedURLs=0
			year=int(Timestamp.strftime("%Y"))
			if URLs:
				URLs=set(URLs)
				urlsToPrint=[]
				for url in URLs:
					url=url.strip()
					if (not url in urlsToPrint) and (not netloc in url) and (not "..." in url):
						printed=False
						for imageSite in image_sites:
							if imageSite in url:
								printed=True
								urlsToPrint.append(url)
								registry[imageSite][year]+=1
								break;
						if not printed and (".jpg" in url.lower() or ".png" in url.lower() or ".gif" in url.lower() or ".tiff" in url.lower()):
							urlsToPrint.append(url)		
				if len(urlsToPrint)>0:
					stringToPrint="%s,%s,%s,%s,%s,%s,"%(site,thread,idPost,Timestamp.strftime("%Y-%m-%d"),author,len(urlsToPrint))
					for n,url in enumerate(urlsToPrint):
						if not url in duplicates.keys():
							fd.write(stringToPrint+"%s,\"%s\"\n"%(n+1,url))
							duplicates[url]=[(site,idPost,n+1)]
							numUrls+=1
						else:
							duplicates[url].append((site,idPost,n+1))
					
	fd.close()
	pickle.dump(duplicates,open(OUTPUT_DIR+'duplicatesImageLinks.pickle','wb'))
	outputFile=OUTPUT_DIR+'imageLink_duplicates.csv'
	fd=open(outputFile,'wb')
	totalDuplicates=0
	for url in duplicates.keys():
		stringToPrint="%s,"%url
		if len(duplicates[url])>1:
			totalDuplicates+=1
			for (s,post,n) in duplicates[url][:-1]:
				stringToPrint+="%s-%s-%s,"%(s,post,n)
			stringToPrint+="%s-%s-%s\n"%duplicates[url][-1]
			fd.write(stringToPrint)
	fd.close()	

	if getTotal:			
		print ("%s Site %s. Extracted a total of %s image urls from %s posts"%(datetime.now().strftime(tsFormat),site,numUrls,len(postsFromTOP)))
		print ("%s Site %s. Found %s duplicates"%(datetime.now().strftime(tsFormat),site,totalDuplicates))	

# Return True if the heading is TOP according to heuristics, False otherwise
def comply_heuristics(heading):
	numKeywords=0
	keywords_heading=[	'pack','packs','package','packages','pics','pictures','videos','vids','video','collection','collections',
						'set','sets','repository','repositories','selling','wts','offering','free','unsaturated',
						'new','giving','compilation','private','girl','girls','sexy']
	if not isTutorial(heading) and getQuestionScore(heading)==0 and not 'scam' in heading:
		for k in keywords_heading:
			if k in heading.replace('[',' ').replace(']',' ').replace('.',' ').replace(',',' ').replace('-',' ').replace('*',' ').replace('|',' ').lower().split():
				numKeywords+=1
				if numKeywords==2:
					return True
	return False

# Prompts the heading and content of [numThreads] threads to be annotate as either T.O.P. (p) or Others (o)
# Updates the annotatedThreads.pickle file 
# applyHeuristics controls whether the set of threads to annotate should comply with the heuristics
def annotateThreads(numThreads,applyHeuristics=False):
	filename=OUTPUT_DIR+'annotatedThreads.pickle'
	if os.path.exists(filename):
		annotated=pickle.load(open(filename))
		print ("%s Read %s annotated threads from disk"%(datetime.now().strftime(tsFormat),len(annotated)))
	else:
		annotated={}
	toAnnotate=numThreads-len(annotated)
	if toAnnotate<=0:
		print ("%s You wanted to annotate %d threads, but you've already annotated %s threads"%(datetime.now().strftime(tsFormat),numThreads,len(annotated)))
		exit()
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	cursor = connector.cursor()

	# Get all the headings related to eWhoring
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	threadsHeadings={}
	for site in data:
		forums=[f for f in data[site] if not 'total' in str(f)]
		for forum in forums:
			for idThread in data[site][forum]:
				if not 'total' in str(idThread):
					if not applyHeuristics or comply_heuristics(data[site][forum][idThread]):
						threadsHeadings[str(site)+'-'+str(idThread)]=data[site][forum][idThread]
	# Randomize order
	threads=threadsHeadings.keys()
	random.shuffle(threads)

	print ("%s Obtained %s threads. Going to annotate %s"%(datetime.now().strftime(tsFormat),len(threads),toAnnotate))
	count=1
	for threadSite in threads[:toAnnotate]:
		if not threadSite in annotated.keys():
			site=threadSite.split('-')[0]
			thread=threadSite.split('-')[1]
			heading=threadsHeadings[threadSite]
			print ("[ANNOTATING Thread %s out of %s]\n"%(count,toAnnotate))
			print ("\n%s\n********************************************"%heading)
			print ("\n")
			annotation=raw_input("Type 's' if want to show content. Otherwise annotate as 'p'=giving pack,'o'=other (default) ") 
			if annotation=='s':
				query=('SELECT "Content" FROM "Post" WHERE "Thread"=%s AND "Site"=%s ORDER BY "IdPost" ASC LIMIT 1'%(thread,site));
				cursor.execute(query)
				post=cursor.fetchone()
				if post:
					content=post[0]
					print ("CONTENT: \n")
					for line in content.split('\n'):
						if line.strip()!='':
							print (line)
					print ()
					print ("------------------------------------------------------")
				annotation=raw_input("Annotate as 'p'=giving pack,'o'=other (default) ") 
			if annotation=='':
				annotation='o'
			annotated[threadSite]=annotation
		count+=1
		pickle.dump(annotated,open(filename,'wb'))

# Use heuristics to get TOP from the set of threads related to ewhoring
def getTOP_FromHeuristics(verbose=False):
	filename=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filename):
		print ("ERROR. %s not found"%filename)
		return
	data=pickle.load(open(filename))
	packs_per_site={}

	for site in data:
		packs=[]
		for forum in data[site]:
			if 'total' in str(forum):
				continue
			for idThread in data[site][forum]:
				if 'total' in str(idThread):
					continue
				if (comply_heuristics(data[site][forum][idThread])):
					if site in packs_per_site:
						packs_per_site[site]+=1
					else:
						packs_per_site[site]=1
					packs.append(idThread)
		pickle.dump(packs,open(OUTPUT_DIR+'TOP_Heuristics_%s.pickle'%site,'wb'))
	if verbose:
		for site,numPacks in sorted(packs_per_site.items(),key=operator.itemgetter(1),reverse=True):
			cursor = connector.cursor()
			if site==0:
				siteName="HackfForums"
			else:
				query=('SELECT "Name" FROM "Site" WHERE "IdSite"=%s'%site)
				cursor.execute(query)
				siteName=cursor.fetchone()[0]
				cursor.close()
			print ("Site: %s, Num TOP: %s"%(siteName.split()[0],numPacks))

# For a given site, creates a CSV with the actors involved in eWhoring and the number of packs provided			
def authorListByNumTOPs(site):
	authors = defaultdict(lambda: 0)
	postsFromTOP=getPostsFromTOP(site)
	for thread,post in postsFromTOP.items():
		if post is not None:
			content,heading,OPAuthor,author,idPost,Timestamp,URLs=post
			authors[OPAuthor]+=1
	authors=sorted(authors.items(),key=operator.itemgetter(1),reverse=True)
	fd=open(OUTPUT_DIR+'/author_packs_%s.csv'%site,'wb')
	fd.write("AUTHOR,NUM_PACKS\n")
	for a,n in authors:
		fd.write("%s,%s\n"%(a,n))
	fd.close()
	return

def get_stats_image_links():
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	sites = [s for s in data.keys() in not 'total' in str(s)]

	domains={}
	for imageSite in image_sites:
		domains[imageSite]=0
	domains['others']=0
	for site in sites:
		links=pd.read_csv(OUTPUT_DIR+'/imageLink_list_%s.csv'%site)
		for i,row in links.iterrows():
			url=row['URL']
			found=False
			for imageSite in image_sites:
				if imageSite in url:
					domains[imageSite]+=1
					found=True
					break
			if not found: domains['others']+=1
	others=domains['others']
	del domains['others']
	ordered=sorted(domains.items(),key=operator.itemgetter(1),reverse=True)
	total=others
	for site,numLinks in ordered[:10]:
		print ("%s & %s\\\\"%(site,numLinks))
		total+=numLinks
	
	for site,numLinks in ordered[10:]:
		others+=numLinks
	total+=others
	print ("Others & %s\\\\"%others)
	print ("\\hline")
	print ("\\bf Total & %s\\\\"%total)
	print ("\\hline")
	print ()

def get_stats_file_links():
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	sites = [s for s in data.keys() in not 'total' in str(s)]

	domains={}
	for site in file_sharing_sites:
		domains[site]=0
	domains['others']=0
	for site in sites:
		links=pd.read_csv(OUTPUT_DIR+'/fileLink_list_%s.csv'%site)
		for i,row in links.iterrows():
			url=row['URL']
			found=False
			for site in file_sharing_sites:
				if site in url:
					domains[site]+=1
					found=True
					break
			if not found: 
				domains['others']+=1
	others=domains['others']
	del domains['others']
	ordered=sorted(domains.items(),key=operator.itemgetter(1),reverse=True)
	total=others
	for site,numLinks in ordered[:10]:
		print ("%s & %s\\\\"%(site,numLinks))
		total+=numLinks
	for site,numLinks in ordered[10:]:
		others+=numLinks
	total+=others
	print ("Others & %s\\\\"%others)
	print ('\\hline')
	print ("\\bf Total & %s\\\\"%total)
	print ('\\hline')
	print ()

def extractLinks(type):
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	sites = [s for s in data.keys() in not 'total' in str(s)]
	for site in sites:
		if typeLink=='PACKS':
			extractPackLinksFromTOP(site,getTotal=True)
		else:
			extractImageLinksFromTOP(site,getTotal=True)

# ------------------------------------------------------------
# METHODS FOR GETTING TOPs.
# 1. To annotate threads, use annotateThreads(1000,applyHeuristics=True)
# 	 Then, use threadClassifier.py to train a ML model using the annotated threads
#
# 2. To extract based on heuristics, use getTOP_FromHeuristics()
#
# 3. To combine both in a single file, use combine_TOP_ML()


# ------------------------------------------------------------
# CODE AND METHODS TO EXTRACT LINKS RELATED TO PACKS AND PREVIEWS
# extractLinks('PACKS')
# extractLinks('PREVIEWS')
# get_stats_image_links()
# get_stats_file_links()
# ------------------------------------------------------------





