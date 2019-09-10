from datetime import datetime,timedelta
import re
import os
import pickle
from collections import defaultdict
import psycopg2
import getpass
import pandas as pd
from datetime import datetime
tsFormat='%Y%m%d_%H%M%S'

# FILE_DIR='../../files/'
FILE_DIR='../../files/'

PATH_FILES=FILE_DIR
DATA_FILE=PATH_FILES+'data_all.pickle'


DB_NAME='crimebb'

currencies={'EUR':['eur'],
			'British Pound':['gbp','pound','sterling'],
			'USD':['usd','dollars'],
			'AUD':['aud'],
			'Canadian Dollar':['cad','cdn']
			}
platforms={'Amazon':['amazon','agc'],
		   'Paypal':['pp','paypal'],
		   'Bitcoin':['btc','bitcoin']}
connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)	
perSiteData=pd.read_csv(FILE_DIR+'proofEarnings.csv')

def get_author_time_stats():
	global author_time_stats
	filename=FILE_DIR+'/ewhoring_actors_time.csv'
	if not os.path.exists(filename):
		print ("ERROR:%s not found"%filename)
		exit()
	author_time_stats=pd.read_csv(filename)



def getSite(idPost):
	posts = list(perSiteData[ (perSiteData['POST'] == int(idPost))]['SITE'])
	if len(posts)>0:
		return posts[0]
	return 0

def generateStats(outputFile):
	connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
	fd=open(outputFile,'w+')
	fd.write("AUTHOR,SITE,POST,BOARD,TS_POST,TS_FROM,TS_TO,PLATFORM,CURRENCY,N_TRANSACTIONS,TOTAL_AMOUNT,PER_DAY\n")
	postsEarnings={}
	print ("%s Going to process %s annotations..."%(datetime.now().strftime(tsFormat),len(data.keys())))
	filenames=[]
	for c,filename in enumerate(data.keys()):
		# if c>0 and c%20==0:
		# 	print ("%s Processed %s annotations."%(datetime.now().strftime(tsFormat),c))
		year=filename.split('_')[0]
		post=filename.split('_')[3]
		if data[filename]['isProof']:
			per_day='NA'
			platform=data[filename]['platform']
			numTransactions=0
			total=data[filename]['totalAmount']
			timestampFrom='NA'
			timestampTo='NA'
			fromT=None
			toT=None
			if data[filename]['hasTransactions']:
				numTransactions=data[filename]['numTransactions']
				if data[filename]['transactionTotal']>0:
					total=data[filename]['transactionTotal']
				timestampFrom=data[filename]['transactionFrom'].strftime("%Y%m%d")
				timestampTo=data[filename]['transactionTo'].strftime("%Y%m%d")
				if int(timestampFrom[:4])>2000 and int(timestampTo[:4])>2000:
					days=(data[filename]['transactionTo']-data[filename]['transactionFrom']).days+1
					fromT=data[filename]['transactionFrom']
					toT=data[filename]['transactionTo']
					if days>0:
						per_day="%.2f"%(float(total)/days)
				elif "same day" in data[filename]['notes'].lower():				
					per_day="%.2f"%(float(total))	
			currencies= getCurrencies(data[filename])

			if len(currencies)>1:
				currency=currencies[0]
				print ("WARNING. File: %s. More than one currency found: %s"%(filename," ".join(currencies)))
				usdExchange=1
			elif len(currencies)==1:
				currency=currencies[0]
				if fromT is not None:
					usdExchange=getUSD_exchange(currencies[0],fromT)
				elif toT is not None:
					usdExchange=getUSD_exchange(currencies[0],toT)
				else: # If the dates are missing, we take the first of June of the year
					usdExchange=getUSD_exchange(currencies[0],datetime(int(year),6,1))
			else:
				print ("WARNING. File: %s. Missing currency"%(filename))
				currency=data[filename]['currency']
				usdExchange=1.0
			if usdExchange==0:
				print ("WARNING. File: %s. Exchange is 1"%(filename))
				usdExchange=1.0
			total=total*(1.0/usdExchange)
			if str(total)=='nan':
				total=0.0
			site=getSite(int(post))
			query=('SELECT "Timestamp","Post"."Author","Forum" FROM "Post","Thread" WHERE "Post"."Thread"="IdThread" AND "IdPost"=%s AND "Post"."Site"=%s AND "Thread"."Site"=%s'%(post,site,site))
			cursor=connector.cursor()
			cursor.execute(query)
			row=cursor.fetchone()
			if row:
				timestampPost=row[0].strftime("%Y%m%d")
				timestampPost1=row[0]
				author=row[1]
				forum=row[2]
				fd.write("%s,%s,%s,%s,%s,%s,%s,\"%s\",\"%s\",%s,%s,%s\n"%(author,site,post,forum,timestampPost,timestampFrom,timestampTo,platform,currency,numTransactions,total,per_day))
			else:
				print ("WARNING. File: %s. Post %s, Site:%s not found in DB"%(filename,post,site))
			cursor.close()		
			
	connector.close()
	fd.close()
def extractPlatformsFromText(text):
	toReturn=[]
	for c in platforms:
		for value in platforms[c]:
			if value.lower() in text.lower():
				toReturn.append(c)
	return toReturn
def extractCurrenciesFromText(text):
	toReturn=[]
	for c in currencies:
		for value in currencies[c]:
			if value in text.lower():
				toReturn.append(c)
	return toReturn
def getPlatforms(data):
	platforms=[]
	otherPlatforms=extractPlatformsFromText(data['notes'])
	if len(otherPlatforms)>0:
		for o in otherPlatforms:
			if o!=data['platform']:
				platforms.append(o)
	if not data['platform'].lower()=='missing' and not data['platform'].lower()=='unknown':
		otherPlatforms=extractPlatformsFromText(data['platform'])
		if len(otherPlatforms)>0:
			platforms.extend(extractPlatformsFromText(data['platform']))
		else:
			platforms=[f.strip() for f in data['platform'].split(',') if not f.strip()=='']
		
	return list(set(platforms))
def getCurrencies(data):
	currencies=[]
	for k,value in data.items():
		if k=='notes' and value!='' and not 'converted' in value.lower():
			otherCurrencies=extractCurrenciesFromText(value)
			if len(otherCurrencies)>0:
				for o in otherCurrencies:
					if o!=data['currency']:
						currencies.append(o)
				
		elif k=='currency' and not data[k].lower()=='missing' and not data[k].lower()=='unknown':
			currencies.append(value)
	return currencies
def getDate(data):
	if data['hasTransactions']:
		if data['transactionTo']>=datetime.strptime('2000','%Y'):
			return data['transactionTo']
		elif data['transactionFrom']>=datetime.strptime('2000','%Y'):
	 		return data['transactionFrom']
	return None

def printData():
	for filename in data.keys():	
		year=filename.split('_')[0]
		postID=filename.split('_')[3]
		if data[filename]['isProof']:
			print (filename)
			currencies=getCurrencies(data[filename])
			if len(currencies)>0:
				print ("\t CURRENCIES:",' '.join(currencies))
			date=getDate(data[filename])
			if date:
				print ("\t DATE",date.strftime("%d-%m-%Y"))
			if data[filename]['hasTransactions']:
				print ("\t NUM TRANSACTIONS",data[filename]['numTransactions'])
				amount=data[filename]['transactionTotal']
			else:
				print ("\t WITHOUT TRANSACTIONS")
				amount=data[filename]['totalAmount']
			print ("\t AMOUNT",amount)
			platforms=getPlatforms(data[filename])
			if len(platforms)>0:
				print ("\t PLATFORMS:",' '.join(platforms))
def getAuthor(postID):
	author=None
	site=getSite(postID)
	query=('SELECT "Author" FROM "Post" WHERE "IdPost"=%s and "Site"=%s'%(postID,site))
	cursor=connector.cursor()
	cursor.execute(query)
	row=cursor.fetchone()
	if row: 
		author=row[0]
	return author
def getFirstDate(date1,date2):
	if date1 is None:
		return date2
	if date2 is None:
		return date1	
	if date1>date2:
		return date2
	return date1
def getLastDate(date1,date2):
	if date1 is None:
		return date2
	if date2 is None:
		return date1
	if date1<date2:
		return date2
	return date1	



def getUSD_exchange(currency,date,verbose=False):
	day=date.strftime('%Y-%m-%d')
	if currency=='USD':
		exchange=1.0
	elif currency=='EUR':
		try:
			exchange=float(usd_exchange.loc[usd_exchange['Time Period']==day,'D:DE:EUR:A'])
		except:
			if verbose: print ("WARNING. Could not find exchange for %s on %s. Using 1"%(currency,day))
			exchange=1.0
	elif currency=='British Pound':
		try:
			exchange=float(usd_exchange.loc[usd_exchange['Time Period']==day,'D:GB:GBP:A'])
		except:
			if verbose: print ("WARNING. Could not find exchange for %s on %s. Using 1"%(currency,day))
			exchange=1.0
	elif currency=='Canadian Dollar':
		try:
			exchange=float(usd_exchange.loc[usd_exchange['Time Period']==day,'D:CA:CAD:A'])
		except:
			if verbose: print ("WARNING. Could not find exchange for %s on %s. Using 1"%(currency,day))
			exchange=1.0
	elif currency=='AUD':
		try:
			exchange=float(usd_exchange.loc[usd_exchange['Time Period']==day,'D:AU:AUD:A'])
		except:
			if verbose: print ("WARNING. Could not find exchange for %s on %s. Using 1"%(currency,day))
			exchange=1.0
	elif currency=='DKK':
		try:
			exchange=float(usd_exchange.loc[usd_exchange['Time Period']==day,'D:DK:DKK:A'])
		except:
			if verbose: print ("WARNING. Could not find exchange for %s on %s. Using 1"%(currency,day))
			exchange=1.0
	elif currency.strip().lower()=='bitcoin' or currency.strip().lower()=='btc':
		# Note: For performance purposes, these were calculated once
		adhocExchanges={'2014-06-01':340.9,'2016-06-01':534.84,'2017-10-12':4816.6,'2017-06-01':2418.64}
		return adhocExchanges[day]
	else:
		if verbose: print ("WARNING: Currency %s not supported"%currency)
		exchange=1.0
	return exchange
def calculateEarningsPerAuthor(verbose=False):
	earnings_per_author={}
	for filename in data.keys():	
		year=filename.split('_')[0]
		postID=filename.split('_')[3]
		if data[filename]['isProof']:
			author=getAuthor(postID)
			amount=float(data[filename]['totalAmount'])
			if amount<0: amount=0.0
			numTransactions=0
			fromT=None
			toT=None					
			if data[filename]['hasTransactions']:
				numTransactions=data[filename]['numTransactions']		
				if data[filename]['transactionFrom']>=datetime.strptime('2000','%Y'): 
					fromT=data[filename]['transactionFrom']
				if data[filename]['transactionTo']>=datetime.strptime('2000','%Y'):
					toT=data[filename]['transactionFrom']
			
			platforms=getPlatforms(data[filename])
			currencies= getCurrencies(data[filename])
			if len(currencies)>1:
				if verbose: print ("WARNING. File: %s. More than one currency found: %s"%(filename," ".join(currencies)))
				usdExchange=1
			elif len(currencies)==1:
				if fromT is not None:
					usdExchange=getUSD_exchange(currencies[0],fromT)
				elif toT is not None:
					usdExchange=getUSD_exchange(currencies[0],toT)
				else: # If the dates are missing, we take the first of June of the year
					usdExchange=getUSD_exchange(currencies[0],datetime(int(year),6,1))
			else:
				if verbose: print ("WARNING. File: %s. Missing currency"%(filename))
				usdExchange=1.0
			if usdExchange==0:
				if verbose: print ("WARNING. File: %s. Exchange is 0"%(filename))
				usdExchange=1.0
			amount=amount*(1.0/usdExchange)
			if str(amount)=='nan':
				amount=0.0
			if not author in earnings_per_author:
				earnings_per_author[author]={'total':amount,'start':fromT,'end':toT,'numProofs':1,'platforms':platforms,'currencies':currencies,'numTransactions':numTransactions}
			else:
				earnings_per_author[author]['total']+=amount
				earnings_per_author[author]['numTransactions']+=numTransactions
				earnings_per_author[author]['numProofs']+=1
				earnings_per_author[author]['start']=getFirstDate(earnings_per_author[author]['start'],fromT)
				earnings_per_author[author]['end']=getLastDate(earnings_per_author[author]['end'],toT)
				earnings_per_author[author]['currencies'].extend([f for f in currencies if not f in earnings_per_author[author]['currencies']])
				earnings_per_author[author]['platforms'].extend([f for f in platforms if not f in earnings_per_author[author]['platforms']])
	# print ("STORED: %s"%earnings_per_author[1093336]['total'])
	ordered=sorted(earnings_per_author,key=lambda x: (earnings_per_author[x]['total']),reverse=True)
	# print ("[")
	print ("AUTHOR,EARNINGS,NUM_PROOFS")
	for author in ordered:
		total=earnings_per_author[author]['total']
		if total>500 and total<=5000:
			numProofs=earnings_per_author[author]['numProofs']
			print ("%s,%s,%s"%(author,total,numProofs))
	return
	for author in ordered[:50]:
		# print ("%s,"%author)
	# print ("]")		
		print ("Author: %s"%author)
		print ("Amount: %.2f"%earnings_per_author[author]['total'])
		print ("NumProofs: %s"%earnings_per_author[author]['numProofs'])
		print ("NumTransactions: %s"%earnings_per_author[author]['numTransactions'])
		print ("Currencies: %s"%(" ".join(earnings_per_author[author]['currencies'])))
		print ("Platforms: %s"%(" ".join(earnings_per_author[author]['platforms'])))
		if earnings_per_author[author]['start'] is not None and earnings_per_author[author]['end'] is not None:
			print ("Period: [%s] - [%s]"%(earnings_per_author[author]['start'].strftime("%d-%m-%Y"),earnings_per_author[author]['end'].strftime("%d-%m-%Y")))
		print ("--------------------")
	moreThan=defaultdict(lambda:0)
	listMT=list(range(1000,-100,-100))
	listMT.extend(list(range(10000,1000,-1000)))
	listMT.extend(list(range(100000,10000,-10000)))
	listMT=sorted(listMT,reverse=True)
	sumTotal=0
	for author in ordered:
		total=earnings_per_author[author]['total']
		print (author,total)
		sumTotal+=total
		for m in listMT:
			if total>=m:
				moreThan[m]+=1
				break
	print ("Average per author:%.2f"%(sumTotal/len(ordered)))
	# for m in listMT:
	# 	print ("Authors making more than %d: %d"%(m,moreThan[m]))
	return earnings_per_author
def globalAnalysis(verbose=False):
	paypalsPerMonth=defaultdict(lambda:0)
	amazonsPerMonth=defaultdict(lambda:0)
	total_amountPerDay=defaultdict(lambda:0)  
	total_amountPerTransactions=defaultdict(lambda:0)
	imageWithTransactionAmount=defaultdict(lambda:0)
	imageWithTransactionDates=defaultdict(lambda:0)
	total_numTransactions=defaultdict(lambda:0)
	numPaypals=defaultdict(lambda:0)
	numAmazon=defaultdict(lambda:0)
	numProofsWithTransactions=defaultdict(lambda:0)
	numNonProofs=defaultdict(lambda:0)
	numProofs=defaultdict(lambda:0)
	numOthersPlatforms=defaultdict(lambda:0)
	paypalAuthors=defaultdict(lambda:0)
	amazonAuthors=defaultdict(lambda:0)
	earnings_per_author={}
	# paypalFilesFD=open(FILE_DIR+'paypalProofOfEarnings.csv','w+')
	highestTotal=0
	periodHighestTotal=0
	fileHighestTotal=''
	totalAmount=0
	postsPaypal=[]
	postsAmazon=[]
	amazonEarnings=0
	paypalEarnings=0
	postAmounts={}
	platformsData=defaultdict(lambda:{'proofs':0,'amount':0})
	for filename in data.keys():	
		year=filename.split('_')[0]
		postID=filename.split('_')[3]
		# author=getAuthor(postID)
		if data[filename]['isProof']:
			author=getAuthor(postID)
			amount=float(data[filename]['totalAmount'])
			if amount<0: amount=0
			numTransactions=0
			fromT=None
			toT=None			
			if data[filename]['hasTransactions']:
				numTransactions=data[filename]['numTransactions']		
				if data[filename]['transactionFrom']>=datetime.strptime('2000','%Y'): 
					fromT=data[filename]['transactionFrom']
					if fromT.strftime("%y")=='00':
						year=filename[:4]
					else:
						year=fromT.strftime("%Y")
				if data[filename]['transactionTo']>=datetime.strptime('2000','%Y'):
					toT=data[filename]['transactionTo']

			numProofs[year]+=1
			currencies= getCurrencies(data[filename])
			if len(currencies)>1:
				if verbose: print ("WARNING. File: %s. More than one currency found: %s"%(filename," ".join(currencies)))
				usdExchange=1
			elif len(currencies)==1:
				if fromT is not None:
					usdExchange=getUSD_exchange(currencies[0],fromT)
				elif toT is not None:
					usdExchange=getUSD_exchange(currencies[0],toT)
				else: # If the dates are missing, we take the first of June of the year
					usdExchange=getUSD_exchange(currencies[0],datetime(int(year),6,1))
			else:
				if verbose: print ("WARNING. File: %s. Missing currency"%(filename))
				usdExchange=1.0
			if usdExchange==0:
				if verbose: print ("WARNING. File: %s. Exchange is 0"%(filename))
				usdExchange=1.0
			amount=amount*(1.0/usdExchange)
			if str(amount)=='nan':
				amount=0

			platforms=getPlatforms(data[filename])
			if 'Paypal' in platforms:
				numPaypals[year]+=1
				paypalAuthors[author]+=1
				paypalEarnings+=amount
				# paypalFilesFD.write(filename+'\n')
			if 'Amazon' in platforms:
				numAmazon[year]+=1
				amazonAuthors[author]+=1
				amazonEarnings+=amount
			if len(platforms)==0 or (not 'Paypal' in platforms and not 'Amazon' in platforms):
				numOthersPlatforms[year]+=1
			for p in platforms:
				platformsData[p]['proofs']+=1
				platformsData[p]['amount']+=amount
			postAmounts[postID]=amount
			
			
			totalAmount+=amount
			if not author in earnings_per_author:
				earnings_per_author[author]={'total':amount,'start':fromT,'end':toT,'numProofs':1,'platforms':platforms,'currencies':currencies,'numTransactions':numTransactions}
			else:
				earnings_per_author[author]['total']+=amount
				earnings_per_author[author]['numTransactions']+=numTransactions
				earnings_per_author[author]['numProofs']+=1
				earnings_per_author[author]['start']=getFirstDate(earnings_per_author[author]['start'],fromT)
				earnings_per_author[author]['end']=getLastDate(earnings_per_author[author]['end'],toT)
				earnings_per_author[author]['currencies'].extend([f for f in currencies if not f in earnings_per_author[author]['currencies']])
				earnings_per_author[author]['platforms'].extend([f for f in platforms if not f in earnings_per_author[author]['platforms']])
			if fromT is not None or toT is not None:
				numProofsWithTransactions[year]+=1
				if data[filename]['numTransactions']>0 and data[filename]['transactionTotal']>=0:
					total_amountPerTransactions[year]+=data[filename]['transactionTotal']/data[filename]['numTransactions']
					imageWithTransactionAmount[year]+=1	
					if fromT is not None and toT is not None:
						numDays=(toT-fromT).days+1
						total_amountPerDay[year]+=data[filename]['transactionTotal']/numDays
						imageWithTransactionDates[year]+=1
						if data[filename]['transactionTotal']>highestTotal:
							highestTotal=data[filename]['transactionTotal']
							periodHighestTotal=numDays
							fileHighestTotal=filename
					if fromT is not None:
						monthYear=fromT.strftime("%m/")+year
					else:
						monthYear=toT.strftime("%m/")+year
					#print (filename,monthYear)
					if 'Paypal' in platforms:
						paypalsPerMonth[monthYear]+=1
					if 'Amazon' in platforms:
						amazonsPerMonth[monthYear]+=1
				elif data[filename]['numTransactions']==1:
					total_amountPerDay[year]+=data[filename]['transactionTotal']
					imageWithTransactionDates[year]+=1
		
		else:
			numNonProofs[year]+=1
	# paypalFilesFD.close()
	
	# print ("Period,Paypal,Amazon")			
	# for year in range(2011,2019):
	# 	for month in range(1,13):
	# 		if month<10:
	# 			m='0'+str(month)
	# 		else:
	# 			m=str(month)
	# 		monthYear=m+"/"+str(year)
	# 		print ("%s,%s,%s"%(monthYear,paypalsPerMonth[monthYear],amazonsPerMonth[monthYear]))
	# exit(0)	
		
	sumProofs=0
	sumProofsTransactions=0
	sumAveragePerTransaction=0
	sumNoProofs=0
	sumPaypals=0
	sumAmazons=0
	sumOtherPlatforms=0		
	for year in numProofs:
		avg_amountPerDay=total_amountPerDay[year]/imageWithTransactionDates[year]
		avg_amountPerTransaction=total_amountPerTransactions[year]/imageWithTransactionAmount[year]
		print ("Year %s:"%year)
		print ("\tNumber of proofs %s"%numProofs[year])
		sumProofs+=numProofs[year]
		print ("\tNumber of proofs with transactions %s"%numProofsWithTransactions[year])
		sumProofsTransactions+=numProofsWithTransactions[year]
		print ("\t Average per transaction %.2f"%avg_amountPerTransaction)
		sumAveragePerTransaction+=avg_amountPerTransaction
		print ("\tNumber of non proofs %s"%numNonProofs[year])
		sumNoProofs+=numNonProofs[year]
		print ("\tNum. paypals %s"%numPaypals[year])
		sumPaypals+=numPaypals[year]
		print ("\tNum. amazon %s"%numAmazon[year])
		sumAmazons+=numAmazon[year]
		print ("\tNum. other %s"%numOthersPlatforms[year])
		sumOtherPlatforms+=numOthersPlatforms[year]
	print ("Number of annotated files: %s"%len(data))
	print ("Number of proofs:%s, of which with transactions:%s"%(sumProofs,sumProofsTransactions))
	print ("Total amount:%.2f"%(totalAmount))
	print ("Average per transaction: %.2f"%(float(sumAveragePerTransaction)/len(numProofs)))
	print ("Number of non proofs:%s"%sumNoProofs)
	print ("Total authors: %d"%len(earnings_per_author))
	print ("Number of Paypal:%s (from %s different authors). Total earnings: %.2f"%(sumPaypals,len(paypalAuthors.keys()),paypalEarnings))
	print ("Number of Amazon:%s (from %s different authors). Total earnings: %.2f"%(sumAmazons,len(amazonAuthors.keys()),amazonEarnings))
	print ("Number of authors with both Amazon and Paypal earnings: %s"%(sum(1 for f in paypalAuthors.keys() if f in amazonAuthors.keys())))
	print ("Number of other platforms:%s"%sumOtherPlatforms)
	for p in sorted(platformsData,key=lambda x:platformsData[x]['proofs'],reverse=True):
		print ("\t %s -> PROOFS:%d, TOTAL_AMOUNT:%.2f"%(p,platformsData[p]['proofs'],platformsData[p]['amount']))
	print ("Highest Total %s, Period:%s days, Filename %s"%(highestTotal,periodHighestTotal,fileHighestTotal))



if os.path.exists(DATA_FILE):
	data,currentFile=pickle.load(open(DATA_FILE,'rb'))
	usd_exchange=pd.read_csv(FILE_DIR+'usd_value.csv')
else:
	print ("ERROR. %s not found"%DATA_FILE)
	exit(-1)

# get_author_time_stats()
globalAnalysis()
# exit()
# calculateEarningsPerAuthor()
# printData()		
# generateStats(FILE_DIR+'proofOfEarnings_annotationStats.csv')





