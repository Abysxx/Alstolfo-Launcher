# Alstolfo-Launcher
A Roblox Downloader For Macos. 
Made for bypassing my schools network restrictions, with socks5 proxies

## How to build

1. Install Requirements
```
pip install -r requirements.txt
```
2. Run setup.py
```
python setup.py py2app
```
3. Move the Bin and Game folders to the app's content folder
```
mv ./Bin/ ./dist/Alstolfo\ Launcher/Contents/
mv ./Game/ ./dist/Alstolfo\ Launcher/Contents/
```
4. Replace the default icns file with Alstolfo's
```
mv ./Extras/PythonApplet.icns ./dist/Alstolfo\ Launcher/Contents/Resources/
```
5. Done
Feel free to move it out of the dist folder and delete any extra stuff.

## Additonal setup
You need to get your roblox .binarycookies file as not everything is bypassed with the proxy
This should be at ~/Library/HTTPStorages/com.roblox.RobloxPlayer.binarycookies

So you'll either need to login on another macbook or get them from your iphone
the only way i know how to get them from your iphone is to jailbreak it and get the file in (RobloxDataPath)/Library/Cookies/Cookies.binarycookies
and rename it and replace it to the one on your macbook

## How to use
**Start** 
- This attempts to launch the roblox game with the selected proxy or will auto select one.
- This works by attempting to launch the game via exporting the proxy to the console then checking for a debug message roblox displays when it launches
- If it fails to launch or the app is deleted it will trigger an error
- If the user has the option "Default To Auto" this will automaticly switch to the auto proxy setting instead of having the user manually click it on fail
  
**Update/Re-Install**
- This gets the newest version of roblox's MacOS application and attempts to sets it up in a way that bypasses my schools detection for roblox
  
**Manage Proxies**
- This is an editor where you can add and delete proxies
- The Refresh button just reloads the editor
- The get button gets new proxies
- The test button tests the connection of the proxies
- The "get test" button just does both of these back to back
- Tested proxies are sorted by connection speed to roblox
- The drop down allows you to set your prefered proxy
  
**Settings**
- These are on the main menu as toggles
- The "Default To Auto" is explained in the Start section
- "Close On Launch" closes Alstolfo Launcher on a sucessful start
- "Auto Update" updates the game every time the user starts it (NOT RECOMMENDED)


