"""
Set UserLocal Password expiration attribut to "Expired" after x days of "Password renewed on"
"""
__author__ = "Pavel Stetinac Stetina"

import requests
import json
import urllib3
import sys
urllib3.disable_warnings()

# ITOP_USER = "stetina-api"
ITOP_URL = "https://myitopurl.com" # iTop URL
ITOP_token = "my token"
ITOP_days = 365 # set password exspiration after x days

DRY_RUN=False # If True only prepare data without calling API
##############################################################################################################

def findExspiredUsers():
    """
    Find users for Class UserLocal with "can_expire" attribut
    Returns JSON data
    """
    REQUEST_KEY = f"SELECT UserLocal WHERE expiration='can_expire' AND password_renewed_date <= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL {ITOP_days} DAY),'%Y-%m-%d')"
    json_data = {
        "operation": "core/get",
        "class": "UserLocal",
        "key": REQUEST_KEY,
        "output_fields": "login, friendlyname, email, password_renewed_date, expiration",
    }
    encoded_data = json.dumps(json_data)
    return API_Request(encoded_data)

def decodeUserStatus(in_data):
    """
    Processes JSON data from in_data
    Returns list of logins
    """
    if in_data:
        json_data=json.loads(in_data)
        finds=json_data['message'] # extract number of returned users
        numout=finds.split() # extract only number for test
        return_data=[]
        if (int(numout[1])) > 0:
            for i in json_data['objects']:
                return_data.append(json_data['objects'][i]['fields']['login']) #extract user login
            # print(return_data)
            return return_data # return dicts with user logins
        else:
            print("No data for update users are given, nothing to do!")
            exit()
    else:
        print("No data for decodeUserStatus") 
        exit()

def setUserExpired(users):
    """
    Set Expired for LocalUsers in "users"
    """
    REQUEST_OPERATION = "core/update"
    REQUEST_CLASS = "UserLocal"
    REQUEST_COMMENT = "Update by snake updater"
    REQUEST_OUTPUT_FIELDS = "status,expiration"
    EXPIRATION = "force_expire"

    if not users:
        print(f"No users to update status")
    else:
        for _ in users:
            login=_ # set login

            json_data = {
                "operation": REQUEST_OPERATION,
                "comment": REQUEST_COMMENT,
                "class":REQUEST_CLASS,
                "key":{"login": login},
                "output_fields":REQUEST_OUTPUT_FIELDS,
                "fields":{"expiration": EXPIRATION}}
            encoded_data = json.dumps(json_data)
       
            if not DRY_RUN: # Call API if DRY_RUN is not set to True
                print(f"User {login} set to {EXPIRATION}")
                API_Request(encoded_data)
            else:
                print(f"DRY RUN: User {login} set to {EXPIRATION}")

def API_Request(json_payload):
    """
    iTop API handler
    """
    if not ITOP_token:
        print("ITOP_token variable is empty")
        exit()
    try:
        req = requests.post(ITOP_URL+'/webservices/rest.php?version=1.3',
                            verify=False,
                            data={'auth_token': ITOP_token,'json_data': json_payload})

        req.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        raise SystemExit(err)

    json_data=json.loads(req.text)
    if json_data['code']> 0:
        print(f"Error code: {json_data['code']}, Error message: {json_data['message']}")
        exit()
    return req.text

if __name__ == "__main__":
    if 'dry' in str(sys.argv): # You can call script with dry parameter - it overrides the DRY_RUN variable
        DRY_RUN = True

    if DRY_RUN:
        print("Dry run is enabled")

    exs_users = findExspiredUsers()
    dec_users = decodeUserStatus(exs_users)
    setUserExpired(dec_users)
