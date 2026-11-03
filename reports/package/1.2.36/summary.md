# Android 1.2.36 startup fix

The 1.2.35 application archive omitted candidate_puzzles.py. Its original archive reproduced ModuleNotFoundError in Android, before the application reached its main loop. Adding this module restored startup.

1.2.36 includes and verifies its bytecode. The exact final private.tar payload was installed in an x86_64 Android test shell with a matching Python bytecode ABI and reached the home screen without a traceback. The delivered APK is arm64-v8a; no physical arm64 phone was connected. Fifteen page checks passed after adding the missing module. Three root-module packaging regression checks passed. APK version, signature, and 743 packaged files passed verification. Signing key matches 1.2.35.
