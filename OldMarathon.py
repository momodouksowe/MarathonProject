import time
import re
import pyodbc
import serial
import string
import math
import vault # this is a compiled Python script that contains all the passwords

# This is the main script for Burro's "Marathon" sms text message database interface.

### DEFINE FUNCTIONS ------------------------------------------------------------------------------

def PrintStatusMessage(messageText):
	# This functon is just to make it easier to toogle responses on and off

	TheAnswerToTheUltimateQuestionOfLifeTheUniverseAndEverything = 42
	
	print messageText # Comment this out to stop Marathon from printing status messages

def ReadFonaResponse(responseString):
	# This function will read the Fona response string. If there are no text messages, the funciton goes into waiting for a few seconds before calling on the system to check the inbox again. If there are text messages, the function passes them on to a function that selects the oldest one.

	PrintStatusMessage('Reading Fona\'s response string')

	PrintStatusMessage(responseString)

	# Do a regular expressions search to find text messages and extract useful information
	FonaIndoxSMSes = re.findall(r'\n\+CMGL: (\d+),"[ A-Z]+","([\+0-9wp\#]+)",.+\n(.*)\r\n',responseString)
	time.sleep(1)

	# Check if there are any messages or not
	if len(FonaIndoxSMSes) == 0:
		PrintStatusMessage('There are no new text messages')		
	elif len(FonaIndoxSMSes) >= 1:
		PrintStatusMessage('There are new text messages')
		TakeOldestSMS(FonaIndoxSMSes)
	else:
		PrintStatusMessage('ERROR: An error occoured while trying to read the SMSes in the inbox on Fona...')

def TakeOldestSMS(FonaIndoxSMSes):
	# This function selects the oldest SMS in the list passed by ReadFonaResponse

	PrintStatusMessage('Fetching the oldest unread text message')

	currentLowestID = 9999999999999999999

	for FonaIndoxSMS in FonaIndoxSMSes:
		FonaIndoxSMSID = int(FonaIndoxSMS[0])
		if FonaIndoxSMSID < currentLowestID:
			CurrentSMSTuple = FonaIndoxSMS
			currentLowestID = FonaIndoxSMSID

	CurrentSMS = list(CurrentSMSTuple)

	PrintStatusMessage('Oldest unread text message fetched:')
	PrintStatusMessage(CurrentSMS)

	SanitizeText(CurrentSMS)

def SanitizeText(CurrentSMS):
	# IMPORTANT SECURITY NOTE: The sanitation step has been retired and replaced with the use of prepared statements with parameterized queries, forcing SQL to read any input strictly as variables and therefore eliminating the need for manual sanitation. This should be combined wth a least-priviliged permission schema where the database user for the script only has the strictly nessisary permissions. This approach was selected based on a review of the following whitepaper on SQL injeection prevention from August, 2016: https://www.owasp.org/index.php/SQL_Injection_Prevention_Cheat_Sheet

	# Take out any characters that could cause trouble

	PrintStatusMessage('Sanitizing message text')

	messageText = CurrentSMS[2]
	messageText = string.replace(messageText,"'","")
	messageText = string.replace(messageText,'"','')
	messageText = string.replace(messageText,';','')
	CurrentSMS[2] = messageText

	PrintStatusMessage('Message text sanitized')
	
	CheckPhoneNumber(CurrentSMS)

def CheckPhoneNumber(CurrentSMS):
	# Checks the phone number in the current SMS against a database of trusted numbers

    currentNumber = CurrentSMS[1]
    trustedNumbersRecords = marathonConnection.execute("SELECT * FROM TrustedNumbers WHERE Number = ?",[currentNumber])
    trustedNumbersRecord = trustedNumbersRecords.fetchone()
    
    try:
            trustedNumber = trustedNumbersRecord[1]
    except:
            trustedNumber = ''
    
    if currentNumber == trustedNumber:
            PrintStatusMessage('The number is trusted')

            SelectFunction(CurrentSMS)

    elif currentNumber != trustedNumber:
            PrintStatusMessage('The number is not trusted!')
            LogRecord(CurrentSMS,'','N')
    else:
            PrintStatusMessage('ERROR: An error occoured while trying confirm that the number is trusted...')

def CheckIfAdmin(CurrentSMS):
	# Checks the phone number in the current SMS against admin numbers
    currentNumber = CurrentSMS[1]
    trustedNumbersRecords = marathonConnection.execute("SELECT * FROM AdminNumbers WHERE Number = ?",[currentNumber])
    trustedNumbersRecord = trustedNumbersRecords.fetchone()
    
    try:
            trustedNumber = trustedNumbersRecord[1]
    except:
            trustedNumber = ''
    
    if currentNumber == trustedNumber:
            PrintStatusMessage('The number is Admin')
            if re.match('add staffer ',CurrentSMS[2].lower()) != None:
                    AddStaffer(CurrentSMS)
            elif re.match('delete staffer ',CurrentSMS[2].lower()) != None:
                    DeleteStaffer(CurrentSMS)
            elif re.match('add admin ',CurrentSMS[2].lower()) != None:
                    AddAdmin(CurrentSMS)
            elif re.match('delete admin ',CurrentSMS[2].lower()) != None:
                    DeleteAdmin(CurrentSMS)
            elif re.match('add reseller ',CurrentSMS[2].lower()) != None:
                    AddReseller(CurrentSMS)
            elif re.match('delete reseller',CurrentSMS[2].lower()) != None:
                    DeleteReseller(CurrentSMS)
            elif re.match('all staffers',CurrentSMS[2].lower()) != None:
                    FindSystemStaffers(CurrentSMS)
            elif re.match('staffer named ',CurrentSMS[2].lower()) != None:
                    FindSystemStaffers(CurrentSMS)
            else:
                    SendResponseSMS(CurrentSMS,'Sorry, I did not understand your request Admin!')

    elif currentNumber != trustedNumber:
            PrintStatusMessage('The number is not an Admin!')
            SendResponseSMS(CurrentSMS,'The number is not an Admin!')
            LogRecord(CurrentSMS,'','N')
    else:
            PrintStatusMessage('ERROR: An error occoured while trying to confirm that the adder is an admin...')
            SendResponseSMS(CurrentSMS,'ERROR: An error occoured while trying to confirm that the adder is an admin...')

def CheckIfAdminOrReseller(CurrentSMS):
	# Checks the phone number in the current SMS against admin numbers
    currentNumber = CurrentSMS[1]
    trustedNumbersRecords = marathonConnection.execute("SELECT * FROM AdminNumbers WHERE Number = ?",[currentNumber])
    trustedNumbersRecord = trustedNumbersRecords.fetchone()
    
    try:
            trustedNumber = trustedNumbersRecord[1]
    except:
            trustedNumber = ''
    if currentNumber == trustedNumber:
            PrintStatusMessage('The number is an Admin')
            if re.match('all resellers',CurrentSMS[2].lower()) != None:
                    FindSystemResellers(CurrentSMS)
            elif re.match('reseller named ',CurrentSMS[2].lower()) != None:
                    FindSystemResellers(CurrentSMS)
            else:
                    SendResponseSMS(CurrentSMS,'Sorry, I did not understand your request')

    elif currentNumber != trustedNumber:
            PrintStatusMessage('The number is not an Admin!')
            stafferNumbersRecords = marathonConnection.execute("SELECT * FROM StaffNumbers WHERE Number = ?",[currentNumber])
            stafferNumbersRecord = stafferNumbersRecords.fetchone()
            
            try:
                   stafferNumber = stafferNumbersRecord[1] 
            except:
                   stafferNumber = ''
            if currentNumber == stafferNumber:
                    PrintStatusMessage('The number is a Staffer')
                    if re.match('all resellers',CurrentSMS[2].lower()) != None:
                            FindSystemResellers(CurrentSMS)
                                    
                    elif re.match('reseller named ',CurrentSMS[2].lower()) != None:
                             FindSystemResellers(CurrentSMS)
                    else:
                            SendResponseSMS(CurrentSMS,'Sorry, I did not understand your request')
                           
    elif currentNumber != stafferNumber:          
            SendResponseSMS(CurrentSMS,'The number is neither a staffer nor an Admin!')
            LogRecord(CurrentSMS,'','N')
    else:
            PrintStatusMessage('ERROR: An error occoured while trying to confirm that the adder is an admin or staffer...')
            SendResponseSMS(CurrentSMS,'ERROR: An error occoured while trying to confirm that the adder is an admin...')

def LogRecord(CurrentSMS,Response,Trusted):
    # Logs a record of the transaction in the Records table of the Marathon database
      
    currentNumber = CurrentSMS[1]
    currentMessage = CurrentSMS[2]
    PrintStatusMessage('Logging a record of the interaction')

    marathonConnection.execute("INSERT INTO records (number, message, response, trusted) VALUES ('%s','%s','%s','%s')" % (currentNumber,currentMessage,Response,Trusted))
    marathonConnection.commit()
    PrintStatusMessage('Record logged')

    DeleteMessage(CurrentSMS)

def DeleteMessage(CurrentSMS):
	# Deletes a message from Fona's internal storage

	currentID = CurrentSMS[0]
	PrintStatusMessage('Deleting message from storage...')
	serialConnection.write('\nAT+CMGD=' + str(currentID) + '\n')
	PrintStatusMessage('Message deleted from storage')

def SelectFunction(CurrentSMS):
	# Figures out which function the user is requesting
	
	currentSMSText = CurrentSMS[2]
	if re.match('add staffer ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to add staffer')
		CheckIfAdmin(CurrentSMS)
	if re.match('delete staffer ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to delete staff')
		CheckIfAdmin(CurrentSMS)
	if re.match('add admin ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to add admin')
		CheckIfAdmin(CurrentSMS)
	if re.match('delete admin ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to delete admin')
		CheckIfAdmin(CurrentSMS)
	if re.match('add reseller ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to add reseller')
		CheckIfAdmin(CurrentSMS)
	if re.match('delete reseller ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to delete reseller')
		CheckIfAdmin(CurrentSMS)
	if re.match('all staffers',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find all system resellers')
		CheckIfAdmin(CurrentSMS)
	if re.match('staffer named',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a specific system staffer')
		CheckIfAdmin(CurrentSMS)
	if re.match('all resellers',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find all system staffers')
		CheckIfAdminOrReseller(CurrentSMS)
	if re.match('reseller named',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a specific system resellers')
		CheckIfAdminOrReseller(CurrentSMS)
	elif re.match('help',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find all the queries structure')
		Help(CurrentSMS)
	elif re.match('reseller ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a reseller')
		FindID(CurrentSMS)
	elif re.match('details ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a reseller details')
		FindDetails(CurrentSMS)
	elif re.match('sales ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a reseller sales status')
		SalesStatus(CurrentSMS)
	elif re.match('job card ',currentSMSText.lower()) != None:
		PrintStatusMessage('Requesting to find a reseller job card')
		JobCard(CurrentSMS)
	else:
		Response = 'Sorry, I did not understand your request.'
		SendResponseSMS(CurrentSMS,Response)

def AddStaffer(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Adding staffer...')
		extraction = re.findall('add staffer ([ a-z]+) with number ([0-9\+]+)',currentSMSText.lower())
		userName = extraction[0][0]
		userPhoneNumber = extraction[0][1]

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("INSERT INTO trustednumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		marathonConnection.execute("INSERT INTO staffnumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		Response = 'The staffer ' + userName + ' has been added!'
		PrintStatusMessage('Staffer added')
		PrintStatusMessage('Sending welcome message...')

		# Send a welcome message to the new staff!
		welcomeMessage = 'Welcome to Marathon!'		
		SendSMSSerial(userPhoneNumber,welcomeMessage)
		PrintStatusMessage('Welcome message sent')

		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: add staffer [name] with number [phone number]")

def AddAdmin(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Adding admin...')
		extraction = re.findall('add admin ([ a-z]+) with number ([0-9\+]+)',currentSMSText.lower())
		userName = extraction[0][0]
		userPhoneNumber = extraction[0][1]

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("INSERT INTO adminnumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		marathonConnection.execute("INSERT INTO trustednumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		Response = 'The user ' + userName + ' has been added as an Admin!'
		PrintStatusMessage('Admin added')
		PrintStatusMessage('Sending welcome message...')

		# Send a welcome message to the new administrator!
		welcomeMessage = 'Welcome to Marathon! You are added as an Admin!'	
		SendSMSSerial(userPhoneNumber,welcomeMessage)
		PrintStatusMessage('Welcome message sent')

		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: add admin [name] with number [phone number]")

def AddReseller(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Adding reseller...')
		extraction = re.findall('add reseller ([ a-z]+) with number ([0-9\+]+)',currentSMSText.lower())
		userName = extraction[0][0]
		userPhoneNumber = extraction[0][1]

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("INSERT INTO resellersnumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		marathonConnection.execute("INSERT INTO trustednumbers (number, name) VALUES (?,?);",[userPhoneNumber,userName])
		marathonConnection.commit()
		Response = 'The reseller ' + userName + ' has been added!'
		PrintStatusMessage('Reseller added')
		PrintStatusMessage('Sending welcome message...')

		# Send a welcome message to the new administrator!
		welcomeMessage = "Welcome to Marathon! You are added as a reseller!"	
		SendSMSSerial(userPhoneNumber,welcomeMessage)
		PrintStatusMessage('Welcome message sent')

		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: add reseller [name] with number [phone number]")

def DeleteStaffer(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Deleting staffer...')
		extraction = re.findall('delete staffer ([0-9\+]+)',currentSMSText.lower())
		userPhoneNumber = extraction[0]

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("DELETE FROM staffnumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		marathonConnection.execute("DELETE FROM trustednumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		Response = 'The staffer ' + userPhoneNumber + ' has been deleted!'
		PrintStatusMessage('Staffer deleted')
		PrintStatusMessage('Sending delete message...')

		# Send a delete message to the old staffer!
		deleteMessage = 'You are deleted from Marathon!'		
		SendSMSSerial(userPhoneNumber,deleteMessage)
		PrintStatusMessage('Delete message sent')
		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: delete staffer [phone number]")

def DeleteAdmin(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Deleting admin...')
		extraction = re.findall('delete admin ([0-9\+]+)',currentSMSText.lower())
		userPhoneNumber = extraction[0]

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("DELETE FROM adminnumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		marathonConnection.execute("DELETE FROM trustednumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		Response = 'The admin ' + userPhoneNumber + ' has been deleted!'
		PrintStatusMessage('Admin deleted')
		PrintStatusMessage('Sending delete message...')

		# Send a delete message to the old Administrator!
		deleteMessage = 'You are deleted from Marathon!'		
		SendSMSSerial(userPhoneNumber,deleteMessage)
		PrintStatusMessage('Delete message sent')
		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: delete admin [phone number]")

def DeleteReseller(CurrentSMS):
	# Add a trusted number to the internal database

	try:
		currentSMSText = CurrentSMS[2]
		PrintStatusMessage('Deleting reseller...')
		extraction = re.findall('delete reseller ([0-9\+]+)',currentSMSText.lower())
		userPhoneNumber = extraction[0]
		print userPhoneNumber

		if userPhoneNumber[0:4] != '+233':
			userPhoneNumber = '+233' + userPhoneNumber[1:15]

		marathonConnection.execute("DELETE FROM resellersnumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		marathonConnection.execute("DELETE FROM trustednumbers WHERE number = ?",[userPhoneNumber])
		marathonConnection.commit()
		Response = 'The reseller ' + userPhoneNumber + ' has been deleted!'
		PrintStatusMessage('Reseller deleted')
		PrintStatusMessage('Sending delete message...')

		# Send a delete message to the old reseller!
		deleteMessage = 'You are deleted from Marathon!'		
		SendSMSSerial(userPhoneNumber,deleteMessage)
		PrintStatusMessage('Delete message sent')
		SendResponseSMS(CurrentSMS,Response)
	except:
	 	SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: delete reseller [phone number]")

def Help(CurrentSMS):
        # Checks the phone number in the current SMS against admin numbers

	try:
		searchResultObject = marathonConnection.execute("SELECT querystructure FROM Help")
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount >= 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += '%s ;' % (row[0])
			SendResponseSMS(CurrentSMS,Response)
				
		else:
			Response = "Sorry there was a problem. Please send : help"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send : help")
		
def FindSystemResellers(CurrentSMS):
        # Checks the system (marathon) resellers

	try:
                currentSMSText = CurrentSMS[2]
                if re.match('all resellers',currentSMSText.lower()) != None:
                        PrintStatusMessage('Requesting to find all the system resellers')
                        searchResultObject = marathonConnection.execute("SELECT * FROM resellersnumbers")
                        
                elif re.match('reseller named ',currentSMSText.lower()) != None:
                        PrintStatusMessage('Requesting to find a specific system reseller')
                        extraction = re.findall('reseller named ([ a-z]+)',currentSMSText.lower())
                        userName = extraction[0]
                        searchResultObject = marathonConnection.execute("SELECT name,number FROM resellersnumbers WHERE name = ?",[userName])
		else:
			Response = "Sorry there was a problem. Please send : all resellers or reseller named [name of person]"
			SendResponseSMS(CurrentSMS,Response)
			
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Name: %s - Number: %s ' % (row[2],row[1])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount > 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Name: %s - Number: %s ; ' % (row[2],row[1])
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: all resellers or reseller named [name of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send : all resellers or reseller named [name of person]")

def FindSystemStaffers(CurrentSMS):
        # Checks the system (marathon) resellers

	try:
                currentSMSText = CurrentSMS[2]
                if re.match('all staffers',currentSMSText.lower()) != None:
                        PrintStatusMessage('Requesting to find all the system staffers')
                        searchResultObject = marathonConnection.execute("SELECT * FROM staffnumbers")
                        
                elif re.match('staffer named ',currentSMSText.lower()) != None:
                        PrintStatusMessage('Requesting to find a specific system staffer')
                        extraction = re.findall('reseller named ([ a-z]+)',currentSMSText.lower())
                        userName = extraction[0]
                        searchResultObject = marathonConnection.execute("SELECT name,number FROM staffnumbers WHERE name = ?",[userName])
		else:
			Response = "Sorry there was a problem. Please send : all staffers or staffer named [name of person]"
			SendResponseSMS(CurrentSMS,Response)
			
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Name: %s - Number: %s ' % (row[2],row[1])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount > 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Name: %s - Number: %s ; ' % (row[2],row[1])
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: all staffers or staffer named [name of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send : all staffers or staffer named [name of person]")

def FindID(CurrentSMS):
	# Look up the ID of a specific reseller; The phone number is the search critetria

	try:
		currentSMSText = CurrentSMS[2]
		extraction = re.findall('reseller ([0-9\+]+)',currentSMSText.lower())
		searchTerm = extraction[0]
		searchQuery = '%' + searchTerm + '%'
		searchResultObject = fodderConnection.execute("select partyID, partyName from vAllPartiesWithExtraDatails where phoneNos like ?;",[searchQuery])
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'ID %s - %s ' % (row[0],row[1])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount <= 5:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'ID %s - %s ; ' % (row[0],row[1])
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount <= 10:
			Response = 'RESULTS: '
			for row in searchResults:
				Response += '%s ; ' % (row[1])
			Response = Response + 'search a specific phone number for more details...'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount > 10:
			Response = 'Your search gave ' + str(resultCount) + ' results. Please be more specific.'
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: reseller [phone number of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: reseller 3[phone number of person]")

def FindDetails(CurrentSMS):
	# Look up the Details of a specific reseller; The ID is the search critetria

	try:
		currentSMSText = CurrentSMS[2]
		extraction = re.findall('details ([0-9\+]+)',currentSMSText.lower())
		searchTerm = extraction[0]
		searchQuery = '%' + searchTerm + '%'
		searchResultObject = fodderConnection.execute("select PhoneNo1,l.cityTown,landmark,p.region from party p join locations l on p.cityTownID = l.locationID where partyID like ?;",[searchQuery])
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Phone Number: %s - Residence: %s - Land Mark: %s - Region: %s' % (row[0],row[1],row[2],row[3])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount <= 5:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Phone Number: %s - Residence: %s - Land Mark: %s - Region: %s ; ' % (row[0],row[1],row[2],row[3])
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount <= 10:
			Response = 'RESULTS: '
			for row in searchResults:
				Response += '%s ; ' % (row[0])
			Response = Response + 'search a specific phone number for more details...'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount > 10:
			Response = 'Your search gave ' + str(resultCount) + ' results. Please be more specific.'
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: details  [ID of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: details  [ID of person]")

def SalesStatus(CurrentSMS):
	# Look up the Sales Status of a specific reseller; The ID is the search critetria

	try:
		currentSMSText = CurrentSMS[2]
		extraction = re.findall('sales ([0-9\+]+)',currentSMSText.lower())
		searchTerm = extraction[0]
		searchQuery = '%' + searchTerm + '%'
		searchResultObject = fodderConnection.execute("select paidT90, DiscountLevel, creditLimit from vResellerPaidT90AndDiscountLevel a join reseller r on a.partyId = r.partyID where a.partyID like ?;",[searchQuery])
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Paid T90: %s - Discount Level: %s - Credit Limit: %s ' % (row[0],row[1],row[2])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount <= 5:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Paid T90: %s - Discount level: %s - Credit Limit: %s ; ' % (row[0],row[1],row[2])
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount <= 10:
			Response = 'RESULTS: '
			for row in searchResults:
				Response += '%s ; ' % (row[1])
			Response = Response + 'search a specific ID for more details...'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount > 10:
			Response = 'Your search gave ' + str(resultCount) + ' results. Please be more specific.'
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: sales [ID of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: sales [ID of person]")

def JobCard(CurrentSMS):
	# Look up the Job Card of a specific reseller; The ID is the search critetria

	try:
		currentSMSText = CurrentSMS[2]
		extraction = re.findall('job card ([0-9\+]+)',currentSMSText.lower())
		searchTerm = extraction[0]
		searchQuery = '%' + searchTerm + '%'
		searchResultObject = fodderConnection.execute("select productName, jobStatus, productLocation from vJobCardsLog where clientID like ?;",[searchQuery])
		searchResults = searchResultObject.fetchall()
		resultCount = len(searchResults)

		# The response depends on the number of results from the query
		if resultCount == 0:
			Response = 'Sorry, your search gave no results.'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount == 1:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Product: %s - Status: %s - Location: %s ' % (row[0],row[1],row[2])	
			SendResponseSMS(CurrentSMS,Response)					
		elif resultCount <= 5:
			Response = 'RESULT: '
			for row in searchResults:
				Response += 'Product: %s - Status: %s - Location: %s ; ' % (row[0],row[1],row[2])
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount <= 10:
			Response = 'RESULTS: '
			for row in searchResults:
				Response += '%s ; ' % (row[1])
			Response = Response + 'search a specific ID for more details...'
			SendResponseSMS(CurrentSMS,Response)
		elif resultCount > 10:
			Response = 'Your search gave ' + str(resultCount) + ' results. Please be more specific.'
			SendResponseSMS(CurrentSMS,Response)
		else:
			Response = "Sorry there was a problem. Please send: job card [ID of person]"
			SendResponseSMS(CurrentSMS,Response)

	except:
		SendResponseSMS(CurrentSMS,"Sorry there was a problem. Please send: job card [ID of person]")
		
def SendResponseSMS(CurrentSMS,Response):
	# This is the function that sends a response back to the user

	currentNumber = CurrentSMS[1]

	# Sometimes the answer is longer than 160 characters, so we have to break it up into several messages.
	individualMessageLength = 155 # max length of an individual message
	responseLength = len(Response)
	responseBlockCount = int(math.ceil(float((responseLength))/float(individualMessageLength))) # how many blocks does the message need to be broken into

	for i in range(1,responseBlockCount+1): # loop over blocks
		blockStart = (i-1)*individualMessageLength
		blockEnd = i*individualMessageLength
		if i == responseLength: # for the last block, we just send the remainder of the string
			blockText = Response[blockStart:]
		else: # for all the other blocks, we send a specific number of characters, followed by [continued]
			blockText = Response[blockStart:blockEnd]

		if (responseBlockCount >= 2):
			blockCounter = '(%s/%s)' % (i,responseBlockCount)
			blockText = blockCounter + blockText

		SendSMSSerial(currentNumber,blockText)

	LogRecord(CurrentSMS,Response,'Y')

def SendSMSSerial(number,message):
	# This handles the serial-port communication nessisary to send an SMS

	print '----- SMS -----'
	print message
	print '----- SMS -----'
	
	serialConnection.write('\rAT+CMGS=\"' + number + '\"\r')
	time.sleep(1)
	serialConnection.write(message)
	time.sleep(1)
	serialConnection.write(chr(26))
	time.sleep(7)
	serialConnection.write('\r\n')	

### INITIATE THE PROGRAM -------------------------------------------------------------------

marathonConnection = pyodbc.connect(DSN='marathonscript-connector') # Connection to the local postgres database as defined in /etc/odbc.ini with a reference to the driver listed in /etc/odbcinst.ini	
fodderConnection = pyodbc.connect('DRIVER=FreeTDS;SERVER=10.11.5.2;PORT=1433;DATABASE=Fodder2.1Live;UID=%s;PWD=%s;TDS_Version=8.0;' % (vault.fodderUID,vault.fodderPWD)) # connection to Burro's Fodder database as defined in /etc/odbc.ini with a reference to the driver listed in /etc/odbcinst.ini. Note that passwords for freeTDS connections cannot be stored in .ini files.
serialConnection = serial.Serial("/dev/serial0", baudrate=115200, timeout=3.0) # Connection to the serial0 port, where the Fona GSM modem is connected
serialConnection.write('\r\n') # Clean the serial terminal in case some data is left
time.sleep(1)
serialConnection.write('AT+CMGF=1\r\n') # Set the SIM card to SMS mode and tell it that messages will be passed as binary ASCII-encoded strings
time.sleep(1)

### RUN INFINITE LOOP -----------------------------------------------------------------------------

while True:
	
	# Query Fona's inbox and return a string with the query response
	PrintStatusMessage('Querying Fona\'s inbox')

	serialConnection.write('\rAT+CMGL=\"ALL\"\r')
	time.sleep(2)

	responseString = ''

	while serialConnection.inWaiting() > 0:
		responseString += serialConnection.read(1)

	# The following line contains a test string for if you temporarily cannot access the modem 
	# responseString = '\n+CMGL: 11,"REC READ","57p666131323","","16/11/18,18:00:51+00"\nTest 2\r\n'

	# This function initiates a series of funcitons to treat the text message
	ReadFonaResponse(responseString)

	PrintStatusMessage('waiting...')
	time.sleep(5)
