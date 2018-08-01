'''
Created on July 21, 2016

@author: Connor Meeks
'''

from django.core.management.base import BaseCommand

from transsend import models as tModels
from flue.DocumentProcessing import DocSource,CommFTP
from transsendlib.TransSendUtil import TransSendUtil
import ftplib
from datetime import datetime
import sys

#sudo pip install XlsxWriter
import xlsxwriter

'''

we want to be able to list all the documents on the ftp server
then at the end we will want to send a report via email that will
tell us this data (via TransSendUtil)

The management command will take in two arguments that dictate the 
report cutoff date and the delete cutoff date

NOTE: ReTransTestMode = False 
NOTE: 500 errors persist...
'''



class Command(BaseCommand):
    
    help =          " \n [Sends a report and deletes files located on the specified FTP client.]" 
    help = help +   " \n The command takes in 1 OR 2 arguments:"
    help = help +   " \n -To specify a report cutoff date enter in a single integer..."
    help = help +   " \n ---(To report files older than 5 days: python manage.py FTP 5) "
    help = help +   " \n -To specify a report AND delete cutoff date enter in 2 integers seperated by a comma..."
    help = help +   " \n ---(To report files older than 5 days and delete files older than 10 days: python manage.py FTP 5,10) "
    
    help = help +   " \n\n NOTE: you can use decimal values for the number of days to be more specific!"
    
    def handle(self, *args, **options):
        
        for arg in args:
            try:
                report_cutoff, delete_cutoff = arg.split(',')#splits your two arguments at the comma
            except ValueError:
                report_cutoff, delete_cutoff = arg, None
        
        try:
            if delete_cutoff == None:
                print "Trying to catch UnboundLocalError" #this will happen when you enter in python manage.py FTP (with no argument)
            
        except UnboundLocalError:
            print "Please enter in an argument to use this command. \nType 'python manage.py FTP --help' for assistance"
            sys.exit(0) #this will stop the program.
        
            
            
        if delete_cutoff == None:
            print "Will Report Files older than [" + str(report_cutoff) +"] day(s)"
            print "Will NOT delete any files"
        else:
            print "Will Report Files older than [" + str(report_cutoff) +"] day(s)"
            print "Will Delete Files older than [" + str(delete_cutoff) +"] day(s)"
            
        ts_util = TransSendUtil()
        headline = "Meeks FTP Report"
        msg = '\n' + "Below you will find the files on each specified FTP client: " +'\n\n'
        
    
        queryset = tModels.TSCommunicationChannel.objects.all().filter(mode__iexact="FTP", test_connectionURL__iexact="ftp2.re-trans.com")
        for obj in queryset:
            doc_points = tModels.TSDocPoint.objects.all().filter(docpointtype = 'Source')
            for dp in doc_points:
                if dp.sk_communicationchannel == obj:
                    source = DocSource(name = dp.name, qualifier = dp.qualifier, documenttype = dp.documenttype)
                    
                    print dp.docpointid
                    print dp.name
                    print dp.documenttype
                    print dp.qualifier
                    print dp.mask
                    print dp.deleteAtSource
                    print dp.sk_communicationchannel
                    print dp.channeltarget
                    print dp.docpointtype
    
                    
                    
                    
                    print "Queryset Info: " + str(obj.name) + "---" + str(obj.user) + "---" + str(obj.mode)+ "---" + str(obj.test_connectionURL)
                    print "Docpoint Info: " + str(dp.name) + "---" + str(dp.qualifier) + "---" + str(dp.documenttype) + str(dp.sk_communicationchannel)
                    
                    delete_counter = 0 #this is used to tell us how many we are to delete, we reset every iteration
                    report_counter = 0 #this is used to tell us how many we are to report, we reset every iteration
                    no_action_counter = 0 #this is used to tell us how many we are to take no action, we reset every iteration
                    
                    try: document_list = source.getDocumentList(date=True)
                                        
                    except ftplib.error_perm, resp:
                            
                            document_list = "ERROR"
                            
                            if str(resp) == "550 I can only retrieve regular files":
                                print "---This one threw 550 I can only retrieve regular files---"
                            elif str(resp).startswith("550 Can't change directory to"):
                                print "---This one threw 550 Can't change directory to...---"
                            else:
                                print "***UNEXPECTED ERROR WARNING!!!***"
                        
                    
                    if document_list == "ERROR":
                        print "[ERROR] Not able to determine if documents or not."
                        
                    elif document_list: #checks to see if the list has data
                        
                        print "(There ARE documents under: " + str(dp.sk_communicationchannel) + ")"
                
                        for document in range(len(document_list)):
                            #print document_list[document]
                            filename, type, file_datetime = document_list[document].split()
                            #print "filename: " + str(filename)
                            #print "type: " + str(type)
                            #print "cutoff date: " + str(cutoff_date) # this is the modtime that is appended to the end of filename!!!
                            
                            
                            file_datetime = datetime.strptime(file_datetime, '%Y%m%d%H%M%S') #correct format of datetime object
                            current_datetime = datetime.now()
                            time_difference = (current_datetime - file_datetime).total_seconds() #seconds is more accurate!
                
                            
                            ''' These reference the arguments in the management command'''
                            report_cutoff_date_days = report_cutoff
                            delete_cutoff_date_days = delete_cutoff
                            
                            
                            
                            sentinel_days = 999999999999999999999 # there shouldnt bee any files older than this.
                            #cant multiply None by 86400
                            if report_cutoff_date_days == None: 
                                report_cutoff_date_days = sentinel_days
                                
                            if delete_cutoff_date_days == None:
                                delete_cutoff_date_days = sentinel_days
                                           
                                           
                            #there are 86400 seconds in a day!
                            report_cutoff_date = float(report_cutoff_date_days) * 86400 #convert to seconds
                            delete_cutoff_date = float(delete_cutoff_date_days) * 86400 #convert to seconds
                            
                            time_difference_days = time_difference/86400
                            rounded_time_difference_days = "%.2f" % time_difference_days #round it to 2 decimal places
                            
                            
                            if time_difference >= delete_cutoff_date:
                                #print file_datetime
                                #print "[TO DELETE]: " + " <" + str(rounded_time_difference_days) + " Days>  " + str(document_list[document])  
                                delete_counter = delete_counter + 1    
                            elif time_difference >= report_cutoff_date: #if the difference between the file date and the current date, then
                                #print "[TO REPORT]: " + " <" + str(rounded_time_difference_days) + " Days>  " + str(document_list[document]) 
                                report_counter = report_counter + 1
                            else:
                                #print "[NO ACTION]: " + " <" + str(rounded_time_difference_days) + " Days>  " + str(document_list[document])
                                no_action_counter = no_action_counter + 1
                        
                    elif not document_list:
                        print "(NO documents under: " + str(dp.sk_communicationchannel) + ")"
                        
                        
                    print "(" + str(delete_counter) + ")" + " Documents will be [DELETED]"
                    print "(" + str(report_counter) + ")" + " Documents will be [REPORTED]"
                    print "(" + str(no_action_counter) + ")" + " Documents will take [NO ACTION] \n"
                        
                       
                       
                    '''create your message here! '''      
                    '''
                    msg = msg + '\n' +  "Communication ID: " + str(obj.communicationid)
                    msg = msg + '\n' +  "Connection URL: " + str(obj.connectionURL)
                    msg = msg + '\n' +  "User: " + str(obj.user)
                    msg = msg + '\n' +  "Password: " + str(obj.password)
                    msg = msg + '\n' +  "Mode: " + str(obj.mode)
                    msg = msg + '\n' +  "Active: " + str(obj.active)
                    msg = msg + '\n' +  "Name: " + str(obj.name)
                    msg = msg + '\n' +  "Port:  " + str(obj.port)
                    msg = msg + '\n' +  "SK Partner: " + str(obj.sk_partner)
                    msg = msg + '\n' +  "Test Connection URL: " + str(obj.test_connectionURL)
                    msg = msg + '\n' +  "Test User: " + str(obj.test_user)
                    msg = msg + '\n' +  "Test Password: " + str(obj.test_password)
                    msg = msg + '\n' +  "Test Port: " + str(obj.test_port)
                
                
                    msg = msg + '\n' +  "Docpoint PrimaryKey: " + str(dp.pk)
                    msg = msg + '\n' +  "Docpoint Name: " + str(dp.name)
                    msg = msg + '\n' +  "Docpoint Qualifier: " + str(dp.qualifier)
                    msg = msg + '\n' +  "Docpoint DocumentType: " + str(dp.documenttype)
                    
                    print dp.docpointid
                    print dp.mask
                    print dp.deleteAtSource
                    print dp.sk_communicationchannel
                    print dp.channeltarget
                    print dp.docpointtype
                    
                    msg = msg + '\n\n' +  "Documents Listed under the Docpoint: "
    
                    for document in range(len(document_list)):
                        msg = msg + '\n' +  document_list[document]
                        
                    msg = msg + '\n\n' + "--------------------------------------------------------------"+ '\n\n'
                    '''
                        
                            
        #ts_util.sendMessage(['cmeeks@re-trans.com', ], headline, msg)
        print "Email sent!"
        print msg
              
        