# -*- coding: utf-8 -*-


# ---------------------------------------------- DISCLAIMER ----------------------------------------------
# This code has been generated combining two tutorial samples from:
# 1) http://scikit-learn.org/stable/auto_examples/hetero_feature_union.html
# 2) https://bbengfort.github.io/tutorials/2016/05/19/text-classification-nltk-sckit-learn.html
# --------------------------------------------------------------------------------------------------------
#
# The pipeline requires a list of threads numbers as main input. Then, the feature extraction will query the database for these threads and extract
# the content of the first post (initial) and the heading for further processing. The pipeline then:
# 1. Extract features using NLTK from the heading and content. For the content, it applies dimensionality reduction  using SVD 
# to reduce the number of components (currently to 50). 
# 2. Extract features as stats from the thread
# 3. Extract features as stats from the initial post
# 4. Train a Linear SVM with 80% of the given set for training and 20% for evaluation. It prints the efficacy
# 5. Then, trains a Linear SVM using the total of the given set as training. This classifier is saved into disk
#
# The script includes auxiliary methods related to ewhoring analysis
#


import os
import time
import string
import pickle
import psycopg2
import socket
import sys
from datetime import datetime
from operator import itemgetter
import random
import types
import numpy as np
import scipy
from nltk.corpus import stopwords as sw
from nltk.corpus import wordnet as wn
from nltk import wordpunct_tokenize
from nltk import WordNetLemmatizer
from nltk import sent_tokenize
from nltk import pos_tag
import nltk
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import SGDClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report as clsr
from sklearn.metrics import confusion_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split as tts
import sys
import getpass

reload(sys) 
sys.setdefaultencoding('utf-8')

# THE FOLLOWING ARE TWO AUXILIARY FUNCTIONS 
def timeit(func):
	"""
	Simple timing decorator
	"""
	def wrapper(*args, **kwargs):
		start  = time.time()
		result = func(*args, **kwargs)
		delta  = time.time() - start
		return result, delta
	return wrapper
def identity(arg):
	"""
	Simple identity function works as a passthrough.
	"""
	return arg


class FeatureExtractor(BaseEstimator, TransformerMixin):
	"""Queries the database and extracts the heading,content and number of posts 
	from a list of threads. Produces a dict of sequences.  Keys are
	`content` and `numPosts_heading`.
	"""
	def fit(self, x, y=None):
		return self

	# Note that the extractor puts into the same variable a tuple with the numPosts and heading
	# This is due to the use of both set of features in the 'ThreadStats' feature extraction
	def transform(self, threads):
		features = np.recarray(shape=(len(threads),),
							   dtype=[('numPosts_heading', object),('content', object)])
		for i, threadSite in enumerate(threads):
			numPosts, heading, content = self.extract(threadSite)
			features['numPosts_heading'][i] = (numPosts,heading)
			features['content'][i] = content

		return features

	def extract(self,threadSite):
		site=threadSite.split('-')[0]
		idThread=threadSite.split('-')[1]
		connector = psycopg2.connect(user=getpass.getuser(), database=DB_NAME)
		cursor = connector.cursor()

		query=('SELECT "Heading","NumPosts" FROM "Thread" WHERE "IdThread"=%s AND "Site"=%s'%(idThread,site)); 
		cursor.execute(query)
		thread=cursor.fetchone()
		
		query=('SELECT "Content" FROM "Post" WHERE "Thread"=%s AND "Site"=%s ORDER BY "IdPost" ASC LIMIT 1'%(idThread,site));
		cursor.execute(query)
		posts=cursor.fetchall()
		if len(posts)>0:
			firstPostContent=posts[0][0].decode('utf-8')
		else:
			firstPostContent=''
		heading,numPosts=thread
		return numPosts,heading.decode('utf-8'),firstPostContent

class NLTKPreprocessor(BaseEstimator, TransformerMixin):
	"""
	Transforms input data by using NLTK tokenization, lemmatization, and
	other normalization and filtering techniques.
	"""

	def __init__(self, stopwords=None, punct=None, lower=True, strip=True):
		"""
		Instantiates the preprocessor, which make load corpora, models, or do
		other time-intenstive NLTK data loading.
		"""
		self.lower      = lower
		self.strip      = strip
		self.stopwords  = set(stopwords) if stopwords else set(sw.words('english'))
		self.punct      = set(punct) if punct else set(string.punctuation)
		self.lemmatizer = WordNetLemmatizer()

	def fit(self, X, y=None):
		"""
		Fit simply returns self, no other information is needed.
		"""
		return self

	def inverse_transform(self, X):
		"""
		No inverse transformation
		"""
		return X

	def transform(self, X):
		"""
		Actually runs the preprocessing on each document.
		"""
		print "%s Preprocessing"%datetime.now().strftime(tsFormat)
		return [
			list(self.tokenize(doc)) for doc in X
		]

	# Due to the use of a tuple for the heading to include the number of posts, first the the input is checked.
	# If it is a tuple it only takes the second component, which is the heading
	def tokenize(self, document):
		"""
		Returns a normalized, lemmatized list of tokens from a document by
		applying segmentation (breaking into sentences), then word/punctuation
		tokenization, and finally part of speech tagging. It uses the part of
		speech tags to look up the lemma in WordNet, and returns the lowercase
		version of all the words, removing stopwords and punctuation.
		"""
		# The following checks whether the given 'document' si a tuple (i.e. a 'numPosts_heading') and takes the second element (i.e. the 'heading')
		if type(document)==types.TupleType:
			document=document[1]
		# ************************************************************************************	
		# UNCOMMENT/COMMENT HERE IF WANT TO TOKENIZE THE CONTENT WITHOUT RICH CONTENT (i.e. LINKS, IMAGES, etc.)
		else:
			document=self.removeRichDataFromContent(document)
		# ************************************************************************************

		# Break the document into sentences
		for sent in sent_tokenize(document):
			# Break the sentence into part of speech tagged tokens
			for token, tag in pos_tag(wordpunct_tokenize(sent)):
				# Apply preprocessing to the token
				token = token.lower() if self.lower else token
				token = token.strip() if self.strip else token
				token = token.strip('_') if self.strip else token
				token = token.strip('*') if self.strip else token

				# If punctuation or stopword, ignore token and continue
				if token in self.stopwords or all(char in self.punct for char in token):
					continue

				# Lemmatize the token and yield
				lemma = self.lemmatize(token, tag)
				yield lemma

	def lemmatize(self, token, tag):
		"""
		Converts the Penn Treebank tag to a WordNet POS tag, then uses that
		tag to perform much more accurate WordNet lemmatization.
		"""
		tag = {
			'N': wn.NOUN,
			'V': wn.VERB,
			'R': wn.ADV,
			'J': wn.ADJ
		}.get(tag[0], wn.NOUN)

		return self.lemmatizer.lemmatize(token, tag)

	def removeRichDataFromContent(self,content):
		toClean=["***IMG***","***LINK***","***CITING***","***IFRAME***","***CODE***"]
		cleanedData=content
		for item in toClean:
			tmp=cleanedData
			if item in tmp:
				cleanedData=""
				n=0     
				for e in tmp.split(item):
					if n%2 == 0:
						cleanedData+=e+" "
					n+=1
		return " ".join([s for s in cleanedData.splitlines() if s.strip()])				

class ItemSelector(BaseEstimator, TransformerMixin):
	"""For data grouped by feature, select subset of data at a provided key.

	The data is expected to be stored in a 2D data structure, where the first
	index is over features and the second is over samples.  i.e.

	>> len(data[key]) == n_samples

	Please note that this is the opposite convention to scikit-learn feature
	matrixes (where the first index corresponds to sample).

	ItemSelector only requires that the collection implement getitem
	(data[key]).  Examples include: a dict of lists, 2D numpy array, Pandas
	DataFrame, numpy record array, etc.

	>> data = {'a': [1, 5, 2, 5, 2, 8],
			   'b': [9, 4, 1, 4, 1, 3]}
	>> ds = ItemSelector(key='a')
	>> data['a'] == ds.transform(data)

	ItemSelector is not designed to handle data grouped by sample.  (e.g. a
	list of dicts).  If your data is structured this way, consider a
	transformer along the lines of `sklearn.feature_extraction.DictVectorizer`.

	Parameters
	----------
	key : hashable, required
		The key corresponding to the desired value in a mappable.
	"""
	def __init__(self, key):
		self.key = key

	def fit(self, x, y=None):
		return self

	def transform(self, data_dict):
		return data_dict[self.key]

class ThreadStats(BaseEstimator, TransformerMixin):
	"""Computes statistics of the thread. Concretely:
	- The number of posts (replies) for this thread
	- The likelihood of the thread being a tutorial
	- The likelihood of the thread being a question
	"""
	def fit(self, x, y=None):
		return self

	def transform(self, threadsNumPosts):
		print "%s Getting Thread stats"%datetime.now().strftime(tsFormat)
		return [{'numPosts': nPosts,
				'isTutorial': self.getQuestionScore(heading)==0 and self.isTutorial(heading),
				'qScore': self.getQuestionScore(heading)}
				for nPosts,heading in threadsNumPosts]
	
	# Uses heuristics to determine whether a heading is offering a tutorial or not
	def isTutorial(self,heading):
		tutorialKeywords=('tutorial', '[tut]','howto','definite guide','guide]','how-to')
		for k in tutorialKeywords:
			if k in heading.lower():
				return True
		return False	 

	# Uses heuristics to determine whether a text is asking for info
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
	def getQuestionScore (self,text):
		questionScore=0
		questionScore+=self.checkKeyPhrasesQuestions(text)*2
		questionScore+=text.count('?')*2
		if 'question' in text:
			questionScore+=1	
		return questionScore

	# Removes the non textual data from the content given as parameter
	def removeRichDataFromContent(self,content):
		toClean=["***IMG***","***LINK***","***CITING***","***IFRAME***","***CODE***"]
		cleanedData=content
		for item in toClean:
			tmp=cleanedData
			if item in tmp:
				cleanedData=""
				n=0     
				for e in tmp.split(item):
					if n%2 == 0:
						cleanedData+=e+" "
					n+=1
		return " ".join([s for s in cleanedData.splitlines() if s.strip()])		

class PostsStats(BaseEstimator, TransformerMixin):
	"""
	 Computes statistics of the post. Concretely:
	 - The number of links to hackforums
	 - The number of links to image sites (based on a whitelist)
	 - The number of links to file sharing sites (based on a whitelist)
	 - The number of links to other sites
	 - The lenght of the post
	 - The likelihood of this content being a question or info request
	 """
	def fit(self, x, y=None):
		return self

	def transform(self, contents):
		toReturn=[]
		print "%s Getting Post stats"%datetime.now().strftime(tsFormat)

		for i,content in enumerate(contents):
	
			links=self.getLinks(content)
	
			hfLinks=self.countHFLinks(links)
	
			imgLinks=self.countImageLinks(links)

			fsLinks=self.countFileSharingLinks(links)
	
			otherLinks=len(links)-hfLinks-imgLinks-fsLinks
			toReturn.append({'externalLinks': otherLinks,
				 'hfLinks':hfLinks,
				 'imgLinks':imgLinks,
				 'fsLinks':fsLinks,
				 'lenght':len(content),
				 'qScore':self.getQuestionScore(content)})
		return toReturn
	
	def countExternalLinks(self,links):
		c=0
		for l in links:
			if 'hackforums' in l:
				c+=1
		return c
	def countHFLinks(self,links):
		c=0
		for l in links:
			if 'hackforums' in l:
				c+=1
		return c
	def countImageLinks(self,links):
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
		c=0
		for l in links:
			for e in image_sites:
				if e in l:
					c+=1
					break;
		return c

	def countFileSharingLinks(self,links):
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
		c=0
		for l in links:
			for e in file_sharing_sites:
				if e in l:
					c+=1
					break;
		return c

	def getLinks(self,content):
		item="***LINK***"
		links=[]
		if item in content:
			for n,e in enumerate(content.split(item)):
				if n%2 == 1:
					links.append(e.split('[')[1].split(']')[0])
		return links

	# Uses heuristics to determine whether a text is asking for info
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

	#Uses heuristics to estimate a score indicating whether this thread is a question (score >=1) or not (score=0)
	def getQuestionScore (self,text):
		questionScore=0
		cleanedText=self.removeRichDataFromContent(text)
		questionScore+=self.checkKeyPhrasesQuestions(cleanedText)*2
		questionScore+=cleanedText.count('?')*2
		if 'question' in cleanedText:
			questionScore+=1	
		return questionScore

	def removeRichDataFromContent(self,content):
		toClean=["***IMG***","***LINK***","***CITING***","***IFRAME***","***CODE***"]
		cleanedData=content
		for item in toClean:
			tmp=cleanedData
			if item in tmp:
				cleanedData=""
				n=0     
				for e in tmp.split(item):
					if n%2 == 0:
						cleanedData+=e+" "
					n+=1
		return " ".join([s for s in cleanedData.splitlines() if s.strip()])		

# Trains and evaluates the model using a 20% of test threads from the annotatedThreads.pickle set
# The retrains the model with the whole set and writes it into a file (given by outpath)
@timeit
def build_and_evaluate(X, y,classifier=SGDClassifier, outpath=None, verbose=True,test_size=0.2):
	"""
	Builds a classifer for the given list of threads and targets. I uses a union of four
	feature extractions, namely tf-idf for heading and post content (using NLTK preprocessor),
	thread metadata and content metadata.

	X: a list or integers corresponding with threadIDs
	y: a list or iterable of labels, which will be label encoded.

	Can specify the classifier to build with: if a class is specified then
	this will build the model with the Scikit-Learn defaults, if an instance
	is given, then it will be used directly in the build pipeline.

	If outpath is given, this function will write the model as a pickle.
	If verbose, this function will print out information to the command line.
	"""

	@timeit
	def build(classifier, X, y=None):
		"""
		Inner build function that builds a single model.
		"""
		if isinstance(classifier, type):
			classifier = classifier()


		model = Pipeline([
			# Extract the heading,content and numPosts
			('features', FeatureExtractor()),

			# Use FeatureUnion to combine the different features
			('union', FeatureUnion(
				transformer_list=[

					# Pipeline for pulling bag-of-words from the thread's heading, after tokenizing and lemmatizing
					# Then, it aplies TF-IDF vectorization on the BoW (also it can be truncated using SVD if needed)
					('heading', Pipeline([
						('selector', ItemSelector(key='numPosts_heading')),
						('preprocessor', NLTKPreprocessor()),
						('vectorizer', TfidfVectorizer(tokenizer=identity, preprocessor=None, lowercase=False)),
						#('featureselector', TruncatedSVD(n_components=20)),
					])),

					# Pipeline for pulling bag-of-words from the thread's first post content, after tokenizing and lemmatizing
					# Then, it aplies TF-IDF vectorization on the BoW and truncates using SVD
					('content', Pipeline([
						('selector', ItemSelector(key='content')),
						('preprocessor', NLTKPreprocessor()),
						('vectorizer', TfidfVectorizer(tokenizer=identity, preprocessor=None, lowercase=False)),
						('featureselector', TruncatedSVD(n_components=50)),
					])),

					# Pipeline for pulling ad hoc features from thhead's heading
					('threadStats', Pipeline([
						('selector', ItemSelector(key='numPosts_heading')),
						('stats', ThreadStats()),  # returns a list of dicts
						('vect', DictVectorizer()),  # list of dicts -> feature matrix
					])),
					# Pipeline for pulling ad hoc features from thread's first post content
					('postStats', Pipeline([
						('selector', ItemSelector(key='content')),
						('stats', PostsStats()),  # returns a list of dicts
						('vect', DictVectorizer()),  # list of dicts -> feature matrix
					])),

				],

				# weight components in FeatureUnion
				transformer_weights={
					'heading': 0.8,
					'content': 0.5,
					'threadStats': 1.0,
					'postStats': 1.0,
				},
			)),

			# Use a SVC classifier on the combined features
			('svc', SVC(kernel='linear')),
		])

		model.fit(X, y)
		return model

	# Label encode the targets
	labels = LabelEncoder()
	y = labels.fit_transform(y)

	# Begin evaluation
	if verbose: print("%s Building for evaluation"%datetime.now().strftime(tsFormat))
	X_train, X_test, y_train, y_test = tts(X, y, test_size=test_size)
	model, secs = build(classifier, X_train, y_train)
	if verbose: print("%s Evaluation model fit in %0.3f seconds"%(datetime.now().strftime(tsFormat),secs))

	if verbose:
		y_pred = model.predict(X_test)
		print("%s Classification Report:\n"%datetime.now().strftime(tsFormat))
		print(clsr(y_test, y_pred, target_names=labels.classes_))
		tn, fp, fn, tp= confusion_matrix(y_test,y_pred).ravel()
		print ("   CONFUSION MATRIX")
		print (" ---------------------")
		print ("        Predicted")
		print ("         'o' \t'p'")
		print ("        --------------")
		print ("Real 'o' |%s \t%s"%(tn,fp))
		print ("     'p' |%s \t%s"%(fn,tp))
		print ()
		print ("FPR:%.3f"%(float(fp)/(fp+tp)))
		print ("TPR:%.3f"%(float(tp)/(tp+fn)))
		print ("ACC:%.3f"%((float(tp)+tn)/(tp+fn+tn+fp)))
		print("%s Building complete model and saving ..."%datetime.now().strftime(tsFormat))

	model, secs = build(classifier, X, y)
	model.labels_ = labels

	if verbose: print("%s Complete model fit in %0.3f seconds"%(datetime.now().strftime(tsFormat),secs))

	if outpath:
		with open(outpath, 'wb') as f:
			pickle.dump(model, f)

		if verbose: print("%s Model written out to %s"%(datetime.now().strftime(tsFormat),outpath))

	return model


reload(sys)
sys.setdefaultencoding('utf-8')


tsFormat='%Y%m%d_%H%M%S'


DB_NAME='crimebb'
OUTPUT_DIR='../files/'




# Auxiliary function. Gets random K elements from a list
def random_subset( list, K ):
	result = []
	N = 0
	for item in list:
		N += 1
		if len(result) < K:
			result.append(item)
		else:
			s = int(random.random() * N)
			if s < K:
				result[s] = item
	return result

 
# Use the classifier to get threads classified as T.O.P. from the set of ewhoring related threads, and writes in file with pickle format 
def getTOP_FromClassifier (verbose=True):
	data=pickle.load(open(OUTPUT_DIR+'threads_ewhoring_all_forums.pickle'))
	for site in data:
		filename=OUTPUT_DIR+'TOP_Classifier_%s.pickle'%site
		if os.path.exists(filename):
			if verbose: print ("%s Reading already classified threads of site %s from disk"%(datetime.now().strftime(tsFormat),site))
			packs=pickle.load(open(filename))
		else:
			X_test=[]
			for forum in data[site]:
				if 'total' in str(forum): continue
				for thread in data[site][forum]:
					if 'total' in str(thread): continue
					siteThread='%s-%s'%(site,thread)
					X_test.append(siteThread)
			
			if verbose: (print "%s Predicting %s threads from forum %s"%(datetime.now().strftime(tsFormat),len(X_test),site))
			y_pred = model.predict(X_test)
			labels=model.labels_
			packs=[]
			for i in range(0,len(X_test)):
				label=y_pred[i]
				if (labels.classes_[label]=='p'):
					packs.append(int(X_test[i].split('-')[1]))
			pickle.dump(packs,open(filename,'wb'))
		numPacks=len(packs)
		if verbose: print ("%s Found %s TOP on site %s"%(datetime.now().strftime(tsFormat),numPacks,site))
	

# Gets the precision,recall and confusion matrix (including False Positive Rate and Detection Rate) 
# of the classifier on the training set
def getTrainingErrors():
		filename=OUTPUT_DIR+'annotatedThreads.pickle'
		if os.path.exists(filename):
			print ("%s Reading already annotated posts from disk"%(datetime.now().strftime(tsFormat)))
			annotated=pickle.load(open(filename))
		else:
			print ("%s ERROR. Annotation file not foud"%(datetime.now().strftime(tsFormat)))
			exit()
		print("%s Predicting annotated"%datetime.now().strftime(tsFormat))
		X_test=annotated.keys()
		y_test=annotated.values()
		y_pred = model.predict(X_test)
		labels=model.labels_
		y_test = labels.fit_transform(y_test)
		print (clsr(y_test, y_pred, target_names=labels.classes_))
		tn, fp, fn, tp= confusion_matrix(y_test,y_pred).ravel()
		print (" ---------------------")
		print ("        Predicted")
		print ("          'o' \t'p'")
		print ("        --------------")
		print ("Real 'o' | %s \t%s"%(tn,fp))
		print ("     'p' | %s \t%s"%(fn,tp))
		print
		print ("FPR:%.3f"%(float(fp)/(fp+tp)))
		print ("TPR:%.3f"%(float(tp)/(tp+fn)))
		print ("ACC:%.3f"%((float(tp)+tn)/(tp+fn+tn+fp)))


if __name__ == "__main__":

	# Obtain the model. If it exists in disk, read it, othewise, train a new model
	PATH = OUTPUT_DIR+"model_TOP_classifier.pickle"
	if not os.path.exists(PATH):
		# Read annotated threads from file
		filename=OUTPUT_DIR+'annotatedThreads.pickle'
		if os.path.exists(filename):
			print ("%s Reading already annotated posts from disk"%(datetime.now().strftime(tsFormat)))
			annotated=pickle.load(open(filename))
		else:
			print ("%s ERROR. Annotation file not foud"%(datetime.now().strftime(tsFormat)))
			exit()
		threads=annotated.keys()
		print ("%s Loaded %s annotated threads"%(datetime.now().strftime(tsFormat),len(threads)))
		random.shuffle(threads)
		# Get x (thread numbers) and y (labels)
		X=[]
		y=[]
		for siteThread in threads:
			X.append(siteThread)
			y.append(annotated[siteThread])    

		model,seconds = build_and_evaluate(X,y,outpath=PATH)
	else:
		with open(PATH, 'rb') as f:
			model = pickle.load(f)

	# Uncomment to Analyse training errors
	# getTrainingErrors()
	# exit()
	
	

	# Use the model to get the T.O.P. from different forums
	getTOP_FromClassifier()

