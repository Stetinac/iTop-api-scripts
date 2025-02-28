"""
Set default Profile and Organisation for disabled users

"""

__author__ = "Pavel Stetinac Stetina"

import requests
import json
import urllib3
import xml.etree.ElementTree as ET
import os
import sys
urllib3.disable_warnings()

DRY_RUN=False # If True only prepare data without calling an API
##############################################################################################################
# Default config

ITOP_CLASSES=("UserLDAP", "UserExternal") # iTop Classes for cleaning users 
XML_LDAP="/opt/ldap-data-collector"       # Path for Class XML config file
XML_SAML="/opt/ldap-data-collector_saml"  # Path for Class XML config file
XML={"UserLDAP":XML_LDAP,"UserExternal":XML_SAML} # Dict of Classes and paths
CFG_FILE="/conf/params.local.xml"   # Path for XML config file - default is /conf/params.local.xml
USER_ORG="my super organization" # Name of Default organization
ITOP_PROFILE=2 # ID (number) of default profile - 2 is for "Portal user"
X_DAYS = 10 # number of days back in history to check changes


def findDefOrg():
    """
    Find ID of specific Organization and return ID as int
    """
    REQUEST_KEY = f'SELECT Organization WHERE name="{USER_ORG}"'

    json_data = {
        "operation": "core/get",
        "class": "Organization",
        "key": REQUEST_KEY,
        "output_fields": "id",
    }
    encoded_data = json.dumps(json_data)
    api_data=API_Request(encoded_data)
    json_data=json.loads(api_data)
    finds=json_data['message']
    numout=finds.split()
    if (int(numout[1])) == 1: # True only if one Org is find
        for i in json_data['objects']:
            return_data = json_data['objects'][i]['fields']['id']
            print(f"Find and set Default org ID: {return_data}")
            return int(return_data)  
    elif (int(numout[1])) > 1: # If two or more Org is find:
        print("To many Organizations are found")
        exit()
    else:
        print("No Organization found")
        exit()

def findDisabledUsers(user_type):
    """
    Find disabled users for Class defined in user_type
    Returns JSON data from API
    """
#    REQUEST_KEY = f'SELECT {user_type} WHERE status = "disabled"' # OQL select
    REQUEST_KEY = f'SELECT u FROM CMDBChangeOpSetAttributeScalar AS sa JOIN CMDBChange AS c ON sa.change = c.id JOIN {user_type} AS u ON sa.objkey = u.id WHERE sa.objclass = "{user_type}" AND c.date >= DATE_SUB(NOW(), INTERVAL {X_DAYS} DAY) AND sa.attcode = "status" AND u.status = "disabled"'

    json_data = {
        "operation": "core/get",
        "class": user_type,
        "key": REQUEST_KEY,
        "output_fields": "login, status, contactid, profile_list, allowed_org_list",
    }
    encoded_data = json.dumps(json_data)
    return API_Request(encoded_data)

def decodeUserStatus(in_data):
    """
    Processes JSON data from in_data
    Returns dict of {login:{profile:[0,1,2,3],allowed_org_list:[0,1,2,3]}} 
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
                u_login=json_data['objects'][i]['fields']['login'] #extract user login

                for x in json_data['objects'][i]['fields']['profile_list']: # extract user profiles
                    u_profiles.append(int(x['profileid']))

                if u_profiles and len(u_profiles) == 1 and ITOP_PROFILE in u_profiles: # if user have default profile set output to none
                    u_profiles = "none"

                if not u_profiles and len(u_profiles) < 1: # if user have no profile set output to none - impossible, but why not be prepared
                    u_profiles = "empty"

                for y in json_data['objects'][i]['fields']['allowed_org_list']: # extract user organizations
                    u_allowed_org.append(int(y['allowed_org_id']))

                if u_allowed_org and len(u_allowed_org) == 1: # if user have default org set output to none
                    u_allowed_org = "none"

                if not u_allowed_org and len(u_allowed_org) < 1: # if user have no org set output to none
                    u_allowed_org = "empty"

                return_data[u_login]={'profile':u_profiles, 'allowed_org':u_allowed_org} # add data to dict

            return return_data # return dicts with data
        else:
            print("No data with users are given")
    else:
        print("No data for decodeUserStatus") 

def clearUserSetup(users, user_type):
    """
    Set default Org and Profile for users by login and user_type (class)

    """
    REQUEST_OPERATION = "core/update"
    REQUEST_CLASS = user_type
    REQUEST_COMMENT = "Update by snake updater"
    REQUEST_OUTPUT_FIELDS = "status"

    if not users:
        print(f"No {user_type} users to update")
    else:
        for _ in users:
            print(f"Update {user_type} status for: {_}")
            login=_ # set login
            fields={} 
            t_profile=users[_]["profile"] # extrakt user list of profiles
            t_org=users[_]["allowed_org"] # extrakt user list of allowed org

            if t_profile != "none":     # if profile list is not only "none" set default profile
                print("Set default Profile")
                fields['profile_list']=[{"profileid": ITOP_PROFILE}]

            if t_org != "none":  # if org list is not only "none" set default profile
                print("Set default Organisation")
                fields['allowed_org_list']=[{"allowed_org_id": ITOP_ORG}]

            if fields: # when fileds is not empty, prepare data for call API
                json_data = {
                     "operation": REQUEST_OPERATION,
                     "comment": REQUEST_COMMENT,
                     "class":REQUEST_CLASS,
                     "key":{"login": login},
                     "output_fields":REQUEST_OUTPUT_FIELDS,
                     "fields":fields
                }
                encoded_data = json.dumps(json_data)
                print(f"Update {user_type} status for: {login} set defaults")
#                print(encoded_data)

                if not DRY_RUN: # Call API if DRY_RUN is not set to True
                    API_Request(encoded_data)

            else:
                print(f"Update {user_type} status for: {login} nothing to do")

#        exit()


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
    return req.text

if __name__ == "__main__":
    if 'dry' in str(sys.argv): # You can call script with dry parameter - it overrides the DRY_RUN variable
        DRY_RUN = True

    if DRY_RUN:
        print("Dry run is enabled")

    for _ in ITOP_CLASSES: # process given classes
        cfg_file = XML[_] + CFG_FILE # make path for XML cfg file

        ITOP_ORG=""

        if os.path.isfile(cfg_file): # testing if XML cfg file exists
            # take data from XML cfg file
            tree=ET.parse(cfg_file)
            root=tree.getroot()
            ITOP_USER = root[1].text
            ITOP_URL = root[0].text
            ITOP_PWD = root[2].text

            # calling functions
            ITOP_ORG = findDefOrg() # find Org ID
            dis_users = findDisabledUsers(_)    # find disabled users
            dec_users = decodeUserStatus(dis_users) # process JSON data from previous task
            clearUserSetup(dec_users, _)    # clear users without defualt Org and Profile

        else:
            print(f"error: {cfg_file} does not exist")
            exit()
