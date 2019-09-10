# This script processes the output regarding the NSFW and OCR scores (obtained using tools/open_nswf/check)
# and applies a series of thresholds to tag the images as Not Safe For Viewing (NSFV) or Safe For Viewing (SFV)

# filename='../files/previews_nsfw_word_detection.csv'
filename='../files/proofOfEarnings_nsfw_word_detection.csv'
#filename='../files/packs_nsfw_word_detection.csv'

# Check if the images being processed are from packs
processingPacks='packs' in filename

# Print output of each file individually
printIndividualFiles=True

# Print overall stats
printStats=False

#Thresholds:
# Min and max NSFW, no matter the OCR
MIN_NSFW=0.01
MAX_NSFW=0.3

# Relations of NSFW with OCR
NSFW_INTERMEDIATE=0.05

# MIN and MAX values for OCRs if NSFW is greater than NSFW_INTERMEDIATE
OCRS_GREATER_INTERMEDIATE=[10,20]

# MIN and MAX values for OCRs if NSFW is lower than NSFW_INTERMEDIATE
OCRS_LOWER_INTERMEDIATE=[0,5]


lines=open(filename).readlines()
SFV=0
Doubtful=0
NSFV=0
noImages=0
packs={}
minNSFW=100
totalNSFW=0
totalImages=0
filenameMin=""
for l in lines:
	ocr=l[l.rfind(',')+1:]
	ocr=ocr.strip()
	rest=l[:l.rfind(',')]
	# nsfw=rest[rest.rfind(',')+1:]
	nsfw='0.1'
	path=rest[:rest.rfind(',')]
	if not processingPacks:
		path=path.replace(',','/')
	directory=path[:path.rfind('/')]
	filename=path[path.rfind('/')+1:]

	if not 'HTML' in nsfw and not "NOT_IMAGE_FILE" in nsfw:
		try:
			# nsfwFloat=float(nsfw)
			nsfwFloat=0.1
			ocrInt=int(ocr)
			totalNSFW+=nsfwFloat
			totalImages+=1
			if nsfwFloat<minNSFW:
				minNSFW=nsfwFloat
				filenameMin=path
			count=True
		except:
			noImages+=1
			count=False
		if count:
			if nsfwFloat<MIN_NSFW:
				if printIndividualFiles:
					print ("SFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
				SFV+=1
			elif nsfwFloat>MAX_NSFW:
				if printIndividualFiles:
					print ("NSFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
				NSFV+=1	
			elif nsfwFloat>NSFW_INTERMEDIATE:
				if ocrInt<OCRS_GREATER_INTERMEDIATE[0]:
					if printIndividualFiles:
						print ("NSFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					NSFV+=1
				elif ocrInt<OCRS_GREATER_INTERMEDIATE[1]:
					if printIndividualFiles:
						print ("Doubtful: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					Doubtful+=1
				else:
					if printIndividualFiles:
						print ("SFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					SFV+=1
			else:
				if ocrInt==OCRS_LOWER_INTERMEDIATE[0]:
					if printIndividualFiles:
						print ("NSFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					NSFV+=1	
				elif ocrInt>OCRS_LOWER_INTERMEDIATE[1]:
					if printIndividualFiles:
						print ("SFV: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					SFV+=1
				else:
					if printIndividualFiles:
						print ("Doubtful: %s (nsfw=%.3f,ocr=%s)"%(path,float(nsfw),ocr))
					Doubtful+=1
			if processingPacks:
				if not directory in packs.keys():
					packs[directory]=[filename]
				else:
					packs[directory].append(filename)
	else:
		noImages+=1

if printStats:
	print ("SFV: %s (%.2f %%)"%(SFV,float(SFV)*100/len(lines)))
	print ("NSFV: %s (%.2f %%)"%(NSFV,float(NSFV)*100/len(lines)))
	print ("Doubtful: %s (%.2f %%)"%(Doubtful,float(Doubtful)*100/len(lines)))
	print ("No Images: %s (%.2f %%)"%(noImages,float(noImages)*100/len(lines)))
	if processingPacks:
		print ("Total Images: %s"%(totalImages))
		print ("Average NSFW: %.2f"%(float(totalNSFW)/totalImages))
		print ("Min NSFW: %s (%s)"%(minNSFW,filenameMin))

		packsPerPost={}
		maxSize=0
		packMaxSize=""
		totalSizes=0
		totalPacks=len(packs.keys())
		for pack in packs.keys():
			trunc=pack[:pack.find('_')]
			post=trunc[trunc.rfind("/")+1:]
			if not post in packsPerPost.keys():
				packsPerPost[post]=[pack]
			else:
				packsPerPost[post].append(pack)
			totalSizes+=len(packs[pack])
			if len(packs[pack])>maxSize:
				maxSize=len(packs[pack])
				packMaxSize=pack
		postMaxPacks=""
		maxSizePosts=0
		totalPostsWithPacks=len(packsPerPost.keys())			
		for post in packsPerPost.keys():
			if len(packsPerPost[post])>maxSizePosts:
				maxSizePosts=len(packsPerPost[post])
				postMaxPacks=post
		print ("Total packs: %s"%totalPacks)
		print ("Average size: %.2f"%(float(totalSizes)/totalPacks))
		print ("Max size: %s (%s)"%(maxSize,packMaxSize))
		print ("Total posts with packs %s"%totalPostsWithPacks)
		print ("Average packs per post %.3f"%(float(totalPacks)/totalPostsWithPacks))
		print ("Max packs in post %s (%s)"%(maxSizePosts,postMaxPacks))
