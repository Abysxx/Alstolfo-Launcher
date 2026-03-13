import os
from setuptools import setup

APP = ['main.py']

OPTIONS = {
    # Prevent Mac from injecting launch args unexpectedly
    'argv_emulation': False,

    # Makes sure ALL PyQt5 stuff is packaged (critical)
    'site_packages': True,

    # Force-includes Qt modules that py2app frequently misses
    'includes': [
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtSvg',
        'sip'
    ],

    # Include these plugin folders (mandatory for PyQt5)
    'qt_plugins': [
        'platforms',
        'imageformats',
        'iconengines',
        'sqldrivers',
        'mediaservice',
        'styles'
    ],

    # Stupid resource error
    #'resources': [
    #    'Bin',
    #    'Game'
    #],
    'resources': [],

    # Hardened plist for production
    'plist': {
        'CFBundleName':               'Alstolfo Launcher',
        'CFBundleDisplayName':        'Alstolfo Launcher',
        'CFBundleVersion':            '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement':                False,

        # Prevent macOS quarantine issues
        'NSHighResolutionCapable':    True,

        # Allow network / LAN access
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        },

        # Silence false unsigned library warnings
        'CSResourcesFileMapped': True,
    },

    # Reduce app crashes caused by partially loaded frameworks
    'optimize': 1
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
