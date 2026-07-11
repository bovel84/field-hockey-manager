[app]

title = Field Hockey Manager
package.name = fieldhockeymanager
package.domain = org.fhm

source.dir = .
source.include_exts = py,json,kv,txt,png,atlas

version = 1.0.0

requirements = python3,kivy,pyjnius,sqlite3

orientation = portrait

android.api = 34
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.skip_update = False
android.accept_sdk_license = True
android.build_tools_version = 34.0.0

fullscreen = 0

android.permissions =

log_level = 2

source.exclude_dirs = tests, .venv, __pycache__, .git, .specify, .vscode, .github, .pytest_cache

[build]
builder = python3
compiler = cython