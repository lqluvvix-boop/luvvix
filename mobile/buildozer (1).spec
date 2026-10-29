[app]
title = Luvvix
package.name = luvvix
package.domain = ru.mirea
source.dir = .
source.include_exts = py,kv,png,jpg,json,atlas
source.exclude_dirs = .buildozer, bin, __pycache__, tests
version = 1.0

# Клиент не использует сторонних HTTP-библиотек (urllib из стандартной библиотеки).
# Версии закреплены под стабильный релиз python-for-android (см. p4a.branch ниже).
requirements = python3,kivy==2.3.0,charset_normalizer==3.3.2

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.allow_backup = False
android.accept_sdk_license = True
android.ndk = 25b

# Стабильный релиз сборщика вместо постоянно меняющейся ветки master
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
