#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import os.path
import re
import sys
import MySQLdb as mdb
import tarfile
import elementtree.ElementTree as etree
import tempfile
def printhelp():
	print
	print "WikiMung revision 17 Apr 2014"
	print "Written by Matthew Saunier"
	print "This code is released under the GPL, version 3 or later (at your option)"
	print
	print "Usage: wikimung [-p <path to wiki>] [-c <category 1> ... <category n>"
	print "       -n <namespace 1> ... <namespace n>] [-o <output>] [-g -b] [-v] [-h]" 
	print 
	print "-p: (MANDATORY) The path of the root of your MediaWiki installation."
	print "    LocalSettings.php and images/ must be present here."
	print "-c: (MANDATORY if n not specified) One or more categories to export. Categories"
	print "    specified must exactly match (including case) their description in the"
	print "    database, so spaces are not allowed. This field accepts UTF-8."
	print "-n: (MANDATORY if c not specified) One or more namespace IDs to export. This"
	print "    option will export the whole of a namespace, use with care. Namespaces must"
	print "    passed as numeric IDs, not descriptions."
	print "-o: The base name of the output file. Defaults to bundle.tar."
	print "-g: Compresses output using gzip."
	print "-b: Compresses output using bzip2."
	print "-v: Maximum verbosity."
	print "-h: Display this summary."
	print
	sys.exit(255)
def prependknownns(title, ns):
	# Magic foo derived from the MediaWiki documentation. Namespaces -1 and -2 are special and should never be exported.
	if ns == "0":
		return title
	elif ns == "1":
		return "Talk:" + title
	elif ns == "2":
		return "User:" + title
	elif ns == "3":
		return "User_talk:" + title
	elif ns == "4":
		return metans + ":" + title
	elif ns == "5":
		return metans + "_talk:" + title
	elif ns == "6":
		return "File:" + title
	elif ns == "7":
		return "File_talk:" + title
	elif ns == "8":
		return "MediaWiki:" + title
	elif ns == "9":
		return "MediaWiki_talk:" + title
	elif ns == "10":
		return "Template:" + title
	elif ns == "11":
		return "Template_talk:" + title
	elif ns == "12":
		return "Help:" + title
	elif ns == "13":
		return "Help_talk:" + title
	elif ns == "14":
		return "Category:" + title
	elif ns == "15":
		return "Category_talk:" + title
	elif ns == "828":
		return "Module:" + title
	elif ns == "829":
		return "Module_talk:" + title
	else:
		print "WARNING: Unknown namespace ID: " + ns
		return title
def modeltoformat(model):
	# Magic foo derived from the MediaWiki source, mostly
	if model == "wikitext":
		return "text/x-wiki"
	elif model == "javascript":
		return "text/javascript"
	elif model == "css":
		return "text/css"
	elif model == "text":
		return "text/plain"
	elif model == "Scribunto":
		return "text/plain"
	else:
		print "WARNING: Unknown content model: " + model
		return "text/plain"
if len(sys.argv) <= 1:
	printhelp()
wikipath = ""
grouplist = set([])
nslist = set([])
exportout = "bundle.tar"
compress = ""
verbose = False
currentarg = ""
for i in range(1,len(sys.argv)):
	arg = sys.argv[i]
	if re.search(r'(?:^-)(.)', arg):
		currentarg = arg[1]
		if currentarg == "g":
			compress = "gzip"
		if currentarg == "b":
			compress = "bzip2"
		if currentarg == "v":
			verbose = True
		if currentarg == "h":
			printhelp()
	else:
		if currentarg == "p":
			wikipath = arg
		elif currentarg == "c":
			grouplist.add(arg.strip())
		elif currentarg == "n":
			nslist.add(arg.strip())
		elif currentarg == "o":
			exportout = arg
		else:
			print "ERROR: Unable to parse the parameter \"" + arg + "\" at position " + str(i)
			sys.exit(1)
if not wikipath:
	print "ERROR: No wikipath specified"
	sys.exit(1)
if not len(grouplist) and not len(nslist):
	print "ERROR: No categories or namespaces specified"
	sys.exit(1)
localsettings = wikipath + "/LocalSettings.php"
try:
	open(localsettings, "r")
except:
	print "ERROR: Unable open \"" + localsettings + "\" for reading"
	sys.exit(1)
imagepath = wikipath + "/images"
if not os.path.isdir(imagepath):
	print "ERROR: Unable open the directory\"" + wikipath + "\""
	sys.exit(1)
if compress == "gzip":
	exportout += ".gz"
elif compress == "bzip2":
	exportout += ".bz2"
try:
	open(exportout, "w")
except:
	print "ERROR: Unable to open \"" + exportout + "\" for writing"
	sys.exit(1)
if verbose:
	print "INFO: LocalSettings.php located at " + localsettings
	print "INFO: Image directory located at " + imagepath
	if len(grouplist):
		print "INFO: Categories to export: ",
		for group in grouplist:
			print group + " ",
		print
	if len(nslist):
		print "INFO: Namespaces to export: ",
		for ns in nslist:
			print ns + " ",
		print
	print "INFO: Writing export bundle to " + exportout
for line in file(localsettings):
	if re.search('^\$wgDBname', line):
		sqldb = line.split('=')[1].split('"')[1]
	elif re.search('^\$wgDBuser', line):
		sqluser = line.split('=')[1].split('"')[1]
	elif re.search('^\$wgDBpassword', line):
		sqlpass = line.split('=')[1].split('"')[1]
	elif re.search('^\$wgMetaNamespace', line):
		metans = line.split('=')[1].split('"')[1]
if verbose:
	print "INFO: Using MariaDB database " + sqldb
try:
	dbconn = mdb.connect('localhost', sqluser, sqlpass, sqldb);
	sql = dbconn.cursor()
	root = etree.Element("mediawiki")
set	root.set("xmlns", "http://www.mediawiki.org/xml/export-0.8/")
	root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
	root.set("xsi:schemaLocation", "http://www.mediawiki.org/xml/export-0.8/ http://www.mediawiki.org/xml/export-0.8.xsd")
	root.set("version", "0.8")
	root.set("xml:lang", "en")
	pagelist = set([])
	for targetgroup in grouplist:
		sql.execute("SELECT cl_from FROM categorylinks WHERE cl_to = \"" + targetgroup + "\"")
		for page in sql.fetchall():
			pagelist.add(page)
	for targetns in nslist:
		sql.execute("SELECT page_id FROM page WHERE page_namespace = \"" + targetns + "\"")
		for page in sql.fetchall():
			pagelist.add(page)
	images = set([])
	for link in pagelist:
		sql.execute("SELECT page_content_model FROM page WHERE page_id = \"" + str(link[0]) + "\"")
		pagemodel = str(sql.fetchall()[0][0])
		page = etree.Element("page")
		title = etree.SubElement(page, "title")
		sql.execute("SELECT page_title FROM page WHERE page_id = \"" + str(link[0]) + "\"")
		title.text = str(sql.fetchall()[0][0])
		if verbose:
			print "INFO: Extracting page " + title.text
		sql.execute("SELECT il_to FROM imagelinks WHERE il_from = \"" + str(link[0]) + "\"")
		for image in sql.fetchall():
			if verbose:
				print "INFO: Extracting image " + image[0]
			images.add(image[0])
		ns = etree.SubElement(page, "ns")
		sql.execute("SELECT page_namespace FROM page WHERE page_id = \"" + str(link[0]) + "\"")
		ns.text = str(sql.fetchall()[0][0])
		title.text = prependknownns(title.text, ns.text)
		pageid = etree.SubElement(page, "id")
		pageid.text = str(link[0])
		sql.execute("SELECT page_latest FROM page WHERE page_id = \"" + str(link[0]) + "\"")
		nextrev = sql.fetchall()[0][0]
		while nextrev != 0:
			revision = etree.SubElement(page, "revision")			
			revid = etree.SubElement(revision, "id")
			revid.text = str(nextrev)
			if verbose:
				print "INFO: Extracting revision " + str(nextrev)
			sql.execute("SELECT rev_parent_id FROM revision WHERE rev_id = \"" + revid.text + "\"")
			rawparentid = sql.fetchall()
			if rawparentid:
				parentid = etree.SubElement(revision, "parentid")
				nextrev = rawparentid[0][0]
				parentid.text = str(nextrev)
			else:
				nextrev = 0
			sql.execute("SELECT rev_timestamp FROM revision WHERE rev_id = \"" + revid.text + "\"")
			timestamp = etree.SubElement(revision, "timestamp")
			timestamp.text = str(sql.fetchall()[0][0])
			contributor = etree.SubElement(revision, "contributor")			
			sql.execute("SELECT rev_user_text FROM revision WHERE rev_id = \"" + revid.text + "\"")
			username = etree.SubElement(contributor, "username")
			username.text = str(sql.fetchall()[0][0])
			sql.execute("SELECT rev_comment FROM revision WHERE rev_id = \"" + revid.text + "\"")
			rawcomment = sql.fetchall()
			if rawcomment:
				comment = etree.SubElement(revision, "comment")
				comment.text = str(rawcomment[0][0])
			sql.execute("SELECT rev_user FROM revision WHERE rev_id = \"" + revid.text + "\"")
			userid = etree.SubElement(contributor, "id")
			userid.text = str(sql.fetchall()[0][0])
			sql.execute("SELECT rev_text_id FROM revision WHERE rev_id = \"" + revid.text + "\"")
			revtext = str(sql.fetchall()[0][0])
			sql.execute("SELECT LENGTH (old_text) FROM text WHERE old_id = \"" + revtext + "\"")
			rawlen = sql.fetchall()
			if rawlen:
				text = etree.SubElement(revision, "text")
				text.set("xml:space", "preserve")
				text.set("bytes", str(rawlen[0][0]))
				sql.execute("SELECT old_text FROM text WHERE old_id = \"" + revtext + "\"")
				text.text = str(sql.fetchall()[0][0])
			sha1 = etree.SubElement(revision, "sha1")
			sql.execute("SELECT rev_sha1 FROM revision WHERE rev_id = \"" + revid.text + "\"")
			sha1.text = str(sql.fetchall()[0][0])
			model = etree.SubElement(revision, "model")
			model.text = pagemodel
			format = etree.SubElement(revision, "format")
			format.text = modeltoformat(pagemodel)
		root.append(page)
except mdb.Error, e:
	print "ERROR: Something went wrong while accessing the database: " % (e.args[0],e.args[1])
	sys.exit(1)
finally:    
	if dbconn:    
		dbconn.close()
if verbose:
	print "INFO: Creating XML for export bundle"
if not compress:
	exportfile = tarfile.open(exportout, "w")
elif compress == "gzip":
	exportfile = tarfile.open(exportout, "w:gz")
elif compress == "bzip2":
	exportfile = tarfile.open(exportout, "w:bz2")
xmlstr = etree.tostring(root, encoding='utf8')
xmlfile = tempfile.NamedTemporaryFile()
xmlfile.write(xmlstr)
xmlfile.flush()
exportfile.add(xmlfile.name, arcname="export.xml")
xmlfile.close()
if verbose:
	print "INFO: Gathering images for export bundle"
imagepaths = set([])
for dirpath, dirnames, filenames in os.walk(imagepath):
	if not dirpath.startswith(imagepath + "/thumb"):
		for filename in [f for f in filenames if f in images]:
			imagepaths.add(os.path.join(dirpath, filename))
imagefile = tempfile.NamedTemporaryFile()
imageout = tarfile.open(imagefile.name, "w")
for imagepath in imagepaths:
	imageout.add(imagepath, arcname=os.path.basename(imagepath))
imageout.close()
exportfile.add(imagefile.name, arcname="image.tar")
imagefile.close()
exportfile.close()
print "INFO: Export bundle created"
