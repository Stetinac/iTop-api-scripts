Python scripts for [iTop][0] API by [Combodo][1].

[0]: https://github.com/Combodo/iTop
[1]: https://www.combodo.com

## Features
- Sync Profiles and Organisations from UserLDAP to UserExternal (SAML)
- Find users with status "Disabled" and set status to "Enabled" if they are found in the iTopUserLDAPCollector-1.csv file
- Set default Organization and Profile to Disabled UserLDAP and UserExternal users
- Set UserLocal Password expiration attribut to "Expired" after x days of "Password renewed on"

## Prerequisites
- iTop 3.x>
- Python 3.11>
- Python modules
- Combodo [iTop Collector base][3] extension
- Combodo [iTop LDAP Collector module][4] extension

[3]: https://github.com/Combodo/itop-data-collector-base
[4]: https://github.com/Combodo/itop-data-collector-ldap


## Install
```
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```
- Set the "Default config" section in the scripts

## Using
```
source .env/bin/activate
python3 <script-name>
```
