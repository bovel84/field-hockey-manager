[app]

# App name
title = Field Hockey Manager

# Package name
package.name = fieldhockeymanager

# Package domain
package.domain = org.fhm

# Source code
source.dir = .
source.include_exts = py,json,db,kv,txt,png

# Version
version = 1.0.0

# Requirements
requirements = kivy,sqlite3,pygame,Pillow

# Orientation
orientation = portrait

# Android SDK/API
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

# Build options
fullscreen = 0

# Permissions (none extra needed)
android.permissions =

# Log
log_level = 2

# Exclude unnecessary files
source.exclude_dirs = tests, .venv, __pycache__, .git, .specify, .vscode, .github

[build]
builder = python3
compiler = cython