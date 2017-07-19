from pymongo import MongoClient

# ******************************************************************
# API Information
# ******************************************************************
# Console Output - Normal - markpy.printToConsole(str)
# Console Output - Error - markpy.printErrorToConsole(str)
#
# Return Entire User List - markpy.getUserList()
#
# Import system states from file - markpy.ImportStates(raw_text_file)
#
# Process State Transitions - markpy.ProcessTransitions(raw_text_file)
#
# Predict User Class - markpy.predictUserClass(raw_text_file)
# ******************************************************************





# Need to configure settings through API
client = MongoClient()
client = MongoClient('localhost', 27017)
db = client.markpy


states = db.states
startingStates = db.StartingStates
transitionMatrixUsers = db.TransitionMatrixUsers
startStateUsers = db.StartStateUsers

def printErrorToConsole(str):
    print()
    print("MarkPy Error: {}".format(str))

def printToConsole(str):
    print()
    print("MarkPy: {}".format(str))

def getUserList():
    userList = []
    for record in startStateUsers.find():
        if record['userId'] not in userList:
            userList.append(record['userId'])
    return userList


# Input File should be in the form of :
# state1
# state2
# state3
def ImportStates(raw_text_file):
    printToConsole("Importing states ...")
    with open(raw_text_file) as f:
        content = f.readlines()
    for record in content:
        state = record.strip()
        recordObject = {}
        recordObject['state'] = state
        try:
            states.update(recordObject,recordObject,upsert=True)
        except:
            printErrorToConsole("Insertion to mongo failed")
            printErrorToConsole("Import failed.")
    printToConsole("Import completed.")
    f.close()

# Input File should be in the form of :
# user1 state1
# user1 state2
# user1 state3
def ProcessTransitions(raw_text_file):
    printToConsole("Processing Transitions ...")

    with open(raw_text_file) as f:
        content = f.readlines()

    prevState = None
    userId = None

    for textRecord in content:
        textRecord  = textRecord.split(" ")
        userId      = textRecord[0].strip()
        currState   = textRecord[1].strip()

        # Processing the start state
        startStateRecord = startStateUsers.find_one({"userId": userId, "state": currState})
        if startStateRecord:
            oldF = startStateRecord['F']
            startStateUsers.update(startStateRecord,
            {
                '$set': {'F':oldF+1}
            })
        else:
            startStateUsers.insert_one({"userId": userId, "state": currState,"F": 1})


        # Processing Transitions
        if prevState:
            # Collection Used: TransitionMatrix {userId,fromState,toState,prob}
            # Updation of F values
            transitionRecord = transitionMatrixUsers.find_one({"userId": userId, "fromState": prevState, "toState": currState})
            # if entry already exists, increase F in records with (fromState and toState)
            if transitionRecord:
                oldF    = transitionRecord['F']
                newF    = oldF+1
                try:
                    transitionMatrixUsers.update(transitionRecord,
                    {
                        '$set': {"F": newF}
                    })
                except:
                    printErrorToConsole("Mongo error while updating record")
            # if entry does not exist, create new record with F=1 and M from some same fromState record (fromState and toState)
            else:
                # Get Sample same fromState record
                try:
                    sampleRecord = transitionMatrixUsers.find_one({"userId": userId, "fromState": prevState})
                    mValueOld = sampleRecord['M']
                    transitionMatrixUsers.insert_one({"userId": userId, "fromState": prevState, "toState": currState, "prob": 999, "M": mValueOld, "F": 1})
                # If entry is first of fromState
                except:
                    transitionMatrixUsers.insert_one({"userId": userId, "fromState": prevState, "toState": currState, "prob": 999, "M": 0, "F": 1})
            # increase M values for records with common(userId, fromState)
            allFromRecords = transitionMatrixUsers.find({"userId": userId, "fromState": prevState},modifiers={"$snapshot": True})
            for j in allFromRecords:
                try:
                    old_M    = j['M']
                    new_M    = old_M + 1
                    transitionMatrixUsers.update(j,
                    {
                        '$set': {"M": new_M}
                    })
                except e:
                    printErrorToConsole(e)

            # Processing Probabilities
            allFromRecords = transitionMatrixUsers.find({"userId": userId, "fromState": prevState},modifiers={"$snapshot": True})
            for k in allFromRecords:
                try:
                    mValue    = k['M']
                    fValue    = k['F']
                    new_ProbFloat = float(fValue)/mValue
                    new_Prob = round(new_ProbFloat,4)
                    transitionMatrixUsers.update(k,
                    {
                        '$set': {"prob": new_Prob}
                    })
                except e:
                    printErrorToConsole(e)

            prevState = currState
        else:
            prevState = currState


    # Update M values in start states
    # Get M value for user
    M = 0
    for record in startStateUsers.find({'userId': userId}):
        M += record['F']
    # Update M value and prob in each starting state for user
    for record in startStateUsers.find({'userId': userId}):
        prob = round(float(record['F'])/M,4)
        startStateUsers.update(record,{
            '$set': {'M': M, 'prob': prob}
        })


    # Update probabilities of transition records
    for record in transitionMatrixUsers.find({'userId': userId}):
        prob = round(float(record['F'])/M,4)
        startStateUsers.update(record,{
            '$set': {'M': M, 'prob': prob}
        })
    f.close()

# Input File should be in the form of :
# state1
# state2
# state3
def predictUserClass(raw_text_file):
    printToConsole("Processing Trails ...")
    userList = getUserList()

    # setting intial prob to 1
    userProb = {x:1 for x in userList}

    # get start state
    with open(raw_text_file) as f:
        firstLine = f.readline()
        firstState = firstLine.strip()

    # calculating starting probabilities
    for eachUser in userList:
        try:
            firstProbRecord = startStateUsers.find_one({'userId': eachUser, 'state': firstState})
            userProb[eachUser] *= firstProbRecord['prob']
        except:
            userProb[eachUser] *= 0.01



    with open(raw_text_file) as f:
        content = f.readlines()

    prevState = None

    for i in content:
        currState = i.strip()
        if prevState:
            for eachUser in userList:
                try:
                    transitionRecord = transitionMatrixUsers.find_one({'userId': eachUser, 'fromState': prevState, 'toState': currState})
                    userProb[eachUser] *= transitionRecord['prob']*10
                except:
                    userProb[eachUser] *= 0.1
            prevState = currState
        else:
            prevState = currState

    print(userProb)
