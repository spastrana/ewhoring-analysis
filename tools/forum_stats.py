import getpass
import re
import pytz
import psycopg2
import socket
import pandas as pd
from datetime import datetime,timedelta;
import operator
from collections import defaultdict

import sys
import os
import pickle 

tsFormat='%Y%m%d_%H%M%S'

### NOTE THAT THIS CODE RELIES ON THE CRIMEBB DATASET #####
DB_NAME='crimebb'

####################################################################################
# Put here your keyactors (the IDs have been removed from the code for ethical reasons)
Top_packs=[]
Top_50_earnings=[]
Top_50_reputation_with_more_than_150_posts_ewhoring=[]
Top_50_popularity_hindex=[]
Top_50_degree=[]
Top_50_eigenvector=[]
Top_50_CE=[]
actorsVariousGroups=[]
####################################################################################

currencies = [
    ["adsense"],
    ["agc","agccom","agcde","agccouk","amazoncouk","amazonuk","amazoncom","amazonde","amazon"],
    ["ap", "alterpay"],
    ["bank", "deposit", "bank deposit"],
    ["bloocoins", "bloocoin"],
    ["btc", "bitcoin", "bit", "coin", "coins", "btc-e", "bitcoins", "bitcoin"],
    ["cage", "cagecoin"],
    ["cashu"],
    ["catcoin"],
    ["cc", "credit", "credit card"],
    ["coye", "coinye"],
    ["doge", "doges", "dogecoin","dogecoinage", "doge coins","doge coin", "dogecoins"],
    ["dwolla"],
    ["ego", "egopay"],
    ['eth','ethereum'],
    ['google wallet'],
    ['xmr','monero'],
    ['psn','playstation'],
    ["flappycoins", "flappycoin"],
    ["freelancers"],
    ["interac"],
    ["liberty", "reserve", "l.r", "lr", "libertyreserve", "liberty reserve"],
    ["ltc", "lite-coin", "lite-coints", "litecoins", "litcoin","litecoinage","litecoin"],
    ["mb", "moneybooker", "booker", "moneybrokers", "moneybookers"],
    ["skrills","skrill","skrill"],
    ["mg", "gram", "moneygram"],
    ["mp", "pak", "moneypaks", "moneypak"],
    ["neteller"],
    ["okpay"],
    ["omc", "omcv2", "omcs", "open metaverse currency", "open metaverse"],
    ["omnicoins", "omnicoin"],
    ["payoneer"],
    ["pf", "perfectmoney", "pm","perfect money"],
    ["pokerstars"],
    ["pp", "pay pal", "pay-pal", "paypal"],
    ["protoshares"],
    ["psc", "paysafe", "paysafecards", "paysafecard", "pay safe card"],
    ["pz", "payza"],
    ["solid", "solidtrustpay"],
    ["starbucks"],
    ["steam"],
    ["stellar","stellars"],
    ["stp"],
    ["ukash"],
    ["venmo"],
    ["wdc", "world coins", "worldcoins"],
    ["wmz", "webmoney", "web money"],
    ["wu", "w.u", "western", "union", "western union","westernunion"],
    ["zetacoin"],
]
currencyREList = ['dollar','usd','eur','pound','aud','cad']
currencyRE=ur'[\$\u20AC\u00A3]{1}'
quantityRE = ur'\d+[\.,]?\d*[k]{0,1}'

regexpression="(%s)[\s]*(%s)|(%s)[\s]*(%s)"%(currencyRE,quantityRE,quantityRE,currencyRE)
for ce in currencyREList:
	regexpression+="|(%s)[\s]*(%s)"%(quantityRE,ce)

regularExpressionQuantityCurrency=re.compile(regexpression,re.UNICODE|re.IGNORECASE)

allMembersEwhoring=list(Top_packs)
allMembersEwhoring.extend(Top_50_earnings)
# allMembersEwhoring.extend(Top_50_reputation_with_more_than_150_posts_ewhoring)
allMembersEwhoring.extend(Top_50_popularity_hindex)
allMembersEwhoring.extend(Top_50_eigenvector)
allMembersEwhoring.extend(Top_50_CE)
allMembersEwhoring=list(set(allMembersEwhoring))

authorsToProcess=list(actorsVariousGroups)
# authorsToProcess.extend(Top_50_earnings[:2])
# authorsToProcess.extend(Top_packs[:2])
# authorsToProcess.extend(Top_50_popularity_hindex[:2])
# authorsToProcess.extend(Top_50_eigenvector[:2])
OUTPUT_DIR='../files/'


# Retuns all the threads related to eWhoring as a dictionary (pickle format). If the output file does not exist, queries the database
def get_num_threads_ewhoring_per_site(latex=False,verbose=False):
	filename=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filename):
		# First use keywords in headings on all the forums
		keywords=['e-whor','ewhor']
		orQuery='(lower("Heading") LIKE \'%'
		for keyword in keywords[:-1]:
			orQuery+=keyword.lower()+'%\' OR lower("Heading") LIKE \'%'
		orQuery+=keywords[-1].lower()+'%\')'
		query=('SELECT "IdThread","Heading","Forum","Site","NumPosts" FROM "Thread" WHERE %s '%orQuery) 
		cursor=connector.cursor()
		cursor.execute(query)
		rows=cursor.fetchall()
		cursor.close()
		if verbose: print ("Found %s threads"%len(rows))
		data={}
		for (thread,heading,forum,site,nPosts) in rows:
			if site==0 and forum==170:
				continue
			if not site in data:
				data[site]={'totalThreads':1,'totalPosts':1}
			else:
				data[site]['totalThreads']+=1
				data[site]['totalPosts']+=nPosts
			if not forum in data[site]:
				data[site][forum]={'totalThreadsForum':1,'totalPostsForum':1}
			else:
				data[site][forum]['totalThreadsForum']+=1
				data[site][forum]['totalPostsForum']+=nPosts
			data[site][forum][thread]=heading

		# Second, get all the threads from the e-whoring forum in hackforums
		query=('SELECT "IdThread","Heading","Forum","Site","NumPosts" FROM "Thread" WHERE "Site"=0 and "Forum"=170') 
		cursor=connector.cursor()
		cursor.execute(query)
		rows=cursor.fetchall()
		if verbose: print ("Found %s threads in hackforums-ewhoring"%len(rows))
		for (thread,heading,forum,site,nPosts) in rows:
			data[site]['totalThreads']+=1
			data[site]['totalPosts']+=nPosts
			if not forum in data[site]:
				data[site][forum]={'totalThreadsForum':1,'totalPostsForum':1}
			else:
				data[site][forum]['totalThreadsForum']+=1
				data[site][forum]['totalThreadsForum']+=nPosts
			data[site][forum][thread]=heading
		cursor.close()
		pickle.dump(data,open(filename,'wb'))
	else:
		data=pickle.load(open(filename))

	if verbose:
		orderedSites=sorted(data,key=lambda k:data[k]['totalThreads'],reverse=True)
		totalThreads=0
		totalPosts=0
		cursor=connector.cursor()
		for site in orderedSites:
			query=('SELECT "Name" FROM "Site" WHERE "IdSite"=%s'%site)
			cursor.execute(query)
			name=cursor.fetchone()[0] 
			print ("[%s] Site: %s: Total Threads: %s"%(site,name,data[site]['totalThreads']))
			totalThreads+=data[site]['totalThreads']
			totalPosts+=data[site]['totalPosts']
			del(data[site]['totalThreads'])
			del(data[site]['totalPosts'])
			orderedForums=sorted(data[site],key=lambda k:data[site][k]['totalThreadsForum'],reverse=True)
			for forum in orderedForums:
				if not 'total' in str(forum):
					query=('SELECT "Title" FROM "Forum" WHERE "IdForum"=%s and "Site"=%s'%(forum,site))
					cursor.execute(query)
					name=cursor.fetchone()[0] 
					print ("\t[%s] Forum_%s: %s : Total Threads: %s"%(site,forum,name,data[site][forum]['totalThreadsForum']))
	if latex:
		print ('\\begin{table}')
		print ('\\centering')
		print ('\\begin{tabular}{lS[table-format=6]S[table-format=6]}')
		print ('\\hline')
		print ('\\bf Forum & \\bf \\#Threads & \\bf \\#Posts \\\\')
		print ('\\hline')
		data=pickle.load(open(filename))
		orderedSites=sorted(data,key=lambda k:data[k]['totalThreads'],reverse=True)
		othersThreads=0
		othersPosts=0
		numOthers=0
		for site in orderedSites:
			if site==0:
				name='HackfForums'
			else:
				query=('SELECT "Name" FROM "Site" WHERE "IdSite"=%s'%site)
				cursor.execute(query)
				name=cursor.fetchone()[0].split(" ")[0]
			if data[site]['totalThreads']>20:
				print ("%s & %d & %d\\\\"%(name.replace('&','and'),data[site]['totalThreads'],data[site]['totalPosts']))
			else:
				othersThreads+=data[site]['totalThreads']
				othersPosts+=data[site]['totalPosts']
				numOthers+=1
		print ("Others (%d): & %d & %d \\\\"%(numOthers,othersThreads,othersPosts))
		print ('\\hline')
		print ("TOTAL: & %d & %d \\\\"%(totalThreads,totalPosts))
		print ('\\hline')
		print ('\\end{tabular}')
		print ('\\caption{Number of e-whoring related conversations per forum in the dataset}')
		print ('\\label{table:forumSummary}')
		print ('\\end{table}')
	return data

# Show the headings of eWhoring-related threads of a given site
def showHeadingsSite(site):
	keywords=['e-whor','ewhor']
	orQuery='(lower("Heading") LIKE \'%'
	for keyword in keywords[:-1]:
		orQuery+=keyword.lower()+'%\' OR lower("Heading") LIKE \'%'
	orQuery+=keywords[-1].lower()+'%\')'
	query=('SELECT "IdThread","Heading","Forum","Site","NumPosts" FROM "Thread" WHERE %s and "Site"=%s '%(orQuery,site)) 
	cursor=connector.cursor()
	cursor.execute(query)
	rows=cursor.fetchall()
	cursor.close()
	for (thread,heading,forum,site,nPosts) in rows:
		print ("%s - %s"%(thread,heading))

# Obtains from the database the currency exchange threads (idThread,heading and timestamp) of the authors involved in eWhoring
def get_CurrencyExchange (verbose=False):
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	authors=[]
	for site in data:	
		if site!=0: continue
		forums=[f for f in data[site] if not 'total' in str(f)]
		for forum in forums:
			for idThread in data[site][forum]:
				if not 'total' in str(idThread):
					query=('SELECT "Author" FROM "Post" WHERE "Thread"=%s and "Site"=%s'%(idThread,site)) 
					cursor=connector.cursor()
					cursor.execute(query)
					rows=cursor.fetchall()
					for row in rows:
						authors.append(row[0])
	members=list(set(authors))	
	filename=OUTPUT_DIR+'/currency_exchange_threads.pickle'
	if os.path.exists(filename):
		memberCE=pickle.load(open(filename))
	else:
		memberCE={}
	if verbose: print ("Going to process %s members"%len(members))
	for c,memberID in enumerate(members):
		if memberID in memberCE:
			continue
		# Get Currency Exchange
		query=('SELECT "IdThread","Heading" FROM "Thread" WHERE "Author"=%s AND "Forum"=182 AND "Site"=0'%memberID)
		cursor=connector.cursor()
		cursor.execute(query)
		rows=cursor.fetchall()	
		for thread,heading in rows:
			query=('SELECT "Timestamp" FROM "Post" WHERE "Author"=%s AND "Thread"=%s AND "Site"=0 ORDER BY "Timestamp" ASC LIMIT 1'%(memberID,thread))
			cursor=connector.cursor()
			cursor.execute(query)
			row=cursor.fetchone()
			if row:
				timestamp=row[0]
				if not memberID in memberCE: memberCE[memberID]=[]
				memberCE[memberID].append((thread,heading,timestamp))
		if verbose: 
			if  memberID in memberCE: 
				print ("Member %s, Num threads in CE:%s"%(memberID,len(memberCE[memberID])))
			else:
				print ("Member %s, Num threads in CE:0"%(memberID))
	pickle.dump(memberCE,open(filename,'w'))

# Print general statistics of the authors involved in eWhoring
def general_stats_authors():
	filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filenameThreads):
		print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
		exit(-1)
	data=pickle.load(open(filenameThreads))
	authors={}
	for site in data:
		authors[site]=defaultdict(lambda:0)
		forums=[f for f in data[site] if not 'total' in str(f)]
		for forum in forums:
			for idThread in data[site][forum]:
				if not 'total' in str(idThread):
					query=('SELECT "IdPost","Author","Timestamp" FROM "Post" WHERE "Thread"=%s and "Site"=%s'%(idThread,site)) 
					cursor=connector.cursor()
					cursor.execute(query)
					rows=cursor.fetchall()
					for post,author,timestamp in rows:
						authors[site][author]+=1
	print ("Site,Author,NumPosts")
	for site in authors:
		ordered=sorted(authors[site].items(),key=operator.itemgetter(1),reverse=True)
		for author,num in ordered:
			if author==-1: continue
			print ("%s,%s,%s"%(site,author,num))

# Generates a CSV file with the stats of the eWhoring actors doing currency exchange before and during/after doing eWhoring
def generate_CE_stats():
	outputfile=OUTPUT_DIR+'/currency_exchange_stats_0.csv'
	filename=OUTPUT_DIR+'/currency_exchange_threads.pickle'
	if not os.path.exists(filename):
		print "ERROR: File %s not found"%filename
	memberCE=pickle.load(open(filename))	
	filename=OUTPUT_DIR+'/ewhoring_actors_time_0.csv'
	if not os.path.exists(filename):
		print ("ERROR:%s not found"%filename)
		exit()
	author_time_stats=pd.read_csv(filename)
	includedAuthors=[]
	for i,values in author_time_stats.iterrows():
		actor=int(values['AUTHOR'])
		include=False
		start=values['START']
		dateInit=values['FIRST_POST_EWHORING']
		dateEnd=values['LAST_POST_EWHORING']
		end=values['END']
		includedAuthors.append(str(actor)+'_'+dateInit+'_'+dateEnd+'_'+start+'_'+end)

	numCEAuthors={}
	for a in includedAuthors:
		idMember=int(a.split('_')[0])
		# if not idMember in memberCE:
			# continue
		dateInit=datetime.strptime(a.split('_')[1],'%Y-%m-%d')
		dateEnd=datetime.strptime(a.split('_')[2],'%Y-%m-%d')
		numCEAuthors[idMember]={'before':0,'during':0}
		if idMember in memberCE:
			for thread,heading,timestamp in memberCE[idMember]:
				if timestamp.replace(tzinfo=None) < dateInit:
					numCEAuthors[idMember]['before']+=1
				# We consider threads in CE that are within two months of the last post in eWhoring
				elif timestamp.replace(tzinfo=None) < (dateEnd+timedelta(days=61)):
					numCEAuthors[idMember]['during']+=1
		if (numCEAuthors[idMember]['before']+numCEAuthors[idMember]['during'])>0:
			numCEAuthors[idMember]['ratioDuring']=float(numCEAuthors[idMember]['during'])/(numCEAuthors[idMember]['before']+numCEAuthors[idMember]['during'])
		else:
			numCEAuthors[idMember]['ratioDuring']=0
	fd=open(outputfile,'wb')
	fd.write("AUTHOR,CE_BEFORE,CE_EWHORING,CE_RATIO\n")
	for idMember in numCEAuthors:
		fd.write("%s,%s,%s,%.2f\n"%(idMember,numCEAuthors[idMember]['before'],numCEAuthors[idMember]['during'],numCEAuthors[idMember]['ratioDuring']))
	fd.close()

# Calculates the impact metrics  (H-index, i10, i50 i100) for the eWhoring actors for a given site
def calculateImpactMetricsEWhoring(idSite=0,printMetrics=False):
	print ("%s Getting impact metrics for eWhoring, site %s"%(datetime.now().strftime(tsFormat),idSite))
	filename=OUTPUT_DIR+'ewhoring_'+str(idSite)+'/impactMetrics_'+str(idSite)+'.pickle'
	if os.path.exists(filename): 
		print ("%s Forum %s. Reading impact from disk"%(datetime.now().strftime(tsFormat),idSite))
		impact=pickle.load(open(filename,'r'))
	else:
		filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
		if not os.path.exists(filenameThreads):
			print ("%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads))
			exit(-1)
		print ("%s Connecting to Database."%(datetime.now().strftime(tsFormat))	)
		connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
		data=pickle.load(open(filenameThreads))	
	
		print ("%s Ewhoring, site %s. Querying DB for impact"%(datetime.now().strftime(tsFormat),idSite))
		threads=[]
		for site in data:
			if not site==idSite:
				continue
			forums=[f for f in data[site] if not 'total' in str(f)]
			for f in forums:
				for idThread in data[site][f]:
					if not 'total' in str(idThread):
						cursor=connector.cursor()
						query=('SELECT "IdThread","Author" FROM "Thread" WHERE "IdThread"=%s AND "Site"=%s');
						args=(idThread,site) 
						cursor.execute(query,args)
						rows=cursor.fetchall()
						threads.extend(rows)
		print ("%s Obtained %s threads"%(datetime.now().strftime(tsFormat),len(threads)))
		impact={}
		count=0
		for thread,author in threads:
			count+=1
			# Be Verbose
			if count%100 == 0 or count==len(threads):
				progress = round(count*100.0/len(threads),2)
				sys.stdout.write("%s Processing thread %s (%s %s) \r"%(datetime.now().strftime(tsFormat), count,progress,'%'))
				sys.stdout.flush()

			if not author in impact.keys():
				impact[author]={}	
			query=('SELECT "IdPost","CitedPost","Author" FROM "Post" WHERE "Thread"=%s AND "Site"=%s ORDER BY "IdPost" ASC');
			data=(thread,SITE) 
			cursor.execute(query,data)
			posts=cursor.fetchall()
			if len(posts)>0:
				opID=long(posts[0][0])
				impact[author][thread]=0
				for post,cited,a in posts[1:]:
					if a!=author and (not cited or len(cited)==0 or cited[0]<0 or opID in cited):
						impact[author][thread]+=1;
		pickle.dump(impact,open(filename,'wb'))
	print ()
	print ("%s Ewhoring site %s. Calculating impactMetrics"%(datetime.now().strftime(tsFormat),idSite))
	metrics={}
	totalCites={}
	fd=open(OUTPUT_DIR+'ewhoring_'+str(idSite)+'/impactMetrics_'+str(idSite)+'.csv','w+')
	fd.write('AUTHOR,H,I10,I50,I100\n')
	for author in impact.keys():
		verbose=False
		h=0
		h10=0
		h50=0
		h100=0
		totalCites[author]=0
		metrics[author]={}
		metrics[author]['numThreads']=0
		metrics[author]['totalCites']=0
		sortedCites=sorted(impact[author].items(),key=operator.itemgetter(1),reverse=True)
		count=0
		for thread,numCites in sortedCites:
			metrics[author]['numThreads']+=1
			totalCites[author]+=numCites
			metrics[author]['totalCites']+=numCites
			if h<numCites:
				h=h+1
			if numCites>=10:
				h10+=1
			if numCites>=50:
				h50+=1
			if numCites>=100:
				h100+=1
			if verbose:
				count+=1
				print ("[%s] Thread %s NumCites %s H - %s h10 - %s"%(count,thread,numCites,h,h10))
		metrics[author]['h']=h
		metrics[author]['h10']=h10
		metrics[author]['h50']=h50
		metrics[author]['h100']=h100
		fd.write('%s,%s,%s,%s,%s\n'%(author,h,h10,h50,h100))
	fd.close()
	
	sortedCites=sorted(metrics, key=lambda author:(metrics[author]['h'],metrics[author]['totalCites']),reverse=True)
	if printMetrics:
		sortedCites=sorted(metrics, key=lambda author:(metrics[author]['h'],metrics[author]['totalCites']),reverse=True)
		if os.path.exists(FILE_EARNINGS):
			print ("Author\tThreads\tCites\tH\tEarnings\tRankEarnings\tH10\t\tH50\t\tH100")
			print ("---------------------------------------------------------------------------------------------------")
			for author in sortedCites[:30]:
				position,earnings=getEarningsAndRelativePosition(author)	
				totalThreads=metrics[author]['numThreads']
				#print ("Author:%s\tNumThreads=%s\tTotalCites:%s\tH:%s\tH10:%s(%.2f%%)\tH50:%s(%.2f%%)\tH100:%s(%.2f%%)"%(author,totalThreads,totalCites[author],metrics[author]['h'],metrics[author]['h10'],metrics[author]['h10']*100.0/totalThreads,metrics[author]['h50'],metrics[author]['h50']*100.0/totalThreads,metrics[author]['h100'],metrics[author]['h100']*100.0/totalThreads))
				print ("%s\t   %s\t%s\t%s\t%.2f\t\t%s\t\t%s (%.2f%%)\t%s (%.2f%%)\t%s (%.2f%%)"%(author,totalThreads,metrics[author]['totalCites'],metrics[author]['h'],earnings,position,metrics[author]['h10'],metrics[author]['h10']*100.0/totalThreads,metrics[author]['h50'],metrics[author]['h50']*100.0/totalThreads,metrics[author]['h100'],metrics[author]['h100']*100.0/totalThreads))
		else:
			print ("Author\tThreads\tCites\tH\tH10\t\tH50\t\tH100")
			print ("-------------------------------------------------------------------------------")
			for author in sortedCites[:30]:
				totalThreads=metrics[author]['numThreads']
				#print ("Author:%s\tNumThreads=%s\tTotalCites:%s\tH:%s\tH10:%s(%.2f%%)\tH50:%s(%.2f%%)\tH100:%s(%.2f%%)"%(author,totalThreads,totalCites[author],metrics[author]['h'],metrics[author]['h10'],metrics[author]['h10']*100.0/totalThreads,metrics[author]['h50'],metrics[author]['h50']*100.0/totalThreads,metrics[author]['h100'],metrics[author]['h100']*100.0/totalThreads))
				print ("%s\t   %s\t%s\t%s\t%s (%.2f%%)\t%s (%.2f%%)\t%s (%.2f%%)"%(author,totalThreads,metrics[author]['totalCites'],metrics[author]['h'],metrics[author]['h10'],metrics[author]['h10']*100.0/totalThreads,metrics[author]['h50'],metrics[author]['h50']*100.0/totalThreads,metrics[author]['h100'],metrics[author]['h100']*100.0/totalThreads)				)
	return metrics

# Utils for summarize actors per group
def summarize_key_actors():
	allTables={'Packs':Top_packs,'Earnings':Top_50_earnings,'Popular':Top_50_popularity_hindex,'Influence':Top_50_eigenvector,'CE':Top_50_CE}
	groups={}
	print len(allMembersEwhoring)
	for m in allMembersEwhoring:
		groups[m]=[]
		for name in allTables:
			if m in allTables[name]:
				groups[m].append(name)
	total1=0
	total2=0
	total3=0
	total4=0
	total5=0
	for m in groups:
		if len(groups[m])==1:
			total1+=1
		if len(groups[m])==2:
			total2+=1
		if len(groups[m])==3:
			print m,"-".join(groups[m])
			total3+=1
		if len(groups[m])==4:
			print m,"-".join(groups[m])
			total4+=1
		if len(groups[m])==5:
			print m,"-".join(groups[m])
			total5+=1			
	print total1,total2,total3,total4,total5
	# return
	# print len([f for f in Top_50_earnings if f in Top_50_CE])


	combos=defaultdict(lambda:0)
	unique={}
	for i,name in enumerate(allTables.keys()):
		unique[name]=[]
		for m in allTables[name]:
			isUnique=True
			for name2 in allTables.keys():
				if name==name2:
					continue
				if m in allTables[name2]:
					 combos[(name,name2)]+=1
					 isUnique=False
			if isUnique:
				unique[name].append(m)
	
	print " &",
	for n in allTables.keys()[:-1]:
		print "%s & "%n,
	print "%s \\\\"%allTables.keys()[-1]
	for n in allTables:
		print "%s &"%n,
		for m in allTables.keys()[:-1]:
			if n==m:
				print " %s &"%len(unique[n]),
			else:
				print " %s &"%combos[(n,m)],
		m=list(allTables.keys())[-1]
		if n==m:
			print "%s \\\\"%len(unique[n])
		else:
			print "%s \\\\"%combos[(n,m)]

def getQuantity(content):
	quantityDict={}
	count=0	
	search=regularExpressionQuantityCurrency.search(content)
	if search is not None:
		return search.group()
	return "unknown"
def getCurrency(text):
	for t in text.split():
		for currency in currencies:
			for c in currency:
				if c in t:
					return currency[0]
	print "CURRENCY-UNKNOWN: %s"%text
	return 'unknown'

def get_top_authors_CE(onlyWithProofOfEarnings=False):
	filename=OUTPUT_DIR+'/ewhoring_actors_time_0.csv'
	if not os.path.exists(filename):
		print ("ERROR:%s not found"%filename)
		exit()
	author_time_stats=pd.read_csv(filename)

	filename=OUTPUT_DIR+'/currency_exchange_threads.pickle'
	if not os.path.exists(filename):
		print "ERROR: File %s not found"%filename
	
	memberCE=pickle.load(open(filename))		
	
	
	FILE_EARNINGS=OUTPUT_DIR+'/proofOfEarnings_annotationStats.csv'
	earnings=pd.read_csv(FILE_EARNINGS)
	
	# CONSIDER ONLY THOSE FROM HACKFORUMS
	indexNames = earnings[ (earnings['SITE'] != 0)].index
	earnings.drop(indexNames , inplace=True)

	earnings = earnings[['AUTHOR','TOTAL_AMOUNT']]
	earnings=earnings.groupby('AUTHOR', as_index=False).agg({"TOTAL_AMOUNT": "sum"})
	earnings=earnings.sort_values(by='TOTAL_AMOUNT', ascending=False)
	author_time_stats=author_time_stats.merge(earnings,on="AUTHOR",how='left')
	indexNames = author_time_stats[ (author_time_stats['AUTHOR'] == -1)].index
	author_time_stats.drop(indexNames , inplace=True)
	includedAuthors=[]
	numCEAuthors={}
	for i,values in author_time_stats.iterrows():
		actor=int(values['AUTHOR'])
		totalAmount=values['TOTAL_AMOUNT']
		include=False
		if actor in memberCE:
			if onlyWithProofOfEarnings and totalAmount>0:
					include=True
			# Remove low interaction users
			elif not onlyWithProofOfEarnings and values['NUM_POSTS_EWHORING']>50:
				include=True
			if include:
				start=values['START']
				dateInit=values['FIRST_POST_EWHORING']
				dateEnd=values['LAST_POST_EWHORING']
				end=values['END']
				includedAuthors.append(str(actor)+'_'+dateInit+'_'+dateEnd+'_'+start+'_'+end+'_'+str(totalAmount))
	print len(includedAuthors)
	correct=0
	total=0	
	totalHave=defaultdict(lambda:0)
	totalWant=defaultdict(lambda:0)	
	for a in includedAuthors:
		idMember=int(a.split('_')[0])
		# if not idMember in memberCE:
			# continue
		dateInit=datetime.strptime(a.split('_')[1],'%Y-%m-%d')
		dateEnd=datetime.strptime(a.split('_')[2],'%Y-%m-%d')
		try:
			totalValue=float(a.split('_')[5])
		except:
			totalValue=0
		numCEAuthors[idMember]={'before':0,'during':0,'earnings':totalValue}
		if idMember in memberCE:
			for thread,heading,timestamp in memberCE[idMember]:
				if timestamp.replace(tzinfo=None) < dateInit:
					numCEAuthors[idMember]['before']+=1
				# We consider threads in CE that are within two months of the last post in eWhoring
				elif timestamp.replace(tzinfo=None) < (dateEnd+timedelta(days=61)):
					total+=1
					numCEAuthors[idMember]['during']+=1
					head=heading.lower().replace('[n]','[w]').replace('have','[h]').replace('want','[w]').replace('need','[w]').replace('(','[').replace(')',']').replace('got','[h]').replace('for','[w]').replace('[ ','[').replace(' ]',']').replace(' h ','[h]').replace(' w ','[w]').replace(' n ','[w]')
					if '[h]' in head and '[w]' in head:
						have=False
						if head.index('[h]')<head.index('[w]'):	
							try:
								have=getCurrency(head.split('[h]')[1].split('[w]')[0])
								totalHave[have]+=1
								have=True
								amount=getQuantity(head.split('[h]')[1].split('[w]')[0])
								want=getCurrency(head.split('[h]')[1].split('[w]')[1])
								totalWant[want]+=1
								# print "%s,%s,[%s],[%s],[%s]"%(idMember,timestamp.strftime('%Y-%m-%d'),have,amount,want)
								correct+=1
							except:
								totalWant['unknown']+=1
								if not have: totalHave['unknown']+=1
								# print "WRONG PROCESSED",head
								pass
						else:
							try:
								have=getCurrency(head.split('[w]')[1].split('[h]')[0])
								totalHave[have]+=1
								have=True
								amount=getQuantity(head.split('[w]')[1].split('[h]')[0])
								want=getCurrency(head.split('[w]')[1].split('[h]')[1])
								totalWant[want]+=1
								# print "%s,%s,[%s],[%s],[%s]"%(idMember,timestamp.strftime('%Y-%m-%d'),have,amount,want)
								correct+=1
							except:
								totalWant['unknown']+=1
								if not have: totalHave['unknown']+=1
								# print "WRONG PROCESSED",head
								pass						
					else:
						print "OTHER",head	
		if (numCEAuthors[idMember]['before']+numCEAuthors[idMember]['during'])>0:
			numCEAuthors[idMember]['ratioDuring']=float(numCEAuthors[idMember]['during'])/(numCEAuthors[idMember]['before']+numCEAuthors[idMember]['during'])
		else:
			numCEAuthors[idMember]['ratioDuring']=0
	print "Processed %s heading from a total of %s"%(correct,total)
	print "TOTAL:%s"%len(numCEAuthors)
	# ordered=sorted(numCEAuthors,key=lambda x:numCEAuthors[x]['ratioDuring']*numCEAuthors[x]['during'],reverse=True)
	ordered=sorted(numCEAuthors,key=lambda x:numCEAuthors[x]['earnings'],reverse=True)
	# for member in ordered[:50]:
	
	for member in ordered:
		if member in Top_50_earnings:
			print "MEMBER: %s,BEFORE: %s, AFTER: %s, RATIO:%.2f %%, EARNINGS: %.2f"%(member,numCEAuthors[member]['before'],numCEAuthors[member]['during'],numCEAuthors[member]['ratioDuring']*100,numCEAuthors[member]['earnings'])
	num=0
	for member in Top_50_earnings:
		if not member in memberCE:
			num+=1
	print "NUM is %s"%num
	# print "[",
	# for member in ordered[:50]:
	# 	print "%s,"%member,
	# print "]"
	totalThreadsCE=0
	authorsWithCE=0
	for member in ordered:
		if numCEAuthors[member]['during']>0:
			totalThreadsCE+=numCEAuthors[member]['during']
			authorsWithCE+=1
	if onlyWithProofOfEarnings: print "AUTHORS WITH EARNINGS:%s"%len(earnings[(earnings['TOTAL_AMOUNT']>0)])
	print "AUTHORS WITH CE DURING EWHORING: %s"%authorsWithCE
	print "AVERAGE CE OF AUTHORS WITH CE: %.2f"%(float(totalThreadsCE)/len(ordered))
	print "CURRENCIES OFFERED:"
	ordered=sorted(totalHave.items(),key=operator.itemgetter(1),reverse=True)
	
	for c,num in ordered[:3]:
		print "%s & "%(c),
	print "others & ? & Total\\\\"
	print "OFFERED &",
	total=0
	for c,num in ordered[:3]:
		print "%d & "%num,
		total+=num
	others=0
	for c,num in ordered[3:]:
		if not c=='unknown':
			others+=num
			total+=num
	total+=totalHave['unknown']
	print "%d & %d & %d\\\\"%(others,totalHave['unknown'],total)
	print "CURRENCIES WANTED:"
	ordered=sorted(totalWant.items(),key=operator.itemgetter(1),reverse=True)
	for c,num in ordered[:3]:
		print "%s & "%(c),
	print "others & ? & Total\\\\"
	print "WANTED &",
	total=0
	for c,num in ordered[:3]:
		print "%d & "%num,
		total+=num
	others=0
	for c,num in ordered[3:]:
		if not c=='unknown':
			others+=num		
			total+=num
	total+=totalWant['unknown']
	print "%d & %d & %d\\\\"%(others,totalWant['unknown'],total)

# Prints the statistics of the groups
def analyse_author_stats_per_group():
	SITE=0
	filename=OUTPUT_DIR+'/ewhoring_actors_time_%s.csv'%SITE
	if not os.path.exists(filename):
		print ("ERROR:%s not found"%filename)
		exit()
	author_time_stats=pd.read_csv(filename)
	
	FILE_EARNINGS=OUTPUT_DIR+'/proofOfEarnings_annotationStats.csv'
	earnings=pd.read_csv(FILE_EARNINGS)
	author_time_stats=author_time_stats.merge(earnings,on="AUTHOR",how='left')

	filename=OUTPUT_DIR+'/currency_exchange_stats_0.csv'
	ce=pd.read_csv(filename)
	author_time_stats=author_time_stats.merge(ce,on="AUTHOR",how='left')

	FILE_IMPACT=OUTPUT_DIR+'/impactMetrics_'+str(SITE)+'.csv'
	impact=pd.read_csv(FILE_IMPACT)
	author_time_stats=author_time_stats.merge(impact,on="AUTHOR",how='left')

	FILE_TOP=OUTPUT_DIR+'/author_packs_'+str(SITE)+'.csv'
	top=pd.read_csv(FILE_TOP)
	author_time_stats=author_time_stats.merge(top,on="AUTHOR",how='left')

	indexNames = author_time_stats[ (author_time_stats['AUTHOR'] == -1)].index
	author_time_stats.drop(indexNames , inplace=True)

	columnsToPrint=['NUM_POSTS_EWHORING','PERCENTAGE_EWHORING','DAYS_BEFORE_EWHORING','TOTAL_AMOUNT','H','I10','I100','NUM_PACKS','CE_EWHORING']
	
	allTables={'P':Top_packs,'\\$':Top_50_earnings,'Hi':Top_50_popularity_hindex,'I':Top_50_eigenvector,'Ce':Top_50_CE}
	allTablesOrdered=['P','I','Hi','\\$','Ce']
	
	print '\\begin{table}'
	print '\\centering'
	print '\\begin{tabular}{l',
	for i in range(0,len(columnsToPrint)):
		print 'S[table-format=6]',
	print "}"
	print "Group & {\\#Posts} & {\\%ewhor.} & {\\#Before} & {\\#Amount} & {H} & {I10} & {I100} & {\\#Packs} & {\\#CE} \\\\ "
	print "\\hline"
	allAuthors=[]
	for name in allTablesOrdered:

		# CONSIDER ONLY THOSE FROM THE CURRENT GROUP
		authorsToProcess=allTables[name]
		allAuthors.extend(authorsToProcess)
		tmp=author_time_stats[author_time_stats['AUTHOR'].isin(authorsToProcess)]
		print "%s "%(name),
		for column in columnsToPrint:	
			# tmp2=tmp.dropna(subset=[column], how='all')
			data=tmp[column].mean()
			if 'PERCENTAGE' in column:
				data=data*100.0
			print "& %.1f"%(data),
		print "\\\\"
	allAuthors=list(set(allAuthors))
	tmp=author_time_stats[author_time_stats['AUTHOR'].isin(allAuthors)]
	print "ALL ",
	for column in columnsToPrint:	
		# tmp2=tmp.dropna(subset=[column], how='all')
		data=tmp[column].mean()
		if 'PERCENTAGE' in column:
			data=data*100.0
		print "& %.1f"%(data),
	print "\\\\"
	print '\\end{tabular}'
	print '\\caption{Characteristics of key actors aggregated by groups}'
	print '\\label{table:keyActorsAggregated}'
	print '\\end{table}'	
	print len(allAuthors)	

# Returns dictionaries with the number of posts, firstPost and lastPost of each actor (dict key). Writes to disk if called for the first time
def get_first_last_posts_ewhoring(SITE=0):
	filename=OUTPUT_DIR+'/first_last_post_ewhoring_%s.pickle'%SITE
	if not os.path.exists(filename):
		filenameThreads=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
		if not os.path.exists(filenameThreads):
			print "%s ERROR: Could not find %s"%(datetime.now().strftime(tsFormat),filenameThreads)
			exit(-1)
		data=pickle.load(open(filenameThreads))
		firstPost={}
		lastPost={}
		numPosts={}
		for site in data:
			if site!=SITE:
				continue
			forums=[f for f in data[site] if not 'total' in str(f)]
			for forum in forums:
				for idThread in data[site][forum]:
					if not 'total' in str(idThread):
						query=('SELECT "IdPost","Author","Timestamp" FROM "Post" WHERE "Thread"=%s and "Site"=%s'%(idThread,site)) 
						cursor=connector.cursor()
						cursor.execute(query)
						rows=cursor.fetchall()
						for idPost,author,timestamp in rows:
							if not author in numPosts: 
								firstPost[author]=(idPost,timestamp)
								if timestamp.strftime('%Y')=='1900':
									timestamp= datetime.utcnow()
									timestamp = timestamp.replace(tzinfo=pytz.utc)
								lastPost[author]=(idPost,timestamp)
								numPosts[author]=1
							else:
								numPosts[author]+=1
								if timestamp.strftime('%Y')!='1900' and timestamp<firstPost[author][1]:
									firstPost[author]=(idPost,timestamp)
								if timestamp.strftime('%Y')!='1900' and timestamp>lastPost[author][1]:
									lastPost[author]=(idPost,timestamp)
			pickle.dump((numPosts,firstPost,lastPost),open(filename,'wb'))
	else:
		numPosts,firstPost,lastPost=pickle.load(open(filename))
	return numPosts,firstPost,lastPost

# Writes a CSV file with the timing stats of each actor involved in eWhoring for a given site
def get_time_stats(SITE=0):
	numPosts,firstEwhoring,lastEwhoring=get_first_last_posts_ewhoring(SITE=SITE)
	outputfile=OUTPUT_DIR+"/ewhoring_actors_time_%s.csv"%SITE
	fd=open(outputfile,'w+')
	fd.write('AUTHOR,TOTAL_POSTS,NUM_POSTS_EWHORING,START,FIRST_POST_EWHORING,DAYS_BEFORE_EWHORING,LAST_POST_EWHORING,END,DAYS_AFTER_EWHORING,PERCENTAGE_EWHORING,REPUTATION\n')
	for author in numPosts:
		query=('SELECT "TotalPosts","RegistrationDate","LastVisitDue","FirstPostDate","LastPostDate","Reputation" FROM "Member" WHERE "IdMember"=%s and "Site"=%s'%(author,SITE)) 
		cursor=connector.cursor()
		cursor.execute(query)
		row=cursor.fetchone()
		if not row:
			print ("WARNING: Author %s not found in DB"%author)
			continue
		totalPosts,regDate,lastVisit,firstPost,lastPost,reputation=row
		if totalPosts==0:
			query=('SELECT Count(*) FROM "Post" WHERE "Author"=%s and "Site"=%s'%(author,SITE)) 
			cursor=connector.cursor()
			cursor.execute(query)
			row=cursor.fetchone()
			totalPosts=row[0]
		start=regDate.replace(tzinfo=None)
		if start<datetime(1990,1,1):
			if firstPost is not None:
				start=firstPost.replace(tzinfo=None)
				if start<datetime(1990,1,1):
					print ("WARNING: Author %s start is %s"%(author,start))	
					continue
			else:
				print ("WARNING: Author %s does not have start"%author)
				continue
		end=lastVisit.replace(tzinfo=None)
		if end<datetime(1990,1,1):
			if lastPost is not None:
				end=lastPost.replace(tzinfo=None)
				if end<datetime(1990,1,1):
					print ("WARNING: Author %s end is %s"%(author,end))	
					continue
			else:
				print ("WARNING: Author %s does not have end"%author)
				continue
		firstPostEwhoring=firstEwhoring[author][1].replace(tzinfo=None)
		lastPostEwhoring=lastEwhoring[author][1].replace(tzinfo=None)
		if lastPostEwhoring<datetime(1990,1,1):
			print ("WARNING: Author %s does not have lastPostEwhoring"%author)
			continue
		if firstPostEwhoring<datetime(1990,1,1):
			print ("WARNING: Author %s does not have firstPostEwhoring"%author)
			continue
		numPostsEwhoring=numPosts[author]
		if totalPosts>0:
			percentageEwhoring=float(numPostsEwhoring)/float(totalPosts)
		else:
			percentageEwhoring=0.0
		daysBeforeEwhoring=(firstPostEwhoring-start).days
		daysAfterEwhoring=(end-lastPostEwhoring).days
		fd.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n"%(author,totalPosts,numPostsEwhoring,start.strftime("%Y-%m-%d"),firstPostEwhoring.strftime("%Y-%m-%d"),daysBeforeEwhoring,lastPostEwhoring.strftime("%Y-%m-%d"),end.strftime("%Y-%m-%d"),daysAfterEwhoring,percentageEwhoring,reputation))
	fd.close()

def check_key_actors(SITE=0):
	numPosts,firstEwhoring,lastEwhoring=get_first_last_posts_ewhoring(SITE=SITE)
	groups={}
	for author in numPosts:
		groups[author]=[]
		if author in Top_50_earnings:
			groups[author].append('earnings')
		if author in Top_packs:
			groups[author].append('packs')
		if author in Top_50_reputation_with_more_than_150_posts_ewhoring:
			groups[author].append('reputation')
		if author in Top_50_popularity_hindex:
			groups[author].append('popularity')
		if author in Top_50_degree:
			groups[author].append('degree')
		if author in Top_50_eigenvector:
			groups[author].append('eigenvector')
	ordered=sorted(groups,key=lambda k:len(groups[k]),reverse=True)
	toProcess=[]
	for author in ordered:
		if len(groups[author])>1:
			toProcess.append(author)
	for author in Top_packs[:5]:
		if not author in toProcess:
			toProcess.append(author)
	for author in Top_50_earnings[:5]:
		if not author in toProcess:
			toProcess.append(author)
	for author in Top_50_reputation_with_more_than_150_posts_ewhoring[:5]:
		if not author in toProcess:
			toProcess.append(author)
	for author in Top_50_popularity_hindex[:5]:
		if not author in toProcess:
			toProcess.append(author)
	for author in Top_50_degree[:5]:
		if not author in toProcess:
			toProcess.append(author)
	for author in Top_50_eigenvector[:5]:
		if not author in toProcess:
			toProcess.append(author)
	print "TOTAL KEY ACTORS:",len(toProcess)
	for author in toProcess:
		print author," - ".join(groups[author])
		fPost=firstEwhoring[author][0]
		query=('SELECT "Content","Thread" FROM "Post" WHERE "IdPost"=%s and "Site"=0 '%(fPost)) 
		cursor=connector.cursor()
		cursor.execute(query)
		row=cursor.fetchone()
		content,thread=row
		query=('SELECT "Heading","Author" FROM "Thread" WHERE "IdThread"=%s and "Site"=0 '%(thread)) 
		cursor.execute(query)
		row=cursor.fetchone()
		cursor.close()
		heading,opAuthor=row
		if opAuthor==author:
			opAuthor='SAME (%s)'%opAuthor
		print "FIRST_POST_EWHORING: %s"%(content.replace('\n','\\'))
		print "OPAUTHOR:%s HEADING: %s"%(opAuthor,heading.replace('\n','\\'))
		print




# Returns the overall time span of each site related to eWhoring
def get_time_span():
	filename=OUTPUT_DIR+"/threads_ewhoring_all_forums.pickle"
	if not os.path.exists(filename):
			print "ERROR. %s not found"%filename
			return
	data=pickle.load(open(filename))
	for site in data:
		forums=[f for f in data[site] if not 'total' in str(f)]
		firstPost=datetime.now()
		lastPost=datetime(1900,1,1)
		query=('SELECT "Name" FROM "Site" WHERE "IdSite"=%s'%(site)) 
		cursor=connector.cursor()
		cursor.execute(query)
		name=cursor.fetchone()[0]
		print "Processing %s"%name
		for forum in forums:
			for idThread in data[site][forum]:
				if not 'total' in str(idThread):
					query=('SELECT "Timestamp" FROM "Post" WHERE "Thread"=%s and "Site"=%s ORDER BY "Timestamp" ASC LIMIT 1'%(idThread,site)) 
					cursor=connector.cursor()
					cursor.execute(query)
					row=cursor.fetchone()
					if row:
						timestamp=row[0].replace(tzinfo=None)
						if int(timestamp.strftime("%Y"))>2005:
							if timestamp<firstPost:
								firstPost=timestamp
							if timestamp>lastPost:
								lastPost=timestamp
		print "SITE:%s. First Post:%s, Last Post:%s"%(name,firstPost.date(),lastPost.date())
		print "%s & %s-%s"%(name,firstPost.strftime("%m/%y"),lastPost.strftime("%m/%y"))








if __name__ == "__main__" :   
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	get_num_threads_ewhoring_per_site(latex=True)