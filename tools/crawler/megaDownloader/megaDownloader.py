# -*- coding: utf-8 -*-

import signal
import random
import os 
import stem
import stem.process
import time
import pickle
import csv

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.common.exceptions import TimeoutException

tsFormat='%Y%m%d_%H%M%S'

# NOTE:
# This crawler relied on directme.ga service provided by https://github.com/qgustavor/direct-mega
# Since October'18 this service is down (https://github.com/qgustavor/direct-mega/issues/21)
# Thus, this script no longer works (at is is)


# mega has a download limit based on the IP, after which the IP gets blocked. This block is eventually lifted, but the waiting time is dynamic. 
# It would be advisable to spread the download of mega based files among different days, maybe using cron jobs, and/or use different proxies
PROXY_PORT=80
proxyListFile="proxyList.txt"



PROJECT_DIR='../../'
OUTPUT_DIR=(PROJECT_DIR+'files/images/packs/')
PROCESSED_URL_FILE=PROJECT_DIR+'files/processedURLDownload.pickle'
FILE_LIST=PROJECT_DIR+'/files/fileLink_listMEGA.csv'
ERROR_DIR=PROJECT_DIR+'tools/logs/directmeGA_errors/'

STATUS_CODES={0:'OK',1:'ERROR',2:'MANUAL',3:'MEGA',4:'NOT-FOUND-MEGA'}

binary=FirefoxBinary('/usr/local/bin/firefox')

def getRandomProxy():
	relays=open(proxyListFile).readlines()
	random.shuffle(relays)
	return relays[0].replace('\n','')

def downloadMegaFile(mega_identifier,dest_path):
	profile = FirefoxProfile()
	maxAttempts100=10
	relay=getRandomProxy()
	print ("%s Using random proxy proxy: %s"%(datetime.now().strftime(tsFormat),relay))
	profile.set_preference( "network.proxy.type", 1 )
	profile.set_preference( "network.proxy.http", relay )
	profile.set_preference( "network.proxy.ssl", relay )
	profile.set_preference( "network.proxy.http_port", PROXY_PORT )
	profile.set_preference( "network.proxy.ssl_port", PROXY_PORT )

	# Set Firefox to download into the given path
	profile.set_preference("browser.download.panel.shown", False)
	profile.set_preference("browser.helperApps.neverAsk.openFile", "application/zip,application/x-rar-compressed,video/webm,application/octet-stream,application/x-7z-compressed,application/gzip,application/tar")
	profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip,application/x-rar-compressed,video/webm,application/octet-stream,application/x-7z-compressed,application/gzip,application/tar")
	profile.set_preference("browser.download.folderList", 2);
	profile.set_preference("browser.download.dir", dest_path)

	print ("%s Connecting to driver"%(datetime.now().strftime(tsFormat)))
	driver=webdriver.Firefox(firefox_profile=profile,firefox_binary=binary)
	print ("%s Downloading file mega_identifier=%s..."%(datetime.now().strftime(tsFormat),mega_identifier))

	driver.get('https://directme.ga/'+mega_identifier)
	downloading=True
	errorPage=ERROR_DIR+'error%s.html'%mega_identifier.replace('#','')
	attempt100=0
	while downloading:
		try:
			hyperlinks = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//a")))
			hyperlinks = driver.find_elements_by_xpath("//a")
			if len(hyperlinks)==1:
				print ("%s DONE!"%datetime.now().strftime(tsFormat))
			elif ("file not found" in driver.page_source.encode('utf8').lower()):
				print ("%s ERROR: File not found for mega_identifier %s"%(datetime.now().strftime(tsFormat),mega_identifier))
				open(errorPage,'wb').write(driver.page_source.encode('utf8'))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 4
			elif 'Select a file from the list below:' in driver.page_source.encode('utf8'):
				listFiles=ERROR_DIR+"listFiles%s.csv"%mega_identifier.replace('#','')
				fd=open(listFiles,'wb')
				details=driver.find_elements_by_xpath('//details')
				if len(details)>0:
					for folder in details:
						folderName=folder.find_element_by_xpath('./summary').text
						links=folder.find_elements_by_xpath('./ul/li/a')
						for l in links:		
							fd.write("%s,%s\n"%(folderName,l.get_attribute('href')))
				else:
					links=driver.find_elements_by_xpath('//a')
					for l in links:		
						fd.write("-,%s\n"%(l.get_attribute('href')))
				fd.close()
				print ("%s WARNING: url %s is a folder. (List of files dumped to %s)"%(datetime.now().strftime(tsFormat),mega_identifier,listFiles))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 2
			elif 'Object (typically, node or user) not found':
				print ("%s ERROR: Object not found for mega_identifier %s (maybe password protected)"%(datetime.now().strftime(tsFormat),mega_identifier))
				open(errorPage,'wb').write(driver.page_source.encode('utf8'))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 4
			elif len(hyperlinks)>1:
				print ("%s WARNING. Found %s hyperlinks in mega_identifier %s. (see %s)"%(datetime.now().strftime(tsFormat),len(hyperlinks),mega_identifier,errorPage))
				open(errorPage,'wb').write(driver.page_source.encode('utf8'))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 1
			else:
				print ("%s ERROR: Something went wrong with mega_identifier %s. Bandwith limit reached? (see %s)"%(datetime.now().strftime(tsFormat),mega_identifier,errorPage))
				open(errorPage,'wb').write(driver.page_source.encode('utf8'))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 1
			downloading=False
		except TimeoutException:
			if "Downloading" in driver.page_source.encode('utf8'):
				status=driver.find_element_by_xpath('/html/body/p[last()]').text
				if not "Downloading" in status:
					print ("%s ERROR: Could not retrieve the file for mega_identifier %s (see %s)"%(datetime.now().strftime(tsFormat),mega_identifier,errorPage))
					open(errorPage,'wb').write(driver.page_source.encode('utf8'))
					driver.service.process.send_signal(signal.SIGTERM)
					driver.quit()
					return 1
				elif "100.00%" in status:
					attempt100+=1
					print"%s 100%% downloaded. Attempt %s out of %s"%(datetime.now().strftime(tsFormat),attempt100,maxAttempts100)
					if attempt100>=maxAttempts100:
						print ("%s WARNING: Reached 100%% but file not downloaded for mega_identifier %s (see %s)"%(datetime.now().strftime(tsFormat),mega_identifier,errorPage))
						open(errorPage,'wb').write(driver.page_source.encode('utf8'))
						driver.service.process.send_signal(signal.SIGTERM)
						driver.quit()
						return 1
				else:
					print"%s %s"%(datetime.now().strftime(tsFormat),status)
			else:
				print ("%s ERROR: Could not retrieve the file for url %s (see %s)"%(datetime.now().strftime(tsFormat),mega_identifier,errorPage))
				open(errorPage,'wb').write(driver.page_source.encode('utf8'))
				driver.service.process.send_signal(signal.SIGTERM)
				driver.quit()
				return 1
	#finally:
	
	print ("%s Quitting..."%datetime.now().strftime(tsFormat))
	driver.service.process.send_signal(signal.SIGTERM)
	driver.quit()
	while (len(os.listdir(dest_path))==0):
		print ("%s Downloading file to %s for mega_identifier %s ... "%(datetime.now().strftime(tsFormat),dest_path,mega_identifier))
		time.sleep(2)
	return 0
def check(url):
	driver=webdriver.PhantomJS()
	driver.get(url)
	try:
		error=driver.find_element_by_xpath('//div[@class="download error-title"]').text
		if error.strip=='':
			raise Exception
		print ("%s ERROR: Checking %s failed %s"%(datetime.now().strftime(tsFormat),url,error))
		return False
	except:
		return True
def parseFileAndCrawl(filename):
	if os.path.exists(PROCESSED_URL_FILE):
		processed=pickle.load(open(PROCESSED_URL_FILE))
	else:
		processed={}

	fd=open(filename)
	csvreader = csv.reader(fd)
	for line in list(csvreader):
		thread,post,timestamp,author,numUrls,posUrl,url=line
		year=timestamp[:4]
		if not url.startswith('http'):
			url='https://'+url
		if not url in processed.keys():
			processed[url]={}
			processed[url]['post']=post
			processed[url]['position']=posUrl
		
			mega_identifier=url[url.rfind('/')+1:]
			destination=PROJECT_DIR+'files/megaTMP/'
			codeReturn=downloadMegaFile(mega_identifier,destination)
			if codeReturn==0:
				prefix=post+"_"+posUrl+'_megaNZ_'
				dest_path=OUTPUT_DIR+year
				megaFileName=os.listdir(destination)[0]
				newName=prefix+megaFileName.replace(' ','-')
				os.rename(destination+"/"+megaFileName,dest_path+'/'+newName)
				print ("%s Renaming %s to %s"%(datetime.now().strftime(tsFormat),destination+"/"+megaFileName,dest_path+'/'+newName))
				processed[url]['status']=STATUS_CODES[codeReturn]+dest_path
			else:		
				processed[url]['status']=STATUS_CODES[codeReturn]		
		else:
			previousPost=processed[url]['post']
			previousPosition=processed[url]['position']
			try:
				status=processed[url]['status']
			except KeyError:
				status='ERROR'
			print ("%s URL already processed.URL=%s,PREV_POST=%s,THIS_POST=%s,PREVIOUS_POSITION=%s,THIS_POSITION=%s,STATUS=%s"%(datetime.now().strftime(tsFormat),url,previousPost,post,previousPosition,posUrl,status)			)
		pickle.dump(processed,open(PROCESSED_URL_FILE,'wb'))	

	

parseFileAndCrawl(FILE_LIST)
		

