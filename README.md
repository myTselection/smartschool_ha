
[![GitHub release](https://img.shields.io/github/release/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/releases)
![GitHub repo size](https://img.shields.io/github/repo-size/myTselection/smartschool_ha.svg)

[![GitHub issues](https://img.shields.io/github/issues/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/commits/main)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/graphs/commit-activity)


# Smartschool Home Assistant integration
[Smartschool](https://www.smartschool.be/) Home Assistant custom component. This custom component has been built from the ground up to bring your Smartschool details into Home Assistant to help you towards a better follow up on your school. This integration is built against the public website provided by Smartschool and has not been tested for any other countries.

This integration is in no way affiliated with Smartschool. 
| :warning: Please don't report issues with this integration to Smartschool, they will not be able to support you. |
| ----------------------------------------------------------------------------------------------------------------------|


This integration has been based on the python application of [https://github.com/IntelCoreI6/smartschool_mcp](https://github.com/IntelCoreI6/smartschool_mcp) (fork of [https://github.com/svaningelgem/smartschool](https://github.com/svaningelgem/smartschool)).

This application has been [forked and extended](https://github.com/myTselection/smartschool_mcp) to support parallel sessions and to support authentication with Google Authenticator (2FA).
<p align="center"><img src="https://github.com/myTselection/smartschool_ha/blob/main/logo.png?raw=true" width="500"/></p>

## Installation
- [HACS](https://hacs.xyz/): (awaiting [brands](https://github.com/home-assistant/brands/pull/7235) HACS approval: search for Smartschool in HACS integrations and install)
  - [![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=myTselection&repository=smartschool_ha&category=integration)
  - or add this repository as custom repository into your HACS
- Restart Home Assistant
- Add 'Smartschool' integration via HA Settings > 'Devices and Services' > 'Integrations'
- Provide Smartschool credentials:
  - smartschool domain: this should be the url used to login, eg '_school_.smartschool.be'
  - username: username, typically the first and last name of the child
  - password: password of the child account or password of the parent account
  - MFA: 
    - when using child account, this is by default the date of birth of the child, notation YYYY-MM-DD
    - when using a parent account or if 2FA has been enabled, the Google Authenticator secret is to be set (see Smartschool > Profile > Login with 2 steps > [Authenticator app](https://school.smartschool.be/profile/twofactor/googleAuthenticator)). If the secret is not known, the Authenticator app will need to be re-linked. During setup of the authenticator app, the 2FA secret can be shown instead of the QR code) 

## Usage

After adding Smartschool account, a 3 sensors and 5 Todo lists will be added.

### Sensors:

- **Tasks**
A sensor `sensor.smartschool_[username]_[school]_tasks` will be added showing the number of tasks to be done for the next schoolday.
The sensor also shows the last update from Smartschool in the attribut last_update.
If desired, an automation can be setup to get notified if the number of tasks for the next schoolday would change.

- **Messages**
A sensor `sensor.smartschool_[username]_[school]_messages` will be added showing the number of outstanding (unread) messages.
The sensor also shows the number of read and total number of messages, as well as the last update from Smartschool in the attribut last_update.

- **Results** (untested)
A sensor `sensor.smartschool_[username]_[school]_results` will be added showing the total results.
Since the results are not always available (some schools only make them available at sepcific intervals), this hasn't been tested yet. Extra results per course might be made availble later on, once tested.
The sensor also shows the last update from Smartschool in the attribut last_update.


### Todo lists:
  - Separate Todo list for "Toetsen", "Taken", "Meebrengen", "Volgende" and "Schooltas"
  - When checking items in Home Assistant Todo list as completed, this will not be reflected into Smartschool. 
  - Only future tasks are fetched from Smartschool but no updates from Home Assistant are sent towards Smartschool.
  - Only items left todo as of today are listed, past items of previous days will automatically be removed of all Todo lists.
  - Each Todo list will contain the username between brackets to distinct the list of different users (if multiple accounts are linked).
  - The Todo items can be checked, if the same item also appears in another list, it will be marked as checked in there as well.
  
  - **Volgende** (`todo.volgende_[username]`):
    - overview of all "Taken", "Toetsen", "Meebrengen" for next planned schoolday (next day or next day after weekend/holiday)
  - **Schooltas** (`todo.schooltas_[username]`):
    - overview of all "Meebrengen" for next planned schoolday (next day or next day after weekend/holiday)
    - overview of all lessons that will take place the next planned schoolday (next day or next day after weekend/holiday)
    - with this checklist, it's easy to validate all stuff that should be in the schoolbag
  - **Meebrengen** (`todo.meebrengen_[username]`):
    - within list "Meebrengen", the title will be the item to bring, while the description will be the course info
    - for other lists, the title contains the course name and the description contains the details of the action
  - **Taken** (`todo.taken_[username]`):
    - All upcoming tasks to do, known for coming days
  - **Toetsen** (`todo.toetsen_[username]`):
    - All upcoming tests scheduled, known for coming days

### Calendar:

I recently [discovered](https://community.home-assistant.io/t/template-with-calendar-events-in-rss-feed/626149/5) Smartschool allows to export lessons and tasks as a iCal calendar.

Home Assistant support importing iCal calendar using the default "[Remote Calendar](https://www.home-assistant.io/integrations/remote_calendar/)" integration. Add the url retrieved from Smartschool > Go To > Schoolagenda > Export. 

Still testing the options of this calendar integration, will probably have to wait till september to get some usefull data into it.

## Status

Still some optimisations are planned, see [Issues](https://github.com/myTselection/smartschool_ha/issues) section in GitHub.

## Technical pointers
The main logic and API connection related code can be found within source code smartschool_ha/custom_components/smartschool_ha:
- [sensor.py](https://github.com/myTselection/smartschool_ha/blob/main/custom_components/smartschool_ha/sensor.py)
- [todo.py](https://github.com/myTselection/smartschool_ha/blob/main/custom_components/smartschool_ha/tddo.py)
- [utils.py](https://github.com/myTselection/smartschool_ha/blob/main/custom_components/smartschool_ha/utils.py) -> mainly pointer to Smartschool class

All other files just contain boilerplat code for the integration to work wtihin HA or to have some constants/strings/translations.

If you would encounter some issues with this custom component, you can enable extra debug logging by adding below into your `configuration.yaml`:
```
logger:
  default: info
  logs:
     custom_components.smartschool_ha: debug
```

## Example usage & screenshots:

<p align="left"><img src="https://github.com/myTselection/smartschool_ha/blob/main/Example1.png?raw=true"/></p>

<p align="left"><img src="https://github.com/myTselection/smartschool_ha/blob/main/Setup.png?raw=true"/></p>

<p align="left"><img src="https://github.com/myTselection/smartschool_ha/blob/main/Sensors.png?raw=true"/></p>
