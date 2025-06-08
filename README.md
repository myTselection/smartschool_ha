
[![GitHub release](https://img.shields.io/github/release/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/releases)
![GitHub repo size](https://img.shields.io/github/repo-size/myTselection/smartschool_ha.svg)

[![GitHub issues](https://img.shields.io/github/issues/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/commits/main)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/myTselection/smartschool_ha.svg)](https://github.com/myTselection/smartschool_ha/graphs/commit-activity)


# Smartschool Home Assistant integration
[Smartschool](https://www.smartschool.be/) Home Assistant custom component. This custom component has been built from the ground up to bring your Smartschool details into Home Assistant to help you towards a better follow up on your school. This integration is built against the public website provided by Smartschool and has not been tested for any other countries.

This integration is in no way affiliated with Smartschool. 
| :warning: Please don't report issues with this integration to Smartschool, they will not be able to support you.** |
| ----------------------------------------------------------------------------------------------------------------------|


Integration of python application of [https://github.com/IntelCoreI6/smartschool_mcp](https://github.com/IntelCoreI6/smartschool_mcp) (fork of [https://github.com/svaningelgem/smartschool](https://github.com/svaningelgem/smartschool)).
<p align="left"><img src="./logo.png" width="64"/></p>

## Installation
- [HACS](https://hacs.xyz/): search for Smartschool in HACS integrations and install
  - [![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=myTselection&repository=smartschool_ha&category=integration)
  - or add this repository as custom repository into your HACS
- Restart Home Assistant
- Add 'Smartschool' integration via HA Settings > 'Devices and Services' > 'Integrations'
- Provide Smartschool credentials

## Usage

After adding Smartschool account a sensor and 4 Todo lists will be added.

- Sensor: 
  - so far limited use, may be extended in future
  - currently only showing last update date

- Todo lists:
  - Separate Todo list for "Toetsen", "Taken", "Meebrengen" and "Volgende"
  - Volgende:
    - overview of all "Taken", "Toetsen", "Meebrengen" for next planned lesson (next day or next day after weekend/holiday)
  - Meebrengen:
    - within list "Meebrengen", the title will be the item to bring, while the description will be the course info
    - for other lists, the title contains the course name and the description contains the details of the action
  - The Todo items can be checked, same items appearing in list "Volgende" will also be checked in specific Todo lists
  - Only items left todo are listed, past items will automatically be removed of all Todo lists


## Status

### Not working:
- login with parent account
- 2FA with bith date, no other 2FA authentication method supported yet


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

## Example usage:

TODO
