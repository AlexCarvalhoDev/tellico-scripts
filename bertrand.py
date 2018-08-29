#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ***************************************************************************
#    Copyright (C) 2006-2009 Mathias Monnerville <tellico@monnerville.com>
# ***************************************************************************
#
# ***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or         *
# *   modify it under the terms of the GNU General Public License as        *
# *   published by the Free Software Foundation; either version 2 of        *
# *   the License or (at your option) version 3 or any later version        *
# *   accepted by the membership of KDE e.V. (or its successor approved     *
# *   by the membership of KDE e.V.), which shall act as a proxy            *
# *   defined in Section 14 of version 3 of the license.                    *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program.  If not, see <http://www.gnu.org/licenses/>. *
# *                                                                         *
# ***************************************************************************

# bertrand.py 12-3-2018, 15h16 - alexcarvalho.pt 
# script developed with help of dark horse comics script for tellico
# $Id: bertrand.py,v 1.9 2018/08/26 18:30:36 njsg Exp njsg $

"""
This script has to be used with tellico (http://periapsis.org/tellico) as an external data source program.
It allows searching through the Bertrand website.

Related info and cover are fetched automatically. It takes only one argument (comic title).

Tellico data source setup:
- source name: Bertrand Livreiros (or whatever you want :)
- Collection type: Books
- Result type: tellico
- Path: /path/to/script/bertrand.py
- Arguments:
Title (checked) = %1
Update (checked) = %{title}
"""

# encoding: utf-8
# encoding: iso-8859-1
# encoding: win-1252
# -*- coding: utf-8 -*-

import sys, os
# This requires python 2
if sys.version_info[:2] > (2, 7):
	try:
		# se o python27 estiver instalado no sistema o script e executado com o python27
		os.execvpe('python27', ['python27'] + sys.argv, os.environ)
	except FileNotFoundError:
		# Idem, se o Python 2.7 estiver instalado como python2.7
		os.execvpe('python2.7', ['python2.7'] + sys.argv, os.environ)


import re, md5, random, string
import urllib, urllib2, time, base64
import xml.dom.minidom

XML_HEADER = """<?xml version="1.0" encoding="UTF-8"?>"""
DOCTYPE = """<!DOCTYPE tellico PUBLIC "-//Robby Stephenson/DTD Tellico V9.0//EN" "http://periapsis.org/tellico/dtd/v9/tellico.dtd">"""
NULLSTRING = ''

VERSION = "0.2"

# Sometimes, results span several pages. While it is technically
# possible to retrieve all of them, we stop after MAX_SEARCH_PAGES.
MAX_SEARCH_PAGES = 5

def genMD5():
	"""
	Generates and returns a random md5 string. Its main purpose is to allow random
	image file name generation.
	"""
	obj = md5.new()
	float = random.random()
	obj.update(str(float))
	return obj.hexdigest()

class BasicTellicoDOM:
	"""
	This class manages tellico's XML data model (DOM)
	"""
	def __init__(self):
		self.__doc = xml.dom.minidom.Document()
		self.__root = self.__doc.createElement('tellico')
		self.__root.setAttribute('xmlns', 'http://periapsis.org/tellico/')
		self.__root.setAttribute('syntaxVersion', '9')

		self.__collection = self.__doc.createElement('collection')
		self.__collection.setAttribute('title', 'My Books')
		self.__collection.setAttribute('type', '2')

		self.__fields = self.__doc.createElement('fields')
		# Add all default (standard) fields
		self.__dfltField = self.__doc.createElement('field')
		self.__dfltField.setAttribute('name', '_default')

		self.__fields.appendChild(self.__dfltField)
		self.__collection.appendChild(self.__fields)

		self.__images = self.__doc.createElement('images')

		self.__root.appendChild(self.__collection)
		self.__doc.appendChild(self.__root)

		# Current movie id. See entry's id attribute in self.addEntry()
		self.__currentId = 0


	def addEntry(self, movieData):
		"""
		Add a comic entry.
		Returns an entry node instance
		"""
		d = movieData
		entryNode = self.__doc.createElement('entry')
		entryNode.setAttribute('id', str(self.__currentId))

		titleNode = self.__doc.createElement('title')
		titleNode.appendChild(self.__doc.createTextNode(d['title']))
		entryNode.appendChild(titleNode)

		yearNode = self.__doc.createElement('pub_year')
		yearNode.appendChild(self.__doc.createTextNode(d['pub_year']))
		entryNode.appendChild(yearNode)

		countryNode = self.__doc.createElement('country')
		countryNode.appendChild(self.__doc.createTextNode(d['country']))
		entryNode.appendChild(countryNode)
		pubNode = self.__doc.createElement('publisher')
		pubNode.appendChild(self.__doc.createTextNode(d['publisher']))
		entryNode.appendChild(pubNode)
		langNode = self.__doc.createElement('language')
		langNode.appendChild(self.__doc.createTextNode(d['language']))
		entryNode.appendChild(langNode)

		authorsNode = self.__doc.createElement('authors')
		for g in d['author']:
			authorNode = self.__doc.createElement('author')
			authorNode.appendChild(self.__doc.createTextNode(g))
			authorsNode.appendChild(authorNode)
			entryNode.appendChild(authorsNode)

		genresNode = self.__doc.createElement('genres')
		if 'genre' in d:
			for g in d['genre']:
				genreNode = self.__doc.createElement('genre')
				genreNode.appendChild(self.__doc.createTextNode(g))
				genresNode.appendChild(genreNode)
			entryNode.appendChild(genresNode)

		commentsNode = self.__doc.createElement('comments')
		#for g in d['comments']:
		#	commentsNode.appendChild(self.__doc.createTextNode("%s\n\n" % g))
		commentsData = string.join(d['comments'], '\n\n')
		commentsNode.appendChild(self.__doc.createTextNode(commentsData))
		entryNode.appendChild(commentsNode)

		if 'pages' in d:
			pagesNode = self.__doc.createElement('pages')
			pagesNode.appendChild(self.__doc.createTextNode(d['pages']))
			entryNode.appendChild(pagesNode)

		if 'isbn' in d:
			isbnNode = self.__doc.createElement('isbn')
			isbnNode.appendChild(self.__doc.createTextNode(d['isbn']))
			entryNode.appendChild(isbnNode)

		if 'image' in d and len(d['image']) == 2:
			imageNode = self.__doc.createElement('image')
			imageNode.setAttribute('format', 'JPEG')
			imageNode.setAttribute('id', d['image'][0])
			imageNode.appendChild(self.__doc.createTextNode(d['image'][1]))
			self.__images.appendChild(imageNode)

			coverNode = self.__doc.createElement('cover')
			coverNode.appendChild(self.__doc.createTextNode(d['image'][0]))
			entryNode.appendChild(coverNode)

		self.__collection.appendChild(entryNode)

		self.__currentId += 1
		return entryNode

	def printEntry(self, nEntry):
		"""
		Prints entry's XML content to stdout
		"""
		try:
			print(nEntry.toxml())
		except:
			sys.stderr.write("Error while outputting XML content from entry to Tellico\n")

	def printXMLTree(self):
		"""
		Outputs XML content to stdout
		"""
		self.__collection.appendChild(self.__images)
		print(XML_HEADER); print(DOCTYPE)
		print(self.__root.toxml())


class DarkHorseParser:
	def __init__(self):
		self.__baseURL 	 = 'https://www.bertrand.pt'
		self.__basePath  = '/livro/'
		self.__searchURL = '/pesquisa/%s'
		self.__coverPath = '/images/'
		self.__movieURL  = self.__baseURL + self.__basePath

		# Define some regexps
		self.__regExps = {

							'title' 				: '<div class="right-title-details" id="productPageSectionDetails-collapseDetalhes-content-title">(?P<title>.*?)</div>',
							'author'				: '<div class="right-author" id="productPageSectionDetails-collapseDetalhes-content-author">(?:de )?(?P<author>.*?)(?:&nbsp;)?</div>',
							'publisher'				: '<span itemprop="name" class="info">(?P<publisher>.*?)</span>',
							'pub_date'				: '<span itemprop="datePublished" class="info">(?P<pub_date>.*?)</span>',
							'isbn'					: '<span itemprop="isbn" class="info">(?P<isbn>.*?)</span>',
							'pages'					: '<span itemprop="numberOfPages" class="info">(?P<pages>.*?)</span>',
							'language'				: '<span itemprop="inLanguage" class="info">(?P<language>.*?)</span>',
							'image'					: '<img itemprop="image".*?src="(?P<image>.*?)".*?class="img-responsive ">',
						}

		# Compile patterns objects
		self.__regExpsPO = {}
		for k, pattern in self.__regExps.iteritems():
			self.__regExpsPO[k] = re.compile(pattern, re.DOTALL)

		self.__domTree = BasicTellicoDOM()

	def run(self, title):
		"""
		Runs the parser: fetch movie related links, then fills and prints the DOM tree
		to stdout (in tellico format) so that tellico can use it.
		"""
		self.__getMovie(title)
		# Print results to stdout
		self.__domTree.printXMLTree()

	def __getHTMLContent(self, url):
		"""
		Fetch HTML `ata from url
		"""
		u = urllib2.urlopen(url)
		self.__data = u.read()
		u.close()

	def __getSearchHTMLContent(self, searchText, pageNumber):
		"""
		Fetch search results from the given "results page"
		"""
		postData = urllib.urlencode({'pagina' : pageNumber,
					      'palavra' : urllib.quote(searchText)})
		baseUrl = 'https://www.bertrand.pt/pesquisando/'
		resultsPage = urllib2.urlopen(baseUrl, postData)
		self.__data = resultsPage.read()
		resultsPage.close()

	def __fetchMovieLinks(self):
		"""
		Retrieve all links related to the search. self.__data contains HTML content fetched by self.__getHTMLContent()
		that need to be parsed.
		"""
		matchList = re.findall("""<a class="title-lnk track" href="(?P<page>.*?)">.*?</a>""", self.__data)
		if not matchList: return None

		return list(set(matchList))

	def __fetchCover(self, path, delete = True):
		"""
		Fetch cover to /tmp. Returns base64 encoding of data.
		The image is deleted if delete is True
		"""
		md5 = genMD5()
		imObj = urllib2.urlopen(path.strip())
		img = imObj.read()
		imObj.close()
		imgPath = "/tmp/%s.jpeg" % md5
		try:
			f = open(imgPath, 'w')
			f.write(img)
			f.close()
		except:
			sys.stderr.write("Error: could not write image into /tmp\n")

		b64data = (md5 + '.jpeg', base64.encodestring(img))

		# Delete temporary image
		if delete:
			try:
				os.remove(imgPath)
			except:
				sys.stderr.write("Error: could not delete temporary image /tmp/%s.jpeg\n" % md5)

		return b64data

	def __fetchMovieInfo(self, url):
		"""
		Looks for movie information
		"""
		self.__getHTMLContent(url)

		matches = {}
		data = {}
		data['comments'] = []
		data['comments'].insert(0, "Bertrand URL: %s" % url)

		# Default values
		data['publisher'] 	= 'Bertrand'
		data['language'] 	= 'Portugues'
		data['country'] 	= 'PT'

		data['pub_year']	= NULLSTRING

		for name, po in self.__regExpsPO.iteritems():
			data[name] = NULLSTRING
			if name == 'desc':
				matches[name] = re.findall(self.__regExps[name], self.__data, re.S | re.I)
			else:
				matches[name] = po.search(self.__data)

			if matches[name]:
				if name == 'title':
					title = matches[name].group('title').strip()
					data[name] = title

				elif name == 'pub_date':
					pub_date = matches[name].group('pub_date').strip()
					data['pub_year'] = pub_date[-4:]
					# Add this to comments field
					data['comments'].insert(0, "Pub. Date: %s" % pub_date)

				elif name == 'isbn':
					isbn = matches[name].group('isbn').strip()
					data[name] = isbn

				elif name == 'publisher':
					publisher = matches[name].group('publisher').strip()
					data[name] = publisher

				elif name == 'language':
					language = matches[name].group('language').strip()
					data[name] = language

				elif name == 'pages':
					pages = matches[name].group('pages').strip()
					data[name] = pages

				elif name == 'desc':
					# Find biggest size
					max = 0
					for i in range(len(matches[name])):
						if len(matches[name][i]) > len(matches[name][max]):
							max = i
					data['comments'].append(matches[name][max].strip())

				elif name == 'author':
					# The Bertrand website is not
					# consistent regarding how the
					# list of authors is written.
					#
					# Sometimes, each author is a
					# link to a separate
					# page, sometimes not.
					#
					# If there is more than one
					# link in the list of authors,
					# the list is split based on
					# that. Otherwise, we split
					# based on ";". If that does
					# not split, we split on
					# ',' and '�e�'.
					data[name] = []
					authorsUnsplit = re.sub('</?a.*?>', '',
								     matches[name].group('author'))
					authorsByLinks = re.findall("<a[^>]*>([^<]*)</a>",
								    matches[name].group('author'),
								    re.S|re.I)
					authorsList = authorsUnsplit.split(';')
					if len(authorsList) < 2:
						authorsList = re.split("(?: e )|,", authorsUnsplit)

					if len(authorsByLinks) > 1:
						for author in authorsByLinks:
							data[name].append(author.strip())
					else:
						for author in authorsList:
							data[name].append(author.strip())
					
					# Something might go wrong.
					# For example, if one author
					# has a link, and another one
					# does not.  To help the user
					# when this happens, the
					# original content of this
					# field is saved, without
					# links, in the comments
					# field.
					data['comments'].insert(0, "Lista de autores: %s" % authorsUnsplit.strip())
				elif name == 'genre':
					# We may find several genres
					data[name] = []
					genresList = re.sub('</?a.*?>', '', matches[name].group('genre')).split(',')
					for d in genresList:
						data[name].append(d.strip())\

				elif name == 'image':
					imgPath = matches[name].group('image').strip()
					b64img = self.__fetchCover(imgPath)
					if b64img is not None:
						data['image'] = b64img

		return data


	def __getMovie(self, title):
		if not len(title): return

		self.__title = title
		page = 1

		while page <= MAX_SEARCH_PAGES:
			self.__getSearchHTMLContent(self.__title, page)
			page += 1
			# Get all links
			links = self.__fetchMovieLinks()

			# Now retrieve info
			if links:
				for entry in links:
					data = self.__fetchMovieInfo( url = self.__baseURL + entry )
					# Add DC link (custom field)
					data['bertrand'] = "%s%s" % (self.__baseURL, entry)
					node = self.__domTree.addEntry(data)
					# Print entries on-the-fly
					#self.__domTree.printEntry(node)
			else:
				# No more results, leave the loop.
				break

def halt():
	print("HALT.")
	sys.exit(0)

def showUsage():
	print("Usage: %s comic" % sys.argv[0])
	sys.exit(1)

def main():
	if len(sys.argv) < 2:
		showUsage()

	parser = DarkHorseParser()
	parser.run(sys.argv[1])

if __name__ == '__main__':
	main()
