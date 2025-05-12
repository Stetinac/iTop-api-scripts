"""
Synchronize Orgs and Profiles from UserLDAP class to UserExternal class

"""

__author__ = "Pavel Stetinac Stetina"

import requests
import json
import urllib3
import xml.etree.ElementTree as ET
import os
import sys
urllib3.disable_warnings()

DRY_RUN=False # If True only prepare data without calling iTop API
##############################################################################################################
# Default config

ITOP_ORG=4  # ID (number) of default org
ITOP_PROFILE=2 # ID (umber) of default profile
XML_LDAP="/opt/ldap-data-collector"       # Path of Class XML config file - working directory of iTop LDAP Sync tool
CFG_FILE="/conf/params.local.xml"   # Path of XML config file - default is /conf/params.local.xml
cfg_file = XML_LDAP + CFG_FILE

def findEnabledUsers():
    """
    Find enabled users for UserLDAP Class
    Returns JSON data from API
    """
    # Select UserLDAP changes since 10 days ago
    REQUEST_KEY ="SELECT u FROM CMDBChangeOpSetAttributeScalar AS sa JOIN CMDBChange AS c ON sa.change = c.id JOIN UserLDAP AS u ON sa.objkey = u.id WHERE sa.objclass = 'UserLDAP' AND c.date >= DATE_SUB(NOW(), INTERVAL 10 DAY) AND sa.attcode = 'status'"
    
    json_data = {
        "operation": "core/get",
        "class": "UserLDAP",
        "key": REQUEST_KEY,
        "output_fields": "login, status, contactid, email, profile_list, allowed_org_list",
    }
    encoded_data = json.dumps(json_data)
    return API_Request(encoded_data)

def decodeUserStatus(in_data):
    """
    Processes JSON data from in_data
    Returns dict of {login:{profile:[0,1,2,3], allowed_org_list:[0,1,2,3], email:example.example.org}} 
    """
    if in_data:
        json_data=json.loads(in_data)
        finds=json_data['message'] # extract number of returned users
        numout=finds.split() # extract only number for test
        return_data={}

        if (int(numout[1])) > 0:
            for i in json_data['objects']:
                u_profiles=[]
                
                u_allowed_org=[]
                
                u_login=json_data['objects'][i]['fields']['login'] # extract user login
                
                u_email=json_data['objects'][i]['fields']['email'] # extract user email

                for _ in json_data['objects'][i]['fields']['profile_list']: # extract list of user profiles
                    u_profiles.append(int(_['profileid']))

                for _ in json_data['objects'][i]['fields']['allowed_org_list']: # extract list of user org
                    u_allowed_org.append(int(_['allowed_org_id']))

                return_data[u_login]={'profile':u_profiles, 'allowed_org':u_allowed_org, 'email': u_email}
            
            return return_data
        else:
            print("No LDAP users to decode")
    else:
        print("No data for decodeUserStatus") 

def setUserExternalSetup(users):
    user_type="UserExternal"
    """
    Sync Profile and Org for ExternalUser class by UserLDAP
    ExternalUser is set by email as login
    UserLDAP email == UserExternal login
    """
    REQUEST_OPERATION = "core/update"
    REQUEST_CLASS = user_type
    REQUEST_COMMENT = "Update by snake updater"
    REQUEST_OUTPUT_FIELDS = "status"

    if users:
        for t_user in users:
            fields={}
            tt_profile=[]
            tt_org=[]

            ldap_login=t_user

            login=users[t_user]["email"] # extract eamil and set as a login
            t_profile=users[t_user]["profile"]   # extract list of profiles
            t_org=users[t_user]["allowed_org"]   # extract list of org

            print(f"Update UserExternal status for: {login} from UserLDAP: {ldap_login}")

            if t_profile: # prepare list of profiles data for JSON
                for _ in t_profile:
                    tem_dp={}
                    tem_dp['profileid']=_
                    tt_profile.append(tem_dp)
                    fields['profile_list']=tt_profile
            else:
                print(f"UserLDAP: {ldap_login} has no profiles")

            if t_org:# prepare list of org data for JSON
                for _ in t_org:
                    tem_do={}
                    tem_do['allowed_org_id']=_
                    tt_org.append(tem_do)
                fields['allowed_org_list']=tt_org
            else:
                print(f"UserLDAP: {ldap_login} has no organization")

            if fields:
                json_data = {
                     "operation": REQUEST_OPERATION,
                     "comment": REQUEST_COMMENT,
                     "class":REQUEST_CLASS,
                     "key":{"login": login},
                     "output_fields":REQUEST_OUTPUT_FIELDS,
                     "fields":fields
                }
                encoded_data = json.dumps(json_data)

                if not DRY_RUN: # Call API if DRY_RUN is not set to True
                    API_Request(encoded_data)
            else:
                print(f"Update UserExternal status for: {login} nothing to do")
    else:
        print(f"No LDAP users to be updated")


def API_Request(json_payload):
    """
    iTop API handler
    """
    try:
        req = requests.post(ITOP_URL+'/webservices/rest.php?version=1.3',
                            verify=False,
                            data={'auth_user': ITOP_USER ,
                                  'auth_pwd': ITOP_PWD ,
                                  'json_data': json_payload})
        
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


    if os.path.isfile(cfg_file):
        # take data from XML cfg file 
        tree=ET.parse(cfg_file)
        root=tree.getroot()
        ITOP_USER = root[1].text
        ITOP_URL = root[0].text
        ITOP_PWD = root[2].text

        # calling functions 
        en_users = findEnabledUsers()  # Find enabled UserLDAP class users
        dec = decodeUserStatus(en_users)   # Process JSON and return dict of logins with data (emails, org lists, profile lists)
        setUserExternalSetup(dec)   # Set UserLDAP orgs and profiles to UserExternal class 

    else:
        print(f"error: {cfg_file} does not exist")
        exit()
