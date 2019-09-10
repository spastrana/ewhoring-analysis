
# This script gets the "Must be recrawled" files, removes them from the processed  and re-generates de list (in stdout)

import pickle
import urllib
import urlparse

filenameURLS='../../files/urlsToRecrawl_previews4.txt'
filenameIMAGELIST='../../files/imageLink_list.csv'

PROCESSED_URL_FILE='../../files/processedURLDownload.pickle'
processed=pickle.load(open(PROCESSED_URL_FILE))

urls=open(filenameURLS).readlines()
links=open(filenameIMAGELIST).readlines()


for url in urls:
	for k in processed.keys():
		if url.strip() in k:
			del processed[k]

	parsed=urlparse.urlparse(urllib.unquote(url.strip().lower()))
	path=parsed.path
	for l in links:
		if path.strip()!='' and path in l.strip():
			print (l.strip())


pickle.dump(processed,open(PROCESSED_URL_FILE,'wb'))			