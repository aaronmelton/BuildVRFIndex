# BuildVRFIndex.py #
---

## BuildVRFIndex v0.0.6-alpha (2013-08-28) ##
* Added functionality to specify configFile from the command line.
* Updated README.md

## BuildVRFIndex v0.0.5-alpha (2013-08-23) ##
* Removed Python modules not required by this application.
* Minor corrections to output spacing.

## BuildVRFIndex v0.0.4-alpha (2013-08-20) ##
* Added additional comments to code, configFile, routerFile.
* Added configFile functionality to give application the ability to retrieve
  user-specified settings from a config file.  Application use now extended
  such that the list of routers, index and respective paths can be specified
  in the file.  Application can also use configured username and password.

## BuildVRFIndex v0.0.3-alpha (2013-08-16) ##
* Changed the configFile format in such a way that a single configFile
  can be used for my different VRF applications.
* Updated error messages so they reflect the actual filename as read
  from the configFile.
* Rewrote "Building index..." message so it does not take up most of the
  screen when working with a large batch of routers.
* Updated example configFile output to reflect new changes in configFile format.

## BuildVRFIndex v0.0.2-alpha (2013-08-15) ##
* Added instructions for creating a password to settings.cfg
* Cleaned up module importing
* Removed quotations around variables in function that writes the example
  configFile (not necessary)

## BuildVRFIndex v0.0.1-alpha (2013-08-15) ##
* Alphabetized functions

## BuildVRFIndex v0.0.1-alpha (2013-08-14) ##
* Initial commit
