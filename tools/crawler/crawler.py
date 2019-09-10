
# This script parses a list of URLS from a file (together with their metadata) which are the ouput of extractPacks or extractProofOfEarnings scripts
# Then, each URL is crawled and the images/files are stored in the outputdir

import argparse
import os
import sys
import re
import shutil
import urlparse
import urllib
import requests
import pickle 

from requests import ConnectionError
from bs4 import BeautifulSoup
from selenium import webdriver
from datetime import datetime,timedelta
import csv

tsFormat='%Y%m%d_%H%M%S'



FILE_LIST='../files/proofEarnings_per_site.csv'
OUTPUT_DIR='../files/images/proofOfEarnings/'

#FILE_LIST='../files/fileLink_list.csv'
#OUTPUT_DIR='../../files/images/packs/'

# FILE_LIST='../files/imageLink_list.csv'
# OUTPUT_DIR='../../files/images/previews/'



PROCESSED_URL_FILE='../files/processedURLDownload.pickle'
MEGANZ_LINKS_FILE='../files/megaLinkFiles.csv'

STATUS_CODES={0:'OK',1:'ERROR',2:'MANUAL',3:'MEGA'}
userAgent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0'
headers=requests.utils.default_headers()
headers.update({'User-Agent': userAgent})



def getArgParser():
	parser = argparse.ArgumentParser(
			 description="Crawl given album and save all images within.",
			 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument("url", metavar="url", type=str,
						help="the source URL")
	parser.add_argument("dest", metavar="dest", type=str, nargs='?', default=".",
						help="the destination folder to save image")
	parser.add_argument("-s", "--simple", action="store_true", default=False,
						help="not show download status")
	return parser

def requestURL(src_url):
	try:
		print ("%s Requesting %s"%(datetime.now().strftime(tsFormat),src_url))
		r=requests.get(src_url,headers=headers)
	except ConnectionError:
		print ("%s Cannot connect to URL %s"%(datetime.now(),src_url))
		return None
	if r.status_code<200 or r.status_code>299:
		print ("%s ERROR. Code %s received for request on URL %s"%(datetime.now().strftime(tsFormat),r.status_code,src_url))
		return None
	return r.content

def downloadFile(src_url, dest_path, img_prefix=None, simple=False):
	if not os.path.exists(dest_path):
		os.makedirs(dest_path)	
	try:
		print ("%s Downloading file from %s"%(datetime.now().strftime(tsFormat),src_url))
		r = requests.get(src_url, stream=True,headers=headers)
	except ConnectionError as e:
		print ("%s ERROR. Cannot connect to URL %s"%(datetime.now().strftime(tsFormat),src_url))
		return 1
	if r.status_code<200 or r.status_code>299:
		print ("%s ERROR. Code %s received for request on URL %s"%(datetime.now().strftime(tsFormat),r.status_code,src_url))
		return 1
	else:
		pass;
		#print ("%s Response received from %s"%(datetime.now().strftime(tsFormat),src_url))
	if img_prefix is not None:
		outfname = os.path.join(dest_path, img_prefix+os.path.basename(src_url))
	else:
		outfname = os.path.join(dest_path, os.path.basename(src_url))
	with open(outfname, "wb") as outfile:
		if not simple:
			size_downloaded = 0
			size_total = len(r.content)

			for chunk in r.iter_content(chunk_size=8192):
				if chunk:
					outfile.write(chunk)
					size_downloaded += len(chunk)
					progress=size_downloaded * 100. / size_total
					sys.stdout.write ("%s Writing to disk %s %10d  [%3.2f%%] \r"%(datetime.now().strftime(tsFormat),src_url,size_downloaded, progress))
					sys.stdout.flush()
			print ()
		else:
			print ("%s Writing to disk %s..." % (datetime.now().strftime(tsFormat),src_url))
			shutil.copyfileobj(r.raw, outfile)
			print (" DONE!")
	return 0

def crawlMediafire(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)	
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		try:
			file_url=soup.find("a",class_="DownloadButtonAd-startDownload").get('href')
		except:
			print ("%s File from %s not found in mediafire"%(datetime.now().strftime(tsFormat),src_url))
			return 1	
		return downloadFile(file_url,dest_path,img_prefix,simple)
	return 1

def crawlZippyshare(src_url, dest_path, img_prefix=None, simple=False):
	#ZippyShare requires solving a javascript, so Selenium is used
	driver=webdriver.PhantomJS()
	driver.get(src_url)
	content=driver.page_source
	if content is not None:
		domain=src_url.split('/')[2]
		items= BeautifulSoup(content, "lxml").find_all(id='dlbutton')
		if len(items)==0:
			print ("%s Images from %s not found in zippyshare"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for i in items:
			file_url="http://"+domain+i.get('href')
			images.append(file_url)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1

def crawlGyazo(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("link",rel='image_src')
		if len(tlist)==0:
			print ("%s Images from %s not found in gyazo"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			image=t.get('href').split('?')[0]
			if not image in images:
				images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1
	
def crawlImgur(src_url, dest_path, img_prefix=None, simple=False):
	if src_url.endswith('zip'):
		print ("%s ZIP file from imgur %s"%(datetime.now().strftime(tsFormat),src_url))
		return 2
	driver=webdriver.PhantomJS()
	driver.get(src_url)
	content=driver.page_source.encode('utf-8')
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		open('prueba.html','wb').write(content)
		tlist=soup.find_all("div",class_='post-image-container')
		if len(tlist)==0:
			print ("%s Images from %s not found in imgur"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			imgs=t.find_all('img')
			for i in imgs:
				image=i.get('src').split('?')[0]
				if not 'https:'+image in images:
					images.append('https:'+image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1

def crawlPrnt(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("img",class_=re.compile("image__pic*"))
		if len(tlist)==0:
			print ("%s Images from %s not found in prnt"%(datetime.now().strftime(tsFormat),src_url))
			return 1		
		images=[]
		for t in tlist:
			image=t.get('src').split('?')[0]
			if not image in images:
				images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1

def crawlImagetwist(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("img",class_=re.compile("pic img*"))
		if len(tlist)==0:
			print ("%s Images from %s not found in ImageTwist"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			image=t.get('src')
			if not image in images:
				images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1

def crawlDirectupload(src_url, dest_path, img_prefix=None, simple=False):
	driver=webdriver.PhantomJS()
	driver.get(src_url)
	content=driver.page_source
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all(id="ImgFrame")
		if len(tlist)==0:
			print ("%s Images from %s not found in DirectUpload"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			image=t.get('src')
			if not image in images:
				images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1
def crawlPostimage(src_url, dest_path, img_prefix=None, simple=False):
	
	if 'gallery' in src_url:
		driver=webdriver.PhantomJS()
		driver.get(src_url)
		try:
			tlist=driver.find_elements_by_xpath('//div[@class="thumb"]/a')
		except:
			print ("%s Images from %s not found in gallery of PostImage. XPATH ERROR"%(datetime.now().strftime(tsFormat),src_url))
			tlist=[]
		if len(tlist)==0:
			print ("%s Images from %s not found in gallery of PostImage"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			image=t.get_attribute('href')
			if not image in images:
				images.append(image)
		for img_src in images:
			valid=crawlPostimage(img_src,dest_path,img_prefix,simple)
		return valid
	else:
		content=requestURL(src_url)
		if content is not None:
			soup = BeautifulSoup(content, "lxml")
			imageContainers=soup.find_all(id="main-image")
			if len(imageContainers)==0:
				print ("%s Images from %s not found in PostImage"%(datetime.now().strftime(tsFormat),src_url))
				return 1
			images=[]
			for i in imageContainers:
				image=i.get('src')
				if not image in images:
					images.append(image)
			for img_src in images:
				valid=downloadFile(img_src,dest_path,img_prefix,simple)
			return valid
	
		
	return 1
def crawlImagePorter(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("a",onclick_="javascript:ghisthendsx();")
		if len(tlist)==0:
			print ("%s Images from %s not found in ImagePorter"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			imageContainers=t.find_all('img')
			for i in imageContainers:
				image=i.get('src')
				if not image in images:
					images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1
def crawlImagebam(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("div",class_="image-container")
		if len(tlist)==0:
			print ("%s Images from %s not found in Imagebam"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			imageContainers=t.find_all('img')
			for i in imageContainers:
				image=i.get('src')
				if not image in images:
					images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1

def crawlImgbox(src_url, dest_path, img_prefix=None, simple=False):
	content=requestURL(src_url)
	if content is not None:
		soup = BeautifulSoup(content, "lxml")
		tlist=soup.find_all("div",class_="image-container")
		if len(tlist)==0:
			print ("%s Images from %s not found in Imagebam"%(datetime.now().strftime(tsFormat),src_url))
			return 1
		images=[]
		for t in tlist:
			imageContainers=t.find_all('img')
			for i in imageContainers:
				image=i.get('src')
				if not image in images:
					images.append(image)
		for img_src in images:
			valid=downloadFile(img_src,dest_path,img_prefix,simple)
		return valid
	return 1


file_sharing_sites={
					# ***********************************
					# Downloads from mega are special. Use special module megaDownloader.py
					# 'mega':crawlMega, 
					
					 'mediafire':crawlMediafire, 
					 #######
					 ## oron.com was suspended
					 #######
					
					
					# Zippyshare File Life: 30 days after no activity.
					 'zippyshare':crawlZippyshare, 
					
					# ***********************************
					# Drobox links must be analysed/download individually and manually
					# ***********************************					

					# ***********************************
					# GoogleDrive links must be analysed/download individually and manually										
					# **********************************

					# ***********************************
					# filedropper uses captcha to prevent crawlers. Must be download manually
					# 'filedropper':crawlFiledropper, 
					# ***********************************
					}


image_sites={
			'imgur':crawlImgur,
			'gyazo':crawlGyazo,
			'postimg':crawlPostimage,
			'postimage':crawlPostimage,
			# ***********************************
			# Photobucket links always are provided with the direct link to the img. 
			# Thus, it does not require special crawling
			# ***********************************
			#'photobucket':crawlPhotobucket,
			'directupload':crawlDirectupload, 
			'prnt':crawlPrnt,
			'imagetwist':crawlImagetwist,
			'imageporter':crawlImagePorter,
			'imgbox':crawlImgbox,
			'imagebam':crawlImagebam
			}

def crawl(url,dest_path,timestamp,img_prefix,year,verbose=False):
	url=url.strip()
	if url[-1]=='/':
		url=url[:-1]
	parsed=urlparse.urlparse(urllib.unquote(url.lower()))
	path=parsed.path
	if (path.endswith(".jpg") or path.endswith(".png") or path.endswith(".gif") or path.endswith(".gifv") or path.endswith(".tiff")):
		return downloadFile(url, dest_path, img_prefix=img_prefix,simple=verbose)
	else:
		function=None
		for s,f in image_sites.items():
			if s in url.lower():
				img_prefix+=s+"_"
				function=f
				break;
		if function is None:
			for s,f in file_sharing_sites.items():
				if s in url.lower():
					img_prefix+=s+"_"
					function=f
					break;
		if function is not None:
			try:
				print ("%s Crawling %s"%(datetime.now().strftime(tsFormat),url))
				res=function(url, dest_path, img_prefix=img_prefix,simple=verbose)
				#res=True
			except Exception as e:
				print ("%s ERROR. %s:%s"%(datetime.now().strftime(tsFormat),e.__class__.__name__,str(e)))
				res=1
			if res==1:
				print ("%s %s must be recrawled"%(datetime.now().strftime(tsFormat),url))
			return res
		else:
			print ("%s ERROR. URL %s not implemented. Timestamp=%s"%(datetime.now().strftime(tsFormat),url,timestamp))
			return 2


def check (url,timestamp,megaLinksFD,year,author,post):
	
	date=datetime.strptime(timestamp,'%Y-%m-%d')
	if 'sendspace' in url:
		if (datetime.now()-date)>timedelta(days=30):
			print ("%s ERROR File from sendspace no longer available. Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
			return 1
	if 'dropbox' in url:
		error=False
		try:
			content=requestURL(url)
			#content=None
			if not content is  None:
				print ("%s WARNING File from DROPBOX must be checked mannually.Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
			else:
				error=2
		except Exception as e:	
			print e
			error=1
		if error:
			print ("%s ERROR File from DROPBOX not found.Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
		return 1
	if 'google' in url:
		print ("%s WARNING File from GOOGLE DRIVE must be downloaded mannually.Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
		return 2
	if 'filedropper' in url:
		print ("%s WARNING File from FILEDROPPER must be checked mannually.Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
		return 2
	if 'mega' in url and '.nz' in url:
		print ("%s WARNING File from MEGA.NZ must be crawled using the special module.Timestamp=%s, URL=%s"%(datetime.now().strftime(tsFormat),timestamp,url))
		megaLinksFD.write("%s,%s,%s,%s\n"%(url,year,author,post))
		return 3
	return 0

def parseFileAndCrawl(filename):
	if os.path.exists(PROCESSED_URL_FILE):
		processed=pickle.load(open(PROCESSED_URL_FILE))
	else:
		processed={}
	fd=open(filename)
	csvreader = csv.reader(fd)
	megaLinksFD=open(MEGANZ_LINKS_FILE,'wb')
	# try:
	for line in list(csvreader):
		thread,post,site,timestamp,author,numUrls,posUrl,url=line
		year=timestamp[:4]
		if not url.startswith('http'):
			url='http://'+url
		if not url in processed.keys():
			processed[url]={}
			processed[url]['post']=post
			processed[url]['position']=posUrl
			processed[url]['site']=site
			codeReturn=check(url,timestamp,megaLinksFD,year,author,post)
			if codeReturn==0:
				prefix=site+"_"+post+"_"+posUrl+"_"
				dest_path=OUTPUT_DIR+year
				codeReturn=crawl(url,dest_path,timestamp,prefix,year,verbose=False)
				if codeReturn==0:
					processed[url]['status']=STATUS_CODES[codeReturn]+dest_path
				else:		
					processed[url]['status']=STATUS_CODES[codeReturn]
			else:		
				processed[url]['status']=STATUS_CODES[codeReturn]
		else:
			previousPost=processed[url]['post']
			if 'site' in processed[url]:
				previousSite=processed[url]['site']
			else:
				previousSite=0
			previousPosition=processed[url]['position']
			status=processed[url]['status']
			print ("%s URL already processed.URL=%s,PREV_SITE=%s,THIS_SITE=%s,PREV_POST=%s,THIS_POST=%s,PREVIOUS_POSITION=%s,THIS_POSITION=%s,STATUS=%s"%(datetime.now().strftime(tsFormat),url,previousSite,site,previousPost,post,previousPosition,posUrl,status)			)
	# except Exception as e:
	# 	print ("%s ERROR %s"%(datetime.now().strftime(tsFormat),e))
	pickle.dump(processed,open(PROCESSED_URL_FILE,'wb'))
	megaLinksFD.close()

if __name__ == "__main__":
	parseFileAndCrawl(FILE_LIST)

